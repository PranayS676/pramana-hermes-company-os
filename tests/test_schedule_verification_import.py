import json

from hermes_company_os.schedule_verification_import import (
    parse_schedule_verification_reply,
    schedule_verification_import_redirect,
    schedule_verification_template_json,
    schedule_verification_template_markdown,
)
from hermes_company_os.secret_guard import secret_violations

CHECKS = [
    {
        "id": "morning-standup-manual-run",
        "label": "Morning Standup manual dashboard run",
        "schedule_id": "morning-standup",
        "schedule_name": "Morning Standup",
        "check_type": "manual_run",
        "status": "needed",
        "schedule_active": 1,
        "evidence": "",
    },
    {
        "id": "morning-standup-cron-installed",
        "label": "Morning Standup cron installed",
        "schedule_id": "morning-standup",
        "schedule_name": "Morning Standup",
        "check_type": "cron_installed",
        "status": "needed",
        "schedule_active": 1,
        "evidence": "",
    },
]


def test_schedule_verification_template_exports_no_secret_reply_format():
    markdown = schedule_verification_template_markdown(CHECKS)
    payload = json.loads(schedule_verification_template_json(CHECKS))
    raw = markdown + json.dumps(payload)

    assert "Schedule Verification Reply Template" in markdown
    assert "morning-standup-manual-run=needed | non-secret schedule evidence" in markdown
    assert payload["allowed_statuses"] == [
        "blocked",
        "deferred",
        "needed",
        "verified",
    ]
    assert payload["entry_points"]["bulk_import"] == "/setup/verification#schedule-verification"
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_parse_schedule_verification_reply_collects_updates_and_bad_status():
    summary = parse_schedule_verification_reply(
        """
        morning-standup-manual-run=verified | Posted summary to Slack.
        morning-standup-cron-installed: blocked | Cron command unavailable.
        unknown-check=verified
        morning-standup-manual-run=done
        not a status line
        """,
        CHECKS,
    )

    assert summary["updates"] == {
        "morning-standup-cron-installed": {
            "status": "blocked",
            "evidence": "Cron command unavailable.",
        }
    }
    assert summary["unknown_ids"] == ["unknown-check"]
    assert summary["invalid_statuses"] == ["morning-standup-manual-run"]
    assert summary["ignored_lines"] == ["not a status line"]


def test_schedule_verification_import_redirect_targets_schedule_panel():
    redirect = schedule_verification_import_redirect(
        {
            "imported": 2,
            "unknown_ids": ["missing"],
            "invalid_statuses": ["bad"],
            "ignored_lines": ["ignored"],
        }
    )

    assert redirect == (
        "/setup/verification?schedule_imported=2&schedule_unknown=1"
        "&schedule_invalid=1&schedule_ignored=1#schedule-verification"
    )
