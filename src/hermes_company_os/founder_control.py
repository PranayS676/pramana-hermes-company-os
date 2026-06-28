from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES


def project_founder_control_summary(
    *,
    project: Mapping[str, Any],
    active_stage: Mapping[str, Any] | None,
    latest_artifact: Mapping[str, Any] | None,
    founder_decisions: Sequence[Mapping[str, Any]],
    agent_work_items: Sequence[Mapping[str, Any]],
    task_stage_approved: bool,
    kanban_ready: bool,
    codex_execution: Mapping[str, Any],
    multi_agent_review: Mapping[str, Any],
) -> dict[str, Any]:
    stage_label = _stage_label(active_stage)
    stage_status = _stage_status(active_stage)
    artifact_status = _artifact_status(latest_artifact, active_stage)
    open_decisions = [
        decision
        for decision in founder_decisions
        if decision.get("status") not in RESOLVED_DECISION_STATUSES
    ]
    queue_blockers = [
        item for item in agent_work_items if item.get("status") == "blocked"
    ]
    founder_queue_items = [
        item for item in agent_work_items if item.get("founder_action_required")
    ]
    codex_status = _codex_signal(codex_execution)
    review_status = _review_signal(multi_agent_review)
    kanban_gate_open = kanban_ready and task_stage_approved
    next_action = _next_action(
        project=project,
        stage_label=stage_label,
        artifact_status=artifact_status,
        has_artifact=bool(latest_artifact),
        open_decision_count=len(open_decisions),
        queue_blocker_count=len(queue_blockers),
        kanban_gate_open=kanban_gate_open,
        codex_execution=codex_execution,
        multi_agent_review=multi_agent_review,
    )

    return {
        "next_action": next_action,
        "signals": [
            {
                "label": "Current stage",
                "value": stage_label,
                "detail": stage_status,
                "status": _signal_status(stage_status),
                "href": "#current-stage",
            },
            {
                "label": "Artifact state",
                "value": artifact_status,
                "detail": "latest artifact" if latest_artifact else "not generated",
                "status": _signal_status(artifact_status),
                "href": "#artifact-preview",
            },
            {
                "label": "Open decisions",
                "value": f"{len(open_decisions)} open decision"
                if len(open_decisions) == 1
                else f"{len(open_decisions)} open decisions",
                "detail": "founder input required" if open_decisions else "none waiting",
                "status": "needed" if open_decisions else "ready",
                "href": f"/decisions?project_id={project['id']}",
            },
            {
                "label": "Queue blockers",
                "value": f"{len(queue_blockers)} blocker"
                if len(queue_blockers) == 1
                else f"{len(queue_blockers)} blockers",
                "detail": (
                    f"{len(founder_queue_items)} founder handoff"
                    if len(founder_queue_items) == 1
                    else f"{len(founder_queue_items)} founder handoffs"
                ),
                "status": "blocked" if queue_blockers else "ready",
                "href": f"/queue?project_id={project['id']}",
            },
            codex_status,
            review_status,
        ],
    }


