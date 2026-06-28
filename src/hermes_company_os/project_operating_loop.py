from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from hermes_company_os.secret_guard import assert_no_secret_values

PROJECT_OPERATING_LOOP_SCHEMA = "project_operating_loop_v1"
PROJECT_EXTERNAL_DISPATCH_PREVIEW_SCHEMA = "project_external_dispatch_preview_v1"


def project_operating_loop_package(repository, project_id: str) -> dict:
    project = repository.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")
    setup_inputs = repository.list_setup_inputs()
    setup_values = {item["key"]: item["value"] for item in setup_inputs}
    integrations = repository.list_integrations()
    secret_requirements = repository.list_secret_requirements()
    messaging_checks = repository.list_messaging_checks()
    kanban_checks = repository.list_kanban_checks()
    workflow_items = repository.list_project_workflow_items(project_id)
    wizard_stages = repository.list_project_wizard_stages(project_id)

    lanes = [
        _slack_lane(setup_inputs, integrations, secret_requirements, messaging_checks),
        _telegram_lane(setup_values, integrations, secret_requirements, messaging_checks),
        _kanban_lane(repository, workflow_items, wizard_stages, kanban_checks),
    ]
    blockers = [
        blocker
        for lane in lanes
        for blocker in lane["blockers"]
        if blocker.strip()
    ]
    ready = all(lane["status"] in {"ready", "linked"} for lane in lanes)
    payload = {
        "schema": PROJECT_OPERATING_LOOP_SCHEMA,
        "project": {
            "id": project["id"],
            "name": project["name"],
            "status": project["status"],
        },
        "policy": {
            "dashboard_source_of_truth": True,
            "external_dispatch_enabled": False,
            "slack_primary": True,
            "telegram_urgent_only": True,
            "kanban_source_of_truth": True,
            "dispatch_mode": "manual_review_only",
        },
        "aggregate": {
            "status": "ready" if ready else "blocked",
            "ready": ready,
            "blocker_count": len(blockers),
        },
        "lanes": lanes,
        "next_actions": _next_actions(lanes),
    }
    assert_no_secret_values({"project_operating_loop": json.dumps(payload, sort_keys=True)})
    return payload


def project_external_dispatch_preview_package(repository, project_id: str) -> dict:
    operating_loop = project_operating_loop_package(repository, project_id)
    workflow_items = repository.list_project_workflow_items(project_id)
    operating_loop_ready = bool(operating_loop["aggregate"]["ready"])
    items = [
        _slack_dispatch_preview(operating_loop),
        _telegram_dispatch_preview(operating_loop),
        *_kanban_dispatch_previews(operating_loop, workflow_items),
    ]
    ready_items = [item for item in items if item["status"] == "ready_for_review"]
    blocked_items = [item for item in items if item["status"] == "blocked"]
    payload = {
        "schema": PROJECT_EXTERNAL_DISPATCH_PREVIEW_SCHEMA,
        "project": operating_loop["project"],
        "policy": {
            "external_dispatch_enabled": False,
            "manual_review_required": True,
            "real_send_allowed": False,
            "preview_only": True,
            "approval_gate": "founder_review_required_before_live_dispatch",
        },
        "readiness": {
            "operating_loop_status": operating_loop["aggregate"]["status"],
            "operating_loop_ready": operating_loop_ready,
            "blocker_count": operating_loop["aggregate"]["blocker_count"],
        },
        "queue": {
            "status": "ready_for_review" if operating_loop_ready else "blocked",
            "item_count": len(items),
            "preview_item_count": len(items),
            "sendable_item_count": 0,
            "ready_item_count": len(ready_items),
            "blocked_item_count": len(blocked_items),
        },
        "items": items,
        "next_actions": _dispatch_preview_next_actions(
            operating_loop=operating_loop,
            ready=operating_loop_ready,
            project_id=project_id,
        ),
    }
    assert_no_secret_values(
        {"project_external_dispatch_preview": json.dumps(payload, sort_keys=True)}
    )
    return payload


