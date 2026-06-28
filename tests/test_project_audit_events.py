from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from hermes_company_os.database import initialize_database
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
