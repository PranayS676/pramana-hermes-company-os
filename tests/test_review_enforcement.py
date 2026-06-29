from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.database import initialize_database
from hermes_company_os.main import create_app
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.review_policy import (
    STAGE_REVIEW_POLICIES,
    required_reviewer_ids,
    stage_review_requirements,
)
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
    response = client.post("/projects", data=STRUCTURED_INTAKE, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def generate_current_stage(client: TestClient, project_id: str) -> None:
    generated = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    assert generated.status_code == 303, generated.text


def approve_current_stage(client: TestClient, project_id: str, stage_id: str) -> None:
    approved = client.post(
        f"/projects/{project_id}/stages/{stage_id}/approve",
        data={"approval_note": f"Approve {stage_id}."},
        follow_redirects=False,
    )
    assert approved.status_code == 303, approved.text


def drive_to_acceptance_draft(app, client: TestClient, project_id: str) -> None:
    """Generate+approve through code_plan, then leave a draft acceptance artifact."""

    for _ in range(len(WIZARD_STAGE_IDS)):
        current = app.state.repository.next_actionable_stage(project_id)
        assert current is not None
        stage_id = current["stage_id"]
        generate_current_stage(client, project_id)
        if stage_id == "acceptance":
            return
        approve_current_stage(client, project_id, stage_id)
    pytest.fail("Did not reach acceptance draft")


def seed_reviews(repository, project_id: str, verdicts: dict[str, str]) -> None:
    for agent_id, verdict in verdicts.items():
        repository.create_project_review_record(
            source_key=f"test-review:{project_id}:{agent_id}",
            project_id=project_id,
            review_batch_id="review-batch-test",
            reviewer_agent_id=agent_id,
            reviewer_name=agent_id.replace("-", " ").title(),
            reviewer_role="Test reviewer role for enforcement coverage.",
            verdict=verdict,
            summary=f"{agent_id} recorded a {verdict} verdict for enforcement test.",
            artifact_ids=["wiz-artifact-test"],
            checks=[{"id": "seeded_check", "status": "passed", "detail": "Seeded."}],
            findings=[
                {"severity": "info", "title": "Seeded finding", "detail": "Seeded."}
            ],
        )


# --- policy data --------------------------------------------------------------


def test_acceptance_requires_qa_critic_and_test_automation():
    assert required_reviewer_ids("acceptance") == ("qa-critic", "test-automation-agent")
    assert STAGE_REVIEW_POLICIES["acceptance"] == (
        "qa-critic",
        "test-automation-agent",
    )


def test_ungated_stage_has_no_requirements():
    assert required_reviewer_ids("prd") == ()


# --- enforcement off (preserves current behaviour) ----------------------------


def test_enforcement_off_allows_approval_without_reviews(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository

    # No reviews exist and enforcement is off (default): approval succeeds.
    assert repository.list_project_review_records(project_id) == []
    repository.approve_stage(project_id, "acceptance")

    stage = repository.get_project_wizard_stage(project_id, "acceptance")
    assert stage["status"] == "approved"


# --- enforcement on -----------------------------------------------------------


def test_enforcement_on_blocks_when_reviews_missing(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository
    repository.configure_review_enforcement(True)

    with pytest.raises(ValueError) as excinfo:
        repository.approve_stage(project_id, "acceptance")

    message = str(excinfo.value)
    assert "acceptance" in message
    assert "qa-critic" in message
    assert "test-automation-agent" in message
    # Approval was blocked: stage stays a draft.
    stage = repository.get_project_wizard_stage(project_id, "acceptance")
    assert stage["status"] == "draft"


def test_enforcement_on_allows_approval_when_required_reviews_approved(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository
    seed_reviews(
        repository,
        project_id,
        {"qa-critic": "approved", "test-automation-agent": "approved"},
    )
    repository.configure_review_enforcement(True)

    repository.approve_stage(project_id, "acceptance")

    stage = repository.get_project_wizard_stage(project_id, "acceptance")
    assert stage["status"] == "approved"


def test_enforcement_on_blocks_when_required_reviewer_blocked(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository
    seed_reviews(
        repository,
        project_id,
        {"qa-critic": "blocked", "test-automation-agent": "approved"},
    )
    repository.configure_review_enforcement(True)

    with pytest.raises(ValueError) as excinfo:
        repository.approve_stage(project_id, "acceptance")

    message = str(excinfo.value)
    assert "qa-critic" in message
    assert "blocked" in message
    stage = repository.get_project_wizard_stage(project_id, "acceptance")
    assert stage["status"] == "draft"


def test_enforcement_on_blocks_when_required_reviewer_needs_revision(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository
    seed_reviews(
        repository,
        project_id,
        {"qa-critic": "approved", "test-automation-agent": "needs_revision"},
    )
    repository.configure_review_enforcement(True)

    with pytest.raises(ValueError) as excinfo:
        repository.approve_stage(project_id, "acceptance")

    assert "needs_revision" in str(excinfo.value)
    stage = repository.get_project_wizard_stage(project_id, "acceptance")
    assert stage["status"] == "draft"


def test_enforcement_on_does_not_gate_ungated_stages(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    repository = app.state.repository
    repository.configure_review_enforcement(True)

    # research is the first stage and is not gated; approval works without reviews.
    current = repository.next_actionable_stage(project_id)
    assert current["stage_id"] == "research"
    generate_current_stage(client, project_id)
    repository.approve_stage(project_id, "research")

    stage = repository.get_project_wizard_stage(project_id, "research")
    assert stage["status"] == "approved"


def test_settings_flag_defaults_off():
    assert Settings().review_enforcement_enabled is False


# --- requirements helper / route ----------------------------------------------


def test_stage_review_requirements_reports_missing_and_present(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief", founder_idea="AI due-diligence workspace."
    )

    requirements = stage_review_requirements(repository, project_id, "acceptance")
    assert requirements["gated"] is True
    assert requirements["missing_reviewer_ids"] == [
        "qa-critic",
        "test-automation-agent",
    ]
    assert requirements["approval_allowed"] is False

    seed_reviews(
        repository,
        project_id,
        {"qa-critic": "approved", "test-automation-agent": "approved"},
    )
    requirements = stage_review_requirements(repository, project_id, "acceptance")
    assert requirements["present_reviewer_ids"] == [
        "qa-critic",
        "test-automation-agent",
    ]
    assert requirements["missing_reviewer_ids"] == []
    assert requirements["approval_allowed"] is True


def test_review_requirements_route_returns_json(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    repository = app.state.repository

    response = client.get(
        f"/projects/{project_id}/stages/acceptance/review-requirements.json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stage_id"] == "acceptance"
    assert body["gated"] is True
    assert body["missing_reviewer_ids"] == ["qa-critic", "test-automation-agent"]
    assert body["approval_allowed"] is False
    assert secret_violations({"requirements": json.dumps(body, sort_keys=True)}) == []

    seed_reviews(
        repository,
        project_id,
        {"qa-critic": "approved", "test-automation-agent": "approved"},
    )
    response = client.get(
        f"/projects/{project_id}/stages/acceptance/review-requirements.json"
    )
    body = response.json()
    assert body["approval_allowed"] is True
    assert body["present_reviewer_ids"] == ["qa-critic", "test-automation-agent"]


def test_review_requirements_route_404_for_unknown_project(tmp_path):
    app, client = app_and_client(tmp_path)
    response = client.get(
        "/projects/does-not-exist/stages/acceptance/review-requirements.json"
    )
    assert response.status_code == 404
