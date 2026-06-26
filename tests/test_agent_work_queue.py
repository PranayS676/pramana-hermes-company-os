from __future__ import annotations

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


def test_repository_creates_filters_and_enforces_founder_approval_transition(tmp_path):
    repository = initialized_repository(tmp_path)
    work_item_id = repository.create_agent_work_item(
        title="Review research evidence",
        owner_agent_id="qa-critic",
        status="assigned",
        priority="high",
        summary="Check whether the research brief has source evidence and open risks.",
    )

    assigned = repository.list_agent_work_items(
        status="assigned",
        owner_agent_id="qa-critic",
    )
    assert [item["id"] for item in assigned] == [work_item_id]

    repository.update_agent_work_item(
        work_item_id,
        status="needs_review",
        priority="urgent",
    )
    needs_review = repository.get_agent_work_item(work_item_id)
    assert needs_review["status"] == "needs_review"
    assert needs_review["founder_action_required"] is True

    with pytest.raises(ValueError, match="Founder confirmation"):
        repository.update_agent_work_item(
            work_item_id,
            status="approved",
            priority="urgent",
        )

    repository.update_agent_work_item(
        work_item_id,
        status="approved",
        priority="medium",
        founder_confirmed=True,
    )
    approved = repository.get_agent_work_item(work_item_id)
    assert approved["status"] == "approved"
    assert approved["founder_action_required"] is False


def test_blocked_queue_items_require_reason_and_show_blocker_metadata(tmp_path):
    repository = initialized_repository(tmp_path)

    with pytest.raises(ValueError, match="blocker reason"):
        repository.create_agent_work_item(
            title="Blocked without reason",
            owner_agent_id="chief-of-staff",
            status="blocked",
            summary="This should not persist without an unblock action.",
        )

    work_item_id = repository.create_agent_work_item(
        title="Resolve acceptance blocker",
        owner_agent_id="chief-of-staff",
        status="blocked",
        priority="urgent",
        summary="Acceptance cannot proceed until the missing evidence is named.",
        blocked_reason="Missing test evidence from the acceptance package.",
        blocked_owner="Test Automation Agent",
    )
    blocked = repository.get_agent_work_item(work_item_id)
    assert blocked["status"] == "blocked"
    assert blocked["blocked_reason"] == "Missing test evidence from the acceptance package."
    assert blocked["blocked_owner"] == "Test Automation Agent"
    assert blocked["blocked_age_label"]


def test_product_wizard_project_syncs_read_first_queue_items(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    items = app.state.repository.list_agent_work_items(project_id=project_id)
    by_stage = {item["stage_id"]: item for item in items}
    assert len(items) == 6
    assert by_stage["research"]["status"] == "assigned"
    assert by_stage["prd"]["status"] == "planned"

    project_page = client.get(f"/projects/{project_id}")
    agent_page = client.get("/agents/research-agent")
    queue_page = client.get(f"/queue?project_id={project_id}")

    assert project_page.status_code == 200
    assert "Project agent queue" in project_page.text
    assert "Research for Atlas Brief" in project_page.text
    assert agent_page.status_code == 200
    assert "Agent Work Queue" in agent_page.text
    assert "Research for Atlas Brief" in agent_page.text
    assert queue_page.status_code == 200
    assert "Agent work queue" in queue_page.text
    assert "Dashboard state is the source of truth" in queue_page.text
    assert secret_violations(
        {
            "project_page": project_page.text,
            "agent_page": agent_page.text,
            "queue_page": queue_page.text,
        }
    ) == []


def test_product_wizard_generation_moves_stage_queue_item_to_needs_review(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )

    assert response.status_code == 303, response.text
    research_item = next(
        item
        for item in app.state.repository.list_agent_work_items(project_id=project_id)
        if item["stage_id"] == "research"
    )
    assert research_item["status"] == "needs_review"
    assert research_item["founder_action_required"] is True
    assert research_item["artifact_id"]
    assert research_item["decision_id"]

    queue_page = client.get(f"/queue?project_id={project_id}&status=needs_review")
    assert "Needs review" in queue_page.text
    assert "Founder required" in queue_page.text


def test_queue_route_creates_filters_and_updates_manual_item(tmp_path):
    app, client = app_and_client(tmp_path)
    created = client.post(
        "/queue",
        data={
            "title": "Clarify code plan owner",
            "owner_agent_id": "engineering-manager",
            "status": "blocked",
            "priority": "urgent",
            "summary": "Implementation cannot start until the backend owner is named.",
            "blocked_reason": "Backend owner is missing from the code plan.",
            "blocked_owner": "Engineering Manager",
            "return_to": "/queue",
        },
        follow_redirects=False,
    )

    assert created.status_code == 303, created.text
    item = app.state.repository.list_agent_work_items(status="blocked")[0]
    filtered = client.get("/queue?status=blocked&owner_agent_id=engineering-manager")
    assert "Clarify code plan owner" in filtered.text
    assert "Backend owner is missing" in filtered.text

    updated = client.post(
        f"/queue/{item['id']}",
        data={
            "status": "assigned",
            "priority": "high",
            "owner_agent_id": "backend-engineer",
            "blocked_reason": "",
            "blocked_owner": "",
            "return_to": "/queue",
        },
        follow_redirects=False,
    )

    assert updated.status_code == 303, updated.text
    saved = app.state.repository.get_agent_work_item(item["id"])
    assert saved["status"] == "assigned"
    assert saved["owner_agent_id"] == "backend-engineer"
    assert saved["blocked_reason"] == ""


def test_queue_route_rejects_secret_policy_inputs(tmp_path):
    app, client = app_and_client(tmp_path)

    response = client.post(
        "/queue",
        data={
            "title": "WORKFLOW_SECRET=" + "do-not-store-here",
            "owner_agent_id": "chief-of-staff",
            "status": "planned",
            "priority": "medium",
            "summary": "This should be rejected before persistence.",
            "return_to": "/queue",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert app.state.repository.list_agent_work_items() == []
