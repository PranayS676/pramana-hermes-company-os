from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from hermes_company_os.fingerprints import fingerprint_json as _fingerprint_json
from hermes_company_os.fingerprints import fingerprint_text as _fingerprint_text
from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.product_wizard import STAGE_CONTRACTS
from hermes_company_os.secret_guard import assert_no_secret_values

CODEX_EXECUTION_SCHEMA = "codex_project_execution_package_v1"
CODEX_EXECUTION_DECISION_SOURCE = "codex_project_execution"
CODEX_EXECUTION_DECISION_TYPE = "external_action_approval"
CODEX_EXECUTION_STAGE_ID = "acceptance"
CODEX_EXECUTION_RUNNER_MODE = "source_only_disabled"
CODEX_GIT_WORKTREE_RUNNER_MODE = "git_worktree"
ACTIVE_CODEX_RUN_STATUSES = frozenset({"queued", "blocked"})


def codex_execution_package(repository, project_id: str) -> dict[str, Any]:
    project = repository.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")

    code_plan_artifact = repository.latest_project_stage_artifact(
        project_id,
        "code_plan",
    )
    acceptance_artifact = repository.latest_project_stage_artifact(
        project_id,
        "acceptance",
    )
    approval = codex_execution_approval(repository, project_id)
    latest_run = repository.latest_codex_execution_run(project_id)
    project_slug = _safe_slug(project["name"] or project_id)
    code_plan_gate = _artifact_gate("code_plan", "Code plan", code_plan_artifact)
    acceptance_gate = _artifact_gate(
        "acceptance",
        "Acceptance package",
        acceptance_artifact,
    )
    artifact_missing_gates = [
        gate["id"]
        for gate in (code_plan_gate, acceptance_gate)
        if not gate["ready"]
    ]
    founder_approved = approval["status"] == "approved"
    approval_request_open = bool(
        approval["id"] and approval["status"] not in RESOLVED_DECISION_STATUSES
    )
    ready_for_founder_approval = not artifact_missing_gates and not (
        founder_approved or approval_request_open
    )
    approval_gate = _approval_gate(
        approval,
        ready_for_founder_approval=ready_for_founder_approval,
    )
    missing_gates = list(artifact_missing_gates)
    if not founder_approved:
        missing_gates.append("founder_execution_approval")

    payload = {
        "schema": CODEX_EXECUTION_SCHEMA,
        "package_id": f"codex-execution:{project_id}:v1",
        "project": {
            "id": project_id,
            "name": project["name"],
            "status": project["status"],
        },
        "execution": {
            "mode": "manual_codex_project_execution",
            "source_of_truth": "dashboard",
            "external_execution_enabled": False,
            "ready_for_founder_approval": ready_for_founder_approval,
            "approval_request_open": approval_request_open,
            "founder_approved_for_execution": founder_approved,
            "ready_for_execution": not missing_gates,
            "decision_id": approval["id"],
            "decision_status": approval["status"],
            "approval_request_allowed": ready_for_founder_approval,
            "policy": (
                "This package previews a Codex implementation handoff. It does not "
                "create branches, create worktrees, spawn chats, or run commands."
            ),
        },
        "runner": _runner_state(
            latest_run,
            founder_approved=founder_approved,
            approval_request_open=approval_request_open,
            artifact_missing_gates=artifact_missing_gates,
        ),
        "approval_gates": {
            "code_plan": code_plan_gate,
            "acceptance": acceptance_gate,
            "founder_execution_approval": approval_gate,
        },
        "missing_gates": missing_gates,
        "source_artifacts": [
            artifact
            for artifact in (
                _artifact_summary(code_plan_artifact),
                _artifact_summary(acceptance_artifact),
            )
            if artifact
        ],
        "branch_plan": {
            "branch_name": f"codex/{project_slug}/implementation-v1",
            "worktree_path": f"../codex-worktrees/{project_slug}-implementation-v1",
            "create_branch": False,
            "create_worktree": False,
        },
        "workstreams": _workstreams(),
        "command_preview": _command_preview(project_slug),
        "acceptance_checklist": _acceptance_checklist(),
    }
    assert_no_secret_values({"codex_execution_package": json.dumps(payload, sort_keys=True)})
    return payload


