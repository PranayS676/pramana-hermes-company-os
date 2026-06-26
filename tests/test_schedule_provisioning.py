import json

from hermes_company_os.schedule_provisioning import (
    schedule_provisioning_json,
    schedule_provisioning_markdown,
    schedule_provisioning_payload,
    schedule_provisioning_powershell,
)
from hermes_company_os.secret_guard import secret_violations

AGENTS = [
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
    }
]

SCHEDULES = [
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
        "minute": 30,
        "timezone": "America/New_York",
        "slack_channel": "#agent-standup",
        "telegram_policy": "urgent only",
        "active": 0,
    },
]

SCHEDULE_CHECKS = [
    {
        "id": "morning-standup-manual-run",
        "label": "Morning Standup manual dashboard run",
        "schedule_id": "morning-standup",
        "status": "needed",
        "evidence": "",
        "schedule_active": 1,
    }
]


def test_schedule_provisioning_payload_maps_active_paused_and_cron_shape():
    payload = schedule_provisioning_payload(
        agents=AGENTS,
        setup_values={"standup_cadence": "weekdays"},
        schedules=SCHEDULES,
        schedule_checks=SCHEDULE_CHECKS,
    )

    assert payload["title"] == "Schedule Provisioning Pack"
    assert payload["owner_profile"]["hermes_command"] == "chief-of-staff"
    assert payload["cadence"] == "every weekday"
    assert payload["delivery_policy"]["primary_workspace"] == "slack"
    assert len(payload["active_schedules"]) == 1
    assert len(payload["paused_schedules"]) == 1
    active = payload["active_schedules"][0]
    assert active["expression"] == "every weekday at 9am"
    assert active["cron_command"].startswith(
        'chief-of-staff cron create "every weekday at 9am"'
    )
    assert payload["verification"]["ready"] is False
    assert payload["runner"]["default_mode"] == "dry_run"
    assert payload["runner"]["commands"]["post_dashboard_status"].startswith(
        "post verified status"
    )
    assert payload["entry_points"]["schedule_config"] == (
        "/setup/schedule-config-template.md"
    )


def test_schedule_provisioning_exports_no_secret_markdown_json_and_runner():
    kwargs = {
        "agents": AGENTS,
        "setup_values": {"standup_cadence": "every day"},
        "schedules": SCHEDULES,
        "schedule_checks": SCHEDULE_CHECKS,
    }
    markdown = schedule_provisioning_markdown(**kwargs)
    payload = json.loads(schedule_provisioning_json(**kwargs))
    script = schedule_provisioning_powershell(
        agents=AGENTS,
        setup_values=kwargs["setup_values"],
        schedules=SCHEDULES,
    )
    raw = json.dumps(payload) + markdown + script

    assert "Schedule Provisioning Pack" in markdown
    assert "Morning Standup" in markdown
    assert "every day at 9am" in markdown
    assert payload["title"] == "Schedule Provisioning Pack"
    assert "Hermes Company OS schedule provisioning runner" in script
    assert "Dry run only" in script
    assert "PostDashboardStatus" in script
    assert "Post-CronInstalledStatus" in script
    assert "/setup/schedule-checks/$checkId" in script
    assert "DASHBOARD verified $checkId" in script
    assert "DASHBOARD skipped ${checkId}:" in script
    assert "DASHBOARD skipped $checkId:" not in script
    assert "-PostDashboardStatus" in markdown
    assert '& $schedule.OwnerCommand "cron" "create"' in script
    assert '"cron" "list"' in script
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
