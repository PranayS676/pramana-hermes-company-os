import json

from fastapi.testclient import TestClient

from hermes_company_os.founder_next_actions import (
    founder_next_actions_json,
    founder_next_actions_markdown,
)
from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def test_founder_next_actions_routes_export_compact_current_packet(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/founder-next-actions.md")
    response = client.get("/setup/founder-next-actions.json")

    assert markdown.status_code == 200
    assert "Founder Next Actions" in markdown.text
    assert "Next best action" in markdown.text
    assert "Non-Secret Dashboard Inputs Needed" in markdown.text
    assert "External Secret Status To Update" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Founder Next Actions"
    assert payload["entry_points"]["input_ledger"] == "/setup/input-ledger.md"
    assert payload["entry_points"]["founder_decisions"] == "/setup/founder-decisions.md"
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
    assert payload["entry_points"]["runtime_preflight_runner"] == (
        "/setup/runtime-preflight.ps1"
    )
    assert payload["entry_points"]["safe_input_collector"] == (
        "/setup/founder-inputs.ps1"
    )
    assert payload["entry_points"]["profile_installation"] == (
        "/setup#profile-installation-tracking"
    )
    assert payload["entry_points"]["safe_inputs"] == "/setup#inputs"
    assert payload["entry_points"]["live_verification"] == "/setup/live-verification.md"
    assert payload["entry_points"]["profile_acceptance_template"] == (
        "/setup/profile-acceptance-template.md"
    )
    focused_by_id = {item["id"]: item for item in payload["focused_setup_imports"]}
    assert focused_by_id["slack_channel"]["template"] == (
        "/setup/slack-channel-template.md"
    )
    assert focused_by_id["credential_status"]["dashboard_anchor"] == (
        "/setup#credential-status-import"
    )
    assert payload["missing_dashboard_inputs"]
    assert "local_runtime" in payload
    assert payload["verification_work"]["profile_installation"]["open"] == 10
    assert payload["founder_decisions"]["open"] == 2
    assert payload["founder_decisions"]["urgent_open"] == 1
    assert "next_best_action" in payload

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []


def test_founder_next_actions_helpers_prioritize_missing_inputs_and_counts():
    kwargs = {
        "activation_checks": [
            {
                "id": "required-inputs",
                "label": "Required dashboard inputs",
                "status": "missing",
                "detail": "Missing: Founder Slack member ID",
            }
        ],
        "setup_inputs": [
            {
                "key": "founder_slack_member_id",
                "group_name": "slack",
                "label": "Founder Slack member ID",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
                "help_text": "Slack member IDs start with U.",
            },
            {
                "key": "slack_channel_alerts",
                "group_name": "slack",
                "label": "#alerts channel ID",
                "value": "",
                "required": 0,
                "secret_policy": "non_secret",
                "help_text": "Optional alerts channel.",
            },
            {
                "key": "llm_provider",
                "group_name": "llm",
                "label": "LLM provider",
                "value": "",
                "required": 0,
                "secret_policy": "secret_external",
                "help_text": "Deferred until last.",
            },
        ],
        "secret_requirements": [
            {
                "id": "chief-of-staff-slack-bot-token",
                "category": "slack",
                "label": "Chief of Staff Slack bot token",
                "owner_name": "Chief of Staff",
                "destination": "chief-of-staff Hermes profile .env",
                "status": "needed",
                "notes": "Private handling note.",
            }
        ],
        "messaging_checks": [{"status": "needed"}],
        "schedule_checks": [{"status": "verified"}],
        "kanban_checks": [{"status": "needed"}],
        "model_preferences": [{"status": "planned"}],
        "integrations": [{"status": "needs_input"}],
        "runtime_checks": [
            {
                "id": "hermes-cli",
                "label": "Hermes CLI",
                "status": "missing",
                "detail": "`hermes` was not found on PATH.",
                "remediation": "Install Hermes or add the Hermes executable to PATH.",
            },
            {
                "id": "python-runtime",
                "label": "Python runtime",
                "status": "ready",
                "detail": "Python 3.11.0",
                "remediation": "Use py -3.11 -m poetry install.",
            },
        ],
        "profile_installation_checks": [{"status": "needed"}],
        "founder_decisions": [
            {
                "id": "decision-first-idea-start",
                "title": "Approve first idea intake start",
                "status": "needed",
                "urgency": "urgent",
                "owner_agent_id": "chief-of-staff",
                "slack_channel": "#founder-command",
            }
        ],
    }

    payload = json.loads(founder_next_actions_json(**kwargs))
    markdown = founder_next_actions_markdown(**kwargs)

    assert payload["missing_dashboard_inputs"][0]["key"] == "founder_slack_member_id"
    assert payload["optional_dashboard_inputs"][0]["key"] == "slack_channel_alerts"
    assert payload["external_secret_status"]["status_counts"] == {"needed": 1}
    assert payload["verification_work"]["messaging"]["open"] == 1
    assert payload["verification_work"]["schedule"]["verified"] == 1
    assert payload["verification_work"]["profile_installation"]["open"] == 1
    assert payload["verification_work"]["profile_acceptance"]["open"] == 0
    assert payload["local_runtime"]["open"] == 1
    assert "/setup/hermes-runtime.md" in payload["local_runtime"]["next_action"]
    assert "/setup/hermes-install.ps1" in payload["local_runtime"]["next_action"]
    assert payload["founder_decisions"]["urgent_open"] == 1
    assert "Required dashboard inputs" in payload["next_best_action"]
    assert "Private handling note" not in json.dumps(payload)
    assert "Founder Slack member ID" in markdown
    assert "Focused Setup Reply Templates" in markdown
    assert "Local Runtime" in markdown
    assert "Install or connect Hermes" in markdown
    assert "/setup/schedule-config-template.md" in markdown
    assert "/setup/messaging-verification-template.md" in markdown
    assert "Profile installation: 0 verified, 1 open." in markdown
    assert "Open decisions: 1 (1 urgent)." in markdown
