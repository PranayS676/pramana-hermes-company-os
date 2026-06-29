"""M7 live external dispatch: gated real-send command boundary + delivery records.

Safety contract under test:
- Real ``hermes`` is NEVER invoked here. The runner is always a fake injected
  via ``app.state.external_dispatch_runner`` (or a fake command runner injected
  into ``HermesExternalDispatchCommandAdapter``).
- A real send is impossible unless ``external_dispatch_enabled`` is true AND the
  four founder gates are satisfied (loop ready, approval requested + approved,
  approval consumed into audit). These tests assert the disabled-by-default path
  attempts no send and writes no delivery row.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from hermes_company_os.external_dispatch import (
    HermesExternalDispatchCommandAdapter,
    external_dispatch_command_contract,
)
from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

STRUCTURED_INTAKE = {
    "wizard_version": "product-wizard-v1",
    "name": "Atlas Brief",
    "product_category": "saas",
    "founder_idea": "AI due-diligence workspace for acquisition teams.",
    "target_audience": "Corporate development teams reviewing small acquisitions.",
    "current_alternative": "Shared docs, spreadsheets, and ad hoc chat threads.",
    "problem_statement": "Teams lose the thread across diligence notes, risks, and asks.",
    "desired_outcome": "A reviewed risk brief with assigned follow-up questions.",
    "launch_tier": "t0_internal",
    "deadline_pressure": "normal",
    "constraints": "Use mock data only; no live customer files in the public demo.",
    "non_goals": "Do not build an enterprise data-room connector in V1.",
    "success_metrics": "Reduce first-pass diligence synthesis time by 40 percent.",
}

WIZARD_STAGE_IDS = ["research", "prd", "architecture", "tasks", "code_plan", "acceptance"]


class RecordingDispatchRunner:
    """Fake dispatch adapter: records every call's argv and returns a send result.

    Stands in for the real ``HermesExternalDispatchCommandAdapter`` so the suite
    never shells out to a real ``hermes`` binary.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def dispatch(self, item: dict) -> dict:
        self.calls.append(item)
        contract = item["adapter_contract"]
        return {
            "status": "succeeded",
            "external_id": f"sent-{item['id']}",
            "detail": "Fake adapter accepted the real-form command.",
            "command_boundary": contract["command_boundary"],
            "command_sha256": contract["argv_sha256"],
            "contract_sha256": contract["contract_sha256"],
            "dry_run": contract["dry_run"],
            "runner_label": "recording_dispatch_runner",
        }


def app_and_client(tmp_path, *, external_dispatch_enabled: bool = False):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            external_dispatch_enabled=external_dispatch_enabled,
        )
    )
    return app, TestClient(app)


