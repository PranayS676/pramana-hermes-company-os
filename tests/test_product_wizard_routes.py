from __future__ import annotations

import json

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

FAKE_OPENAI_ENV_SECRET = "OPENAI_API_KEY=sk-" + "abcdefghijklmnopqrstuvwxyz123456"

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

STRUCTURED_FIELD_NAMES = [
    "name",
    "product_category",
    "founder_idea",
    "target_audience",
    "current_alternative",
    "problem_statement",
    "desired_outcome",
    "launch_tier",
    "deadline_pressure",
    "constraints",
    "non_goals",
    "success_metrics",
]

STRUCTURED_FIELD_LABELS = [
    "Project name",
    "Product category",
    "Founder idea",
    "Target audience",
    "Current alternative",
    "Problem statement",
    "Desired outcome",
    "Launch tier",
    "Deadline pressure",
    "Constraints",
    "Non-goals",
    "Success metrics",
]

WIZARD_STAGE_IDS = ["research", "prd", "architecture", "tasks", "code_plan", "acceptance"]


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient, **overrides: str) -> tuple[str, str]:
    response = client.post(
        "/projects",
        data={**STRUCTURED_INTAKE, **overrides},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    location = response.headers["location"]
    assert location.startswith("/projects/")
    return location.rsplit("/", 1)[-1], location


def test_new_project_wizard_form_renders_structured_intake(tmp_path):
    _, client = app_and_client(tmp_path)

    response = client.get("/projects/new")

    assert response.status_code == 200
    assert "New product wizard" in response.text
    assert 'action="/projects"' in response.text
    assert 'method="post"' in response.text.lower()
    assert 'name="wizard_version"' in response.text
    assert 'value="product-wizard-v1"' in response.text
    for field_name in STRUCTURED_FIELD_NAMES:
        assert f'name="{field_name}"' in response.text
    for label in STRUCTURED_FIELD_LABELS:
        assert label in response.text


def test_create_project_uses_structured_wizard_flow_and_redirects_to_detail(tmp_path):
    app, client = app_and_client(tmp_path)

    project_id, location = create_structured_project(client)

    project = app.state.repository.get_project(project_id)
    assert project is not None
    assert project["name"] == STRUCTURED_INTAKE["name"]
    assert project["status"] == "wizard_active"
    stages = app.state.repository.list_project_wizard_stages(project_id)
    assert [stage["stage_id"] for stage in stages] == WIZARD_STAGE_IDS
    assert [stage["status"] for stage in stages] == [
        "ready",
        "waiting",
        "waiting",
        "waiting",
        "waiting",
        "waiting",
    ]
    assert app.state.repository.list_project_workflow_items(project_id) == []

    detail = client.get(location)
    assert detail.status_code == 200
    for value in (
        STRUCTURED_INTAKE["target_audience"],
        STRUCTURED_INTAKE["problem_statement"],
        STRUCTURED_INTAKE["constraints"],
        STRUCTURED_INTAKE["success_metrics"],
    ):
        assert value in detail.text
    assert secret_violations({"project_detail": detail.text}) == []


def test_secret_shaped_structured_intake_is_rejected_and_not_persisted(tmp_path):
    app, client = app_and_client(tmp_path)

    response = client.post(
        "/projects",
        data={
            **STRUCTURED_INTAKE,
            "problem_statement": (
                "This should never persist because it contains " + FAKE_OPENAI_ENV_SECRET
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert app.state.repository.list_projects() == []
    projects_page = client.get("/projects")
    assert "sk-" not in projects_page.text
    assert "OPENAI_API_KEY" not in projects_page.text


def test_generate_current_stage_uses_public_demo_local_generation(tmp_path, monkeypatch):
    for env_name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "HERMES_API_KEY",
        "HERMES_COMMAND_PRODUCT_MANAGER",
        "HERMES_COMMAND_RESEARCH_AGENT",
    ):
        monkeypatch.delenv(env_name, raising=False)
    app, client = app_and_client(tmp_path)
    project_id, _ = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )

    assert response.status_code == 303, response.text
    artifact = app.state.repository.latest_project_stage_artifact(project_id, "research")
    assert artifact is not None
    assert artifact["status"] == "draft"
    assert artifact["version"] == 1
    raw_artifact = json.dumps(artifact, sort_keys=True)
    assert "local_fake_public_demo" in raw_artifact
    assert "Opportunity Research" in raw_artifact
    assert secret_violations({"artifact": raw_artifact}) == []