def _next_action(
    *,
    project: Mapping[str, Any],
    stage_label: str,
    artifact_status: str,
    has_artifact: bool,
    open_decision_count: int,
    queue_blocker_count: int,
    kanban_gate_open: bool,
    codex_execution: Mapping[str, Any],
    multi_agent_review: Mapping[str, Any],
) -> dict[str, str]:
    project_id = project["id"]
    codex_state = codex_execution.get("execution") or {}
    codex_runner = codex_execution.get("runner") or {}
    review_aggregate = (multi_agent_review.get("aggregate") or {})

    if open_decision_count:
        return {
            "label": "Review project decisions",
            "detail": f"{open_decision_count} open decision"
            if open_decision_count == 1
            else f"{open_decision_count} open decisions",
            "href": f"/decisions?project_id={project_id}",
            "cta_label": "Open project decisions",
            "icon": "gavel",
            "status": "needed",
        }
    if queue_blocker_count:
        return {
            "label": "Clear queue blockers",
            "detail": f"{queue_blocker_count} blocked queue item needs ownership.",
            "href": f"/queue?project_id={project_id}&status=blocked",
            "cta_label": "Open project queue",
            "icon": "list-checks",
            "status": "blocked",
        }
    if not has_artifact or artifact_status in {"ready", "needs_revision", "blocked"}:
        return {
            "label": f"Generate {stage_label} artifact",
            "detail": "Create the current stage artifact before founder review.",
            "href": "#current-stage",
            "cta_label": "Go to stage actions",
            "icon": "play",
            "status": "ready",
        }
    if artifact_status == "draft":
        return {
            "label": f"Approve {stage_label} artifact",
            "detail": "Review the generated artifact and either approve it or request revision.",
            "href": "#current-stage",
            "cta_label": "Review artifact",
            "icon": "check-circle-2",
            "status": "needed",
        }
    if multi_agent_review.get("ready") and review_aggregate.get("status") != "approved":
        return {
            "label": "Run multi-agent review",
            "detail": "Reviewer records are ready after approved code plan and acceptance package.",
            "href": "#multi-agent-review",
            "cta_label": "Open review loop",
            "icon": "scan-search",
            "status": "needed",
        }
    if codex_state.get("approval_request_allowed"):
        return {
            "label": "Request Codex execution approval",
            "detail": "Founder approval is required before implementation branch work starts.",
            "href": "#codex-execution",
            "cta_label": "Open Codex gate",
            "icon": "shield-check",
            "status": "needed",
        }
    if codex_runner.get("queue_request_allowed"):
        return {
            "label": "Queue Codex runner",
            "detail": "Founder approval can now be consumed into an execution audit record.",
            "href": "#codex-execution",
            "cta_label": "Open Codex gate",
            "icon": "list-start",
            "status": "ready",
        }
    if kanban_gate_open:
        return {
            "label": "Push workflow to Kanban",
            "detail": "Task artifacts are approved and Kanban verification is ready.",
            "href": "#kanban-push",
            "cta_label": "Open Kanban gate",
            "icon": "kanban-square",
            "status": "ready",
        }
    return {
        "label": "Continue staged review",
        "detail": "Advance the current approved workflow gate before external execution.",
        "href": "#current-stage",
        "cta_label": "Open current stage",
        "icon": "arrow-right",
        "status": "manual",
    }


def _codex_signal(codex_execution: Mapping[str, Any]) -> dict[str, str]:
    execution = codex_execution.get("execution") or {}
    runner = codex_execution.get("runner") or {}
    latest_run = runner.get("latest_run") or {}
    if latest_run.get("status") == "completed":
        value = "worktree ready"
        status = "ready"
        detail = latest_run.get("runner_mode", "git worktree")
    elif runner.get("queue_open"):
        value = "queued"
        status = "queued"
        detail = "runner audit exists"
    elif execution.get("founder_approved_for_execution"):
        value = "approved"
        status = "ready"
        detail = "runner queue available"
    elif execution.get("approval_request_open"):
        value = "approval open"
        status = "needed"
        detail = "founder decision pending"
    elif execution.get("ready_for_founder_approval"):
        value = "approval ready"
        status = "needed"
        detail = "code plan and acceptance approved"
    else:
        value = "locked"
        status = "manual"
        detail = "waiting on plan and acceptance"
    return {
        "label": "Codex handoff",
        "value": value,
        "detail": detail,
        "status": status,
        "href": "#codex-execution",
    }


def _review_signal(multi_agent_review: Mapping[str, Any]) -> dict[str, str]:
    aggregate = multi_agent_review.get("aggregate") or {}
    value = aggregate.get("status") or "blocked"
    reviewer_count = aggregate.get("reviewer_count", 0)
    required_count = aggregate.get("required_reviewer_count", 5)
    return {
        "label": "Review loop",
        "value": value,
        "detail": f"{reviewer_count}/{required_count} reviewer records",
        "status": _signal_status(value),
        "href": "#multi-agent-review",
    }


def _stage_label(stage: Mapping[str, Any] | None) -> str:
    if not stage:
        return "Not started"
    return str(
        stage.get("label")
        or stage.get("name")
        or str(stage.get("stage_id", "stage")).replace("_", " ").title()
    )


def _stage_status(stage: Mapping[str, Any] | None) -> str:
    if not stage:
        return "not started"
    return str(stage.get("status") or "ready")


def _artifact_status(
    artifact: Mapping[str, Any] | None,
    stage: Mapping[str, Any] | None,
) -> str:
    if artifact:
        return str(artifact.get("status") or "draft")
    if stage:
        return str(stage.get("status") or "ready")
    return "ready"


def _signal_status(value: str) -> str:
    normalized = value.lower().replace(" ", "_")
    if normalized in {"approved", "ready", "completed", "done"}:
        return "ready"
    if normalized in {"blocked", "failed"}:
        return "blocked"
    if normalized in {"needed", "needs_review", "draft", "approval_open", "pending"}:
        return "needed"
    if normalized in {"queued", "planned"}:
        return "queued"
    return "manual"
