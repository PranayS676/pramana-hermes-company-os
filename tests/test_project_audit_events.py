from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from hermes_company_os.database import initialize_database
from hermes_company_os.kanban_client import KanbanResult
from hermes_company_os.main import create_app
from hermes_company_os.product_wizard import generate_wizard_artifact
from hermes_company_os.repository import CompanyRepository
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


class CapturingGenerationService:
    def __init__(self):
        self.requests = []

    def generate_stage(self, request):
        self.requests.append(request)
        return generate_wizard_artifact(
            request.stage_id,
            request.intake,
            request.approved_sources,
            memory_context=request.memory_context,
            memory_policy=request.memory_policy,
        )


class FakeKanbanClient:
    def __init__(self) -> None:
        self.created_tasks: list[dict] = []

    def diagnostics(self) -> KanbanResult:
        return KanbanResult(ok=True, output='{"ok": true}')

    def create_task(self, task: dict) -> KanbanResult:
        self.created_tasks.append(task)
        task_id = f"kb_{len(self.created_tasks)}"
        return KanbanResult(ok=True, output=f'{{"id": "{task_id}"}}', task_id=task_id)


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


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def test_project_audit_schema_and_repository_list_project_events(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI diligence workspace.",
    )

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(audit_events)")}

    event_id = repository.create_audit_event(
        project_id=project_id,
        event_type="memory_created",
        status="succeeded",
        actor_agent_id="chief-of-staff",
        source_table="project_memory_entries",
        source_id="memory-demo",
        summary="Founder-approved project memory was captured.",
        payload={"category": "founder_preference"},
    )
    events = repository.list_audit_events(project_id=project_id)

    assert {
        "id",
        "project_id",
        "event_type",
        "status",
        "actor_agent_id",
        "source_table",
        "source_id",
        "summary",
        "payload_json",
        "created_at",
    }.issubset(columns)
    assert [event["id"] for event in events] == [event_id]
    assert events[0]["event_type"] == "memory_created"
    assert events[0]["event_label"] == "Memory captured"
    assert events[0]["payload"] == {"category": "founder_preference"}
    assert secret_violations({"audit_event": json.dumps(events[0], sort_keys=True)}) == []


def test_project_activity_json_exports_recent_events(tmp_path):
    app, client = app_and_client(tmp_path)
    generation_service = CapturingGenerationService()
    app.state.generation_service = generation_service
    project_id = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    export_response = client.get(f"/projects/{project_id}/activity.json")
    payload = export_response.json()

    assert response.status_code == 303
    assert export_response.status_code == 200
    assert payload["schema"] == "project_activity_package_v1"
    assert payload["project"]["id"] == project_id
    assert payload["aggregate"]["event_count"] >= 2
    assert payload["events"][0]["event_label"]
    assert payload["events"][0]["source_table"]
    assert payload["events"][0]["source_id"]
    assert "payload_json" not in payload["events"][0]
    assert "generation_succeeded" in {
        event["event_type"] for event in payload["events"]
    }
    assert secret_violations({"activity_json": json.dumps(payload, sort_keys=True)}) == []


def test_generation_route_records_project_activity_events(tmp_path):
    app, client = app_and_client(tmp_path)
    generation_service = CapturingGenerationService()
    app.state.generation_service = generation_service
    project_id = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    artifact = app.state.repository.latest_project_stage_artifact(project_id, "research")
    generation_run = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )[0]
    events = app.state.repository.list_audit_events(project_id=project_id)
    event_types = [event["event_type"] for event in events]
    project_page = client.get(f"/projects/{project_id}")
    css = client.get("/static/styles.css")

    assert response.status_code == 303, response.text
    assert artifact is not None
    assert generation_run["status"] == "succeeded"
    assert "generation_succeeded" in event_types
    assert "generation_started" in event_types
    succeeded_event = next(
        event for event in events if event["event_type"] == "generation_succeeded"
    )
    assert succeeded_event["source_table"] == "generation_runs"
    assert succeeded_event["source_id"] == generation_run["id"]
    assert succeeded_event["payload"]["stage_id"] == "research"
    assert succeeded_event["payload"]["artifact_id"] == artifact["id"]
    assert project_page.status_code == 200
    assert 'id="project-activity"' in project_page.text
    assert "Agent Activity" in project_page.text
    assert "Generation succeeded" in project_page.text
    assert "Activity JSON" in project_page.text
    assert f'href="/projects/{project_id}/activity.json"' in project_page.text
    assert generation_run["id"] in project_page.text
    assert css.status_code == 200
    assert ".project-activity-panel" in css.text
    assert ".activity-event-row" in css.text
    assert secret_violations(
        {
            "audit_events": json.dumps(events, sort_keys=True),
            "project_page": project_page.text,
            "css": css.text,
        }
    ) == []


def test_founder_decision_lifecycle_records_activity_events(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI diligence workspace.",
    )

    decision_id = repository.create_founder_decision(
        title="Approve research artifact",
        urgency="normal",
        decision_type="artifact_approval",
        source="project-wizard-review",
        owner_agent_id="product-manager",
        project_id=project_id,
        stage_id="research",
        artifact_id=None,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if launch is blocked.",
        context="Founder review is required before this artifact becomes source input.",
        evidence="Research artifact is ready for review.",
        requires_founder_approval=True,
    )
    repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Approved for the next stage.",
        founder_confirmed=True,
    )
    events = repository.list_audit_events(project_id=project_id)
    event_types = [event["event_type"] for event in events]

    assert event_types[:2] == ["founder_decision_resolved", "founder_decision_created"]
    assert events[0]["source_table"] == "founder_decisions"
    assert events[0]["source_id"] == decision_id
    assert events[0]["payload"]["decision_type"] == "artifact_approval"
    assert events[0]["payload"]["status"] == "approved"
    assert secret_violations({"audit_events": json.dumps(events, sort_keys=True)}) == []


