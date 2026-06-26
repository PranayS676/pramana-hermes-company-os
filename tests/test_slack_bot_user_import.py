import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.slack_bot_user_import import (
    parse_slack_bot_user_reply,
    slack_bot_user_import_redirect,
    slack_bot_user_template_json,
    slack_bot_user_template_markdown,
)

AGENTS = [
    {"id": "chief-of-staff", "name": "Chief of Staff"},
    {"id": "engineering-manager", "name": "Engineering Manager"},
]


def test_slack_bot_user_templates_are_no_secret_and_profile_keyed():
    markdown = slack_bot_user_template_markdown(
        AGENTS,
        {"slack_bot_user_id_chief_of_staff": "U012ABCDEF"},
    )
    payload = json.loads(
        slack_bot_user_template_json(
            AGENTS,
            {"slack_bot_user_id_chief_of_staff": "U012ABCDEF"},
        )
    )
    raw = markdown + json.dumps(payload)

    assert "Slack Bot User ID Reply Template" in markdown
    assert "chief-of-staff=U012ABCDEF" in markdown
    assert payload["entry_points"]["bulk_import"] == "/setup#slack-bot-user-import"
    assert payload["bot_user_ids"][0]["input_key"] == (
        "slack_bot_user_id_chief_of_staff"
    )
    assert secret_violations({"raw": raw}) == []


def test_parse_slack_bot_user_reply_accepts_json_and_lines():
    json_summary = parse_slack_bot_user_reply(
        '{"bot_user_ids":{"chief-of-staff":"U012ABCDEF"}}',
        AGENTS,
    )
    line_summary = parse_slack_bot_user_reply(
        "engineering-manager=U045GHIJKL\nmissing-profile=U999AAAAAA\nignored line",
        AGENTS,
    )

    assert json_summary["values"] == {
        "slack_bot_user_id_chief_of_staff": "U012ABCDEF"
    }
    assert line_summary["values"] == {
        "slack_bot_user_id_engineering_manager": "U045GHIJKL"
    }
    assert line_summary["unknown_profiles"] == ["missing-profile"]
    assert line_summary["ignored_lines"] == ["ignored line"]


def test_parse_slack_bot_user_reply_rejects_invalid_ids_and_ignores_placeholders():
    summary = parse_slack_bot_user_reply(
        """
        chief-of-staff=U_REPLACE_WITH_CHIEF_OF_STAFF_BOT_USER_ID
        engineering-manager=not-a-slack-id
        """,
        AGENTS,
    )

    assert summary["values"] == {}
    assert summary["invalid_user_ids"] == ["engineering-manager"]
    assert summary["ignored_lines"] == ["chief-of-staff=<empty>"]


def test_slack_bot_user_redirect_counts_import_summary():
    summary = {
        "imported": 2,
        "unknown_profiles": ["missing"],
        "invalid_user_ids": [],
        "ignored_lines": ["ignored"],
    }

    assert slack_bot_user_import_redirect(summary) == (
        "/setup?slack_bot_user_imported=2&slack_bot_user_unknown=1"
        "&slack_bot_user_invalid=0&slack_bot_user_ignored=1"
        "#slack-bot-user-import"
    )
