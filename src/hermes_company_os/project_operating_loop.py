from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.secret_guard import assert_no_secret_values

PROJECT_OPERATING_LOOP_SCHEMA = "project_operating_loop_v1"
PROJECT_EXTERNAL_DISPATCH_PREVIEW_SCHEMA = "project_external_dispatch_preview_v1"
PROJECT_EXTERNAL_DISPATCH_AUDIT_SCHEMA = "project_external_dispatch_audit_v1"
EXTERNAL_DISPATCH_DECISION_SOURCE = "external_dispatch_preview"
EXTERNAL_DISPATCH_DECISION_TYPE = "external_action_approval"
EXTERNAL_DISPATCH_STAGE_ID = "external_operating_loop"
EXTERNAL_DISPATCH_AUDIT_EVENT_TYPE = "external_dispatch_preview_audit_consumed"


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
    approval = external_dispatch_approval(repository, project_id)
    latest_audit = latest_external_dispatch_audit(repository, project_id)
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
        "approval": _dispatch_approval_state(
            approval=approval,
            ready=operating_loop_ready,
            latest_audit=latest_audit,
        ),
        "audit": _dispatch_audit_state(
            approval=approval,
            ready=operating_loop_ready,
            latest_audit=latest_audit,
        ),
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


def request_external_dispatch_approval(repository, project_id: str) -> str:
    package = project_external_dispatch_preview_package(repository, project_id)
    approval = package["approval"]
    if not approval["request_allowed"]:
        raise ValueError(approval["blocker"])
    preview_fingerprint = _fingerprint_json(_preview_snapshot(package))
    item_count = package["queue"]["item_count"]
    decision_id = repository.create_founder_decision(
        title=f"Approve external dispatch preview for {package['project']['name']}",
        urgency="urgent",
        decision_type=EXTERNAL_DISPATCH_DECISION_TYPE,
        source=EXTERNAL_DISPATCH_DECISION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id=EXTERNAL_DISPATCH_STAGE_ID,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if dispatch approval blocks active execution.",
        context=(
            f"Approve the reviewed external dispatch preview for {package['project']['name']}. "
            "This approval does not send Slack, Telegram, or Kanban messages."
        ),
        evidence=(
            f"Preview items: {item_count}. Preview SHA256: {preview_fingerprint}. "
            "External dispatch remains disabled and requires a later live connector gate."
        ),
        requires_founder_approval=True,
    )
    return decision_id


def consume_external_dispatch_preview_approval(repository, project_id: str) -> dict:
    package = project_external_dispatch_preview_package(repository, project_id)
    audit_state = package["audit"]
    if not audit_state["consume_allowed"]:
        raise ValueError(audit_state["blocker"])
    decision = repository.get_founder_decision(package["approval"]["id"])
    if decision is None or decision["status"] != "approved":
        raise ValueError("Founder approval is required.")
    audit = _external_dispatch_audit(package=package, decision=decision)
    event_id = repository.create_audit_event(
        project_id=project_id,
        event_type=EXTERNAL_DISPATCH_AUDIT_EVENT_TYPE,
        status="consumed",
        actor_agent_id="chief-of-staff",
        source_table="founder_decisions",
        source_id=decision["id"],
        summary=(
            "External dispatch preview approval consumed into immutable no-send "
            "audit evidence."
        ),
        payload={
            "audit": audit,
            "decision_id": decision["id"],
            "preview_sha256": audit["preview_fingerprint"]["sha256"],
            "external_dispatch_enabled": False,
            "real_send_allowed": False,
        },
    )
    events = repository.list_audit_events(
        project_id=project_id,
        event_type=EXTERNAL_DISPATCH_AUDIT_EVENT_TYPE,
        limit=1,
    )
    event = events[0] if events else {"id": event_id, "payload": {"audit": audit}}
    assert_no_secret_values({"external_dispatch_audit": json.dumps(event, sort_keys=True)})
    return event


def external_dispatch_approval(repository, project_id: str) -> dict:
    decisions = [
        decision
        for decision in repository.list_founder_decisions(
            project_id=project_id,
            decision_type=EXTERNAL_DISPATCH_DECISION_TYPE,
        )
        if decision["source"] == EXTERNAL_DISPATCH_DECISION_SOURCE
    ]
    approved = next(
        (decision for decision in decisions if decision["status"] == "approved"),
        None,
    )
    if approved:
        return _approval_reference(approved)
    open_decision = next(
        (
            decision
            for decision in decisions
            if decision["status"] not in RESOLVED_DECISION_STATUSES
        ),
        None,
    )
    if open_decision:
        return _approval_reference(open_decision)
    return {
        "id": "",
        "status": "",
        "stage_id": "",
        "artifact_id": "",
        "request_open": False,
        "founder_approved": False,
    }