def create_structured_project(client: TestClient) -> str:
    response = client.post("/projects", data=STRUCTURED_INTAKE, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def generate_and_approve_current_stage(app, client: TestClient, project_id: str) -> str:
    current = app.state.repository.next_actionable_stage(project_id)
    assert current is not None
    stage_id = current["stage_id"]
    generated = client.post(
        f"/projects/{project_id}/stages/current/generate", follow_redirects=False
    )
    assert generated.status_code == 303, generated.text
    approved = client.post(
        f"/projects/{project_id}/stages/{stage_id}/approve", follow_redirects=False
    )
    assert approved.status_code == 303, approved.text
    return stage_id


def approve_until_stage(app, client, project_id: str, target_stage_id: str) -> None:
    for _ in range(len(WIZARD_STAGE_IDS)):
        stage_id = generate_and_approve_current_stage(app, client, project_id)
        if stage_id == target_stage_id:
            return
    raise AssertionError(f"Did not reach {target_stage_id}.")


def mark_external_loop_ready(app) -> None:
    repository = app.state.repository
    repository.update_setup_inputs(
        {
            "slack_workspace_name": "Pramana Hermes",
            "founder_slack_member_id": "U012FOUND",
            "slack_channel_founder_command": "C012FOUNDER",
            "slack_channel_agent_standup": "C012STANDUP",
            "slack_channel_product": "C012PRODUCT",
            "slack_channel_research": "C012RESEARCH",
            "slack_channel_engineering": "C012ENGINEER",
            "slack_channel_marketing": "C012MARKET",
            "slack_channel_qa_review": "C012QAREV",
            "founder_telegram_user_id": "123456789",
            "telegram_home_channel": "-1001234567890",
        }
    )
    for requirement in repository.list_secret_requirements():
        if requirement["category"] in {"slack", "telegram"}:
            repository.update_secret_requirement(
                requirement["id"],
                status="loaded",
                notes="Loaded externally for delivery readiness test.",
            )
    for check in repository.list_messaging_checks():
        repository.update_messaging_check(
            check["id"], status="verified", evidence="Verified in delivery test."
        )
    for check in repository.list_kanban_checks():
        repository.update_kanban_check(
            check["id"], status="verified", evidence="Verified in delivery test."
        )


def external_dispatch_decision(app, project_id: str) -> dict:
    decisions = app.state.repository.list_founder_decisions(
        project_id=project_id, decision_type="external_action_approval"
    )
    return next(
        item for item in decisions if item["source"] == "external_dispatch_preview"
    )


def approve_and_audit_external_dispatch(app, client, project_id: str) -> dict:
    client.post(
        f"/projects/{project_id}/external-dispatch-approval", follow_redirects=False
    )
    decision = external_dispatch_decision(app, project_id)
    app.state.repository.update_founder_decision(
        decision["id"],
        status="approved",
        decision="Founder approves the gated live external dispatch.",
        founder_confirmed=True,
    )
    response = client.post(
        f"/projects/{project_id}/external-dispatch-audit", follow_redirects=False
    )
    assert response.status_code == 303, response.text
    return decision


# --------------------------------------------------------------------------- #
# Corrected real command forms (no real hermes; just the built contract argv).
# --------------------------------------------------------------------------- #
def test_corrected_contracts_use_real_hermes_send_and_kanban_forms():
    slack = external_dispatch_command_contract(
        {
            "id": "slack-standup-preview",
            "platform": "slack",
            "action": "post_message_preview",
            "target_input_key": "slack_channel_agent_standup",
            "target_value": "C012STANDUP",
            "message_preview": "Reviewed project handoff is ready.",
            "command_preview": "slack post",
        }
    )
    telegram = external_dispatch_command_contract(
        {
            "id": "telegram-urgent-alert-preview",
            "platform": "telegram",
            "action": "send_urgent_alert_preview",
            "target_input_key": "founder_telegram_user_id",
            "target_value": "123456789",
            "message_preview": "Urgent founder alert.",
            "command_preview": "telegram send",
        }
    )
    kanban = external_dispatch_command_contract(
        {
            "id": "kanban-task-create-preview-task-abc",
            "platform": "hermes-kanban",
            "action": "create_task_preview",
            "owner_agent_id": "engineering-manager",
            "idempotency_key": "task-abc",
            "title": "Implement onboarding flow",
            "message_preview": "Create Hermes Kanban task.",
            "command_preview": "hermes kanban create",
        }
    )

    assert slack["argv"] == [
        "hermes",
        "send",
        "--to",
        "slack:C012STANDUP",
        "Reviewed project handoff is ready.",
    ]
    assert telegram["argv"] == [
        "hermes",
        "send",
        "--to",
        "telegram:123456789",
        "Urgent founder alert.",
    ]
    assert telegram["urgent_only"] is True
    assert kanban["argv"] == [
        "hermes",
        "kanban",
        "create",
        "Implement onboarding flow",
        "--assignee",
        "engineering-manager",
        "--idempotency-key",
        "task-abc",
        "--json",
    ]
    # No fictional `hermes dispatch` verb and no synthetic --dry-run anywhere.
    for contract in (slack, telegram, kanban):
        assert "dispatch" not in contract["argv"]
        assert "--dry-run" not in contract["argv"]
        assert len(contract["argv_sha256"]) == 64
        assert len(contract["contract_sha256"]) == 64
    assert (
        secret_violations(
            {
                "slack": json.dumps(slack, sort_keys=True),
                "telegram": json.dumps(telegram, sort_keys=True),
                "kanban": json.dumps(kanban, sort_keys=True),
            }
        )
        == []
    )


# --------------------------------------------------------------------------- #
# Disabled by default: no send attempted, no delivery row written.
# --------------------------------------------------------------------------- #
def test_disabled_by_default_writes_no_delivery_and_attempts_no_send(tmp_path):
    app, client = app_and_client(tmp_path)  # external_dispatch_enabled defaults off
    runner = RecordingDispatchRunner()
    app.state.external_dispatch_runner = runner
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    approve_and_audit_external_dispatch(app, client, project_id)

    response = client.post(
        f"/projects/{project_id}/external-dispatch-run", follow_redirects=False
    )
    deliveries = app.state.repository.list_external_dispatch_deliveries(project_id)

    assert response.status_code == 409
    assert "External dispatch runner is disabled" in response.json()["detail"]
    assert runner.calls == []
    assert deliveries == []


# --------------------------------------------------------------------------- #
# Enabled + approved: real-form argv built and one delivery recorded per item.
# --------------------------------------------------------------------------- #
def test_enabled_and_approved_records_one_delivery_per_item(tmp_path):
    app, client = app_and_client(tmp_path, external_dispatch_enabled=True)
    runner = RecordingDispatchRunner()
    app.state.external_dispatch_runner = runner
    app.state.external_dispatch_runner_label = "recording_dispatch_runner"
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    approve_and_audit_external_dispatch(app, client, project_id)
    preview = client.get(
        f"/projects/{project_id}/external-dispatch-preview.json"
    ).json()
    item_count = preview["queue"]["item_count"]

    response = client.post(
        f"/projects/{project_id}/external-dispatch-run", follow_redirects=False
    )
    deliveries = app.state.repository.list_external_dispatch_deliveries(project_id)
    events = app.state.repository.list_audit_events(
        project_id=project_id, event_type="external_dispatch_runner_completed"
    )
    runner_audit = events[0]["payload"]["runner_audit"]

    assert response.status_code == 303
    assert len(runner.calls) == item_count
    # The fake adapter received the corrected real-form argv (no fictional verbs).
    slack_call = next(c for c in runner.calls if c["platform"] == "slack")
    telegram_call = next(c for c in runner.calls if c["platform"] == "telegram")
    assert slack_call["adapter_contract"]["argv"][:4] == [
        "hermes",
        "send",
        "--to",
        "slack:C012STANDUP",
    ]
    assert telegram_call["adapter_contract"]["argv"][:4] == [
        "hermes",
        "send",
        "--to",
        "telegram:123456789",
    ]
    assert len(deliveries) == item_count
    assert {d["status"] for d in deliveries} == {"succeeded"}
    assert all(len(d["argv_sha256"]) == 64 for d in deliveries)
    assert all(len(d["contract_sha256"]) == 64 for d in deliveries)
    assert all(
        d["command_boundary"] == "hermes_command_boundary" for d in deliveries
    )
    # Kanban delivery keys carry the native idempotency key (the task id).
    kanban_deliveries = [d for d in deliveries if d["platform"] == "hermes-kanban"]
    assert kanban_deliveries
    assert all("task-" in d["idempotency_key"] for d in kanban_deliveries)
    assert runner_audit["external_dispatch_enabled"] is True
    assert runner_audit["dispatch_attempted"] is True
    assert all(r["status"] == "succeeded" for r in runner_audit["results"])
    assert (
        secret_violations(
            {
                "deliveries": json.dumps(deliveries, sort_keys=True),
                "runner_event": json.dumps(events[0], sort_keys=True),
            }
        )
        == []
    )


# --------------------------------------------------------------------------- #
# Idempotency: a pre-existing delivery short-circuits with no second send.
# --------------------------------------------------------------------------- #
def test_idempotency_skips_resend_when_delivery_already_exists(tmp_path):
    app, client = app_and_client(tmp_path, external_dispatch_enabled=True)
    runner = RecordingDispatchRunner()
    app.state.external_dispatch_runner = runner
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    approve_and_audit_external_dispatch(app, client, project_id)
    preview = client.get(
        f"/projects/{project_id}/external-dispatch-preview.json"
    ).json()

    # Pre-seed a delivery for the Slack item so the runner must skip it.
    slack_item = next(i for i in preview["items"] if i["platform"] == "slack")
    contract = slack_item["adapter_contract"]
    seed_key = f"slack:{slack_item['id']}:{contract['argv_sha256']}"
    app.state.repository.record_external_dispatch_delivery(
        idempotency_key=seed_key,
        project_id=project_id,
        item_id=slack_item["id"],
        platform="slack",
        action=slack_item["action"],
        command_boundary=contract["command_boundary"],
        contract_sha256=contract["contract_sha256"],
        argv_sha256=contract["argv_sha256"],
        status="succeeded",
        external_id="pre-existing-slack",
    )

    response = client.post(
        f"/projects/{project_id}/external-dispatch-run", follow_redirects=False
    )
    deliveries = app.state.repository.list_external_dispatch_deliveries(project_id)
    events = app.state.repository.list_audit_events(
        project_id=project_id, event_type="external_dispatch_runner_completed"
    )
    results = events[0]["payload"]["runner_audit"]["results"]

    assert response.status_code == 303
    # The runner was NOT called for the already-delivered Slack item.
    assert all(c["platform"] != "slack" for c in runner.calls)
    slack_results = [r for r in results if r["platform"] == "slack"]
    assert len(slack_results) == 1
    assert slack_results[0]["status"] == "skipped_duplicate"
    assert slack_results[0]["external_id"] == "pre-existing-slack"
    # Exactly one delivery row for the seeded Slack key (no duplicate written).
    slack_deliveries = [d for d in deliveries if d["idempotency_key"] == seed_key]
    assert len(slack_deliveries) == 1
    assert slack_deliveries[0]["external_id"] == "pre-existing-slack"


def test_record_delivery_is_idempotent_on_duplicate_key(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    repository = app.state.repository

    first = repository.record_external_dispatch_delivery(
        idempotency_key="slack:slack-standup-preview:abc",
        project_id=project_id,
        item_id="slack-standup-preview",
        platform="slack",
        action="post_message_preview",
        command_boundary="hermes_command_boundary",
        contract_sha256="c" * 64,
        argv_sha256="a" * 64,
        status="succeeded",
        external_id="first",
    )
    second = repository.record_external_dispatch_delivery(
        idempotency_key="slack:slack-standup-preview:abc",
        project_id=project_id,
        item_id="slack-standup-preview",
        platform="slack",
        action="post_message_preview",
        command_boundary="hermes_command_boundary",
        contract_sha256="c" * 64,
        argv_sha256="a" * 64,
        status="failed",
        external_id="second-should-be-ignored",
    )

    # INSERT OR IGNORE: the second call returns the original, unchanged row.
    assert first["id"] == second["id"]
    assert second["status"] == "succeeded"
    assert second["external_id"] == "first"
    assert (
        repository.get_external_dispatch_delivery(
            "slack:slack-standup-preview:abc"
        )["id"]
        == first["id"]
    )
    assert len(repository.list_external_dispatch_deliveries(project_id)) == 1


# --------------------------------------------------------------------------- #
# Disabled adapter refuses to call the command runner (real-send guard intact).
# --------------------------------------------------------------------------- #
def test_disabled_command_adapter_never_shells_real_hermes(tmp_path):
    shelled: list[list[str]] = []

    def fake_command_runner(argv: list[str]):
        shelled.append(argv)
        raise AssertionError("disabled adapter must not shell out to hermes")

    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    payload = client.get(
        f"/projects/{project_id}/external-dispatch-preview.json"
    ).json()
    item = payload["items"][0]
    adapter = HermesExternalDispatchCommandAdapter(
        enabled=False,
        runner=fake_command_runner,
        runner_label="fake_command_runner",
    )

    result = adapter.dispatch(item)

    assert shelled == []
    assert result["status"] == "blocked"
    assert result["dispatch_attempted"] is False
    assert result["blocker"] == (
        "Hermes external dispatch command adapter is disabled."
    )
    assert secret_violations({"result": json.dumps(result, sort_keys=True)}) == []
