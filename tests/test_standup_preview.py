import json

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.settings import Settings
from hermes_company_os.standup_preview import standup_preview_json, standup_preview_markdown


def test_standup_preview_routes_include_active_prompts_and_drills(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/standup-preview.md")
    response = client.get("/setup/standup-preview.json")

    assert markdown.status_code == 200
    assert "Standup Preview And Drill Pack" in markdown.text
    assert "Morning Standup" in markdown.text
    assert "Afternoon Standup" in markdown.text
    assert "Telegram escalation" in markdown.text
    assert "Founder approval needed" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Standup Preview And Drill Pack"
    assert payload["owner_profile"] == "chief-of-staff"
    assert payload["delivery_policy"]["primary_workspace"] == "slack"
    assert payload["delivery_policy"]["telegram"] == "urgent founder alerts only"
    assert len(payload["schedules"]) == 2
    assert payload["schedules"][0]["prompt"]
    assert payload["verification"]["cron_install"] == "/setup/standup-cron.ps1"

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw


def test_standup_preview_helpers_use_current_tasks_and_documents():
    kwargs = {
        "schedules": [
            {
                "id": "morning-standup",
                "name": "Morning Standup",
                "hour": 9,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent only",
                "active": 1,
            }
        ],
        "agents": [
            {
                "name": "Engineering Manager",
                "id": "engineering-manager",
                "slack_channel": "#engineering",
            }
        ],
        "tasks": [
            {
                "status": "planned",
                "priority": "high",
                "title": "Write architecture plan",
                "owner_name": "Engineering Manager",
            }
        ],
        "documents": [
            {
                "status": "draft",
                "title": "Architecture plan",
                "doc_type": "architecture",
            }
        ],
        "slack_founder_command": "#founder-command",
        "slack_alerts": "#alerts",
        "telegram_urgent_label": "Founder Telegram urgent channel",
    }

    payload = json.loads(standup_preview_json(**kwargs))
    markdown = standup_preview_markdown(**kwargs)

    prompt = payload["schedules"][0]["prompt"]
    assert "Write architecture plan" in prompt
    assert "Architecture plan" in prompt
    assert "#founder-command" in prompt
    assert "#alerts" in prompt
    assert payload["drill_cases"][0]["expected_telegram"] == "none"
    assert "Failed scheduled operation" in markdown
    assert "TELEGRAM_BOT_TOKEN" not in markdown
