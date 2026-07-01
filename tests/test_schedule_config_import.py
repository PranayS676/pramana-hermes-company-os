import json

from hermes_company_os.schedule_config_import import (
    parse_schedule_config_reply,
    schedule_config_import_redirect,
    schedule_config_template_json,
    schedule_config_template_markdown,
)
from hermes_company_os.secret_guard import secret_violations

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
        "id": "afternoon-standup",
        "name": "Afternoon Standup",
        "hour": 15,
        "minute": 0,
        "timezone": "America/New_York",
        "slack_channel": "#agent-standup",
        "telegram_policy": "urgent only",
        "active": 1,
    },
]


def test_schedule_config_templates_are_no_secret_and_show_current_values():
    markdown = schedule_config_template_markdown(SCHEDULES)
    payload = json.loads(schedule_config_template_json(SCHEDULES))
    raw = markdown + json.dumps(payload)

    assert "Schedule Configuration Reply Template" in markdown
    assert "morning-standup.hour=9" in markdown
    assert payload["entry_points"]["bulk_import"] == "/setup/schedules#schedule-config-import"
    assert payload["schedules"][0]["id"] == "morning-standup"
    assert secret_violations({"raw": raw}) == []


def test_parse_schedule_config_reply_accepts_json_and_partial_line_updates():
    json_summary = parse_schedule_config_reply(
        '{"schedules":[{"id":"morning-standup","hour":10,"minute":15,"active":false}]}',
        SCHEDULES,
    )
    line_summary = parse_schedule_config_reply(
        "afternoon-standup.name=Founder sync\n"
        "afternoon-standup.slack_channel=CSTANDUP123\n"
        "missing-standup.hour=8\n"
        "ignored line",
        SCHEDULES,
    )

    assert json_summary["updates"]["morning-standup"]["hour"] == 10
    assert json_summary["updates"]["morning-standup"]["minute"] == 15
    assert json_summary["updates"]["morning-standup"]["active"] is False
    assert json_summary["updates"]["morning-standup"]["timezone"] == "America/New_York"
    assert line_summary["updates"]["afternoon-standup"]["name"] == "Founder sync"
    assert line_summary["updates"]["afternoon-standup"]["slack_channel"] == "CSTANDUP123"
    assert line_summary["updates"]["afternoon-standup"]["hour"] == 15
    assert line_summary["unknown_schedules"] == ["missing-standup"]
    assert line_summary["ignored_lines"] == ["ignored line"]


def test_parse_schedule_config_reply_rejects_invalid_values():
    summary = parse_schedule_config_reply(
        """
        morning-standup.hour=26
        morning-standup.slack_channel=not a channel
        morning-standup.active=maybe
        afternoon-standup.nope=value
        """,
        SCHEDULES,
    )

    assert summary["updates"] == {}
    assert summary["invalid_schedules"] == ["morning-standup"]
    assert summary["invalid_fields"] == [
        "afternoon-standup.nope",
        "morning-standup.active",
        "morning-standup.hour",
        "morning-standup.slack_channel",
    ]


def test_schedule_config_redirect_counts_import_summary():
    summary = {
        "imported": 1,
        "unknown_schedules": ["missing"],
        "invalid_fields": ["morning-standup.hour"],
        "ignored_lines": ["ignored"],
    }

    assert schedule_config_import_redirect(summary) == (
        "/setup/schedules?schedule_config_imported=1&schedule_config_unknown=1"
        "&schedule_config_invalid=1&schedule_config_ignored=1"
        "#schedule-config-import"
    )
