import sqlite3

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.database import initialize_database
from hermes_company_os.main import create_app
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

STRUCTURED_INTAKE = {
    "wizard_version": "product-wizard-v1",
    "name": "Atlas Brief",
    "product_category": "saas",
    "founder_idea": "AI due-diligence workspace for acquisition teams.",
    "target_audience": "Corporate development teams.",
    "current_alternative": "Shared docs and ad hoc chat threads.",
    "problem_statement": "Teams lose the thread across diligence notes.",
    "desired_outcome": "A reviewed risk brief with assigned questions.",
    "launch_tier": "t0_internal",
    "deadline_pressure": "normal",
    "constraints": "Use mock data only.",
    "non_goals": "Do not build a data-room connector in V1.",
    "success_metrics": "Reduce first-pass synthesis time by 40 percent.",
}


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


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


def test_founder_decision_schema_migrates_old_table_shape(tmp_path):
    database_path = tmp_path / "company.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE founder_decisions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                urgency TEXT NOT NULL,
                source TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL,
                slack_channel TEXT NOT NULL,
                telegram_policy TEXT NOT NULL,
                context TEXT NOT NULL,
                decision TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(founder_decisions)")
        }
    assert {
        "decision_type",
        "project_id",
        "stage_id",
        "artifact_id",
        "evidence",
        "requires_founder_approval",
        "resolved_at",
        "resolution_note",
    }.issubset(columns)


def test_repository_filters_project_decisions_and_enforces_founder_only_resolution(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI diligence workspace.",
    )
    artifact_id = repository.save_stage_artifact_draft(
        project_id=project_id,
        stage_id="research",
        markdown_content="# Research\n\nSafe opportunity evidence.",
        json_content={"stage": "research"},
    )

    decision_id = repository.create_founder_decision(
        title="Accept scoped research risk",
        urgency="urgent",
        decision_type="accepted_risk",
        source="qa-review",
        owner_agent_id="qa-critic",
        project_id=project_id,
        stage_id="research",
        artifact_id=artifact_id,
        slack_channel="#decisions",
        telegram_policy="Telegram only if launch is blocked.",
        context="A known research gap can ship only with founder rationale.",
        evidence="Severity medium; owner QA Critic; mitigation follow-up interview.",
    )

    linked = repository.list_founder_decisions(
        project_id=project_id,
        stage_id="research",
        decision_type="accepted_risk",
        include_resolved=False,
    )
    assert [item["id"] for item in linked] == [decision_id]
    assert linked[0]["project_name"] == "Atlas Brief"
    assert linked[0]["requires_founder_approval"] == 1

    with pytest.raises(ValueError, match="Founder confirmation"):
        repository.update_founder_decision(
            decision_id,
            status="approved",
            decision="Accepted with a follow-up interview mitigation.",
        )

    repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Accepted with a follow-up interview mitigation.",
        founder_confirmed=True,
    )
    saved = repository.get_founder_decision(decision_id)
    assert saved["resolved_at"]
    assert saved["resolution_note"] == "Accepted with a follow-up interview mitigation."


def test_decision_inbox_renders_filters_and_founder_only_guard(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    decision_id = app.state.repository.create_founder_decision(
        title="Approve external beta invite",
        urgency="urgent",
        decision_type="external_action_approval",
        source="manual",
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id="acceptance",
        slack_channel="#founder-command",
        telegram_policy="Telegram only if beta launch is blocked.",
        context="Approve sending the first private beta invite.",
        evidence="Launch tier T1 private beta; no credentials or customer files.",
    )

    inbox = client.get(f"/decisions?project_id={project_id}&status=open")
    detail = client.get(f"/decisions/{decision_id}")
    blocked_update = client.post(
        f"/decisions/{decision_id}",
        data={
            "status": "approved",
            "decision": "Approved for one private beta invite.",
            "return_to": "/decisions",
        },
        follow_redirects=False,
    )
    confirmed_update = client.post(
        f"/decisions/{decision_id}",
        data={
            "status": "approved",
            "decision": "Approved for one private beta invite.",
            "founder_confirmed": "confirmed",
            "return_to": "/decisions",
        },
        follow_redirects=False,
    )

    assert inbox.status_code == 200
    assert "Decision inbox" in inbox.text
    assert "Approve external beta invite" in inbox.text
    assert "founder-only" in inbox.text
    assert "Atlas Brief" in inbox.text
    assert detail.status_code == 200
    assert "Decision inbox" in detail.text
    assert "Approve external beta invite" in detail.text
    assert blocked_update.status_code == 400
    assert confirmed_update.status_code == 303
    assert app.state.repository.get_founder_decision(decision_id)["status"] == "approved"


def test_product_wizard_generation_creates_project_review_decision(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    generated = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    decisions = app.state.repository.list_founder_decisions(
        project_id=project_id,
        stage_id="research",
        decision_type="artifact_approval",
        include_resolved=False,
    )
    project_page = client.get(f"/projects/{project_id}")
    inbox = client.get(f"/decisions?project_id={project_id}")
    approved = client.post(
        f"/projects/{project_id}/stages/research/approve",
        follow_redirects=False,
    )
    saved_decision = app.state.repository.get_founder_decision(decisions[0]["id"])

    assert generated.status_code == 303
    assert len(decisions) == 1
    assert decisions[0]["artifact_id"].startswith("wiz-artifact-")
    assert decisions[0]["evidence"]
    assert "local_fake_public_demo" in decisions[0]["evidence"]
    assert project_page.status_code == 200
    assert "Project decisions" in project_page.text
    assert "Approve Research artifact for Atlas Brief" in project_page.text
    assert inbox.status_code == 200
    assert "Approve Research artifact for Atlas Brief" in inbox.text
    assert approved.status_code == 303
    assert saved_decision["status"] == "approved"
    assert saved_decision["resolved_at"]


def test_project_page_surfaces_founder_control_summary(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    project_page = client.get(f"/projects/{project_id}")
    css = client.get("/static/styles.css")

    assert project_page.status_code == 200
    assert 'aria-label="Founder control summary"' in project_page.text
    assert "Founder Control Summary" in project_page.text
    assert "Next Founder Action" in project_page.text
    assert "Generate Research artifact" in project_page.text
    assert 'href="#current-stage"' in project_page.text
    for label in (
        "Current stage",
        "Artifact state",
        "Open decisions",
        "Queue blockers",
        "Codex handoff",
        "Review loop",
    ):
        assert label in project_page.text
    assert "Research" in project_page.text
    assert "0 blockers" in project_page.text
    assert "locked" in project_page.text
    assert "blocked" in project_page.text
    assert css.status_code == 200
    assert ".founder-control-summary" in css.text
    assert ".founder-action-card" in css.text
    assert ".founder-signal-grid" in css.text
    assert secret_violations(
        {
            "project_page": project_page.text,
            "css": css.text,
        }
    ) == []


def test_project_founder_control_summary_prioritizes_open_decisions(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    generated = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    project_page = client.get(f"/projects/{project_id}")

    assert generated.status_code == 303
    assert project_page.status_code == 200
    assert "Review project decisions" in project_page.text
    assert "1 open decision" in project_page.text
    assert "Open project decisions" in project_page.text
    assert "Approve Research artifact for Atlas Brief" in project_page.text
    assert app.state.repository.list_founder_decisions(project_id=project_id)
    assert secret_violations({"project_page": project_page.text}) == []
