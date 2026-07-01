from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from hermes_company_os.external_dispatch import (
    command_boundary_summary,
    external_dispatch_command_contract,
)
from hermes_company_os.fingerprints import fingerprint_json as _fingerprint_json
from hermes_company_os.fingerprints import fingerprint_text as _fingerprint_text
from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.secret_guard import assert_no_secret_values

PROJECT_OPERATING_LOOP_SCHEMA = "project_operating_loop_v1"
PROJECT_EXTERNAL_DISPATCH_PREVIEW_SCHEMA = "project_external_dispatch_preview_v1"
PROJECT_EXTERNAL_DISPATCH_AUDIT_SCHEMA = "project_external_dispatch_audit_v1"
PROJECT_EXTERNAL_DISPATCH_RUNNER_AUDIT_SCHEMA = (
    "project_external_dispatch_runner_audit_v1"
)
EXTERNAL_DISPATCH_DECISION_SOURCE = "external_dispatch_preview"
EXTERNAL_DISPATCH_DECISION_TYPE = "external_action_approval"
EXTERNAL_DISPATCH_STAGE_ID = "external_operating_loop"
EXTERNAL_DISPATCH_AUDIT_EVENT_TYPE = "external_dispatch_preview_audit_consumed"
EXTERNAL_DISPATCH_RUNNER_BLOCKED_EVENT_TYPE = "external_dispatch_runner_blocked"
EXTERNAL_DISPATCH_RUNNER_COMPLETED_EVENT_TYPE = "external_dispatch_runner_completed"


def project_operating_loop_package(
    repository: RepositoryProtocol, project_id: str
) -> dict:
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


