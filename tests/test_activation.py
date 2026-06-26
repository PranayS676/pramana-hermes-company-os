from hermes_company_os.activation import (
    activation_commands,
    cron_commands,
    missing_required_inputs,
)


def test_activation_commands_use_saved_non_secret_values():
    agents = [
        {
            "id": "chief-of-staff",
            "name": "Chief of Staff",
            "hermes_command": "chief-of-staff",
            "slack_channel": "#founder-command",
        }
    ]

    commands = activation_commands(
        agents,
        {
            "founder_slack_member_id": "U123",
            "slack_channel_founder_command": "C123",
            "founder_telegram_user_id": "987",
        },
    )

    env = commands[0]["env"]
    assert "SLACK_ALLOWED_USERS=U123" in env
    assert "SLACK_HOME_CHANNEL=C123" in env
    assert "SLACK_BOT_TOKEN=TODO" in env
    assert "SLACK_APP_TOKEN=TODO" in env
    assert "TELEGRAM_BOT_TOKEN=TODO" in env
    assert "TELEGRAM_ALLOWED_USERS=987" in env
    assert "TELEGRAM_HOME_CHANNEL=987" in env
    assert commands[0]["model"] == "chief-of-staff model"
    assert commands[0]["config_template"] == "/setup/profile-config/chief-of-staff.yaml"


def test_cron_commands_can_use_weekdays():
    commands = cron_commands({"standup_cadence": "weekdays"})

    assert '"every weekday at 9am"' in commands[0]
    assert '"every weekday at 3pm"' in commands[1]


def test_cron_commands_use_active_schedule_rows():
    commands = cron_commands(
        {"standup_cadence": "every day"},
        [
            {
                "name": "late founder sync",
                "hour": 18,
                "minute": 30,
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent founder alerts",
                "active": 1,
            },
            {
                "name": "paused sync",
                "hour": 23,
                "minute": 0,
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent founder alerts",
                "active": 0,
            },
        ],
    )

    assert len(commands) == 1
    assert '"every day at 6:30pm"' in commands[0]
    assert "late founder sync" in commands[0]
    assert "paused sync" not in commands[0]


def test_missing_required_inputs_ignores_external_secret_fields():
    missing = missing_required_inputs(
        [
            {
                "key": "founder_name",
                "required": 1,
                "secret_policy": "non_secret",
                "value": "",
            },
            {
                "key": "llm_provider",
                "required": 1,
                "secret_policy": "secret_external",
                "value": "",
            },
        ]
    )

    assert [item["key"] for item in missing] == ["founder_name"]
