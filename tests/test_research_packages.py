from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.database import get_schema_version, initialize_database
from hermes_company_os.main import create_app
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.research_packages import (
    build_research_package,
    research_package_markdown,
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

SAMPLE_FINDINGS = [
    {
        "title": "Blocked state is hidden behind hover",
        "severity": "high",
        "detail": "Blocked reason only appears on hover.",
        "evidence": "Queue row renders blocker in a tooltip on /queue.",
        "surface": "/queue",
    },
    {
        "title": "Approval pill says ready without context",
        "severity": "critical",
        "detail": "`ready` does not say ready for what.",
        "evidence": "Status pill text on project page.",
        "surface": "project page",
    },
    {
        "title": "Minor spacing inconsistency",
        "severity": "low",
        "detail": "Panel padding differs.",
    },
]

SAMPLE_RECOMMENDATIONS = [
    {
        "behavior": "Surface blocked reason and owner inline.",
        "surface": "Queue row component",
        "acceptance_signal": "Blocked items show reason and owner without hover.",
    }
]

SAMPLE_DECISIONS = [
    {
        "decision": "Should blocked rows default to expanded?",
        "why_it_matters": "Founder must see blockers immediately.",
        "default_recommendation": "Default to expanded for blocked rows.",
        "impact_if_deferred": "Founder may miss urgent blockers.",
    }
]


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient) -> str:
    response = client.post("/projects", data=STRUCTURED_INTAKE, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def first_project_id(repository: CompanyRepository) -> str:
    repository.create_structured_project("Atlas Brief", "AI diligence workspace.")
    return repository.list_projects()[0]["id"]


# --- schema -------------------------------------------------------------


def test_research_packages_schema_is_initialized(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(research_packages)").fetchall()
        }
        version = get_schema_version(connection)
    assert {"id", "project_id", "method", "status", "findings_json"} <= columns
    assert version >= 3


# --- builder + markdown -------------------------------------------------


def test_build_research_package_normalizes_and_sorts_findings():
    package = build_research_package(
        title="Queue clarity",
        research_thread="Agent Work Queue UX",
        research_question="Are blockers visible?",
        method="State analysis",
        findings=SAMPLE_FINDINGS,
        recommendations=SAMPLE_RECOMMENDATIONS,
        founder_decisions_needed=SAMPLE_DECISIONS,
    )
    assert package["method"] == "state_analysis"
    # critical sorts ahead of high which sorts ahead of low
    severities = [finding["severity"] for finding in package["findings"]]
    assert severities == ["critical", "high", "low"]
    assert package["recommendations"][0]["behavior"].startswith("Surface")


def test_build_research_package_rejects_empty_title():
    with pytest.raises(ValueError):
        build_research_package(
            title="   ",
            research_thread="Thread",
            research_question="Q?",
            method="workflow_analysis",
        )


def test_build_research_package_rejects_unknown_method():
    with pytest.raises(ValueError):
        build_research_package(
            title="t",
            research_thread="thread",
            research_question="q?",
            method="not_a_method",
        )


def test_research_package_markdown_includes_sections():
    package = build_research_package(
        title="Queue clarity",
        research_thread="Agent Work Queue UX",
        research_question="Are blockers visible?",
        method="state_analysis",
        findings=SAMPLE_FINDINGS,
        recommendations=SAMPLE_RECOMMENDATIONS,
        founder_decisions_needed=SAMPLE_DECISIONS,
    )
    markdown = research_package_markdown(package)
    assert "# UI/UX Research Package: Queue clarity" in markdown
    assert "## Findings" in markdown
    assert "## Implementation Recommendations" in markdown
    assert "## Founder Decisions Needed" in markdown
    assert "[Critical]" in markdown


# --- secret guard -------------------------------------------------------


def test_build_research_package_blocks_secret_values():
    leak = "".join(["xoxb-", "1234567890", "abcdefghij"])
    with pytest.raises(ValueError):
        build_research_package(
            title="Leak",
            research_thread="thread",
            research_question="q?",
            method="workflow_analysis",
            summary=leak,
        )


def test_stored_and_rendered_text_is_secret_clean(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = first_project_id(repository)
    package_id = repository.create_research_package(
        title="Queue clarity",
        research_thread="Agent Work Queue UX",
        research_question="Are blockers visible?",
        method="state_analysis",
        project_id=project_id,
        findings=SAMPLE_FINDINGS,
        recommendations=SAMPLE_RECOMMENDATIONS,
        founder_decisions_needed=SAMPLE_DECISIONS,
    )
    stored = repository.get_research_package(package_id)
    markdown = research_package_markdown(stored)
    assert secret_violations({"stored": str(stored), "markdown": markdown}) == []


# --- repository CRUD ----------------------------------------------------


def test_create_list_get_research_package(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = first_project_id(repository)
    package_id = repository.create_research_package(
        title="Queue clarity",
        research_thread="Agent Work Queue UX",
        research_question="Are blockers visible?",
        method="state_analysis",
        project_id=project_id,
        findings=SAMPLE_FINDINGS,
    )
    fetched = repository.get_research_package(package_id)
    assert fetched is not None
    assert fetched["title"] == "Queue clarity"
    assert fetched["project_id"] == project_id
    assert len(fetched["findings"]) == 3

    listed = repository.list_research_packages(project_id=project_id)
    assert [package["id"] for package in listed] == [package_id]


def test_get_missing_research_package_returns_none(tmp_path):
    repository = initialized_repository(tmp_path)
    assert repository.get_research_package("research-missing") is None


def test_create_research_package_unknown_project_raises(tmp_path):
    repository = initialized_repository(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        repository.create_research_package(
            title="x",
            research_thread="thread",
            research_question="q?",
            method="state_analysis",
            project_id="project-does-not-exist",
        )


def test_retire_hides_package_then_reactivate(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = first_project_id(repository)
    package_id = repository.create_research_package(
        title="Queue clarity",
        research_thread="Agent Work Queue UX",
        research_question="Are blockers visible?",
        method="state_analysis",
        project_id=project_id,
    )
    repository.retire_research_package(package_id)
    assert repository.list_research_packages(project_id=project_id) == []
    assert (
        len(repository.list_research_packages(project_id=project_id, include_retired=True))
        == 1
    )
    repository.update_research_package_status(package_id, "active")
    assert len(repository.list_research_packages(project_id=project_id)) == 1


def test_retire_unknown_package_raises(tmp_path):
    repository = initialized_repository(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        repository.retire_research_package("research-missing")


# --- routes -------------------------------------------------------------


def test_create_and_list_routes(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/research",
        data={
            "title": "Queue clarity",
            "research_thread": "Agent Work Queue UX",
            "research_question": "Are blockers visible?",
            "method": "state_analysis",
            "finding_title": "Blocked state hidden",
            "finding_severity": "high",
            "finding_evidence": "Hover-only blocker on /queue.",
            "recommendation_behavior": "Show blocker inline.",
            "founder_decision": "Default blocked rows to expanded?",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    json_response = client.get(f"/projects/{project_id}/research.json")
    assert json_response.status_code == 200
    payload = json_response.json()
    assert payload["count"] == 1
    package_id = payload["packages"][0]["id"]

    html_response = client.get(f"/projects/{project_id}/research")
    assert html_response.status_code == 200
    assert "Queue clarity" in html_response.text

    md_response = client.get(f"/research/packages/{package_id}.md")
    assert md_response.status_code == 200
    assert "## Findings" in md_response.text


def test_routes_404_for_unknown_project_and_package(tmp_path):
    _, client = app_and_client(tmp_path)
    assert client.get("/projects/nope/research.json").status_code == 404
    assert client.get("/projects/nope/research").status_code == 404
    assert client.get("/research/packages/nope.json").status_code == 404
    assert client.get("/research/packages/nope.md").status_code == 404


def test_create_route_invalid_method_returns_409(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    response = client.post(
        f"/projects/{project_id}/research",
        data={
            "title": "Queue clarity",
            "research_thread": "Agent Work Queue UX",
            "research_question": "Are blockers visible?",
            "method": "not_a_method",
        },
        follow_redirects=False,
    )
    assert response.status_code == 409


def test_retire_route_then_reactivate(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    client.post(
        f"/projects/{project_id}/research",
        data={
            "title": "Queue clarity",
            "research_thread": "Agent Work Queue UX",
            "research_question": "Are blockers visible?",
            "method": "state_analysis",
        },
        follow_redirects=False,
    )
    package_id = client.get(f"/projects/{project_id}/research.json").json()["packages"][0][
        "id"
    ]
    retire = client.post(
        f"/projects/{project_id}/research/{package_id}",
        data={"research_action": "retire"},
        follow_redirects=False,
    )
    assert retire.status_code == 303
    stored = client.get(f"/research/packages/{package_id}.json").json()
    assert stored["status"] == "retired"
