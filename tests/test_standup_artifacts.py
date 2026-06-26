from hermes_company_os.standup_artifacts import (
    standup_cron_powershell,
    standup_runbook_markdown,
)


def test_standup_runbook_lists_schedules_commands_and_checks():
    runbook = standup_runbook_markdown(
        {"standup_cadence": "weekdays"},
        [
            {
                "id": "morning-standup",
                "name": "Morning Standup",
                "hour": 9,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent only",
                "active": 1,
            }
        ],
        [
            {
                "id": "morning-standup-manual-run",
                "label": "Morning Standup manual dashboard run",
                "status": "needed",
                "evidence": "",
                "schedule_active": 1,
            }
        ],
    )

    assert "Standup Scheduling Runbook" in runbook
    assert "Morning Standup" in runbook
    assert "`09:00`" in runbook
    assert '"every weekday at 9am"' in runbook
    assert "`morning-standup-manual-run`" in runbook
    assert "Telegram stays quiet" in runbook
    assert "xoxb-" not in runbook
    assert "TELEGRAM_BOT_TOKEN" not in runbook
    assert "sk-" not in runbook


def test_standup_cron_powershell_exports_active_commands_only():
    script = standup_cron_powershell(
        {"standup_cadence": "every day"},
        [
            {
                "id": "morning-standup",
                "name": "Morning Standup",
                "hour": 9,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent only",
                "active": 1,
            },
            {
                "id": "paused-standup",
                "name": "Paused Standup",
                "hour": 23,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent only",
                "active": 0,
            },
        ],
    )

    assert "Hermes Company OS standup cron installer" in script
    assert 'chief-of-staff cron create "every day at 9am"' in script
    assert "chief-of-staff cron list" in script
    assert "Paused Standup" not in script
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
