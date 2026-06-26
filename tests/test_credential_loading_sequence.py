import json

from hermes_company_os.credential_loading_sequence import (
    credential_loading_json,
    credential_loading_markdown,
    credential_loading_payload,
)
from hermes_company_os.secret_guard import secret_violations

SECRET_REQUIREMENTS = [
    {
        "id": "chief-of-staff-slack-bot-token",
        "category": "slack",
        "label": "Chief of Staff Slack bot token",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "owner_command": "chief-of-staff",
        "destination": "chief-of-staff Hermes profile .env",
        "environment_key": "SLACK_BOT_TOKEN",
        "status": "needed",
    },
    {
        "id": "chief-of-staff-telegram-bot-token",
        "category": "telegram",
        "label": "Chief of Staff Telegram bot token",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "owner_command": "chief-of-staff",
        "destination": "chief-of-staff Hermes profile .env",
        "environment_key": "TELEGRAM_BOT_TOKEN",
        "status": "needed",
    },
    {
        "id": "chief-of-staff-llm-provider-credential",
        "category": "llm",
        "label": "Chief of Staff LLM provider credential",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "owner_command": "chief-of-staff",
        "destination": "chief-of-staff Hermes profile .env",
        "environment_key": "PROVIDER_API_KEY_OR_OAUTH",
        "status": "deferred",
    },
]

MODEL_PREFERENCES = [
    {
        "agent_id": "chief-of-staff",
        "provider": "openrouter",
        "model": "openai/gpt-5",
        "fallback_provider": "openai-codex",
        "fallback_model": "gpt-5-codex",
    }
]

INTEGRATIONS = [
    {
        "id": "hermes-kanban",
        "name": "Hermes Kanban board",
        "category": "kanban",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "status": "needs_setup",
        "validation_command": "hermes kanban diagnostics --json",
    },
    {
        "id": "standup-cron",
        "name": "9 AM / 3 PM standup cron",
        "category": "schedule",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "status": "needs_setup",
        "validation_command": "chief-of-staff cron list",
    },
]


def test_credential_loading_payload_orders_messaging_before_llm():
    payload = credential_loading_payload(
        secret_requirements=SECRET_REQUIREMENTS,
        model_preferences=MODEL_PREFERENCES,
        integrations=INTEGRATIONS,
        profile_installation_checks=[{"status": "verified"}],
        profile_acceptance_checks=[{"status": "needed"}],
    )

    assert payload["title"] == "External Credential Loading Sequence"
    assert payload["verification_last"] is True
    assert [phase["id"] for phase in payload["phase_order"]] == [
        "profile_installation_precheck",
        "messaging_credentials",
        "messaging_verification",
        "kanban_and_scheduling",
        "llm_credentials_last",
        "profile_acceptance_final",
    ]
    phase_by_id = {phase["id"]: phase for phase in payload["phase_order"]}
    assert phase_by_id["profile_installation_precheck"]["status"] == {"verified": 1}
    assert phase_by_id["messaging_credentials"]["status"] == {"needed": 2}
    assert phase_by_id["profile_acceptance_final"]["status"] == {"needed": 1}
    llm_requirement = phase_by_id["llm_credentials_last"]["requirements"][0]
    assert llm_requirement["resolved_keys"] == [
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
    ]
    assert llm_requirement["audit_last"] is True
    assert payload["profile_files"][0]["gateway_env"] == (
        "/setup/profile-env/chief-of-staff.env"
    )


def test_credential_loading_markdown_and_json_are_no_secret_artifacts():
    markdown = credential_loading_markdown(
        secret_requirements=SECRET_REQUIREMENTS,
        model_preferences=MODEL_PREFERENCES,
        integrations=INTEGRATIONS,
        profile_installation_checks=[{"status": "needed", "evidence": "Private note."}],
        profile_acceptance_checks=[
            {"status": "needed", "evidence": "Private acceptance note."}
        ],
    )
    payload = json.loads(
        credential_loading_json(
            secret_requirements=SECRET_REQUIREMENTS,
            model_preferences=MODEL_PREFERENCES,
            integrations=INTEGRATIONS,
            profile_installation_checks=[
                {"status": "needed", "evidence": "Private note."}
            ],
            profile_acceptance_checks=[
                {"status": "needed", "evidence": "Private acceptance note."}
            ],
        )
    )

    assert "External Credential Loading Sequence" in markdown
    assert "Profile Installation Precheck" in markdown
    assert "LLM Credentials Last" in markdown
    assert "Profile Acceptance Last" in markdown
    assert "/setup#profile-installation-tracking" in markdown
    assert "/setup#profile-acceptance-tracking" in markdown
    assert "/setup/llm-provisioning.md" in markdown
    assert ".\\secret-audit.ps1 -AuditLlm -PostDashboardStatus" in markdown
    assert payload["entry_points"]["llm_provisioning"] == (
        "/setup/llm-provisioning.md"
    )
    assert payload["entry_points"]["profile_installation"] == (
        "/setup#profile-installation-tracking"
    )
    assert payload["entry_points"]["profile_acceptance"] == (
        "/setup#profile-acceptance-tracking"
    )
    assert payload["entry_points"]["live_verification"] == "/setup/live-verification.md"
    raw = json.dumps(payload) + markdown
    assert "Private note." not in raw
    assert "Private acceptance note." not in raw
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
