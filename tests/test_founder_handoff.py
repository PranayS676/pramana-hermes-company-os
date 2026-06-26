import json

from hermes_company_os.founder_handoff import (
    founder_handoff_json,
    founder_handoff_markdown,
    founder_handoff_payload,
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
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "destination": "chief-of-staff Hermes profile .env",
        "environment_key": "SLACK_BOT_TOKEN",
        "status": "needed",
    },
    {
        "id": "chief-of-staff-llm-provider-credential",
        "category": "llm",
        "label": "Chief of Staff LLM provider credential",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "destination": "chief-of-staff Hermes profile .env",
        "environment_key": "PROVIDER_API_KEY_OR_OAUTH",
        "status": "deferred",
    },
]

MODEL_PREFERENCES = [
    {
        "agent_id": "chief-of-staff",
        "agent_name": "Chief of Staff",
        "provider": "openai-codex",
        "model": "gpt-5-codex",
        "status": "planned",
    }
]


def test_founder_handoff_payload_combines_safe_inputs_and_external_status():
    payload = founder_handoff_payload(
        setup_inputs=SETUP_INPUTS,
        secret_requirements=SECRET_REQUIREMENTS,
        model_preferences=MODEL_PREFERENCES,
    )

    assert payload["title"] == "Founder Return Packet"
    assert payload["safe_dashboard_reply_template"][0].startswith("founder_name=")
    assert payload["safe_dashboard_inputs"][0]["status"] == "missing"
    assert payload["deferred_preferences"][0]["key"] == "llm_provider"
    assert payload["external_credentials_to_load"]["slack"][0]["owner"] == (
        "Chief of Staff"
    )
    assert payload["credential_status_reply_template"][0] == (
        "chief-of-staff-slack-bot-token=needed | status note only"
    )
    assert payload["llm_profiles"][0]["llm_env"] == (
        "/setup/profile-llm-env/chief-of-staff.env"
    )
    assert payload["entry_points"]["gateway_operations"] == (
        "/setup/gateway-operations.md"
    )
    assert payload["entry_points"]["llm_provisioning"] == (
        "/setup/llm-provisioning.md"
    )
    assert payload["entry_points"]["slack_channel_template"] == (
        "/setup/slack-channel-template.md"
    )
    focused_by_id = {item["id"]: item for item in payload["focused_setup_imports"]}
    assert focused_by_id["slack_bot_user"]["dashboard_anchor"] == (
        "/setup#slack-bot-user-import"
    )
    assert focused_by_id["profile_acceptance"]["template"] == (
        "/setup/profile-acceptance-template.md"
    )


def test_founder_handoff_markdown_and_json_are_no_secret_artifacts():
    markdown = founder_handoff_markdown(
        setup_inputs=SETUP_INPUTS,
        secret_requirements=SECRET_REQUIREMENTS,
        model_preferences=MODEL_PREFERENCES,
    )
    payload = json.loads(
        founder_handoff_json(
            setup_inputs=SETUP_INPUTS,
            secret_requirements=SECRET_REQUIREMENTS,
            model_preferences=MODEL_PREFERENCES,
        )
    )
    raw = json.dumps(payload) + markdown

    assert "Founder Return Packet" in markdown
    assert "Credential Status Reply Template" in markdown
    assert "Focused Setup Reply Templates" in markdown
    assert "/setup#input-import" in markdown
    assert "/setup/slack-bot-user-map-template.md" in markdown
    assert "/setup/profile-acceptance-template.md" in markdown
    assert "/setup/llm-provisioning.md" in markdown
    assert "/setup/llm-finalize.md" in markdown
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
