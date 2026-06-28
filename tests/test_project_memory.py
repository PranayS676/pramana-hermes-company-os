from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

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


def fake_provider_assignment() -> str:
    return "".join(["OPEN", "AI", "_", "API", "_", "KEY", "=", "s", "k", "-", "a" * 32])


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


def future_iso(days: int = 30) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def past_iso(days: int = 1) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def test_project_memory_schema_is_initialized(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(project_memory_entries)")
        }

    assert {
        "id",
        "source_key",
        "project_id",
        "category",
        "memory_type",
        "owner_agent_id",
        "source",
        "source_artifact_id",
        "source_decision_id",
        "title",
        "summary",
        "body",
        "confidence",
        "status",
        "pinned",
        "review_after",
        "expires_at",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_project_memory_repository_filters_reusable_and_stale_entries(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI diligence workspace.",
    )
    company_memory_id = repository.create_project_memory_entry(
        source_key="company:technical-standard:mock-data",
        project_id="",
        category="technical_standard",
        memory_type="standard",
        owner_agent_id="engineering-manager",
        source="founder-control-plane",
        title="Use mock data in public demos",
        summary="Public demo work must not include real customer files.",
        body="Use fixture data and synthetic examples in public demo artifacts.",
        confidence="high",
        status="active",
        pinned=True,
        review_after=future_iso(),
        expires_at=future_iso(60),
    )
    project_memory_id = repository.create_project_memory_entry(
        source_key="project:atlas:accepted-risk",
        project_id=project_id,
        category="accepted_risk",
        memory_type="decision",
        owner_agent_id="qa-critic",
        source="acceptance-review",
        title="Accept internal-only research gaps",
        summary="Internal launch can proceed with a clearly owned follow-up interview.",
        body="Founder accepted the research-depth risk for T0 internal usage.",
        confidence="medium",
        status="active",
        pinned=False,
        review_after=future_iso(),
        expires_at=future_iso(60),
    )
    expired_memory_id = repository.create_project_memory_entry(
        source_key="project:atlas:expired-learning",
        project_id=project_id,
        category="launch_learning",
        memory_type="lesson",
        owner_agent_id="chief-of-staff",
        source="old-launch",
        title="Old onboarding assumption",
        summary="This should require founder review before reuse.",
        body="Expired launch lesson.",
        confidence="low",
        status="active",
        pinned=True,
        review_after=past_iso(2),
        expires_at=past_iso(),
    )
    retired_memory_id = repository.create_project_memory_entry(
        source_key="project:atlas:retired-idea",
        project_id=project_id,
        category="rejected_idea",
        memory_type="decision",
        owner_agent_id="product-manager",
        source="prd-review",
        title="Retired enterprise connector",
        summary="Do not use retired memory for new generation.",
        body="The connector idea was retired for V1.",
        confidence="high",
        status="retired",
        pinned=False,
        review_after="",
        expires_at="",
    )

    reusable = repository.list_reusable_project_memory_entries(project_id)
    all_entries = repository.list_project_memory_entries(
        project_id=project_id,
        include_company_wide=True,
        include_retired=True,
        include_expired=True,
    )
    reusable_ids = {entry["id"] for entry in reusable}
    all_ids = {entry["id"] for entry in all_entries}

    assert company_memory_id in reusable_ids
    assert project_memory_id in reusable_ids
    assert expired_memory_id not in reusable_ids
    assert retired_memory_id not in reusable_ids
    assert {company_memory_id, project_memory_id, expired_memory_id, retired_memory_id}
    assert {company_memory_id, project_memory_id, expired_memory_id, retired_memory_id}.issubset(
        all_ids
    )
    assert next(entry for entry in reusable if entry["id"] == company_memory_id)[
        "scope_label"
    ] == "company-wide"
    assert next(entry for entry in all_entries if entry["id"] == expired_memory_id)[
        "expired"
    ] is True


def test_project_memory_rejects_secret_shaped_content(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI diligence workspace.",
    )

    with pytest.raises(ValueError):
        repository.create_project_memory_entry(
            source_key="project:atlas:secret",
            project_id=project_id,
            category="technical_standard",
            memory_type="standard",
            owner_agent_id="engineering-manager",
            source="manual",
            title="Unsafe provider setup",
            summary="Contains a fake secret shape.",
            body=f"Do not store {fake_provider_assignment()}",
            confidence="high",
            status="active",
            pinned=True,
            review_after="",
            expires_at="",
        )


def test_project_memory_exports_and_ui_render_reviewable_context(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    memory_id = app.state.repository.create_project_memory_entry(
        source_key="project:atlas:founder-preference",
        project_id=project_id,
        category="founder_preference",
        memory_type="preference",
        owner_agent_id="chief-of-staff",
        source="founder-control-plane",
        title="Keep public demo data synthetic",
        summary="Founder prefers public demos that prove workflow without customer files.",
        body="Use generated companies, fixture risks, and synthetic diligence notes.",
        confidence="high",
        status="active",
        pinned=True,
        review_after=future_iso(),
        expires_at=future_iso(60),
    )

    json_response = client.get(f"/projects/{project_id}/memory.json")
    markdown_response = client.get(f"/projects/{project_id}/memory.md")
    project_page = client.get(f"/projects/{project_id}")
    css = client.get("/static/styles.css")
    payload = json_response.json()

    assert json_response.status_code == 200
    assert payload["schema"] == "project_memory_package_v1"
    assert payload["project"]["id"] == project_id
    assert payload["aggregate"]["total_count"] == 1
    assert payload["aggregate"]["reusable_count"] == 1
    assert payload["entries"][0]["id"] == memory_id
    assert payload["entries"][0]["reusable"] is True
    assert markdown_response.status_code == 200
    assert "Project Memory Package" in markdown_response.text
    assert "Keep public demo data synthetic" in markdown_response.text
    assert project_page.status_code == 200
    assert 'id="project-memory"' in project_page.text
    assert "Project Memory" in project_page.text
    assert "Reusable context" in project_page.text
    assert "Auto-reuse policy" in project_page.text
    assert "Allowed auto-reuse categories" in project_page.text
    assert "founder_approved_product_wizard_memory_policy_v1" in project_page.text
    assert "Founder preference" in project_page.text
    assert "Keep public demo data synthetic" in project_page.text
    assert "Memory package JSON" in project_page.text
    assert css.status_code == 200
    assert ".project-memory-panel" in css.text
    assert ".memory-policy-card" in css.text
    assert ".audit-chip-list" in css.text
    assert ".memory-entry-row" in css.text
    assert secret_violations(
        {
            "json": json.dumps(payload, sort_keys=True),
            "markdown": markdown_response.text,
            "project_page": project_page.text,
            "css": css.text,
        }
    ) == []


def test_project_memory_create_and_retire_routes_are_founder_gated_ui_actions(tmp_path):
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
            "review_after": future_iso(),
            "expires_at": future_iso(90),
        },
        follow_redirects=False,
    )
    entries = app.state.repository.list_project_memory_entries(project_id=project_id)
    memory_id = entries[0]["id"]
    retired = client.post(
        f"/projects/{project_id}/memory/{memory_id}",
        data={"memory_action": "retire"},
        follow_redirects=False,
    )
    retired_entry = app.state.repository.get_project_memory_entry(memory_id)

    assert created.status_code == 303
    assert len(entries) == 1
    assert entries[0]["title"] == "Start with acquisition diligence teams"
    assert entries[0]["pinned"] is True
    assert retired.status_code == 303
    assert retired_entry["status"] == "retired"
    assert app.state.repository.list_reusable_project_memory_entries(project_id) == []
