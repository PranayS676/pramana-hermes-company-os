import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.telegram_policy import (
    TELEGRAM_ALERT_RULES,
    telegram_policy_json,
    telegram_policy_markdown,
    telegram_policy_payload,
)


def test_telegram_policy_payload_is_chief_owned_and_keeps_llm_out():
    payload = telegram_policy_payload(
        {
            "founder_telegram_user_id": "123456",
            "telegram_home_channel": "-100987654",
        },
        [
            {
                "id": "morning-standup",
                "name": "Morning Standup",
                "hour": 9,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "telegram_policy": "Only blockers",
                "active": 1,
            }
        ],
    )

    assert payload["owner_profile"] == "chief-of-staff"
    assert payload["founder_telegram_user_id"] == "123456"
    assert payload["telegram_home_channel"] == "-100987654"
    assert payload["standup_schedules"][0]["time"] == "09:00"
    assert any(rule["decision"] == "send_telegram" for rule in payload["rules"])
    assert any(rule["decision"] == "slack_only" for rule in payload["rules"])


def test_telegram_policy_exports_markdown_and_json_without_secret_values():
    setup_values = {"founder_telegram_user_id": "123456"}
    schedules = []

    markdown = telegram_policy_markdown(setup_values, schedules)
    payload = json.loads(telegram_policy_json(setup_values, schedules))

    assert "Telegram Urgent Policy" in markdown
    assert "Send Telegram" in markdown
    assert "Keep In Slack Only" in markdown
    assert "/setup/telegram-policy.json" in markdown
    assert payload["title"] == "Telegram Urgent Policy"
    assert payload["owner_profile"] == "chief-of-staff"
    assert "TELEGRAM_BOT_TOKEN" not in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
    assert secret_violations({"markdown": markdown, "json": json.dumps(payload)}) == []


def test_telegram_alert_rules_have_clear_decisions():
    decisions = {rule["decision"] for rule in TELEGRAM_ALERT_RULES}

    assert decisions == {"send_telegram", "slack_only"}
    for rule in TELEGRAM_ALERT_RULES:
        assert rule["id"]
        assert rule["severity"] in {"urgent", "normal"}
        assert rule["description"]
        assert rule["example"]
