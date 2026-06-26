import json

from fastapi.testclient import TestClient

from hermes_company_os.kickoff_readiness import (
    kickoff_readiness_json,
    kickoff_readiness_markdown,
    kickoff_readiness_payload,
)
from hermes_company_os.main import create_app
from hermes_company_os.runtime_preflight import RuntimePreflightCheck
from hermes_company_os.settings import Settings


def test_kickoff_readiness_routes_default_to_draft_only(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/kickoff-readiness.md")
    response = client.get("/setup/kickoff-readiness.json")

    assert markdown.status_code == 200
    assert "First Project Kickoff Readiness" in markdown.text
    assert "Draft workflow creation allowed: yes" in markdown.text
    assert "Live kickoff ready: no" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "draft_only"
    assert payload["draft_workflow_allowed"] is True
    assert payload["live_kickoff_ready"] is False
    assert payload["entry_points"]["projects"] == "/projects"
    assert any(gate["id"] == "llm" for gate in payload["gates"])
    assert any(gate["id"] == "profile_installation" for gate in payload["gates"])
    assert any(gate["id"] == "profile_acceptance" for gate in payload["gates"])

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw


def test_kickoff_readiness_payload_becomes_live_ready_when_all_gates_pass():
    payload = kickoff_readiness_payload(
        agents=[
            {
                "id": "chief-of-staff",
                "name": "Chief of Staff",
                "description": "Coordinates agents.",
                "soul": "Coordinate well.",
                "capabilities": ["orchestration"],
                "hermes_command": "chief-of-staff",
            }
        ],
        workflow_templates=[{"id": "founder-decision-memo"}],
        activation_checks=[
            {
                "id": "required-inputs",
                "label": "Required dashboard inputs",
                "status": "ready",
                "detail": "ready",
            },
            {
                "id": "slack-member-id",
                "label": "Founder Slack member ID",
                "status": "ready",
                "detail": "ready",
            },
            {
                "id": "slack-channel-ids",
                "label": "Slack channel IDs",
                "status": "ready",
                "detail": "ready",
            },
            {
                "id": "telegram-ids",
                "label": "Telegram IDs",
                "status": "ready",
                "detail": "ready",
            },
            {
                "id": "standup-schedules",
                "label": "Standup schedules",
                "status": "ready",
                "detail": "ready",
            },
        ],
        runtime_checks=[
            RuntimePreflightCheck(
                id="hermes-cli",
                label="Hermes CLI",
                status="ready",
                detail="hermes",
                remediation="none",
            ),
            RuntimePreflightCheck(
                id="integration-llm-provider",
                label="LLM provider status",
                status="deferred",
                detail="Dashboard status: deferred",
                remediation="Configure last.",
            )
        ],
        secret_requirements=[
            {
                "category": "llm",
                "status": "verified",
            }
        ],
        messaging_checks=[{"status": "verified"}],
        schedule_checks=[{"status": "verified", "schedule_active": 1}],
        kanban_checks=[{"status": "verified"}],
        model_preferences=[{"status": "verified"}],
        integrations=[
            {"category": "slack", "status": "configured"},
            {"category": "telegram", "status": "configured"},
            {"category": "kanban", "status": "configured"},
            {"category": "schedule", "status": "configured"},
            {"category": "runtime", "status": "configured"},
        ],
        profile_installation_checks=[{"status": "verified"}],
        profile_acceptance_checks=[{"status": "verified"}],
    )

    assert payload["mode"] == "live_ready"
    assert payload["live_kickoff_ready"] is True
    assert all(gate["status"] == "ready" for gate in payload["gates"])
    gate_by_id = {gate["id"]: gate for gate in payload["gates"]}
    assert gate_by_id["profile_installation"]["label"] == (
        "Hermes profile installation"
    )
    assert gate_by_id["profile_acceptance"]["label"] == "Hermes profile acceptance"


def test_kickoff_readiness_helpers_omit_verification_evidence_text():
    kwargs = {
        "agents": [
            {
                "id": "engineering-manager",
                "name": "Engineering Manager",
                "description": "Builds systems.",
                "soul": "Think big.",
                "capabilities": ["architecture"],
                "hermes_command": "engineering-manager",
            }
        ],
        "workflow_templates": [{"id": "architecture-plan"}],
        "activation_checks": [
            {
                "id": "required-inputs",
                "label": "Required dashboard inputs",
                "status": "missing",
                "detail": "Founder name missing",
            }
        ],
        "runtime_checks": [
            RuntimePreflightCheck(
                id="hermes-cli",
                label="Hermes CLI",
                status="missing",
                detail="missing",
                remediation="Install Hermes.",
            )
        ],
        "secret_requirements": [
            {
                "category": "llm",
                "status": "deferred",
                "notes": "private notes",
            }
        ],
        "messaging_checks": [
            {
                "status": "needed",
                "evidence": "Private Slack reply details.",
            }
        ],
        "schedule_checks": [],
        "kanban_checks": [],
        "model_preferences": [{"status": "planned"}],
        "integrations": [
            {"category": "runtime", "status": "deferred"},
        ],
        "profile_installation_checks": [
            {
                "status": "needed",
                "evidence": "Private file audit note.",
            }
        ],
        "profile_acceptance_checks": [
            {
                "status": "needed",
                "evidence": "Private acceptance note.",
            }
        ],
    }

    payload = json.loads(kickoff_readiness_json(**kwargs))
    markdown = kickoff_readiness_markdown(**kwargs)

    assert payload["mode"] == "draft_only"
    assert payload["gates"][0]["id"] == "runtime"
    assert "Install Hermes." in payload["next_best_action"]
    assert "Private Slack reply details." not in json.dumps(payload)
    assert "Private file audit note." not in json.dumps(payload)
    assert "Private acceptance note." not in json.dumps(payload)
    assert "private notes" not in json.dumps(payload)
    assert "Credential Boundary" in markdown
