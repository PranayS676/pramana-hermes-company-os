"""M7 operating-loop UI: read-only founder view of external-dispatch deliveries.

Safety contract under test:
- These routes are STRICTLY READ-ONLY. They render existing
  ``external_dispatch_deliveries`` rows; they never send, call live Hermes, flip
  flags, or write state. No delivery is seeded via a live path here.
- Rendered HTML must be secret-free (``secret_violations`` over the page body).
"""

from __future__ import annotations

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


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient) -> str:
    response = client.post("/projects", data=STRUCTURED_INTAKE, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def seed_delivery(repository, project_id: str, **overrides) -> dict:
    """Seed a delivery row DIRECTLY via the repository (no live send path)."""
    payload = {
        "idempotency_key": "slack:slack-standup-preview:abc123",
        "project_id": project_id,
        "item_id": "slack-standup-preview",
        "platform": "slack",
        "action": "post_message_preview",
        "command_boundary": "hermes_command_boundary",
        "contract_sha256": "c" * 64,
        "argv_sha256": "a" * 64,
        "status": "succeeded",
        "external_id": "sent-slack-standup-preview",
        "result": {"detail": "Fake adapter accepted the real-form command."},
    }
    payload.update(overrides)
    return repository.record_external_dispatch_delivery(**payload)


# --------------------------------------------------------------------------- #
# Company-wide page renders with expected labels.
# --------------------------------------------------------------------------- #
def test_company_operating_loop_renders_expected_labels(tmp_path):
    _, client = app_and_client(tmp_path)
    response = client.get("/operating-loop")
    assert response.status_code == 200
    body = response.text
    assert "operating loop" in body.lower()
    assert "Total deliveries" in body
    assert "Deliveries by platform" in body
    assert "Deliveries by status" in body
    assert "Delivery records" in body


# --------------------------------------------------------------------------- #
# Empty state renders gracefully (default demo state has no deliveries).
# --------------------------------------------------------------------------- #
def test_company_operating_loop_empty_state(tmp_path):
    _, client = app_and_client(tmp_path)
    response = client.get("/operating-loop")
    assert response.status_code == 200
    assert "No external-dispatch activity yet." in response.text


def test_project_operating_loop_empty_state(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    response = client.get(f"/projects/{project_id}/operating-loop")
    assert response.status_code == 200
    assert "No external-dispatch activity yet." in response.text


# --------------------------------------------------------------------------- #
# Per-project page: 200 for known project, 404 for unknown.
# --------------------------------------------------------------------------- #
def test_project_operating_loop_404_for_unknown_project(tmp_path):
    _, client = app_and_client(tmp_path)
    response = client.get("/projects/does-not-exist/operating-loop")
    assert response.status_code == 404


def test_project_operating_loop_renders_for_known_project(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    response = client.get(f"/projects/{project_id}/operating-loop")
    assert response.status_code == 200
    assert "Atlas Brief operating loop" in response.text


# --------------------------------------------------------------------------- #
# A seeded delivery appears in both the per-project and company-wide views.
# --------------------------------------------------------------------------- #
def test_seeded_delivery_appears_in_project_view(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    seed_delivery(app.state.repository, project_id)

    response = client.get(f"/projects/{project_id}/operating-loop")
    body = response.text
    assert response.status_code == 200
    assert "slack:slack-standup-preview:abc123" in body
    assert "slack-standup-preview" in body
    assert "sent-slack-standup-preview" in body
    assert "post_message_preview" in body
    # Empty-state copy is gone once a delivery exists.
    assert "No external-dispatch activity yet." not in body


def test_seeded_delivery_appears_in_company_view_with_project_name(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    seed_delivery(app.state.repository, project_id)

    response = client.get("/operating-loop")
    body = response.text
    assert response.status_code == 200
    assert "slack:slack-standup-preview:abc123" in body
    # Company-wide view annotates each delivery with its project name.
    assert "Atlas Brief" in body


def test_failed_delivery_surfaces_failure_detail(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    seed_delivery(
        app.state.repository,
        project_id,
        idempotency_key="slack:slack-standup-preview:fail",
        status="failed",
        external_id="",
        result={"blocker": "Hermes command returned a non-zero status."},
    )

    response = client.get(f"/projects/{project_id}/operating-loop")
    body = response.text
    assert response.status_code == 200
    assert "Hermes command returned a non-zero status." in body
    assert "failed" in body


# --------------------------------------------------------------------------- #
# No-secret assertion over the rendered HTML.
# --------------------------------------------------------------------------- #
def test_rendered_html_has_no_secrets(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    seed_delivery(app.state.repository, project_id)

    company = client.get("/operating-loop").text
    project = client.get(f"/projects/{project_id}/operating-loop").text
    assert secret_violations({"company": company, "project": project}) == []
