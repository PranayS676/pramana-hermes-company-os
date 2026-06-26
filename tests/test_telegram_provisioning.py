import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.telegram_provisioning import (
    telegram_provisioning_json,
    telegram_provisioning_markdown,
    telegram_provisioning_payload,
    telegram_provisioning_powershell,
)


def test_telegram_provisioning_payload_is_chief_owned_and_llm_last_safe():
    payload = telegram_provisioning_payload(
        setup_values={
            "slack_workspace_name": "Founder Lab",
            "founder_telegram_user_id": "123456",
            "telegram_home_channel": "-100987654",
        }
    )

    assert payload["title"] == "Telegram Provisioning Pack"
    assert payload["owner_profile"] == "chief-of-staff"
    assert payload["bot_identity"]["display_name"] == "Hermes Chief of Staff"
    assert payload["bot_identity"]["suggested_username"] == (
        "hermes_founder_lab_chief_bot"
    )
    assert payload["founder_user_id_captured"] is True
    assert payload["home_chat_captured"] is True
    assert payload["bot_api_methods"] == {
        "check_bot": "getMe",
        "register_commands": "setMyCommands",
        "send_test": "sendMessage",
    }
    assert payload["runner"]["default_mode"] == "dry_run"
    assert payload["runner"]["post_dashboard_status"].startswith(
        "post verified status"
    )
    assert payload["entry_points"]["recipient_template"] == (
        "/setup/telegram-recipient-template.md"
    )
    assert payload["entry_points"]["messaging_verification"] == (
        "/setup#messaging-verification"
    )


def test_telegram_provisioning_exports_no_secret_markdown_json_and_runner():
    setup_values = {
        "founder_telegram_user_id": "123456",
        "telegram_home_channel": "-100987654",
    }
    markdown = telegram_provisioning_markdown(setup_values=setup_values)
    payload = json.loads(telegram_provisioning_json(setup_values=setup_values))
    script = telegram_provisioning_powershell(setup_values=setup_values)
    raw = json.dumps(payload) + markdown + script

    assert "Telegram Provisioning Pack" in markdown
    assert "getMe" in markdown
    assert "setMyCommands" in markdown
    assert "sendMessage" in markdown
    assert payload["title"] == "Telegram Provisioning Pack"
    assert "Hermes Company OS Telegram provisioning runner" in script
    assert "Dry run only" in script
    assert "Invoke-TelegramApi" in script
    assert "PostDashboardStatus" in script
    assert "Post-TelegramUrgentAlertStatus" in script
    assert "/setup/messaging-checks/chief-of-staff-telegram-urgent-alert" in script
    assert "DASHBOARD verified chief-of-staff-telegram-urgent-alert" in script
    assert "-PostDashboardStatus" in markdown
    assert "Token values were not printed" in script
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert "AAFD39" not in raw
    assert secret_violations({"raw": raw}) == []
