import json

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.messaging_drill_artifacts import (
    messaging_drill_json,
    messaging_drill_markdown,
)
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def test_messaging_drill_routes_export_slack_and_telegram_drills(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/messaging-drill.md")
    response = client.get("/setup/messaging-drill.json")

    assert markdown.status_code == 200
    assert "Messaging Drill Pack" in markdown.text
    assert "Slack Profile Drills" in markdown.text
    assert "Telegram Urgency Drills" in markdown.text
    assert "Chief of Staff" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Messaging Drill Pack"
    assert payload["policy"]["primary_workspace"] == "slack"
    assert payload["policy"]["telegram_owner"] == "chief-of-staff"
    assert payload["slack_drills"][0]["profile_id"] == "chief-of-staff"
    assert any(drill["decision"] == "send_telegram" for drill in payload["telegram_drills"])
    assert payload["entry_points"]["verification_template"] == (
        "/setup/messaging-verification-template.md"
    )
    assert payload["entry_points"]["messaging_verification"] == (
        "/setup/messaging#messaging-verification"
    )

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []


def test_messaging_drill_helpers_include_check_statuses_and_channel_ids():
    agents = [
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "slack_channel": "#engineering",
            "hermes_command": "engineering-manager",
        }
    ]
    setup_values = {
        "slack_channel_engineering": "CENG",
        "slack_channel_agent_standup": "CSTANDUP",
    }
    messaging_checks = [
        {"id": "engineering-manager-slack-gateway", "status": "verified"},
        {"id": "engineering-manager-slack-dm", "status": "loaded"},
        {"id": "engineering-manager-slack-channel", "status": "needed"},
        {"id": "chief-of-staff-telegram-urgent-alert", "status": "needed"},
    ]
    secret_requirements = [
        {"category": "slack", "status": "loaded"},
        {"category": "telegram", "status": "needed"},
    ]

    payload = json.loads(
        messaging_drill_json(
            agents=agents,
            setup_values=setup_values,
            messaging_checks=messaging_checks,
            secret_requirements=secret_requirements,
        )
    )
    markdown = messaging_drill_markdown(
        agents=agents,
        setup_values=setup_values,
        messaging_checks=messaging_checks,
        secret_requirements=secret_requirements,
    )

    drill = payload["slack_drills"][0]
    assert drill["gateway_status"] == "verified"
    assert drill["dm_status"] == "loaded"
    assert drill["channel_status"] == "needed"
    assert any(channel["channel_id"] == "CENG" for channel in payload["slack_channels"])
    assert payload["status"]["slack_credentials"] == {"loaded": 1}
    assert payload["status"]["telegram_credentials"] == {"needed": 1}
    assert "/setup/messaging-verification-template.md" in markdown
    assert "No Telegram message. Keep the update in Slack only." in markdown
