from hermes_company_os.telegram_artifacts import (
    TELEGRAM_COMMANDS,
    suggested_bot_username,
    telegram_botfather_setup_markdown,
)


def test_telegram_botfather_setup_is_chief_only_and_no_secret():
    sheet = telegram_botfather_setup_markdown(
        {
            "founder_telegram_user_id": "123456",
            "telegram_home_channel": "-100987654",
            "slack_workspace_name": "Founder Lab",
        }
    )

    assert "Telegram BotFather Setup Sheet" in sheet
    assert "Owner profile: `chief-of-staff`" in sheet
    assert "TELEGRAM_ALLOWED_USERS=123456" in sheet
    assert "TELEGRAM_HOME_CHANNEL=-100987654" in sheet
    assert "TELEGRAM_BOT_TOKEN=REPLACE_WITH_BOTFATHER_TOKEN" in sheet
    assert "Routine smoke prompt sends no Telegram message" in sheet
    assert "xoxb-" not in sheet
    assert "xapp-" not in sheet
    assert "sk-" not in sheet
    assert "AAFD39" not in sheet


def test_telegram_commands_are_botfather_safe():
    for command, description in TELEGRAM_COMMANDS:
        assert command == command.lower()
        assert command.replace("_", "").isalnum()
        assert len(command) <= 32
        assert description


def test_suggested_bot_username_uses_workspace_when_available():
    assert suggested_bot_username({"slack_workspace_name": "Founder Lab!"}) == (
        "hermes_founder_lab_chief_bot"
    )
    assert suggested_bot_username({}) == "hermes_chief_of_staff_bot"
