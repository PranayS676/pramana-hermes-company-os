from hermes_company_os.env_templates import profile_env_template


def test_chief_of_staff_env_template_includes_telegram():
    template = profile_env_template(
        {
            "id": "chief-of-staff",
            "name": "Chief of Staff",
            "slack_channel": "#founder-command",
        },
        {
            "founder_slack_member_id": "U123",
            "slack_channel_founder_command": "C123",
            "founder_telegram_user_id": "987",
        },
    )

    assert "SLACK_HOME_CHANNEL_NAME=founder-command" in template
    assert "SLACK_ALLOWED_USERS=U123" in template
    assert "SLACK_HOME_CHANNEL=C123" in template
    assert "SLACK_BOT_TOKEN=TODO" in template
    assert "SLACK_APP_TOKEN=TODO" in template
    assert "xoxb-" not in template
    assert "xapp-" not in template
    assert "TELEGRAM_BOT_TOKEN=TODO" in template
    assert "TELEGRAM_ALLOWED_USERS=987" in template


def test_non_chief_env_template_excludes_telegram():
    template = profile_env_template(
        {
            "id": "product-manager",
            "name": "Product Manager",
            "slack_channel": "#product",
        }
    )

    assert "SLACK_HOME_CHANNEL_NAME=product" in template
    assert "TELEGRAM_BOT_TOKEN" not in template
