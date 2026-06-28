from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.product_wizard import STAGE_CONTRACTS
from hermes_company_os.secret_guard import assert_no_secret_values

CODEX_EXECUTION_SCHEMA = "codex_project_execution_package_v1"
CODEX_EXECUTION_DECISION_SOURCE = "codex_project_execution"
CODEX_EXECUTION_DECISION_TYPE = "external_action_approval"
CODEX_EXECUTION_STAGE_ID = "acceptance"


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


def codex_execution_markdown(package: Mapping[str, Any]) -> str:
    gates = package["approval_gates"]
    source_artifacts = package["source_artifacts"]
    command_preview = package["command_preview"]
    workstreams = package["workstreams"]
    checklist = package["acceptance_checklist"]
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
        "## Approval Gates",
        "",
    ]
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
