from __future__ import annotations

import json

from fastapi.testclient import TestClient

from hermes_company_os.external_dispatch import HermesExternalDispatchCommandAdapter
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


class FakeExternalDispatchRunner:
    def __init__(self):
        self.calls = []

    def dispatch(self, item: dict) -> dict:
        self.calls.append(item)
        contract = item["adapter_contract"]
        return {
            "status": "succeeded",
            "external_id": f"fake-{item['id']}",
            "detail": "Fake external dispatch runner accepted preview item.",
            "command_boundary": contract["command_boundary"],
            "command_sha256": contract["argv_sha256"],
            "dry_run": contract["dry_run"],
        }


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient) -> str:
    response = client.post(
        "/projects",
        data=STRUCTURED_INTAKE,
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def generate_and_approve_current_stage(app, client: TestClient, project_id: str) -> str:
    current = app.state.repository.next_actionable_stage(project_id)
    assert current is not None
    stage_id = current["stage_id"]
    generated = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    assert generated.status_code == 303, generated.text
    approved = client.post(
        f"/projects/{project_id}/stages/{stage_id}/approve",
        follow_redirects=False,
    )
    assert approved.status_code == 303, approved.text
    return stage_id


def approve_until_stage(app, client: TestClient, project_id: str, target_stage_id: str) -> None:
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
                notes="Loaded externally for operating-loop readiness test.",
            )
    for check in repository.list_messaging_checks():
        repository.update_messaging_check(
            check["id"],
            status="verified",
            evidence="Verified in operating-loop readiness test.",
        )
    for check in repository.list_kanban_checks():
        repository.update_kanban_check(
            check["id"],
            status="verified",
            evidence="Verified in operating-loop readiness test.",
        )


def lane(payload: dict, lane_id: str) -> dict:
    return next(item for item in payload["lanes"] if item["id"] == lane_id)


def assert_adapter_contract(item: dict) -> dict:
    contract = item["adapter_contract"]
    assert contract["schema"] == "external_dispatch_command_contract_v1"
    assert contract["item_id"] == item["id"]
    assert contract["platform"] == item["platform"]
    assert contract["action"] == item["action"]
    assert contract["command_boundary"] == "hermes_command_boundary"
    assert contract["dry_run"] is True
    assert contract["enabled"] is False
    assert contract["argv"]
    assert len(contract["argv_sha256"]) == 64
    assert len(contract["command_preview_sha256"]) == 64
    assert secret_violations({"adapter_contract": json.dumps(contract)}) == []
    return contract


def external_dispatch_decision(app, project_id: str) -> dict:
    decisions = app.state.repository.list_founder_decisions(
        project_id=project_id,
        decision_type="external_action_approval",
    )
    return next(item for item in decisions if item["source"] == "external_dispatch_preview")


