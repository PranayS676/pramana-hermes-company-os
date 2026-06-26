import pytest

from hermes_company_os.secret_guard import assert_no_secret_values, secret_violations

FAKE_SLACK_BOT_TOKEN = "xoxb-" + "123456789012-abcdefABCDEF"
FAKE_SLACK_APP_TOKEN = "xapp-" + "1-ABCDEFabcdef123456"
FAKE_TELEGRAM_BOT_TOKEN = "123456789:" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"
FAKE_OPENROUTER_KEY = "sk-or-v1-" + "abcdefghijklmnopqrstuvwxyz123456"
FAKE_OPENAI_KEY = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
FAKE_OPENAI_ENV_SECRET = "OPENAI_API_KEY=" + FAKE_OPENAI_KEY
FAKE_ANTHROPIC_ENV_SECRET = "ANTHROPIC_API_KEY=" + "sk-ant-" + "abcdefghijklmnop"


def test_secret_guard_allows_non_secret_operational_ids():
    assert (
        secret_violations(
            {
                "slack_member": "U123ABC",
                "slack_channel": "C123ABC",
                "telegram_user": "123456789",
                "provider": "openai-codex",
                "model": "gpt-5-codex",
            }
        )
        == []
    )


def test_secret_guard_detects_common_tokens():
    violations = secret_violations(
        {
            "slack_bot": FAKE_SLACK_BOT_TOKEN,
            "slack_app": FAKE_SLACK_APP_TOKEN,
            "telegram": FAKE_TELEGRAM_BOT_TOKEN,
            "provider": FAKE_OPENROUTER_KEY,
            "env": FAKE_OPENAI_ENV_SECRET,
        }
    )

    assert violations == [
        "slack_bot: Slack bot token",
        "slack_app: Slack app token",
        "telegram: Telegram bot token",
        "provider: OpenRouter API key",
        "env: OpenAI-style API key",
    ]


def test_assert_no_secret_values_raises_actionable_message():
    with pytest.raises(ValueError, match="Store them in the real Hermes profile"):
        assert_no_secret_values({"notes": FAKE_ANTHROPIC_ENV_SECRET})
