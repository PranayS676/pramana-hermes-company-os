import json

from hermes_company_os.input_ledger import (
    input_ledger_json,
    input_ledger_markdown,
    input_ledger_payload,
)
from hermes_company_os.secret_guard import secret_violations

SETUP_INPUTS = [
    {
        "key": "founder_name",
        "group_name": "founder",
        "label": "Founder name",
        "value": "",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Name agents should use.",
    },
    {
        "key": "slack_workspace_name",
        "group_name": "slack",
        "label": "Slack workspace name",
        "value": "Founder Lab",
        "required": 1,
        "secret_policy": "non_secret",
        "help_text": "Human-readable workspace name.",
    },
    {
        "key": "llm_provider",
        "group_name": "llm",
        "label": "LLM provider",
        "value": "",
        "required": 0,
        "secret_policy": "secret_external",
        "help_text": "Provider is configured externally.",
    },
]

SECRET_REQUIREMENTS = [
    {
        "id": "chief-of-staff-slack-bot-token",
        "category": "slack",
        "label": "Chief of Staff Slack bot token",
        "owner_name": "Chief of Staff",
        "destination": "chief-of-staff Hermes profile .env",
        "status": "needed",
    },
    {
        "id": "chief-of-staff-llm-provider-credential",
        "category": "llm",
        "label": "Chief of Staff LLM provider credential",
        "owner_name": "Chief of Staff",
        "destination": "chief-of-staff Hermes profile .env",
        "status": "deferred",
    },
]


def _kwargs() -> dict:
    return {
        "setup_inputs": SETUP_INPUTS,
        "secret_requirements": SECRET_REQUIREMENTS,
        "messaging_checks": [{"status": "needed"}],
        "schedule_checks": [{"status": "verified", "schedule_active": 1}],
        "kanban_checks": [{"status": "needed"}],
        "model_preferences": [{"status": "planned"}],
        "integrations": [{"category": "runtime", "status": "deferred"}],
    }


def test_input_ledger_payload_groups_questions_and_phase_unlocks():
    payload = input_ledger_payload(**_kwargs())

    assert payload["title"] == "Founder Input Ledger"
    assert payload["verification_last"] is True
    assert payload["summary"]["safe_inputs"]["status"] == {
        "captured": 1,
        "missing": 1,
    }
    assert payload["safe_dashboard_inputs"][0]["key"] == "founder_name"
    assert payload["safe_dashboard_inputs"][0]["status"] == "missing"
    assert payload["deferred_external_preferences"][0]["key"] == "llm_provider"
    assert payload["external_credentials_status_only"][0]["status_only"] is True
    focused_by_id = {item["id"]: item for item in payload["focused_setup_imports"]}
    assert focused_by_id["slack_channel"]["template"] == (
        "/setup/slack-channel-template.md"
    )
    assert focused_by_id["llm_preference"]["dashboard_anchor"] == (
        "/setup#llm-preference-import"
    )
    assert payload["founder_questions"][0]["priority"] == "now"
    assert any(
        question["priority"] == "status-only"
        for question in payload["founder_questions"]
    )
    phase_by_id = {phase["id"]: phase for phase in payload["phase_unlocks"]}
    assert phase_by_id["profiles"]["status"] == "waiting"
    assert phase_by_id["schedule"]["status"] == "ready"
    assert phase_by_id["llm"]["next_route"] == "/setup/llm-provisioning.md"


def test_input_ledger_markdown_and_json_are_no_secret_artifacts():
    markdown = input_ledger_markdown(**_kwargs())
    payload = json.loads(input_ledger_json(**_kwargs()))
    raw = markdown + json.dumps(payload)

    assert "Founder Input Ledger" in markdown
    assert "Questions For You" in markdown
    assert "Safe Reply Template" in markdown
    assert "Credential Status Reply Template" in markdown
    assert "Focused Setup Reply Templates" in markdown
    assert "/setup#input-import" in markdown
    assert "/setup/telegram-recipient-template.md" in markdown
    assert "/setup/kanban-verification-template.md" in markdown
    assert payload["entry_points"]["founder_handoff"] == "/setup/founder-handoff.md"
    assert payload["entry_points"]["schedule_config_template"] == (
        "/setup/schedule-config-template.md"
    )
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert "SLACK_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []
