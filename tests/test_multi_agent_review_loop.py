from __future__ import annotations

import json

import pytest
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
        data={"approval_note": f"Approve {stage_id} for review loop test."},
        follow_redirects=False,
    )
    assert approved.status_code == 303, approved.text
    return stage_id


def approve_until_stage(
    app,
    client: TestClient,
    project_id: str,
    target_stage_id: str,
) -> list[str]:
    approved = []
    for _ in range(len(WIZARD_STAGE_IDS)):
        stage_id = generate_and_approve_current_stage(app, client, project_id)
        approved.append(stage_id)
        if stage_id == target_stage_id:
            return approved
    pytest.fail(f"Did not reach {target_stage_id}; approved {approved}")


def test_multi_agent_review_generation_waits_for_approved_plan_and_acceptance(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/multi-agent-review",
        follow_redirects=False,
    )
    package_response = client.get(f"/projects/{project_id}/multi-agent-review.json")
    project_page = client.get(f"/projects/{project_id}")

    assert response.status_code == 409
    assert "approved code plan and acceptance package" in response.json()["detail"]
    assert app.state.repository.list_project_review_records(project_id) == []
    assert package_response.status_code == 200
    assert package_response.json()["aggregate"]["status"] == "blocked"
    assert "Multi-agent Review" in project_page.text
    assert "Review waits for approved code plan and acceptance package" in project_page.text
    assert secret_violations({"project_page": project_page.text}) == []


def test_multi_agent_review_loop_creates_idempotent_reviewer_records(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    approve_until_stage(app, client, project_id, "acceptance")

    first = client.post(
        f"/projects/{project_id}/multi-agent-review",
        follow_redirects=False,
    )
    second = client.post(
        f"/projects/{project_id}/multi-agent-review",
        follow_redirects=False,
    )
    records = app.state.repository.list_project_review_records(project_id)
    package_response = client.get(f"/projects/{project_id}/multi-agent-review.json")
    markdown_response = client.get(f"/projects/{project_id}/multi-agent-review.md")
    project_page = client.get(f"/projects/{project_id}")
    package = package_response.json()
    reviewer_ids = [record["reviewer_agent_id"] for record in records]

    assert first.status_code == 303
    assert second.status_code == 303
    assert len(records) == 5
    assert reviewer_ids == [
        "qa-critic",
        "test-automation-agent",
        "product-manager",
        "engineering-manager",
        "ui-ux-research-agent",
    ]
    assert len({record["review_batch_id"] for record in records}) == 1
    assert all(record["verdict"] == "approved" for record in records)
    assert all(record["checks"] for record in records)
    assert all(record["findings"] for record in records)
    assert package_response.status_code == 200
    assert package["schema"] == "multi_agent_review_package_v1"
    assert package["aggregate"]["status"] == "approved"
    assert package["aggregate"]["reviewer_count"] == 5
    assert package["acceptance_rules"][0]["id"] == "approved_source_artifacts"
    assert package["reviewers"][-1]["reviewer_agent_id"] == "ui-ux-research-agent"
    assert markdown_response.status_code == 200
    assert "Multi-Agent Review Package" in markdown_response.text
    assert "UI/UX Research Agent" in markdown_response.text
    assert project_page.status_code == 200
    assert "Multi-agent Review" in project_page.text
    assert "5 reviewer records" in project_page.text
    assert "ui-ux-research-agent" in project_page.text
    assert "Review approved" in project_page.text
    assert secret_violations(
        {
            "package": json.dumps(package, sort_keys=True),
            "markdown": markdown_response.text,
            "project_page": project_page.text,
            "records": json.dumps(records, sort_keys=True),
        }
    ) == []
