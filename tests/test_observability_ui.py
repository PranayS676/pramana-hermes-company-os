"""Route/UI tests for the M8 observability HTML views.

These exercise the founder-facing HTML rendering of the existing read-only
observability metrics package. They assert founder-visible content (metric
labels and values appear in the rendered HTML), 404 handling for unknown
projects, and that no secret-shaped values leak into the rendered markup.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def _seed_project(repository: CompanyRepository, name: str = "Atlas Brief") -> str:
    return repository.create_structured_project(
        name=name,
        founder_idea="AI diligence workspace.",
    )


# --- Company-wide HTML view -------------------------------------------------


def test_company_observability_html_returns_200(tmp_path):
    _, client = app_and_client(tmp_path)

    response = client.get("/observability")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_company_observability_html_shows_metric_labels(tmp_path):
    _, client = app_and_client(tmp_path)

    response = client.get("/observability")
    body = response.text

    # Roadmap M8 metric vocabulary should be founder-visible in the HTML.
    assert "Observability" in body
    assert "Runs by agent" in body
    assert "Average latency" in body
    assert "Retry count" in body
    assert "Open founder decisions" in body
    assert "Open review findings" in body
    assert "Blocked" in body
    # Company-wide framing.
    assert "Company-wide" in body


def test_company_observability_html_renders_metric_values(tmp_path):
    app, client = app_and_client(tmp_path)
    # Seed a couple of projects so the project count / scope is non-trivial.
    _seed_project(app.state.repository, "Atlas Brief")
    _seed_project(app.state.repository, "Beacon Brief")

    response = client.get("/observability")
    body = response.text

    assert response.status_code == 200
    # Total runs metric value present (zeroed but rendered).
    assert "Total runs" in body
    # Project count value should render the seeded count.
    assert "2" in body


def test_company_observability_html_has_no_secret_values(tmp_path):
    app, client = app_and_client(tmp_path)
    _seed_project(app.state.repository)

    response = client.get("/observability")

    assert secret_violations({"observability_html": response.text}) == []


def test_company_observability_html_links_per_project(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    response = client.get("/observability")

    assert f"/projects/{project_id}/observability" in response.text


# --- Per-project HTML view --------------------------------------------------


def test_project_observability_html_returns_200(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    response = client.get(f"/projects/{project_id}/observability")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    # The project name should appear in the scoped view.
    assert "Atlas Brief" in response.text
    assert "Runs by agent" in response.text


def test_project_observability_html_missing_project_404(tmp_path):
    _, client = app_and_client(tmp_path)

    response = client.get("/projects/does-not-exist/observability")

    assert response.status_code == 404


def test_project_observability_html_has_no_secret_values(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    response = client.get(f"/projects/{project_id}/observability")

    assert secret_violations({"project_observability_html": response.text}) == []


def test_project_observability_html_links_back_to_json_and_md(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    body = client.get(f"/projects/{project_id}/observability").text

    assert f"/projects/{project_id}/observability.json" in body
    assert f"/projects/{project_id}/observability.md" in body


# --- Entry points -----------------------------------------------------------


def test_dashboard_links_to_observability(tmp_path):
    _, client = app_and_client(tmp_path)

    body = client.get("/").text

    assert 'href="/observability"' in body


def test_project_page_links_to_observability(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    body = client.get(f"/projects/{project_id}").text

    assert f"/projects/{project_id}/observability" in body
