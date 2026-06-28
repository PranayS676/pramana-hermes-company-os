from __future__ import annotations

import json

from fastapi.testclient import TestClient

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
    assert project_page.status_code == 200
    assert "External Dispatch Preview" in project_page.text
    assert "Dispatch remains disabled" in project_page.text
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
