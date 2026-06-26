import json

from fastapi.testclient import TestClient

from hermes_company_os.idea_intake import idea_intake_json, idea_intake_markdown
from hermes_company_os.main import create_app
from hermes_company_os.settings import Settings

FAKE_OPENAI_SECRET = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
FAKE_SLACK_BOT_SECRET = "xoxb-" + "123456789012-abcdefABCDEF"


def test_idea_intake_routes_export_safe_template_and_routing(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/idea-intake.md")
    response = client.get("/setup/idea-intake.json")

    assert markdown.status_code == 200
    assert "Founder Idea Intake Packet" in markdown.text
    assert "Safe Reply Template" in markdown.text
    assert "project_name=" in markdown.text
    assert "founder_idea=" in markdown.text
    assert "Workflow Routing" in markdown.text
    assert "Architecture plan" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Founder Idea Intake Packet"
    assert payload["draft_mode"]["available_now"] is True
    assert payload["entry_points"]["projects"] == "/projects"
    assert any(item["id"] == "architecture-plan" for item in payload["routing"])

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "TELEGRAM_BOT_TOKEN=" not in raw
    assert "API_KEY=" not in raw


def test_idea_intake_helpers_sort_and_sanitize_templates():
    templates = [
        {
            "id": "second",
            "name": "Second",
            "phase": "product",
            "owner_agent_id": "product-manager",
            "owner_name": "Product Manager",
            "sort_order": 20,
            "doc_type": "prd",
            "priority": "high",
            "title_template": "Second " + FAKE_SLACK_BOT_SECRET,
        },
        {
            "id": "first",
            "name": "First",
            "phase": "research",
            "owner_agent_id": "research-agent",
            "owner_name": "Research Agent",
            "sort_order": 10,
            "doc_type": "research",
            "priority": "medium",
            "title_template": "First " + FAKE_OPENAI_SECRET,
        },
    ]

    payload = json.loads(idea_intake_json(templates))
    markdown = idea_intake_markdown(templates)

    assert [item["id"] for item in payload["routing"]] == ["first", "second"]
    assert "sk_REDACTED" in payload["routing"][0]["title_template"]
    assert "xoxb_REDACTED" in payload["routing"][1]["title_template"]
    assert FAKE_OPENAI_SECRET not in json.dumps(payload)
    assert FAKE_SLACK_BOT_SECRET not in markdown
