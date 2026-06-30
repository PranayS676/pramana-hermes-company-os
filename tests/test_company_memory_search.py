from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from hermes_company_os.database import initialize_database
from hermes_company_os.main import create_app
from hermes_company_os.project_memory import company_memory_search_package
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def future_iso(days: int = 60) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def seed_two_projects_with_memory(repository: CompanyRepository) -> dict[str, str]:
    project_a = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI diligence workspace.",
    )
    project_b = repository.create_structured_project(
        name="Beacon Signals",
        founder_idea="Market signal monitor.",
    )
    ids: dict[str, str] = {"project_a": project_a, "project_b": project_b}
    ids["atlas_active"] = repository.create_project_memory_entry(
        source_key="project:atlas:strategy",
        project_id=project_a,
        category="product_strategy",
        memory_type="decision",
        owner_agent_id="product-manager",
        source="prd-review",
        title="Focus Atlas on diligence teams",
        summary="The Atlas wedge stays on corporate development diligence.",
        body="Avoid expanding into a generic research workspace in V1.",
        confidence="high",
        status="active",
        pinned=True,
        review_after=future_iso(),
        expires_at=future_iso(90),
    )
    ids["beacon_active"] = repository.create_project_memory_entry(
        source_key="project:beacon:strategy",
        project_id=project_b,
        category="product_strategy",
        memory_type="decision",
        owner_agent_id="product-manager",
        source="prd-review",
        title="Beacon targets market analysts",
        summary="Beacon prioritizes early market signal detection for analysts.",
        body="Keep diligence integrations out of Beacon V1 scope.",
        confidence="medium",
        status="active",
        pinned=False,
        review_after=future_iso(),
        expires_at=future_iso(90),
    )
    ids["beacon_retired"] = repository.create_project_memory_entry(
        source_key="project:beacon:retired",
        project_id=project_b,
        category="rejected_idea",
        memory_type="decision",
        owner_agent_id="product-manager",
        source="prd-review",
        title="Retired Beacon connector",
        summary="A retired diligence connector idea for Beacon.",
        body="The connector idea was retired for Beacon V1.",
        confidence="low",
        status="retired",
        pinned=False,
        review_after="",
        expires_at="",
    )
    ids["company_standard"] = repository.create_project_memory_entry(
        source_key="company:technical-standard",
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
        expires_at=future_iso(90),
    )
    return ids


def test_search_company_memory_returns_entries_across_projects(tmp_path):
    repository = initialized_repository(tmp_path)
    ids = seed_two_projects_with_memory(repository)

    results = repository.search_company_memory()
    result_ids = {entry["id"] for entry in results}

    assert ids["atlas_active"] in result_ids
    assert ids["beacon_active"] in result_ids
    assert ids["company_standard"] in result_ids
    # Active is the default status, retired excluded.
    assert ids["beacon_retired"] not in result_ids
    # Cross-project: entries from both Atlas and Beacon are present.
    project_ids = {entry["project_id"] for entry in results}
    assert ids["project_a"] in project_ids
    assert ids["project_b"] in project_ids


def test_search_company_memory_text_filter_matches_title_summary_body(tmp_path):
    repository = initialized_repository(tmp_path)
    ids = seed_two_projects_with_memory(repository)

    by_title = repository.search_company_memory(query="Beacon targets")
    by_body = repository.search_company_memory(query="generic research workspace")
    by_summary = repository.search_company_memory(query="market signal detection")

    assert {entry["id"] for entry in by_title} == {ids["beacon_active"]}
    assert {entry["id"] for entry in by_body} == {ids["atlas_active"]}
    assert {entry["id"] for entry in by_summary} == {ids["beacon_active"]}


def test_search_company_memory_category_filter(tmp_path):
    repository = initialized_repository(tmp_path)
    ids = seed_two_projects_with_memory(repository)

    technical = repository.search_company_memory(category="technical_standard")

    assert {entry["id"] for entry in technical} == {ids["company_standard"]}


def test_search_company_memory_status_defaults_to_active_and_can_request_retired(tmp_path):
    repository = initialized_repository(tmp_path)
    ids = seed_two_projects_with_memory(repository)

    default_results = repository.search_company_memory()
    retired_results = repository.search_company_memory(status="retired")

    assert ids["beacon_retired"] not in {entry["id"] for entry in default_results}
    assert {entry["id"] for entry in retired_results} == {ids["beacon_retired"]}


def test_search_company_memory_confidence_filter(tmp_path):
    repository = initialized_repository(tmp_path)
    ids = seed_two_projects_with_memory(repository)

    high = repository.search_company_memory(confidence="high")
    high_ids = {entry["id"] for entry in high}

    assert ids["atlas_active"] in high_ids
    assert ids["company_standard"] in high_ids
    assert ids["beacon_active"] not in high_ids


def test_company_memory_search_package_groups_results_with_project_linkage(tmp_path):
    repository = initialized_repository(tmp_path)
    ids = seed_two_projects_with_memory(repository)

    package = company_memory_search_package(repository, query="", category="", status="active")

    assert package["schema"] == "company_memory_search_package_v1"
    assert package["aggregate"]["result_count"] >= 3
    result_ids = {entry["id"] for entry in package["results"]}
    assert ids["atlas_active"] in result_ids
    assert ids["company_standard"] in result_ids
    # Project linkage is exposed on results.
    atlas = next(e for e in package["results"] if e["id"] == ids["atlas_active"])
    assert atlas["project_id"] == ids["project_a"]
    assert atlas["project_name"] == "Atlas Brief"
    company = next(e for e in package["results"] if e["id"] == ids["company_standard"])
    assert company["scope_label"] == "company-wide"
    # No secrets in the package.
    assert secret_violations(
        {"package": json.dumps(package, sort_keys=True)}
    ) == []


def test_memory_search_json_route_success_and_filters(tmp_path):
    app, client = app_and_client(tmp_path)
    ids = seed_two_projects_with_memory(app.state.repository)

    response = client.get("/memory/search.json", params={"q": "Beacon targets"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["schema"] == "company_memory_search_package_v1"
    assert {entry["id"] for entry in payload["results"]} == {ids["beacon_active"]}
    assert secret_violations({"payload": json.dumps(payload, sort_keys=True)}) == []


def test_memory_search_html_route_renders_results_and_is_secret_safe(tmp_path):
    app, client = app_and_client(tmp_path)
    seed_two_projects_with_memory(app.state.repository)

    response = client.get("/memory/search")

    assert response.status_code == 200
    assert "Company memory search" in response.text
    assert "Focus Atlas on diligence teams" in response.text
    assert "Beacon targets market analysts" in response.text
    assert "Atlas Brief" in response.text
    assert secret_violations({"html": response.text}) == []


def test_memory_search_html_route_empty_result(tmp_path):
    app, client = app_and_client(tmp_path)
    seed_two_projects_with_memory(app.state.repository)

    response = client.get("/memory/search", params={"q": "no-such-memory-anywhere"})

    assert response.status_code == 200
    assert "Focus Atlas on diligence teams" not in response.text
    # Empty-state messaging is present.
    assert "No matching memory" in response.text