def _slack_lane(
    setup_inputs: Sequence[Mapping],
    integrations: Sequence[Mapping],
    secret_requirements: Sequence[Mapping],
    messaging_checks: Sequence[Mapping],
) -> dict:
    required_inputs = [
        item
        for item in setup_inputs
        if item["group_name"] == "slack"
        and item["required"]
        and item["secret_policy"] == "non_secret"
    ]
    completed_inputs = [item for item in required_inputs if item["value"].strip()]
    checks = [item for item in messaging_checks if item["platform"] == "slack"]
    verified_checks = [item for item in checks if item["status"] == "verified"]
    requirements = [
        item for item in secret_requirements if item["category"] == "slack"
    ]
    open_requirements = [
        item for item in requirements if item["status"] not in {"loaded", "verified"}
    ]
    integration_items = [
        item for item in integrations if item["category"] == "slack"
    ]
    blockers = []
    if len(completed_inputs) < len(required_inputs):
        blockers.append("Slack channel/member IDs are incomplete.")
    if open_requirements:
        blockers.append("Slack profile credentials are still marked external/not loaded.")
    if len(verified_checks) < len(checks):
        blockers.append("Slack messaging verification is incomplete.")
    status = "ready" if not blockers else "blocked"
    return {
        "id": "slack",
        "label": "Slack routine coordination",
        "status": status,
        "role": "Primary workspace for routine cross-agent coordination.",
        "dispatch_mode": "manual_review_only",
        "setup_href": "/setup#messaging-verification",
        "required_input_count": len(required_inputs),
        "completed_input_count": len(completed_inputs),
        "open_secret_count": len(open_requirements),
        "verified_check_count": len(verified_checks),
        "total_check_count": len(checks),
        "integration_count": len(integration_items),
        "blockers": blockers,
    }


def _telegram_lane(
    setup_values: Mapping[str, str],
    integrations: Sequence[Mapping],
    secret_requirements: Sequence[Mapping],
    messaging_checks: Sequence[Mapping],
) -> dict:
    checks = [item for item in messaging_checks if item["platform"] == "telegram"]
    verified_checks = [item for item in checks if item["status"] == "verified"]
    requirements = [
        item for item in secret_requirements if item["category"] == "telegram"
    ]
    open_requirements = [
        item for item in requirements if item["status"] not in {"loaded", "verified"}
    ]
    integration_items = [
        item for item in integrations if item["category"] == "telegram"
    ]
    blockers = []
    if not setup_values.get("founder_telegram_user_id", "").strip():
        blockers.append("Founder Telegram user ID is not captured.")
    if open_requirements:
        blockers.append("Chief of Staff Telegram credential is still external/not loaded.")
    if len(verified_checks) < len(checks):
        blockers.append("Telegram urgent-alert verification is incomplete.")
    status = "ready" if not blockers else "blocked"
    return {
        "id": "telegram",
        "label": "Telegram urgent founder alerts",
        "status": status,
        "role": "Chief of Staff only, urgent founder escalation path.",
        "owner_agent_id": "chief-of-staff",
        "urgent_only": True,
        "dispatch_mode": "chief_of_staff_urgent_only",
        "setup_href": "/setup#telegram-recipient-import",
        "open_secret_count": len(open_requirements),
        "verified_check_count": len(verified_checks),
        "total_check_count": len(checks),
        "integration_count": len(integration_items),
        "blockers": blockers,
    }


def _kanban_lane(
    repository,
    workflow_items: Sequence[Mapping],
    wizard_stages: Sequence[Mapping],
    kanban_checks: Sequence[Mapping],
) -> dict:
    linked_items = [item for item in workflow_items if item["kanban_task_id"]]
    pending_items = [
        item
        for item in workflow_items
        if item["task_id"] and not item["kanban_task_id"]
    ]
    task_stage = next(
        (stage for stage in wizard_stages if stage["stage_id"] == "tasks"),
        None,
    )
    task_stage_approved = bool(task_stage and task_stage["status"] == "approved")
    verification_ready = repository.kanban_verification_ready()
    blockers = []
    if not task_stage_approved:
        blockers.append("Tasks stage must be approved before Kanban handoff.")
    if not verification_ready:
        blockers.append("Hermes Kanban verification is incomplete.")
    if not workflow_items:
        blockers.append("Project workflow items are not generated yet.")
    if not blockers and workflow_items and not pending_items:
        status = "linked"
    elif not blockers:
        status = "ready"
    else:
        status = "blocked"
    verified_checks = [item for item in kanban_checks if item["status"] == "verified"]
    return {
        "id": "kanban",
        "label": "Kanban source of truth",
        "status": status,
        "role": "Shared work board after founder-approved task planning.",
        "dispatch_mode": "idempotent_task_create_only",
        "setup_href": "/setup#kanban-verification",
        "task_stage_approved": task_stage_approved,
        "verification_ready": verification_ready,
        "workflow_task_count": len(workflow_items),
        "linked_task_count": len(linked_items),
        "pending_task_count": len(pending_items),
        "verified_check_count": len(verified_checks),
        "total_check_count": len(kanban_checks),
        "blockers": blockers,
    }


