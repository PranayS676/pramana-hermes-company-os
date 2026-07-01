import json

from hermes_company_os.messaging_verification_import import (
    messaging_verification_import_redirect,
    messaging_verification_template_json,
    messaging_verification_template_markdown,
    parse_messaging_verification_reply,
)
from hermes_company_os.secret_guard import secret_violations

CHECKS = [
    {
        "id": "research-agent-slack-dm",
        "label": "Research Agent Slack DM response",
        "platform": "slack",
        "owner_agent_id": "research-agent",
        "owner_name": "Research Agent",
        "status": "needed",
        "evidence": "",
    },
    {
        "id": "chief-of-staff-telegram-urgent-alert",
        "label": "Chief of Staff Telegram urgent alert",
        "platform": "telegram",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "status": "loaded",
        "evidence": "",
    },
]


def test_messaging_verification_template_exports_no_secret_reply_format():
    markdown = messaging_verification_template_markdown(CHECKS)
    payload = json.loads(messaging_verification_template_json(CHECKS))
    raw = markdown + json.dumps(payload)

    assert "Messaging Verification Reply Template" in markdown
    assert "research-agent-slack-dm=needed | non-secret evidence" in markdown
    assert payload["allowed_statuses"] == [
        "blocked",
        "deferred",
        "loaded",
        "needed",
        "verified",
    ]
    assert payload["entry_points"]["bulk_import"] == "/setup/messaging#messaging-verification"
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_parse_messaging_verification_reply_collects_updates_and_rejects_bad_status():
    summary = parse_messaging_verification_reply(
        """
        research-agent-slack-dm=verified | Founder DM reply observed.
        chief-of-staff-telegram-urgent-alert: blocked | Chat ID not available yet.
        unknown-check=verified
        research-agent-slack-dm=done
        not a status line
        """,
        CHECKS,
    )

    assert summary["updates"] == {
        "chief-of-staff-telegram-urgent-alert": {
            "status": "blocked",
            "evidence": "Chat ID not available yet.",
        }
    }
    assert summary["unknown_ids"] == ["unknown-check"]
    assert summary["invalid_statuses"] == ["research-agent-slack-dm"]
    assert summary["ignored_lines"] == ["not a status line"]


def test_messaging_verification_import_redirect_targets_messaging_panel():
    summary = {
        "imported": 2,
        "unknown_ids": ["missing"],
        "invalid_statuses": [],
        "ignored_lines": ["ignored"],
    }

    assert messaging_verification_import_redirect(summary) == (
        "/setup/messaging?messaging_imported=2&messaging_unknown=1&messaging_invalid=0"
        "&messaging_ignored=1#messaging-verification"
    )