def queue_codex_execution_run(repository, project_id: str) -> dict[str, Any]:
    package = codex_execution_package(repository, project_id)
    runner = package["runner"]
    if not runner["queue_request_allowed"]:
        raise ValueError(runner["blocker"])
    decision = repository.get_founder_decision(package["execution"]["decision_id"])
    if decision is None or decision["status"] != "approved":
        raise ValueError("Founder approval is required before queuing Codex execution.")

    run_id = f"codex-run-{uuid4().hex[:10]}"
    source_artifact_ids = [artifact["id"] for artifact in package["source_artifacts"]]
    approval_snapshot = _approval_snapshot(decision)
    audit = _run_audit(
        package=package,
        run_id=run_id,
        approval_snapshot=approval_snapshot,
    )
    repository.create_codex_execution_run(
        run_id=run_id,
        project_id=project_id,
        decision_id=decision["id"],
        package_id=package["package_id"],
        status="queued",
        runner_mode=CODEX_EXECUTION_RUNNER_MODE,
        external_execution_enabled=False,
        branch_name=package["branch_plan"]["branch_name"],
        worktree_path=package["branch_plan"]["worktree_path"],
        source_artifact_ids=source_artifact_ids,
        command_preview=package["command_preview"],
        approval_snapshot=approval_snapshot,
        audit=audit,
    )
    run = repository.get_codex_execution_run(run_id)
    assert run is not None
    assert_no_secret_values({"codex_execution_run": json.dumps(run, sort_keys=True)})
    return run