def project_external_dispatch_preview_package(
    repository: RepositoryProtocol,
    project_id: str,
    *,
    external_dispatch_enabled: bool = False,
) -> dict:
    operating_loop = project_operating_loop_package(repository, project_id)
    workflow_items = repository.list_project_workflow_items(project_id)
    setup_values = repository.setup_input_map()
    operating_loop_ready = bool(operating_loop["aggregate"]["ready"])
    approval = external_dispatch_approval(repository, project_id)
    latest_audit = latest_external_dispatch_audit(repository, project_id)
    latest_runner = latest_external_dispatch_runner_audit(repository, project_id)
    items = [
        _slack_dispatch_preview(operating_loop, setup_values),
        _telegram_dispatch_preview(operating_loop, setup_values),
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
        "command_boundary": command_boundary_summary(
            enabled=external_dispatch_enabled,
            runner_label="external_dispatch_runner",
        ),
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
        "runner": _dispatch_runner_state(
            external_dispatch_enabled=external_dispatch_enabled,
            latest_audit=latest_audit,
            latest_runner=latest_runner,
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


def run_external_dispatch_runner(
    repository,
    project_id: str,
    *,
    enabled: bool,
    runner,
    runner_label: str = "external_dispatch_runner",
) -> dict:
    package = project_external_dispatch_preview_package(
        repository,
        project_id,
        external_dispatch_enabled=enabled,
    )
    runner_state = package["runner"]
    latest_runner = runner_state["latest"]
    if latest_runner and latest_runner["status"] == "succeeded":
        raise ValueError("External dispatch runner already completed.")
    if not package["audit"]["latest"]:
        raise ValueError("Dispatch approval audit is required before running dispatch.")
    if not enabled:
        event = _record_external_dispatch_runner_event(
            repository,
            package=package,
            event_type=EXTERNAL_DISPATCH_RUNNER_BLOCKED_EVENT_TYPE,
            status="blocked",
            runner_label=runner_label,
            dispatch_attempted=False,
            results=[],
            blocker="External dispatch runner is disabled.",
        )
        assert_no_secret_values({"external_dispatch_runner_blocked": json.dumps(event)})
        raise ValueError("External dispatch runner is disabled.")
    if runner is None:
        event = _record_external_dispatch_runner_event(
            repository,
            package=package,
            event_type=EXTERNAL_DISPATCH_RUNNER_BLOCKED_EVENT_TYPE,
            status="blocked",
            runner_label=runner_label,
            dispatch_attempted=False,
            results=[],
            blocker="External dispatch runner is enabled but no adapter is configured.",
        )
        assert_no_secret_values({"external_dispatch_runner_blocked": json.dumps(event)})
        raise ValueError("External dispatch runner is enabled but no adapter is configured.")

    results = []
    for item in package["items"]:
        results.append(
            _dispatch_item(runner, item, repository=repository, project_id=project_id)
        )
    status = (
        "succeeded"
        if all(result.get("status") == "succeeded" for result in results)
        else "failed"
    )
    event = _record_external_dispatch_runner_event(
        repository,
        package=package,
        event_type=EXTERNAL_DISPATCH_RUNNER_COMPLETED_EVENT_TYPE,
        status=status,
        runner_label=runner_label,
        dispatch_attempted=True,
        results=results,
        blocker="",
    )
    assert_no_secret_values({"external_dispatch_runner_completed": json.dumps(event)})
    return event


def latest_external_dispatch_runner_audit(repository, project_id: str) -> dict:
    events = repository.list_audit_events(project_id=project_id, limit=50)
    event = next(
        (
            item
            for item in events
            if item["event_type"]
            in {
                EXTERNAL_DISPATCH_RUNNER_BLOCKED_EVENT_TYPE,
                EXTERNAL_DISPATCH_RUNNER_COMPLETED_EVENT_TYPE,
            }
        ),
        None,
    )
    if not event:
        return {}
    audit = (event.get("payload") or {}).get("runner_audit") or {}
    return {
        "event_id": event["id"],
        "event_type": event["event_type"],
        "status": event["status"],
        "schema": audit.get("schema", ""),
        "runner_label": audit.get("runner_label", ""),
        "external_dispatch_enabled": bool(audit.get("external_dispatch_enabled")),
        "dispatch_attempted": bool(audit.get("dispatch_attempted")),
        "result_count": int(audit.get("result_count") or 0),
        "blocker": audit.get("blocker", ""),
        "command_boundary": dict(audit.get("command_boundary") or {}),
        "command_fingerprints": list(audit.get("command_fingerprints") or []),
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
        "setup_href": "/setup/messaging#messaging-verification",
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
        "setup_href": "/setup/inputs#telegram-recipient-import",
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
        "setup_href": "/setup/verification#kanban-verification",
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


def _slack_dispatch_preview(operating_loop: Mapping, setup_values: Mapping[str, str]) -> dict:
    project = operating_loop["project"]
    lane = _lane_by_id(operating_loop, "slack")
    target_input_key = "slack_channel_agent_standup"
    item = {
        "id": "slack-standup-preview",
        "platform": "slack",
        "lane_id": "slack",
        "label": "Slack standup preview",
        "status": _preview_status(lane),
        "action": "post_message_preview",
        "owner_agent_id": "chief-of-staff",
        "target_input_key": target_input_key,
        "target_value": str(setup_values.get(target_input_key, "")).strip(),
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
    return _with_adapter_contract(item)


def _telegram_dispatch_preview(
    operating_loop: Mapping, setup_values: Mapping[str, str]
) -> dict:
    project = operating_loop["project"]
    lane = _lane_by_id(operating_loop, "telegram")
    target_input_key = "founder_telegram_user_id"
    item = {
        "id": "telegram-urgent-alert-preview",
        "platform": "telegram",
        "lane_id": "telegram",
        "label": "Telegram urgent alert preview",
        "status": _preview_status(lane),
        "action": "send_urgent_alert_preview",
        "owner_agent_id": "chief-of-staff",
        "target_input_key": target_input_key,
        "target_value": str(setup_values.get(target_input_key, "")).strip(),
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
    return _with_adapter_contract(item)


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
        preview = {
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
        previews.append(_with_adapter_contract(preview))
    return previews


def _with_adapter_contract(item: Mapping) -> dict:
    payload = dict(item)
    payload["adapter_contract"] = external_dispatch_command_contract(payload)
    return payload


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


def _dispatch_runner_state(
    *,
    external_dispatch_enabled: bool,
    latest_audit: Mapping,
    latest_runner: Mapping,
) -> dict:
    completed = latest_runner.get("status") == "succeeded"
    run_allowed = bool(external_dispatch_enabled and latest_audit and not completed)
    if completed:
        blocker = "External dispatch runner already completed."
    elif not latest_audit:
        blocker = "Dispatch approval audit is required before running dispatch."
    elif not external_dispatch_enabled:
        blocker = "External dispatch runner is disabled."
    else:
        blocker = ""
    return {
        "mode": "external_dispatch_runner",
        "external_dispatch_enabled": bool(external_dispatch_enabled),
        "run_allowed": run_allowed,
        "latest": dict(latest_runner),
        "blocker": blocker,
        "policy": (
            "The runner can execute only after founder approval is consumed into "
            "preview audit evidence and HERMES_EXTERNAL_DISPATCH_ENABLED is true."
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
            "contract_sha256": item["adapter_contract"]["contract_sha256"],
            "argv_sha256": item["adapter_contract"]["argv_sha256"],
            "command_boundary": item["adapter_contract"]["command_boundary"],
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


def _record_external_dispatch_runner_event(
    repository,
    *,
    package: Mapping,
    event_type: str,
    status: str,
    runner_label: str,
    dispatch_attempted: bool,
    results: Sequence[Mapping],
    blocker: str,
) -> dict:
    audit = _external_dispatch_runner_audit(
        package=package,
        runner_label=runner_label,
        dispatch_attempted=dispatch_attempted,
        results=results,
        blocker=blocker,
    )
    repository.create_audit_event(
        project_id=package["project"]["id"],
        event_type=event_type,
        status=status,
        actor_agent_id="chief-of-staff",
        source_table="audit_events",
        source_id=package["audit"]["latest"]["event_id"],
        summary=_runner_event_summary(status, dispatch_attempted, blocker),
        payload={
            "runner_audit": audit,
            "external_dispatch_enabled": audit["external_dispatch_enabled"],
            "dispatch_attempted": dispatch_attempted,
            "result_count": len(results),
        },
    )
    events = repository.list_audit_events(
        project_id=package["project"]["id"],
        event_type=event_type,
        limit=1,
    )
    return events[0]


def _external_dispatch_runner_audit(
    *,
    package: Mapping,
    runner_label: str,
    dispatch_attempted: bool,
    results: Sequence[Mapping],
    blocker: str,
) -> dict:
    item_fingerprints = [
        {
            "id": item["id"],
            "platform": item["platform"],
            "action": item["action"],
            "sha256": _fingerprint_json(item),
            "command_sha256": _fingerprint_text(item["command_preview"]),
            "contract_sha256": item["adapter_contract"]["contract_sha256"],
            "argv_sha256": item["adapter_contract"]["argv_sha256"],
            "command_boundary": item["adapter_contract"]["command_boundary"],
        }
        for item in package["items"]
    ]
    command_fingerprints = _command_fingerprints(package["items"])
    return {
        "schema": PROJECT_EXTERNAL_DISPATCH_RUNNER_AUDIT_SCHEMA,
        "immutable": True,
        "project_id": package["project"]["id"],
        "runner_label": runner_label,
        "external_dispatch_enabled": package["runner"]["external_dispatch_enabled"],
        "dispatch_attempted": dispatch_attempted,
        "blocker": blocker,
        "command_boundary": command_boundary_summary(
            enabled=package["runner"]["external_dispatch_enabled"],
            runner_label=runner_label,
        ),
        "approval_audit_event_id": package["audit"]["latest"]["event_id"],
        "preview_fingerprint": package["audit"]["latest"]["preview_fingerprint"],
        "item_fingerprints": item_fingerprints,
        "command_fingerprints": command_fingerprints,
        "result_count": len(results),
        "results": [dict(result) for result in results],
        "post_run_review": {
            "status": _runner_review_status(
                dispatch_attempted=dispatch_attempted,
                results=results,
            ),
            "next_gate": "review runner evidence before expanding automation",
            "no_live_send_attempted": not dispatch_attempted,
        },
    }


def _runner_review_status(
    *,
    dispatch_attempted: bool,
    results: Sequence[Mapping],
) -> str:
    if not dispatch_attempted:
        return "blocked"
    if all(result.get("status") == "succeeded" for result in results):
        return "external_dispatch_completed"
    return "external_dispatch_failed"


def _runner_event_summary(status: str, dispatch_attempted: bool, blocker: str) -> str:
    if status == "succeeded":
        return "External dispatch runner completed through configured adapter."
    if status == "failed":
        return "External dispatch runner completed with failed item results."
    if dispatch_attempted:
        return "External dispatch runner attempted dispatch and was blocked."
    return f"External dispatch runner blocked: {blocker}"


def _dispatch_item(runner, item: Mapping, *, repository, project_id: str) -> dict:
    """Dispatch one preview item through the enabled adapter, idempotently.

    Safety: before invoking the runner we check for an existing delivery row
    keyed by the item's stable idempotency key. If one exists we short-circuit
    with status ``skipped_duplicate`` and DO NOT call the runner again, so the
    same item is never sent twice. Only on a genuinely new key do we attempt the
    real send and then record an idempotent delivery row.
    """
    contract = item["adapter_contract"]
    idempotency_key = _delivery_idempotency_key(item)
    existing = repository.get_external_dispatch_delivery(idempotency_key)
    if existing is not None:
        skipped = {
            "status": "skipped_duplicate",
            "external_id": existing.get("external_id", ""),
            "detail": "Existing delivery found for idempotency key; no re-send.",
            "command_boundary": contract["command_boundary"],
            "command_sha256": contract["argv_sha256"],
            "contract_sha256": contract["contract_sha256"],
            "dry_run": contract["dry_run"],
            "idempotency_key": idempotency_key,
            "item_id": item["id"],
            "platform": item["platform"],
            "action": item["action"],
            "delivery_id": existing.get("id", ""),
        }
        assert_no_secret_values({"external_dispatch_result": json.dumps(skipped)})
        return skipped

    raw_result = (
        runner.dispatch(dict(item)) if hasattr(runner, "dispatch") else runner(dict(item))
    )
    if isinstance(raw_result, Mapping):
        normalized = dict(raw_result)
    else:
        normalized = {"status": "succeeded", "detail": str(raw_result)}
    normalized.setdefault("status", "succeeded")
    normalized.setdefault("external_id", "")
    normalized.setdefault("detail", "")
    normalized.setdefault("command_boundary", contract["command_boundary"])
    normalized.setdefault("command_sha256", contract["argv_sha256"])
    normalized.setdefault("contract_sha256", contract["contract_sha256"])
    normalized.setdefault("dry_run", contract["dry_run"])
    normalized["idempotency_key"] = idempotency_key
    normalized["item_id"] = item["id"]
    normalized["platform"] = item["platform"]
    normalized["action"] = item["action"]
    assert_no_secret_values({"external_dispatch_result": json.dumps(normalized)})
    delivery = repository.record_external_dispatch_delivery(
        idempotency_key=idempotency_key,
        project_id=project_id,
        item_id=str(item["id"]),
        platform=str(item["platform"]),
        action=str(item["action"]),
        command_boundary=str(contract["command_boundary"]),
        contract_sha256=str(contract["contract_sha256"]),
        argv_sha256=str(contract["argv_sha256"]),
        status=str(normalized["status"]),
        runner_label=str(normalized.get("runner_label", "")),
        external_id=str(normalized.get("external_id", "")),
        result=_delivery_result_snapshot(normalized),
    )
    normalized["delivery_id"] = delivery["id"]
    assert_no_secret_values({"external_dispatch_result": json.dumps(normalized)})
    return normalized


def _delivery_idempotency_key(item: Mapping) -> str:
    """Build a stable per-item idempotency key.

    Kanban items carry a native ``idempotency_key`` (the task id); reuse it so the
    dashboard key matches the native ``hermes kanban create --idempotency-key``.
    Slack/Telegram items have no native key, so derive a deterministic one from
    the contract argv fingerprint, which changes only if the command itself does.
    """
    native = str(item.get("idempotency_key", "")).strip()
    if native:
        return f"{item['platform']}:{native}"
    contract = item["adapter_contract"]
    return f"{item['platform']}:{item['id']}:{contract['argv_sha256']}"


def _delivery_result_snapshot(normalized: Mapping) -> dict:
    """Project the runner result down to non-secret, stored delivery fields."""
    return {
        "status": normalized.get("status", ""),
        "external_id": normalized.get("external_id", ""),
        "command_boundary": normalized.get("command_boundary", ""),
        "command_sha256": normalized.get("command_sha256", ""),
        "contract_sha256": normalized.get("contract_sha256", ""),
        "dry_run": bool(normalized.get("dry_run", True)),
        "returncode": normalized.get("returncode"),
        "timed_out": bool(normalized.get("timed_out", False)),
    }


def _command_fingerprints(items: Sequence[Mapping]) -> list[dict]:
    return [
        {
            "item_id": item["id"],
            "platform": item["platform"],
            "adapter": item["adapter_contract"]["adapter"],
            "command_kind": item["adapter_contract"]["command_kind"],
            "command_boundary": item["adapter_contract"]["command_boundary"],
            "contract_sha256": item["adapter_contract"]["contract_sha256"],
            "argv_sha256": item["adapter_contract"]["argv_sha256"],
            "dry_run": bool(item["adapter_contract"]["dry_run"]),
        }
        for item in items
    ]


def _preview_snapshot(package: Mapping) -> dict:
    return {
        "schema": package["schema"],
        "project": package["project"],
        "policy": package["policy"],
        "readiness": package["readiness"],
        "queue": package["queue"],
        "items": package["items"],
    }