def test_stage_approval_and_revision_routes_record_activity_events(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    generated = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    approved = client.post(
        f"/projects/{project_id}/stages/research/approve",
        follow_redirects=False,
    )
    revision = client.post(
        f"/projects/{project_id}/stages/research/revision",
        data={
            "revision_reason": "evidence_gap",
            "revision_request": "Add clearer primary-source evidence before PRD.",
        },
        follow_redirects=False,
    )
    events = app.state.repository.list_audit_events(project_id=project_id)
    approval_event = next(
        event for event in events if event["event_type"] == "stage_approved"
    )
    revision_event = next(
        event for event in events if event["event_type"] == "stage_revision_requested"
    )
    project_page = client.get(f"/projects/{project_id}")

    assert generated.status_code == 303
    assert approved.status_code == 303
    assert revision.status_code == 303
    assert approval_event["source_table"] == "product_wizard_project_stages"
    assert approval_event["payload"]["stage_id"] == "research"
    assert approval_event["payload"]["artifact_id"]
    assert revision_event["source_table"] == "product_wizard_project_stages"
    assert revision_event["payload"]["stage_id"] == "research"
    assert revision_event["payload"]["reason"] == "evidence_gap"
    assert "Stage approved" in project_page.text
    assert "Stage revision requested" in project_page.text
    assert secret_violations(
        {
            "audit_events": json.dumps(events, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_memory_routes_record_project_activity_and_render_timeline(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    created = client.post(
        f"/projects/{project_id}/memory",
        data={
            "category": "product_strategy",
            "memory_type": "decision",
            "owner_agent_id": "product-manager",
            "source": "founder-memory-form",
            "title": "Start with acquisition diligence teams",
            "summary": "The initial product wedge stays focused on corp-dev diligence.",
            "body": "Avoid expanding V1 into a generic research workspace.",
            "confidence": "high",
            "pinned": "on",
        },
        follow_redirects=False,
    )
    memory_id = app.state.repository.list_project_memory_entries(project_id=project_id)[0][
        "id"
    ]
    retired = client.post(
        f"/projects/{project_id}/memory/{memory_id}",
        data={"memory_action": "retire"},
        follow_redirects=False,
    )
    events = app.state.repository.list_audit_events(project_id=project_id)
    event_types = [event["event_type"] for event in events]
    project_page = client.get(f"/projects/{project_id}")

    assert created.status_code == 303
    assert retired.status_code == 303
    assert event_types[:2] == ["memory_retired", "memory_created"]
    assert events[0]["source_table"] == "project_memory_entries"
    assert events[0]["source_id"] == memory_id
    assert events[0]["payload"]["status"] == "retired"
    assert project_page.status_code == 200
    assert "Memory retired" in project_page.text
    assert "Memory captured" in project_page.text
    assert memory_id in project_page.text
    assert secret_violations(
        {
            "audit_events": json.dumps(events, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []


def test_multi_agent_review_routes_record_blocked_and_completed_activity(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    blocked = client.post(
        f"/projects/{project_id}/multi-agent-review",
        follow_redirects=False,
    )
    approve_until_stage(app, client, project_id, "acceptance")
    completed = client.post(
        f"/projects/{project_id}/multi-agent-review",
        follow_redirects=False,
    )
    records = app.state.repository.list_project_review_records(project_id)
    events = app.state.repository.list_audit_events(project_id=project_id)
    blocked_event = next(
        event for event in events if event["event_type"] == "multi_agent_review_blocked"
    )
    completed_event = next(
        event for event in events if event["event_type"] == "multi_agent_review_completed"
    )

    assert blocked.status_code == 409
    assert completed.status_code == 303
    assert len(records) == 5
    assert blocked_event["source_table"] == "company_projects"
    assert blocked_event["source_id"] == project_id
    assert "approved code plan and acceptance package" in blocked_event["summary"]
    assert completed_event["source_table"] == "project_review_records"
    assert completed_event["payload"]["reviewer_count"] == 5
    assert completed_event["payload"]["status"] == "approved"
    assert secret_violations({"audit_events": json.dumps(events, sort_keys=True)}) == []


def test_project_kanban_route_records_blocked_and_linked_activity(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    project_id = app.state.repository.create_project_with_workflow(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )
    client = TestClient(app)

    blocked = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)
    for check in app.state.repository.list_kanban_checks():
        app.state.repository.update_kanban_check(
            check_id=check["id"],
            status="verified",
            evidence="Verified before project handoff.",
        )
    pushed = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)
    events = app.state.repository.list_audit_events(project_id=project_id)
    event_types = [event["event_type"] for event in events]
    linked_events = [
        event for event in events if event["event_type"] == "kanban_task_linked"
    ]

    assert blocked.status_code == 409
    assert pushed.status_code == 303
    assert "kanban_push_blocked" in event_types
    assert "kanban_push_started" in event_types
    assert linked_events
    assert len(linked_events) == len(app.state.kanban_client.created_tasks)
    assert linked_events[0]["source_table"] == "tasks"
    assert linked_events[0]["payload"]["kanban_task_id"].startswith("kb_")
    assert secret_violations({"audit_events": json.dumps(events, sort_keys=True)}) == []