def latest_external_dispatch_audit(repository, project_id: str) -> dict:
    events = repository.list_audit_events(
        project_id=project_id,
        event_type=EXTERNAL_DISPATCH_AUDIT_EVENT_TYPE,
        limit=1,
    )
    if not events:
        return {}
    event = events[0]
    audit = (event.get("payload") or {}).get("audit") or {}
    return {
        "event_id": event["id"],
        "status": event["status"],
        "schema": audit.get("schema", ""),
        "preview_fingerprint": audit.get("preview_fingerprint", {}),
        "approval_consumption": audit.get("approval_consumption", {}),
        "post_run_review": audit.get("post_run_review", {}),
        "created_at": event.get("created_at", ""),
    }


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


def _dispatch_approval_state(
    *,
    approval: Mapping,
    ready: bool,
    latest_audit: Mapping,
) -> dict:
    request_open = bool(approval.get("request_open"))
    founder_approved = bool(approval.get("founder_approved"))
    request_allowed = ready and not request_open and not founder_approved and not latest_audit
    if latest_audit:
        blocker = "Dispatch preview approval already consumed."
    elif not ready:
        blocker = "External operating loop must be ready before dispatch approval."
    elif request_open:
        blocker = "Dispatch approval request is already open."
    elif founder_approved:
        blocker = "Dispatch approval is approved and ready for audit consumption."
    else:
        blocker = ""
    return {
        **dict(approval),
        "request_allowed": request_allowed,
        "request_open": request_open,
        "founder_approved": founder_approved,
        "blocker": blocker,
    }


def _dispatch_audit_state(
    *,
    approval: Mapping,
    ready: bool,
    latest_audit: Mapping,
) -> dict:
    founder_approved = bool(approval.get("founder_approved"))
    consume_allowed = ready and founder_approved and not latest_audit
    if latest_audit:
        blocker = "Dispatch preview approval already consumed."
    elif not ready:
        blocker = "External operating loop must be ready before audit consumption."
    elif not founder_approved:
        blocker = "Founder approval is required."
    else:
        blocker = ""
    return {
        "consume_allowed": consume_allowed,
        "blocker": blocker,
        "latest": dict(latest_audit),
        "policy": (
            "Consuming approval records immutable preview evidence only. It does "
            "not send Slack, Telegram, or Kanban messages."
        ),
    }


def _approval_reference(decision: Mapping) -> dict:
    status = decision["status"]
    return {
        "id": decision["id"],
        "status": status,
        "stage_id": decision.get("stage_id") or "",
        "artifact_id": decision.get("artifact_id") or "",
        "request_open": status not in RESOLVED_DECISION_STATUSES,
        "founder_approved": status == "approved",
    }


def _external_dispatch_audit(
    *,
    package: Mapping,
    decision: Mapping,
) -> dict:
    snapshot = _preview_snapshot(package)
    item_fingerprints = [
        {
            "id": item["id"],
            "platform": item["platform"],
            "action": item["action"],
            "sha256": _fingerprint_json(item),
            "command_sha256": _fingerprint_text(item["command_preview"]),
            "dispatch_enabled": bool(item["dispatch_enabled"]),
            "runs_automatically": bool(item["runs_automatically"]),
        }
        for item in package["items"]
    ]
    return {
        "schema": PROJECT_EXTERNAL_DISPATCH_AUDIT_SCHEMA,
        "immutable": True,
        "project_id": package["project"]["id"],
        "preview_fingerprint": {
            "sha256": _fingerprint_json(snapshot),
            "schema": package["schema"],
        },
        "approval_consumption": {
            "decision_id": decision["id"],
            "decision_status": decision["status"],
            "status": "consumed",
            "source": decision["source"],
            "decision_type": decision["decision_type"],
            "stage_id": decision.get("stage_id") or "",
        },
        "item_fingerprints": item_fingerprints,
        "post_run_review": {
            "status": "dispatch_preview_audited_no_send",
            "external_dispatch_enabled": False,
            "real_send_allowed": False,
            "next_gate": "separate live connector runner approval",
        },
    }


def _preview_snapshot(package: Mapping) -> dict:
    return {
        "schema": package["schema"],
        "project": package["project"],
        "policy": package["policy"],
        "readiness": package["readiness"],
        "queue": package["queue"],
        "items": package["items"],
    }


def _fingerprint_json(value: Mapping | Sequence) -> str:
    return _fingerprint_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _fingerprint_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
