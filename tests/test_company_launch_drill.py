import json

from fastapi.testclient import TestClient

from hermes_company_os.company_launch_drill import (
    company_launch_drill_json,
    company_launch_drill_markdown,
    company_launch_drill_payload,
)
from hermes_company_os.main import create_app
from hermes_company_os.profile_acceptance import profile_acceptance_suite
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def test_company_launch_drill_payload_marks_tracked_gates_ready():
    agents = [
        {
            "id": "chief-of-staff",
            "name": "Chief of Staff",
            "role": "Orchestrator",
            "hermes_command": "chief-of-staff",
            "capabilities": ["orchestration"],
        },
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "role": "Engineering",
            "hermes_command": "engineering-manager",
            "capabilities": ["architecture"],
        },
    ]
    acceptance_checks = [
        {"status": "verified"} for _case in profile_acceptance_suite(agents)["cases"]
    ]

    payload = company_launch_drill_payload(
        agents=agents,
        relationships=[
            {
                "id": "engineering-manager-backend-engineer",
                "manager_agent_id": "engineering-manager",
                "member_agent_id": "backend-engineer",
            }
        ],
        schedules=[{"id": "morning", "active": 1}],
        workflow_templates=[{"id": "architecture-plan"}],
        activation_checks=[
            {
                "id": "required-inputs",
                "label": "Required dashboard inputs",
                "status": "ready",
                "detail": "Ready.",
            }
        ],
        secret_requirements=[
            {"category": "slack", "status": "loaded"},
            {"category": "telegram", "status": "verified"},
            {"category": "llm", "status": "verified"},
        ],
        messaging_checks=[{"status": "verified"}],
        schedule_checks=[{"status": "verified", "schedule_active": 1}],
        kanban_checks=[{"status": "verified"}],
        model_preferences=[{"status": "verified"}],
        integrations=[
            {"category": "slack", "status": "configured"},
            {"category": "telegram", "status": "configured"},
            {"category": "runtime", "status": "configured"},
        ],
        setup_inputs=[
            {
                "key": "founder_name",
                "required": 1,
                "secret_policy": "non_secret",
                "value": "Masad",
            }
        ],
        runtime_checks=[
            {
                "id": "hermes-cli",
                "label": "Hermes CLI",
                "status": "ready",
                "detail": "C:/tools/hermes.exe",
                "remediation": "Install Hermes.",
            }
        ],
        profile_acceptance_checks=acceptance_checks,
        profile_installation_checks=[
            {"status": "verified"},
            {"status": "verified"},
        ],
        founder_decisions=[
            {
                "status": "approved",
                "urgency": "routine",
                "decision": "Approved.",
            }
        ],
    )

    assert payload["title"] == "Company Launch Drill"
    assert payload["tracked_gates_ready"] is True
    assert payload["first_idea_mode"] == "ready_for_manual_founder_go"
    assert payload["manual_profile_installation_required"] is False
    assert payload["manual_acceptance_required"] is False
    assert payload["manual_founder_decision_required"] is False
    phases = {phase["id"]: phase for phase in payload["phases"]}
    assert phases["safe-founder-inputs"]["status"] == "ready"
    assert phases["local-hermes-runtime"]["status"] == "ready"
    assert phases["slack-telegram-gateways"]["status"] == "ready"
    assert phases["profile-installation"]["status"] == "ready"
    assert phases["profile-acceptance"]["status"] == "ready"
    assert phases["profile-acceptance"]["tracked_gate"] is True
    assert phases["founder-decisions"]["status"] == "ready"


def test_company_launch_drill_exports_no_secret_rehearsal_packet():
    kwargs = {
        "agents": [
            {
                "id": "chief-of-staff",
                "name": "Chief of Staff",
                "role": "Orchestrator",
                "hermes_command": "chief-of-staff",
                "capabilities": ["orchestration"],
            }
        ],
        "relationships": [],
        "schedules": [],
        "workflow_templates": [],
        "activation_checks": [
            {
                "id": "required-inputs",
                "label": "Required dashboard inputs",
                "status": "missing",
                "detail": "Missing values.",
            }
        ],
        "secret_requirements": [{"category": "llm", "status": "deferred"}],
        "messaging_checks": [{"status": "needed"}],
        "schedule_checks": [{"status": "needed"}],
        "kanban_checks": [{"status": "needed"}],
        "model_preferences": [{"status": "planned"}],
        "integrations": [{"category": "runtime", "status": "deferred"}],
        "setup_inputs": [
            {
                "key": "founder_name",
                "required": 1,
                "secret_policy": "non_secret",
                "value": "",
            }
        ],
        "runtime_checks": [
            {
                "id": "hermes-cli",
                "label": "Hermes CLI",
                "status": "missing",
                "detail": "Missing.",
                "remediation": "Install Hermes.",
            }
        ],
        "profile_acceptance_checks": [{"status": "needed"}],
        "profile_installation_checks": [{"status": "needed"}],
        "founder_decisions": [
            {
                "status": "needed",
                "urgency": "urgent",
                "decision": "",
            }
        ],
    }

    markdown = company_launch_drill_markdown(**kwargs)
    payload = json.loads(company_launch_drill_json(**kwargs))

    assert "Company Launch Drill" in markdown
    assert "Founder Go / No-Go Rule" in markdown
    assert payload["tracked_gates_ready"] is False
    assert payload["entry_points"]["idea_intake"] == "/setup/idea-intake.md"
    assert payload["entry_points"]["input_collector"] == "/setup/founder-inputs.ps1"
    assert payload["entry_points"]["first_run"] == "/setup/first-run.md"
    assert payload["entry_points"]["first_run_runner"] == "/setup/first-run.ps1"
    assert payload["entry_points"]["progress_board"] == "/setup/progress-board.md"
    assert payload["entry_points"]["progress_board_json"] == (
        "/setup/progress-board.json"
    )
    assert payload["entry_points"]["hermes_runtime"] == "/setup/hermes-runtime.md"
    assert payload["entry_points"]["hermes_install_runner"] == (
        "/setup/hermes-install.ps1"
    )
    assert payload["entry_points"]["profile_installation"] == (
        "/setup/profile-installation.md"
    )
    assert payload["entry_points"]["founder_decisions"] == (
        "/setup/founder-decisions.md"
    )
    raw = json.dumps(payload) + markdown
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_company_launch_drill_routes_export_current_state(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/company-launch-drill.md")
    response = client.get("/setup/company-launch-drill.json")

    assert markdown.status_code == 200
    assert "Company Launch Drill" in markdown.text
    assert "Tracked gates ready" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Company Launch Drill"
    assert payload["tracked_gates_ready"] is False
    assert payload["manual_profile_installation_required"] is True
    assert payload["manual_acceptance_required"] is True
    assert payload["manual_founder_decision_required"] is True
    assert any(phase["id"] == "safe-founder-inputs" for phase in payload["phases"])
    assert any(phase["id"] == "local-hermes-runtime" for phase in payload["phases"])
    assert any(phase["id"] == "llm-final-smoke" for phase in payload["phases"])
    assert any(phase["id"] == "profile-installation" for phase in payload["phases"])
    assert any(phase["id"] == "founder-decisions" for phase in payload["phases"])
