from __future__ import annotations

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.settings import Settings


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def test_extracted_routes_are_registered_on_the_app(tmp_path):
    app, _client = app_and_client(tmp_path)
    paths = {route.path for route in app.routes}
    for expected in {
        "/queue",
        "/queue/{work_item_id}",
        "/queue/{work_item_id}/handoff.json",
        "/queue/{work_item_id}/handoff.md",
        "/decisions",
        "/decisions/{decision_id}",
        "/agents/{agent_id}",
        "/agents/{agent_id}/profile",
        "/agents/{agent_id}/routing",
        "/agents/{agent_id}/run",
    }:
        assert expected in paths, f"missing route: {expected}"


def test_queue_route_responds(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.get("/queue")
    assert response.status_code == 200


def test_decisions_route_responds(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.get("/decisions")
    assert response.status_code == 200


def test_agent_detail_responds_for_seeded_agent(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.get("/agents/chief-of-staff")
    assert response.status_code == 200


def test_agent_detail_missing_returns_404_via_helper(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.get("/agents/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"


def test_queue_item_missing_returns_404(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.get("/queue/does-not-exist/handoff.json")
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent work item not found"


def test_decision_missing_returns_404(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.get("/decisions/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "Founder decision not found"


def test_update_agent_profile_missing_returns_404_via_helper(tmp_path):
    _app, client = app_and_client(tmp_path)
    response = client.post(
        "/agents/does-not-exist/profile",
        data={"description": "x", "soul": "y", "capabilities": "a"},
        follow_redirects=False,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"