def start_codex_execution_git_worktree(
    repository,
    project_id: str,
    *,
    enabled: bool,
    workspace_root: Path,
    worktree_root: Path,
) -> dict[str, Any]:
    if not enabled:
        raise ValueError(
            "Real Codex execution is disabled. Set "
            "HERMES_CODEX_EXECUTION_ENABLED=true only after founder approval."
        )
    run = repository.latest_codex_execution_run(project_id)
    if run is None:
        raise ValueError("Queue Codex execution before starting the real runner.")
    if run["status"] != "queued":
        raise ValueError(f"Codex execution run {run['id']} is {run['status']}.")

    repo_root = Path(workspace_root).expanduser().resolve()
    _assert_git_repository(repo_root)
    resolved_worktree_root = _resolve_worktree_root(repo_root, worktree_root)
    planned_leaf = Path(run["worktree_path"]).name
    worktree_path = (resolved_worktree_root / planned_leaf).resolve()
    _assert_child_path(worktree_path, resolved_worktree_root)
    if worktree_path.exists():
        raise ValueError(f"Codex worktree path already exists: {worktree_path}")
    resolved_worktree_root.mkdir(parents=True, exist_ok=True)

    command = [
        "git",
        "-C",
        str(repo_root),
        "worktree",
        "add",
        "-b",
        run["branch_name"],
        str(worktree_path),
        "HEAD",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    audit = _git_worktree_audit(
        run=run,
        repo_root=repo_root,
        worktree_path=worktree_path,
        command=command,
        result=result,
    )
    if result.returncode != 0:
        repository.update_codex_execution_run(
            run["id"],
            status="failed",
            runner_mode=CODEX_GIT_WORKTREE_RUNNER_MODE,
            external_execution_enabled=True,
            audit=audit,
            error=_safe_runner_output(result.stderr or result.stdout),
        )
        raise ValueError("Git worktree runner failed. Inspect the run audit.")
    repository.update_codex_execution_run(
        run["id"],
        status="completed",
        runner_mode=CODEX_GIT_WORKTREE_RUNNER_MODE,
        external_execution_enabled=True,
        audit=audit,
    )
    updated = repository.get_codex_execution_run(run["id"])
    assert updated is not None
    assert_no_secret_values({"codex_execution_run": json.dumps(updated, sort_keys=True)})
    return updated


def codex_execution_markdown(package: Mapping[str, Any]) -> str:
    gates = package["approval_gates"]
    source_artifacts = package["source_artifacts"]
    command_preview = package["command_preview"]
    workstreams = package["workstreams"]
    checklist = package["acceptance_checklist"]
    runner = package["runner"]
    latest_run = runner.get("latest_run") or {}
    lines = [
        f"# Codex Project Execution Package: {package['project']['name']}",
        "",
        f"- Schema: `{package['schema']}`",
        f"- Package ID: `{package['package_id']}`",
        f"- Project: `{package['project']['id']}`",
        f"- Source of truth: `{package['execution']['source_of_truth']}`",
        "- External execution started: `false`",
        (
            "- Ready for founder approval: "
            f"`{str(package['execution']['ready_for_founder_approval']).lower()}`"
        ),
        (
            "- Founder approved for execution: "
            f"`{str(package['execution']['founder_approved_for_execution']).lower()}`"
        ),
        (
            "- Ready for execution handoff: "
            f"`{str(package['execution']['ready_for_execution']).lower()}`"
        ),
        "",
        "No branch or worktree is created by this export.",
        "",
        "## Runner State",
        "",
        f"- Runner mode: `{runner['mode']}`",
        f"- Queue request allowed: `{str(runner['queue_request_allowed']).lower()}`",
        f"- Queue open: `{str(runner['queue_open']).lower()}`",
        "- External execution enabled: `false`",
    ]
    if latest_run:
        lines.extend(
            [
                f"- Latest run: `{latest_run['id']}`",
                f"- Latest run status: `{latest_run['status']}`",
                f"- Approval consumed: `{latest_run['decision_id']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Approval Gates",
            "",
        ]
    )
    for gate in gates.values():
        lines.append(
            f"- `{gate['id']}`: {gate['status']} - {gate['detail']}"
        )
    lines.extend(["", "## Source Artifacts", ""])
    if source_artifacts:
        for artifact in source_artifacts:
            lines.append(
                f"- `{artifact['stage_id']}`: {artifact['id']} "
                f"v{artifact['version']} ({artifact['status']})"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Branch And Worktree Plan", ""])
    lines.append(f"- Branch: `{package['branch_plan']['branch_name']}`")
    lines.append(f"- Worktree: `{package['branch_plan']['worktree_path']}`")
    lines.append("- Create branch automatically: `false`")
    lines.append("- Create worktree automatically: `false`")
    lines.extend(["", "## Command Preview", ""])
    for command in command_preview:
        lines.append(f"- `{command['command']}`")
    lines.extend(["", "## Workstreams", ""])
    for stream in workstreams:
        lines.append(
            f"- `{stream['id']}` owned by `{stream['owner_agent_id']}`: "
            f"{stream['objective']}"
        )
    lines.extend(["", "## Acceptance Checklist", ""])
    for item in checklist:
        lines.append(f"- `{item['id']}`: {item['label']}")
    lines.append("")
    return "\n".join(lines)


def codex_execution_approval(repository, project_id: str) -> dict[str, str]:
    decisions = [
        decision
        for decision in repository.list_founder_decisions(
            project_id=project_id,
            decision_type=CODEX_EXECUTION_DECISION_TYPE,
        )
        if decision["source"] == CODEX_EXECUTION_DECISION_SOURCE
    ]
    approved = next(
        (decision for decision in decisions if decision["status"] == "approved"),
        None,
    )
    if approved:
        return {
            "id": approved["id"],
            "status": approved["status"],
            "stage_id": approved.get("stage_id") or "",
            "artifact_id": approved.get("artifact_id") or "",
        }
    open_decision = next(
        (
            decision
            for decision in decisions
            if decision["status"] not in RESOLVED_DECISION_STATUSES
        ),
        None,
    )
    if open_decision:
        return {
            "id": open_decision["id"],
            "status": open_decision["status"],
            "stage_id": open_decision.get("stage_id") or "",
            "artifact_id": open_decision.get("artifact_id") or "",
        }
    return {"id": "", "status": "", "stage_id": "", "artifact_id": ""}


def _runner_state(
    latest_run: Mapping[str, Any] | None,
    *,
    founder_approved: bool,
    approval_request_open: bool,
    artifact_missing_gates: list[str],
) -> dict[str, Any]:
    run_summary = _run_summary(latest_run)
    has_run = bool(latest_run)
    queue_open = bool(
        latest_run and latest_run["status"] in ACTIVE_CODEX_RUN_STATUSES
    )
    queue_request_allowed = (
        founder_approved and not artifact_missing_gates and not has_run
    )
    if queue_open:
        blocker = f"Codex execution is already queued in {latest_run['id']}."
    elif has_run:
        blocker = f"Codex execution already has run evidence in {latest_run['id']}."
    elif artifact_missing_gates:
        blocker = (
            "Approve required artifacts before queuing Codex execution: "
            + ", ".join(artifact_missing_gates)
            + "."
        )
    elif not founder_approved:
        blocker = "Founder approval is required before queuing Codex execution."
    elif approval_request_open:
        blocker = "Founder approval is still pending."
    else:
        blocker = ""
    return {
        "mode": CODEX_EXECUTION_RUNNER_MODE,
        "external_execution_enabled": False,
        "queue_request_allowed": queue_request_allowed,
        "queue_open": queue_open,
        "latest_run": run_summary,
        "blocker": blocker,
        "policy": (
            "Queueing records approval consumption and source-only runner intent. "
            "It does not run Git, create worktrees, or start Codex processes."
        ),
    }


def _run_summary(run: Mapping[str, Any] | None) -> dict[str, Any]:
    if not run:
        return {}
    audit = run.get("audit") or {}
    approval = audit.get("approval_consumption") or {}
    return {
        "id": run["id"],
        "status": run["status"],
        "runner_mode": run["runner_mode"],
        "external_execution_enabled": bool(run["external_execution_enabled"]),
        "decision_id": run["decision_id"],
        "branch_name": run["branch_name"],
        "worktree_path": run["worktree_path"],
        "approval_consumption": approval,
        "created_at": run["created_at"],
    }


def _approval_snapshot(decision: Mapping[str, Any]) -> dict[str, str]:
    return {
        "decision_id": decision["id"],
        "status": decision["status"],
        "source": decision["source"],
        "decision_type": decision["decision_type"],
        "project_id": decision.get("project_id") or "",
        "stage_id": decision.get("stage_id") or "",
        "artifact_id": decision.get("artifact_id") or "",
        "resolved_at": decision.get("resolved_at") or "",
        "updated_at": decision.get("updated_at") or "",
    }


def _run_audit(
    *,
    package: Mapping[str, Any],
    run_id: str,
    approval_snapshot: Mapping[str, str],
) -> dict[str, Any]:
    package_fingerprint = _fingerprint_json(package)
    command_fingerprints = [
        {
            "id": command["id"],
            "sha256": _fingerprint_text(command["command"]),
            "runs_automatically": bool(command["runs_automatically"]),
        }
        for command in package["command_preview"]
    ]
    return {
        "schema": "codex_execution_run_audit_v1",
        "immutable": True,
        "run_id": run_id,
        "package_id": package["package_id"],
        "package_fingerprint": {
            "sha256": package_fingerprint,
            "schema": package["schema"],
        },
        "approval_consumption": {
            "decision_id": approval_snapshot["decision_id"],
            "decision_status": approval_snapshot["status"],
            "status": "consumed",
            "consumed_by_run_id": run_id,
            "source": approval_snapshot["source"],
        },
        "source_artifacts": [
            {
                "id": artifact["id"],
                "stage_id": artifact["stage_id"],
                "version": artifact["version"],
                "status": artifact["status"],
            }
            for artifact in package["source_artifacts"]
        ],
        "branch_plan": {
            "branch_name": package["branch_plan"]["branch_name"],
            "worktree_path": package["branch_plan"]["worktree_path"],
            "create_branch": False,
            "create_worktree": False,
        },
        "command_fingerprints": command_fingerprints,
        "post_queue_review": {
            "status": "awaiting_founder_or_operator_review",
            "external_execution_enabled": False,
            "next_gate": "explicit real Codex runner implementation approval",
        },
    }


def _git_worktree_audit(
    *,
    run: Mapping[str, Any],
    repo_root: Path,
    worktree_path: Path,
    command: list[str],
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    audit = dict(run["audit"])
    stdout = _safe_runner_output(result.stdout)
    stderr = _safe_runner_output(result.stderr)
    audit["git_worktree"] = {
        "status": "branch_ready" if result.returncode == 0 else "failed",
        "repo_root": str(repo_root),
        "worktree_path": str(worktree_path),
        "branch_name": run["branch_name"],
        "returncode": result.returncode,
        "command_fingerprint": {
            "sha256": _fingerprint_text(" ".join(command)),
            "argv": command,
        },
        "stdout": stdout,
        "stderr": stderr,
    }
    audit["post_queue_review"] = {
        "status": "git_worktree_ready" if result.returncode == 0 else "git_worktree_failed",
        "external_execution_enabled": True,
        "next_gate": "manual Codex implementation worktree review",
    }
    assert_no_secret_values({"codex_git_worktree_audit": json.dumps(audit, sort_keys=True)})
    return audit


def _assert_git_repository(repo_root: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Codex workspace root is not a Git repository: {repo_root}")
    discovered = Path(result.stdout.strip()).resolve()
    if discovered != repo_root:
        raise ValueError(f"Codex workspace root must be the Git root: {repo_root}")


def _resolve_worktree_root(repo_root: Path, worktree_root: Path) -> Path:
    root = Path(worktree_root).expanduser()
    if not root.is_absolute():
        root = repo_root / root
    return root.resolve()


def _assert_child_path(path: Path, parent: Path) -> None:
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"Codex worktree path escapes configured root: {path}") from exc


def _safe_runner_output(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    assert_no_secret_values({"codex_runner_output": cleaned})
    return cleaned[:1200]


def _artifact_gate(
    gate_id: str,
    label: str,
    artifact: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if artifact is None:
        return {
            "id": gate_id,
            "label": label,
            "status": "missing",
            "ready": False,
            "artifact_id": "",
            "detail": f"Generate and approve the {label.lower()} first.",
        }
    ready = artifact["status"] == "approved"
    return {
        "id": gate_id,
        "label": label,
        "status": artifact["status"],
        "ready": ready,
        "artifact_id": artifact["id"],
        "version": artifact["version"],
        "detail": (
            f"{label} artifact {artifact['id']} v{artifact['version']} is approved."
            if ready
            else f"{label} artifact exists but is {artifact['status']}."
        ),
    }


def _approval_gate(
    approval: Mapping[str, str],
    *,
    ready_for_founder_approval: bool,
) -> dict[str, Any]:
    if approval["status"] == "approved":
        status = "approved"
        detail = f"Founder approved Codex execution in {approval['id']}."
        ready = True
    elif approval["id"]:
        status = approval["status"]
        detail = f"Founder approval is pending in {approval['id']}."
        ready = False
    elif ready_for_founder_approval:
        status = "requestable"
        detail = "Code plan and acceptance package are approved; request founder approval."
        ready = False
    else:
        status = "not_requested"
        detail = "Founder approval can be requested after required artifacts are approved."
        ready = False
    return {
        "id": "founder_execution_approval",
        "label": "Founder Codex execution approval",
        "status": status,
        "ready": ready,
        "decision_id": approval["id"],
        "detail": detail,
    }


def _artifact_summary(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    metadata = artifact.get("json") or {}
    return {
        "id": artifact["id"],
        "stage_id": artifact["stage_id"],
        "status": artifact["status"],
        "version": artifact["version"],
        "title": metadata.get("title", artifact["stage_id"]),
        "owner_agent_id": artifact["owner_agent_id"],
    }


def _workstreams() -> list[dict[str, Any]]:
    code_plan = STAGE_CONTRACTS["code_plan"]
    acceptance = STAGE_CONTRACTS["acceptance"]
    return [
        {
            "id": "backend-implementation",
            "owner_agent_id": code_plan.owner_agent_id,
            "supporting_agent_ids": ["engineering-manager"],
            "objective": "Implement the backend/API/data portions of the approved code plan.",
        },
        {
            "id": "frontend-experience",
            "owner_agent_id": "frontend-engineer",
            "supporting_agent_ids": ["product-manager", "qa-critic"],
            "objective": "Implement the founder-facing UI flow and responsive states.",
        },
        {
            "id": "cloud-and-runtime",
            "owner_agent_id": "cloud-infra-agent",
            "supporting_agent_ids": ["backend-engineer"],
            "objective": "Prepare local runtime, configuration, and deployment guardrails.",
        },
        {
            "id": "test-and-acceptance",
            "owner_agent_id": acceptance.owner_agent_id,
            "supporting_agent_ids": list(acceptance.supporting_agent_ids),
            "objective": "Turn the acceptance package into automated and manual verification.",
        },
    ]


def _command_preview(project_slug: str) -> list[dict[str, Any]]:
    branch = f"codex/{project_slug}/implementation-v1"
    worktree = f"../codex-worktrees/{project_slug}-implementation-v1"
    return [
        {
            "id": "create_branch",
            "command": f"git switch -c {branch}",
            "runs_automatically": False,
        },
        {
            "id": "prepare_worktree",
            "command": f"git worktree add {worktree} {branch}",
            "runs_automatically": False,
        },
        {
            "id": "start_codex",
            "command": f"codex --worktree {worktree}",
            "runs_automatically": False,
        },
        {
            "id": "verify",
            "command": "py -3.11 -m poetry run pytest",
            "runs_automatically": False,
        },
    ]


def _acceptance_checklist() -> list[dict[str, str]]:
    return [
        {
            "id": "approved_code_plan",
            "label": "Code plan artifact is approved and linked.",
        },
        {
            "id": "approved_acceptance_package",
            "label": "Acceptance artifact is approved and linked.",
        },
        {
            "id": "founder_execution_approval",
            "label": "Founder explicitly approves Codex execution start.",
        },
        {
            "id": "tdd_verification",
            "label": "Implementation starts from tests or documents the test rationale.",
        },
        {
            "id": "no_secret_scan",
            "label": "Changed files and generated outputs pass a no-secret scan.",
        },
        {
            "id": "review_before_push",
            "label": "Founder-visible summary and verification evidence are reviewed before push.",
        },
    ]


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return (slug or "project")[:48].strip("-") or "project"
