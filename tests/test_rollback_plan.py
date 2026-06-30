from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.kanban_client import KanbanResult
from hermes_company_os.main import create_app
from hermes_company_os.rollback_plan import (
    ROLLBACK_PLAN_SCHEMA,
    rollback_plan_markdown,
    rollback_plan_package,
)
from hermes_company_os.settings import Settings

PROJECT_INTAKE = {
    "wizard_version": "product-wizard-v1",
    "name": "Atlas Brief",
    "product_category": "saas",
    "founder_idea": "AI due-diligence workspace for acquisition teams.",
    "target_audience": "Corporate development teams reviewing small acquisitions.",
    "current_alternative": "Shared docs, spreadsheets, and ad hoc chat threads.",
    "problem_statement": "Teams lose the thread across diligence notes, risks, and asks.",
    "desired_outcome": "A reviewed risk brief with assigned follow-up questions.",
    "launch_tier": "t2_beta",
    "deadline_pressure": "normal",
    "constraints": "Use mock data only; no live customer files in the public demo.",
    "non_goals": "Do not build an enterprise data-room connector in V1.",
    "success_metrics": "Reduce first-pass diligence synthesis time by 40 percent.",
}


class FakeKanbanClient:
    def diagnostics(self) -> KanbanResult:
        return KanbanResult(ok=True, output='{"ok": true}')

    def create_task(self, task: dict) -> KanbanResult:
        return KanbanResult(ok=True, output='{"id": "kb_1"}', task_id="kb_1")


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    return app, TestClient(app)


def make_project(app, intake: dict | None = None) -> str:
    repository = app.state.repository
    payload = dict(PROJECT_INTAKE)
    if intake is not None:
        payload.update(intake)
    return repository.create_structured_project(
        name=payload["name"],
        founder_idea=payload["founder_idea"],
        intake=payload,
    )


def generate_all_stages_through_acceptance(app, client: TestClient, project_id: str) -> None:
    repository = app.state.repository
    for _ in range(12):
        stage = repository.next_actionable_stage(project_id)
        if stage is None:
            break
        stage_id = stage["stage_id"]
        generate = client.post(
            f"/projects/{project_id}/stages/current/generate",
            follow_redirects=False,
        )
        assert generate.status_code == 303, generate.text
        approve = client.post(
            f"/projects/{project_id}/stages/{stage_id}/approve",
            data={"approval_note": f"Approved {stage_id} for rollback test."},
            follow_redirects=False,
        )
        assert approve.status_code == 303, approve.text
        if stage_id == "acceptance":
            break


def test_package_builds_without_acceptance_artifacts(tmp_path):
    app, _client = app_and_client(tmp_path)
    project_id = make_project(app)
    package = rollback_plan_package(app.state.repository, project_id)

    assert package["schema"] == ROLLBACK_PLAN_SCHEMA
    assert package["project"]["id"] == project_id
    # Degrades gracefully: no acceptance artifact present.
    assert package["artifacts_available"] is False
    assert package["launch_tier"]["id"]
    assert package["trigger_conditions"]
    assert package["rollback_steps"]
    assert package["verification_checks"]
    assert package["data_reversal_notes"]
    assert package["founder_sign_off"]["status"] == "pending"


def test_package_builds_with_acceptance_artifacts(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = make_project(app)
    generate_all_stages_through_acceptance(app, client, project_id)

    package = rollback_plan_package(app.state.repository, project_id)
    assert package["artifacts_available"] is True
    stage_ids = {item["stage_id"] for item in package["source_artifacts"]}
    assert "acceptance" in stage_ids


def test_required_sections_present(tmp_path):
    app, _client = app_and_client(tmp_path)
    project_id = make_project(app)
    package = rollback_plan_package(app.state.repository, project_id)

    for key in (
        "schema",
        "project",
        "launch_tier",
        "trigger_conditions",
        "rollback_steps",
        "verification_checks",
        "data_reversal_notes",
        "founder_sign_off",
        "credential_boundary",
    ):
        assert key in package, key

    # Each rollback step is ordered and has an owner.
    orders = [step["order"] for step in package["rollback_steps"]]
    assert orders == sorted(orders)
    for step in package["rollback_steps"]:
        assert step["owner"]
        assert step["action"]


def test_launch_tier_derived_from_intake(tmp_path):
    app, _client = app_and_client(tmp_path)
    project_id = make_project(app, intake={"launch_tier": "t3_ga"})
    package = rollback_plan_package(app.state.repository, project_id)
    assert package["launch_tier"]["id"] == "t3_ga"


def test_unknown_tier_degrades_gracefully(tmp_path):
    app, _client = app_and_client(tmp_path)
    project_id = make_project(app, intake={"launch_tier": ""})
    package = rollback_plan_package(app.state.repository, project_id)
    # Falls back to a defined default tier, still valid.
    assert package["launch_tier"]["id"]
    assert package["rollback_steps"]


def test_unknown_project_raises(tmp_path):
    app, _client = app_and_client(tmp_path)
    with pytest.raises(ValueError):
        rollback_plan_package(app.state.repository, "proj-does-not-exist")


def test_markdown_export(tmp_path):
    app, _client = app_and_client(tmp_path)
    project_id = make_project(app)
    package = rollback_plan_package(app.state.repository, project_id)
    markdown = rollback_plan_markdown(package)

    assert markdown.startswith("# Rollback Plan")
    assert "## Trigger Conditions" in markdown
    assert "## Rollback Steps" in markdown
    assert "## Verification Checks" in markdown
    assert "## Data And Migration Reversal" in markdown
    assert "## Founder Sign-Off" in markdown


def test_route_json_success(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = make_project(app)
    response = client.get(f"/projects/{project_id}/rollback-plan.json")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema"] == ROLLBACK_PLAN_SCHEMA
    assert payload["project"]["id"] == project_id


def test_route_markdown_success(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = make_project(app)
    response = client.get(f"/projects/{project_id}/rollback-plan.md")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.startswith("# Rollback Plan")


def test_route_unknown_project_404(tmp_path):
    app, client = app_and_client(tmp_path)
    assert client.get("/projects/nope/rollback-plan.json").status_code == 404
    assert client.get("/projects/nope/rollback-plan.md").status_code == 404


def test_secret_guard_over_package(tmp_path):
    # The package builder runs assert_no_secret_values internally; serialising
    # the result must not surface any secret-shaped values.
    from hermes_company_os.secret_guard import secret_violations

    app, _client = app_and_client(tmp_path)
    project_id = make_project(app)
    package = rollback_plan_package(app.state.repository, project_id)
    violations = secret_violations(
        {"rollback_plan_package": json.dumps(package, sort_keys=True)}
    )
    assert violations == []
