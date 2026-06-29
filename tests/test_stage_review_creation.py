"""Tests for pre-approval stage review creation (M6 follow-up).

Resolves the chicken-and-egg between M6 enforcement (stage approval requires
reviews to exist) and the post-acceptance review batch (which requires the
stage to already be approved): ``generate_stage_reviews`` records the required
reviews against the stage's *draft* artifact so they can gate the approval.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.database import initialize_database
from hermes_company_os.main import create_app
from hermes_company_os.multi_agent_review import generate_stage_reviews
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


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient) -> str:
    response = client.post("/projects", data=STRUCTURED_INTAKE, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def generate_current_stage(client: TestClient, project_id: str) -> None:
    generated = client.post(
        f"/projects/{project_id}/stages/current/generate", follow_redirects=False
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


# --- service ------------------------------------------------------------------


def test_generate_stage_reviews_creates_required_records(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository

    package = generate_stage_reviews(repository, project_id, "acceptance")

    assert package["stage_id"] == "acceptance"
    assert len(package["created_review_ids"]) == 2
    assert package["requirements"]["approval_allowed"] is True

    reviewer_ids = {
        record["reviewer_agent_id"]
        for record in repository.list_project_review_records(project_id)
    }
    assert reviewer_ids == {"qa-critic", "test-automation-agent"}


def test_generate_stage_reviews_resolves_chicken_and_egg(tmp_path):
    """End-to-end: with enforcement on, generating stage reviews unblocks approval."""

    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository
    repository.configure_review_enforcement(True)

    # Before reviews exist, enforcement blocks acceptance approval.
    with pytest.raises(ValueError):
        repository.approve_stage(project_id, "acceptance")

    # Generate the required pre-approval reviews against the draft artifact.
    generate_stage_reviews(repository, project_id, "acceptance")

    # Now approval succeeds.
    repository.approve_stage(project_id, "acceptance")
    stage = repository.get_project_wizard_stage(project_id, "acceptance")
    assert stage["status"] == "approved"


def test_generate_stage_reviews_is_idempotent(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository

    generate_stage_reviews(repository, project_id, "acceptance")
    generate_stage_reviews(repository, project_id, "acceptance")

    records = repository.list_project_review_records(project_id)
    assert len(records) == 2  # no duplicates for the same draft


def test_generate_stage_reviews_ungated_stage_raises(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    repository = app.state.repository

    with pytest.raises(ValueError, match="no required cross-agent reviews"):
        generate_stage_reviews(repository, project_id, "prd")


def test_generate_stage_reviews_missing_artifact_raises(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief", founder_idea="AI due-diligence workspace."
    )

    with pytest.raises(ValueError, match="before requesting its cross-agent reviews"):
        generate_stage_reviews(repository, project_id, "acceptance")


def test_generate_stage_reviews_unknown_project_raises(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    with pytest.raises(ValueError, match="Unknown project"):
        generate_stage_reviews(repository, "does-not-exist", "acceptance")


def test_stage_review_package_is_no_secret(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)
    repository = app.state.repository

    package = generate_stage_reviews(repository, project_id, "acceptance")
    assert secret_violations({"package": json.dumps(package, sort_keys=True)}) == []


# --- route --------------------------------------------------------------------


def test_stage_reviews_route_success(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    drive_to_acceptance_draft(app, client, project_id)

    response = client.post(f"/projects/{project_id}/stages/acceptance/reviews")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stage_id"] == "acceptance"
    assert len(body["created_review_ids"]) == 2
    assert body["requirements"]["approval_allowed"] is True
    assert secret_violations({"body": json.dumps(body, sort_keys=True)}) == []


def test_stage_reviews_route_404_for_unknown_project(tmp_path):
    app, client = app_and_client(tmp_path)
    response = client.post("/projects/does-not-exist/stages/acceptance/reviews")
    assert response.status_code == 404


def test_stage_reviews_route_409_for_ungated_stage(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.post(f"/projects/{project_id}/stages/prd/reviews")
    assert response.status_code == 409
    assert "no required cross-agent reviews" in response.json()["detail"]