def approve_and_audit_external_dispatch(app, client: TestClient, project_id: str) -> dict:
    client.post(
        f"/projects/{project_id}/external-dispatch-approval",
        follow_redirects=False,
    )
    decision = external_dispatch_decision(app, project_id)
    app.state.repository.update_founder_decision(
        decision["id"],
        status="approved",
        decision="Founder approves recording no-send dispatch preview evidence.",
        founder_confirmed=True,
    )
    response = client.post(
        f"/projects/{project_id}/external-dispatch-audit",
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return decision


def test_project_operating_loop_json_defaults_to_safe_locked_state(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.get(f"/projects/{project_id}/operating-loop.json")
    project_page = client.get(f"/projects/{project_id}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["schema"] == "project_operating_loop_v1"
    assert payload["project"]["id"] == project_id
    assert payload["policy"]["dashboard_source_of_truth"] is True
    assert payload["policy"]["external_dispatch_enabled"] is False
    assert payload["policy"]["slack_primary"] is True
    assert payload["policy"]["telegram_urgent_only"] is True
    assert payload["aggregate"]["status"] == "blocked"
    assert lane(payload, "slack")["status"] == "blocked"
    assert lane(payload, "slack")["dispatch_mode"] == "manual_review_only"
    assert lane(payload, "telegram")["urgent_only"] is True
    assert lane(payload, "telegram")["owner_agent_id"] == "chief-of-staff"
    assert lane(payload, "kanban")["task_stage_approved"] is False
    assert lane(payload, "kanban")["status"] == "blocked"
    assert payload["next_actions"]
    assert project_page.status_code == 200
    assert "External Operating Loop" in project_page.text
    assert "Slack routine coordination" in project_page.text
    assert "Telegram urgent founder alerts" in project_page.text
    assert "Kanban source of truth" in project_page.text
    assert "External dispatch disabled" in project_page.text
    assert "Operating loop JSON" in project_page.text
    assert f'href="/projects/{project_id}/operating-loop.json"' in project_page.text
    assert secret_violations(
        {
            "operating_loop": json.dumps(payload, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_project_operating_loop_reports_ready_external_handoff_without_dispatching(
    tmp_path,
):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")

    response = client.get(f"/projects/{project_id}/operating-loop.json")
    project_page = client.get(f"/projects/{project_id}")
    payload = response.json()
    kanban_lane = lane(payload, "kanban")

    assert response.status_code == 200
    assert payload["aggregate"]["status"] == "ready"
    assert payload["aggregate"]["ready"] is True
    assert payload["policy"]["external_dispatch_enabled"] is False
    assert lane(payload, "slack")["status"] == "ready"
    assert lane(payload, "telegram")["status"] == "ready"
    assert kanban_lane["status"] == "ready"
    assert kanban_lane["task_stage_approved"] is True
    assert kanban_lane["verification_ready"] is True
    assert kanban_lane["pending_task_count"] == kanban_lane["workflow_task_count"]
    assert kanban_lane["linked_task_count"] == 0
    assert project_page.status_code == 200
    assert "Operating loop ready" in project_page.text
    assert "Manual review only" in project_page.text
    assert "Push workflow to Kanban" in project_page.text
    assert secret_violations(
        {
            "operating_loop": json.dumps(payload, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_external_dispatch_preview_defaults_to_no_send_locked_state(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.get(f"/projects/{project_id}/external-dispatch-preview.json")
    project_page = client.get(f"/projects/{project_id}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["schema"] == "project_external_dispatch_preview_v1"
    assert payload["project"]["id"] == project_id
    assert payload["policy"]["external_dispatch_enabled"] is False
    assert payload["policy"]["manual_review_required"] is True
    assert payload["policy"]["real_send_allowed"] is False
    assert payload["queue"]["status"] == "blocked"
    assert payload["queue"]["sendable_item_count"] == 0
    assert payload["readiness"]["operating_loop_ready"] is False
    assert {item["id"] for item in payload["items"]} >= {
        "slack-standup-preview",
        "telegram-urgent-alert-preview",
    }
    assert all(item["dispatch_enabled"] is False for item in payload["items"])
    assert all(item["runs_automatically"] is False for item in payload["items"])
    assert all(assert_adapter_contract(item) for item in payload["items"])
    assert project_page.status_code == 200
    assert "External Dispatch Preview" in project_page.text
    assert "Dispatch remains disabled" in project_page.text
    assert "Hermes command boundary" in project_page.text
    assert "Review previews" in project_page.text
    assert f'href="/projects/{project_id}/external-dispatch-preview.json"' in (
        project_page.text
    )
    assert secret_violations(
        {
            "dispatch_preview": json.dumps(payload, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_external_dispatch_approval_request_opens_founder_only_decision(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")

    response = client.post(
        f"/projects/{project_id}/external-dispatch-approval",
        follow_redirects=False,
    )
    package = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    project_page = client.get(f"/projects/{project_id}")
    decision = external_dispatch_decision(app, project_id)

    assert response.status_code == 303
    assert decision["decision_type"] == "external_action_approval"
    assert decision["source"] == "external_dispatch_preview"
    assert decision["requires_founder_approval"] == 1
    assert decision["status"] == "needed"
    assert decision["stage_id"] == "external_operating_loop"
    assert "Approve external dispatch preview" in decision["title"]
    assert package["approval"]["id"] == decision["id"]
    assert package["approval"]["status"] == "needed"
    assert package["approval"]["request_open"] is True
    assert package["approval"]["request_allowed"] is False
    assert package["audit"]["consume_allowed"] is False
    assert project_page.status_code == 200
    assert "Open dispatch approval" in project_page.text
    assert decision["id"] in project_page.text
    assert secret_violations(
        {
            "dispatch_preview": json.dumps(package, sort_keys=True),
            "decision": json.dumps(decision, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_external_dispatch_audit_requires_approved_founder_decision(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    client.post(
        f"/projects/{project_id}/external-dispatch-approval",
        follow_redirects=False,
    )

    response = client.post(
        f"/projects/{project_id}/external-dispatch-audit",
        follow_redirects=False,
    )
    package = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    events = app.state.repository.list_audit_events(
        project_id=project_id,
        event_type="external_dispatch_preview_audit_consumed",
    )

    assert response.status_code == 409
    assert "Founder approval is required" in response.json()["detail"]
    assert package["audit"]["consume_allowed"] is False
    assert package["audit"]["blocker"] == "Founder approval is required."
    assert events == []


def test_external_dispatch_audit_consumes_approval_into_immutable_no_send_evidence(
    tmp_path,
):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    client.post(
        f"/projects/{project_id}/external-dispatch-approval",
        follow_redirects=False,
    )
    decision = external_dispatch_decision(app, project_id)
    app.state.repository.update_founder_decision(
        decision["id"],
        status="approved",
        decision="Founder approves recording no-send dispatch preview evidence.",
        founder_confirmed=True,
    )

    response = client.post(
        f"/projects/{project_id}/external-dispatch-audit",
        follow_redirects=False,
    )
    second_response = client.post(
        f"/projects/{project_id}/external-dispatch-audit",
        follow_redirects=False,
    )
    package = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    project_page = client.get(f"/projects/{project_id}")
    events = app.state.repository.list_audit_events(
        project_id=project_id,
        event_type="external_dispatch_preview_audit_consumed",
    )
    event = events[0]
    audit = event["payload"]["audit"]

    assert response.status_code == 303
    assert second_response.status_code == 409
    assert "already consumed" in second_response.json()["detail"]
    assert len(events) == 1
    assert event["status"] == "consumed"
    assert event["source_table"] == "founder_decisions"
    assert event["source_id"] == decision["id"]
    assert audit["schema"] == "project_external_dispatch_audit_v1"
    assert audit["immutable"] is True
    assert audit["approval_consumption"]["decision_id"] == decision["id"]
    assert audit["approval_consumption"]["status"] == "consumed"
    assert audit["approval_consumption"]["decision_status"] == "approved"
    assert audit["preview_fingerprint"]["sha256"]
    assert audit["preview_fingerprint"]["schema"] == "project_external_dispatch_preview_v1"
    assert audit["item_fingerprints"]
    assert all(item["dispatch_enabled"] is False for item in audit["item_fingerprints"])
    assert all(item["runs_automatically"] is False for item in audit["item_fingerprints"])
    assert all(item["contract_sha256"] for item in audit["item_fingerprints"])
    assert all(
        item["command_boundary"] == "hermes_command_boundary"
        for item in audit["item_fingerprints"]
    )
    assert audit["post_run_review"]["external_dispatch_enabled"] is False
    assert audit["post_run_review"]["real_send_allowed"] is False
    assert package["audit"]["latest"]["event_id"] == event["id"]
    assert package["audit"]["latest"]["schema"] == "project_external_dispatch_audit_v1"
    assert package["audit"]["consume_allowed"] is False
    assert package["audit"]["blocker"] == "Dispatch preview approval already consumed."
    assert project_page.status_code == 200
    assert "Dispatch approval consumed" in project_page.text
    assert "Preview fingerprint" in project_page.text
    assert "External dispatch still disabled" in project_page.text
    assert secret_violations(
        {
            "dispatch_preview": json.dumps(package, sort_keys=True),
            "audit_event": json.dumps(event, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_external_dispatch_runner_is_disabled_by_default_and_records_blocked_audit(
    tmp_path,
):
    app, client = app_and_client(tmp_path)
    fake_runner = FakeExternalDispatchRunner()
    app.state.external_dispatch_runner = fake_runner
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    approve_and_audit_external_dispatch(app, client, project_id)

    response = client.post(
        f"/projects/{project_id}/external-dispatch-run",
        follow_redirects=False,
    )
    package = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    project_page = client.get(f"/projects/{project_id}")
    events = app.state.repository.list_audit_events(
        project_id=project_id,
        event_type="external_dispatch_runner_blocked",
    )
    event = events[0]
    runner_audit = event["payload"]["runner_audit"]

    assert response.status_code == 409
    assert "External dispatch runner is disabled" in response.json()["detail"]
    assert fake_runner.calls == []
    assert len(events) == 1
    assert event["status"] == "blocked"
    assert runner_audit["schema"] == "project_external_dispatch_runner_audit_v1"
    assert runner_audit["external_dispatch_enabled"] is False
    assert runner_audit["dispatch_attempted"] is False
    assert runner_audit["result_count"] == 0
    assert runner_audit["blocker"] == "External dispatch runner is disabled."
    assert runner_audit["command_boundary"]["name"] == "Hermes command boundary"
    assert runner_audit["command_boundary"]["status"] == "disabled"
    assert runner_audit["command_fingerprints"]
    assert all(item["contract_sha256"] for item in runner_audit["command_fingerprints"])
    assert package["runner"]["external_dispatch_enabled"] is False
    assert package["runner"]["latest"]["event_id"] == event["id"]
    assert package["runner"]["latest"]["status"] == "blocked"
    assert project_page.status_code == 200
    assert "External dispatch runner disabled" in project_page.text
    assert "Runner evidence" in project_page.text
    assert "Hermes command boundary" in project_page.text
    assert "Command fingerprints" in project_page.text
    assert "No live send attempted" in project_page.text
    assert secret_violations(
        {
            "dispatch_preview": json.dumps(package, sort_keys=True),
            "runner_event": json.dumps(event, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_external_dispatch_runner_uses_enabled_injected_adapter_and_records_results(
    tmp_path,
):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            external_dispatch_enabled=True,
        )
    )
    fake_runner = FakeExternalDispatchRunner()
    app.state.external_dispatch_runner = fake_runner
    app.state.external_dispatch_runner_label = "fake_external_dispatch_runner"
    client = TestClient(app)
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")
    approve_and_audit_external_dispatch(app, client, project_id)
    preview = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()

    response = client.post(
        f"/projects/{project_id}/external-dispatch-run",
        follow_redirects=False,
    )
    second_response = client.post(
        f"/projects/{project_id}/external-dispatch-run",
        follow_redirects=False,
    )
    package = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    project_page = client.get(f"/projects/{project_id}")
    events = app.state.repository.list_audit_events(
        project_id=project_id,
        event_type="external_dispatch_runner_completed",
    )
    event = events[0]
    runner_audit = event["payload"]["runner_audit"]

    assert response.status_code == 303
    assert second_response.status_code == 409
    assert "already completed" in second_response.json()["detail"]
    assert len(events) == 1
    assert event["status"] == "succeeded"
    assert len(fake_runner.calls) == preview["queue"]["item_count"]
    assert all("adapter_contract" in item for item in fake_runner.calls)
    assert all(
        item["adapter_contract"]["argv_sha256"]
        for item in fake_runner.calls
    )
    assert runner_audit["schema"] == "project_external_dispatch_runner_audit_v1"
    assert runner_audit["external_dispatch_enabled"] is True
    assert runner_audit["dispatch_attempted"] is True
    assert runner_audit["runner_label"] == "fake_external_dispatch_runner"
    assert runner_audit["command_boundary"]["name"] == "Hermes command boundary"
    assert runner_audit["command_boundary"]["status"] == "enabled"
    assert runner_audit["command_fingerprints"]
    assert all(item["contract_sha256"] for item in runner_audit["command_fingerprints"])
    assert runner_audit["result_count"] == preview["queue"]["item_count"]
    assert all(result["status"] == "succeeded" for result in runner_audit["results"])
    assert all(
        result["command_boundary"] == "hermes_command_boundary"
        for result in runner_audit["results"]
    )
    assert all(result["command_sha256"] for result in runner_audit["results"])
    assert package["runner"]["latest"]["event_id"] == event["id"]
    assert package["runner"]["latest"]["status"] == "succeeded"
    assert package["runner"]["run_allowed"] is False
    assert project_page.status_code == 200
    assert "External dispatch runner completed" in project_page.text
    assert "fake_external_dispatch_runner" in project_page.text
    assert "Hermes command boundary" in project_page.text
    assert "Command fingerprints" in project_page.text
    assert secret_violations(
        {
            "dispatch_preview": json.dumps(package, sort_keys=True),
            "runner_event": json.dumps(event, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_external_dispatch_preview_builds_ready_no_send_handoff_queue(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    mark_external_loop_ready(app)
    approve_until_stage(app, client, project_id, "tasks")

    response = client.get(f"/projects/{project_id}/external-dispatch-preview.json")
    project_page = client.get(f"/projects/{project_id}")
    payload = response.json()
    kanban_items = [
        item for item in payload["items"] if item["platform"] == "hermes-kanban"
    ]
    workflow_count = lane(
        client.get(f"/projects/{project_id}/operating-loop.json").json(),
        "kanban",
    )["workflow_task_count"]

    assert response.status_code == 200
    assert payload["queue"]["status"] == "ready_for_review"
    assert payload["queue"]["item_count"] == len(payload["items"])
    assert payload["queue"]["sendable_item_count"] == 0
    assert payload["queue"]["preview_item_count"] == len(payload["items"])
    assert payload["readiness"]["operating_loop_ready"] is True
    assert all(item["dispatch_enabled"] is False for item in payload["items"])
    assert all(item["runs_automatically"] is False for item in payload["items"])
    assert any(item["label"] == "Slack standup preview" for item in payload["items"])
    assert any(
        item["label"] == "Telegram urgent alert preview" for item in payload["items"]
    )
    assert len(kanban_items) == workflow_count
    assert all(item["label"] == "Kanban task create preview" for item in kanban_items)
    assert all(item["idempotency_key"].startswith("task-") for item in kanban_items)
    assert all("hermes kanban create" in item["command_preview"] for item in kanban_items)
    contracts = [assert_adapter_contract(item) for item in payload["items"]]
    slack_contract = next(
        contract for contract in contracts if contract["platform"] == "slack"
    )
    telegram_contract = next(
        contract for contract in contracts if contract["platform"] == "telegram"
    )
    kanban_contracts = [
        contract for contract in contracts if contract["platform"] == "hermes-kanban"
    ]
    assert slack_contract["adapter"] == "slack"
    assert slack_contract["command_kind"] == "slack.chat.postMessage"
    assert slack_contract["target_input_key"] == "slack_channel_agent_standup"
    assert "--channel-ref" in slack_contract["argv"]
    assert telegram_contract["adapter"] == "telegram"
    assert telegram_contract["command_kind"] == "telegram.sendMessage"
    assert telegram_contract["target_input_key"] == "founder_telegram_user_id"
    assert telegram_contract["urgent_only"] is True
    assert "--urgent-only" in telegram_contract["argv"]
    assert len(kanban_contracts) == workflow_count
    assert all(contract["adapter"] == "hermes-kanban" for contract in kanban_contracts)
    assert all(
        contract["command_kind"] == "hermes kanban create"
        for contract in kanban_contracts
    )
    assert all("--idempotency-key" in contract["argv"] for contract in kanban_contracts)
    assert project_page.status_code == 200
    assert "Ready for founder review" in project_page.text
    assert "Slack standup preview" in project_page.text
    assert "Telegram urgent alert preview" in project_page.text
    assert "Kanban task create preview" in project_page.text
    assert secret_violations(
        {
            "dispatch_preview": json.dumps(payload, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_hermes_external_dispatch_command_adapter_disabled_refuses_without_calling_runner(
    tmp_path,
):
    calls = []

    def fake_command_runner(argv: list[str]):
        calls.append(argv)
        raise AssertionError("disabled adapter must not call the command runner")

    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    payload = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    item = payload["items"][0]
    adapter = HermesExternalDispatchCommandAdapter(
        enabled=False,
        runner=fake_command_runner,
        runner_label="fake_command_runner",
    )

    result = adapter.dispatch(item)

    assert calls == []
    assert result["status"] == "blocked"
    assert result["dispatch_attempted"] is False
    assert result["command_boundary"] == "hermes_command_boundary"
    assert result["runner_label"] == "fake_command_runner"
    assert result["command_sha256"] == item["adapter_contract"]["argv_sha256"]
    assert result["blocker"] == "Hermes external dispatch command adapter is disabled."
    assert secret_violations({"adapter_result": json.dumps(result, sort_keys=True)}) == []


def test_hermes_external_dispatch_command_adapter_enabled_runs_contract_argv(
    tmp_path,
):
    calls = []

    def fake_command_runner(argv: list[str]):
        calls.append(argv)
        return {
            "returncode": 0,
            "stdout": "dry run accepted",
            "stderr": "",
            "duration_ms": 3,
        }

    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    payload = client.get(f"/projects/{project_id}/external-dispatch-preview.json").json()
    item = payload["items"][0]
    adapter = HermesExternalDispatchCommandAdapter(
        enabled=True,
        runner=fake_command_runner,
        runner_label="fake_command_runner",
    )

    result = adapter.dispatch(item)

    assert calls == [item["adapter_contract"]["argv"]]
    assert result["status"] == "succeeded"
    assert result["dispatch_attempted"] is True
    assert result["returncode"] == 0
    assert result["command_boundary"] == "hermes_command_boundary"
    assert result["command_sha256"] == item["adapter_contract"]["argv_sha256"]
    assert result["stdout_capture"]["bytes"] == len("dry run accepted")
    assert result["stdout_capture"]["sha256"]
    assert result["stderr_capture"]["bytes"] == 0
    assert secret_violations({"adapter_result": json.dumps(result, sort_keys=True)}) == []
