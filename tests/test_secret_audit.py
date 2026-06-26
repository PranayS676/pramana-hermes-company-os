from hermes_company_os.secret_audit import (
    secret_audit_markdown,
    secret_audit_powershell,
    secret_audit_requirements,
)
from hermes_company_os.secret_guard import secret_violations


def test_secret_audit_maps_llm_provider_keys_and_defers_llm_by_flag():
    requirements = secret_audit_requirements(
        [
            {
                "id": "chief-of-staff-slack-bot-token",
                "owner_agent_id": "chief-of-staff",
                "category": "slack",
                "label": "Chief of Staff Slack bot token",
                "environment_key": "SLACK_BOT_TOKEN",
            },
            {
                "id": "chief-of-staff-llm-provider-credential",
                "owner_agent_id": "chief-of-staff",
                "category": "llm",
                "label": "Chief of Staff LLM provider credential",
                "environment_key": "PROVIDER_API_KEY_OR_OAUTH",
            },
        ],
        [
            {
                "agent_id": "chief-of-staff",
                "provider": "openrouter",
                "fallback_provider": "openai-codex",
            }
        ],
    )

    by_id = {item.id: item for item in requirements}
    assert by_id["chief-of-staff-slack-bot-token"].keys == ["SLACK_BOT_TOKEN"]
    assert by_id["chief-of-staff-slack-bot-token"].audit_last is False
    assert by_id["chief-of-staff-llm-provider-credential"].keys == [
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
    ]
    assert by_id["chief-of-staff-llm-provider-credential"].audit_last is True


def test_secret_audit_exports_no_secret_markdown_and_script():
    requirements = secret_audit_requirements(
        [
            {
                "id": "chief-of-staff-slack-app-token",
                "owner_agent_id": "chief-of-staff",
                "category": "slack",
                "label": "Chief of Staff Slack app token",
                "environment_key": "SLACK_APP_TOKEN",
            },
            {
                "id": "chief-of-staff-telegram-bot-token",
                "owner_agent_id": "chief-of-staff",
                "category": "telegram",
                "label": "Chief of Staff Telegram bot token",
                "environment_key": "TELEGRAM_BOT_TOKEN",
            },
        ],
        [],
    )

    markdown = secret_audit_markdown(requirements)
    script = secret_audit_powershell(requirements)

    assert "External Secret Audit" in markdown
    assert "-AuditLlm" in markdown
    assert "PostDashboardStatus" in script
    assert "Test-ProfileEnvKeys" in script
    assert "SLACK_APP_TOKEN" in script
    assert "TELEGRAM_BOT_TOKEN" in script
    assert "Values were not printed" in script
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
    assert secret_violations({"markdown": markdown, "script": script}) == []