def _next_actions(lanes: Sequence[Mapping]) -> list[dict[str, str]]:
    actions = []
    for lane in lanes:
        if lane["status"] in {"ready", "linked"}:
            continue
        blockers = lane.get("blockers") or []
        actions.append(
            {
                "lane_id": lane["id"],
                "label": f"Unblock {lane['label']}",
                "href": lane["setup_href"],
                "detail": blockers[0] if blockers else "Review setup readiness.",
            }
        )
    return actions


def _slack_dispatch_preview(operating_loop: Mapping) -> dict:
    project = operating_loop["project"]
    lane = _lane_by_id(operating_loop, "slack")
    return {
        "id": "slack-standup-preview",
        "platform": "slack",
        "lane_id": "slack",
        "label": "Slack standup preview",
        "status": _preview_status(lane),
        "action": "post_message_preview",
        "owner_agent_id": "chief-of-staff",
        "target_input_key": "slack_channel_agent_standup",
        "target_label": "agent standup channel",
        "message_preview": (
            f"Project {project['name']}: founder-reviewed workflow handoff is ready "
            "for routine agent coordination. Review the dashboard before any "
            "external dispatch."
        ),
        "command_preview": (
            "slack.chat.postMessage channel=${slack_channel_agent_standup} "
            "text=<reviewed project handoff>"
        ),
        "dispatch_enabled": False,
        "runs_automatically": False,
        "manual_review_required": True,
        "blockers": lane["blockers"],
    }


def _telegram_dispatch_preview(operating_loop: Mapping) -> dict:
    project = operating_loop["project"]
    lane = _lane_by_id(operating_loop, "telegram")
    return {
        "id": "telegram-urgent-alert-preview",
        "platform": "telegram",
        "lane_id": "telegram",
        "label": "Telegram urgent alert preview",
        "status": _preview_status(lane),
        "action": "send_urgent_alert_preview",
        "owner_agent_id": "chief-of-staff",
        "target_input_key": "founder_telegram_user_id",
        "target_label": "founder urgent recipient",
        "urgent_only": True,
        "requires_urgent_condition": True,
        "message_preview": (
            f"Urgent founder alert preview for {project['name']}: a decision, "
            "failure, or schedule risk needs founder attention. Chief of Staff "
            "reviews before send."
        ),
        "command_preview": (
            "telegram.sendMessage chat_id=${founder_telegram_user_id} "
            "text=<urgent founder alert>"
        ),
        "dispatch_enabled": False,
        "runs_automatically": False,
        "manual_review_required": True,
        "blockers": lane["blockers"],
    }


def _kanban_dispatch_previews(
    operating_loop: Mapping,
    workflow_items: Sequence[Mapping],
) -> list[dict]:
    lane = _lane_by_id(operating_loop, "kanban")
    previews = []
    for item in workflow_items:
        if item["kanban_task_id"] or not item["task_id"]:
            continue
        title = str(item["title"])
        task_id = str(item["task_id"])
        owner_agent_id = str(item["owner_agent_id"])
        previews.append(
            {
                "id": f"kanban-task-create-preview-{task_id}",
                "platform": "hermes-kanban",
                "lane_id": "kanban",
                "label": "Kanban task create preview",
                "status": _preview_status(lane),
                "action": "create_task_preview",
                "owner_agent_id": owner_agent_id,
                "owner_name": item.get("owner_name", owner_agent_id),
                "workflow_item_id": item["id"],
                "task_id": task_id,
                "idempotency_key": task_id,
                "title": title,
                "message_preview": (
                    f"Create Hermes Kanban task for {item.get('owner_name', owner_agent_id)}: "
                    f"{title}"
                ),
                "command_preview": (
                    f"hermes kanban create {json.dumps(title)} "
                    f"--assignee {owner_agent_id} --idempotency-key {task_id} --json"
                ),
                "dispatch_enabled": False,
                "runs_automatically": False,
                "manual_review_required": True,
                "blockers": lane["blockers"],
            }
        )
    return previews


def _dispatch_preview_next_actions(
    *,
    operating_loop: Mapping,
    ready: bool,
    project_id: str,
) -> list[dict[str, str]]:
    if ready:
        return [
            {
                "label": "Review previews",
                "href": f"/projects/{project_id}#external-dispatch-preview",
                "detail": (
                    "Founder reviews Slack, Telegram, and Kanban previews before "
                    "any live connector work is allowed."
                ),
            }
        ]
    return [
        {
            "label": action["label"],
            "href": action["href"],
            "detail": action["detail"],
        }
        for action in operating_loop["next_actions"]
    ]


def _lane_by_id(operating_loop: Mapping, lane_id: str) -> Mapping:
    return next(lane for lane in operating_loop["lanes"] if lane["id"] == lane_id)


def _preview_status(lane: Mapping) -> str:
    if lane["status"] in {"ready", "linked"}:
        return "ready_for_review"
    return "blocked"
