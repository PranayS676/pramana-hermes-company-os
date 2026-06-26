import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.slack_channel_import import (
    parse_slack_channel_reply,
    slack_channel_import_redirect,
    slack_channel_template_json,
    slack_channel_template_markdown,
)

AGENTS = [
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
    },
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "hermes_command": "engineering-manager",
    },
]


def test_slack_channel_templates_are_no_secret_and_show_current_values():
    setup_values = {
        "slack_channel_founder_command": "CFOUNDER123",
        "slack_channel_engineering": "CENGINEER123",
    }
    markdown = slack_channel_template_markdown(AGENTS, setup_values)
    payload = json.loads(slack_channel_template_json(AGENTS, setup_values))
    raw = markdown + json.dumps(payload)

    assert "Slack Channel ID Reply Template" in markdown
    assert "slack_channel_founder_command=CFOUNDER123" in markdown
    assert payload["entry_points"]["bulk_import"] == "/setup#slack-channel-import"
    assert payload["channel_ids"]["slack_channel_engineering"] == "CENGINEER123"
    assert secret_violations({"raw": raw}) == []


def test_parse_slack_channel_reply_accepts_json_and_channel_name_lines():
    json_summary = parse_slack_channel_reply(
        '{"channel_ids":{"slack_channel_founder_command":"CFOUNDER123"}}'
    )
    line_summary = parse_slack_channel_reply(
        "#engineering=CENGINEER123\nagent-standup=CSTANDUP123\nunknown=CUNKNOWN123\nignored line"
    )

    assert json_summary["values"] == {
        "slack_channel_founder_command": "CFOUNDER123"
    }
    assert line_summary["values"] == {
        "slack_channel_engineering": "CENGINEER123",
        "slack_channel_agent_standup": "CSTANDUP123",
    }
    assert line_summary["unknown_keys"] == ["unknown"]
    assert line_summary["ignored_lines"] == ["ignored line"]


def test_parse_slack_channel_reply_rejects_invalid_ids_and_placeholders():
    summary = parse_slack_channel_reply(
        """
        slack_channel_founder_command=C_REPLACE_WITH_FOUNDER_COMMAND_CHANNEL_ID
        slack_channel_engineering=not-a-channel-id
        """
    )

    assert summary["values"] == {}
    assert summary["invalid_channel_ids"] == ["slack_channel_engineering"]
    assert summary["ignored_lines"] == ["slack_channel_founder_command=<empty>"]


def test_slack_channel_redirect_counts_import_summary():
    summary = {
        "imported": 2,
        "unknown_keys": ["unknown"],
        "invalid_channel_ids": [],
        "ignored_lines": ["ignored"],
    }

    assert slack_channel_import_redirect(summary) == (
        "/setup?slack_channel_imported=2&slack_channel_unknown=1"
        "&slack_channel_invalid=0&slack_channel_ignored=1"
        "#slack-channel-import"
    )
