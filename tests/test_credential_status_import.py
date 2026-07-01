import json

from hermes_company_os.credential_status_import import (
    credential_status_import_redirect,
    credential_status_template_json,
    credential_status_template_markdown,
    parse_credential_status_reply,
)

REQUIREMENTS = [
    {
        "id": "chief-of-staff-slack-bot-token",
        "category": "slack",
        "label": "Chief of Staff Slack bot token",
        "owner_name": "Chief of Staff",
        "owner_agent_id": "chief-of-staff",
        "environment_key": "SLACK_BOT_TOKEN",
        "destination": "chief-of-staff Hermes profile .env",
        "status": "needed",
        "notes": "Load externally.",
    },
    {
        "id": "chief-of-staff-llm-provider-credential",
        "category": "llm",
        "label": "Chief of Staff LLM provider credential",
        "owner_name": "Chief of Staff",
        "owner_agent_id": "chief-of-staff",
        "environment_key": "PROVIDER_API_KEY_OR_OAUTH",
        "destination": "chief-of-staff Hermes profile .env",
        "status": "deferred",
        "notes": "Final provider credentials are last.",
    },
]


def test_credential_status_template_markdown_has_no_secret_examples():
    markdown = credential_status_template_markdown(REQUIREMENTS)

    assert "External Credential Status Template" in markdown
    assert "chief-of-staff-slack-bot-token=needed | status note only" in markdown
    assert "/setup/messaging#credential-status-import" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown


def test_credential_status_template_json_is_structured():
    payload = json.loads(credential_status_template_json(REQUIREMENTS))

    assert payload["title"] == "External Credential Status Template"
    assert payload["entry_points"]["bulk_import"] == "/setup/messaging#credential-status-import"
    assert payload["requirements"][0]["id"] == "chief-of-staff-slack-bot-token"
    assert payload["requirements"][0]["environment_key"] == "SLACK_BOT_TOKEN"


def test_parse_credential_status_reply_tracks_updates_and_skips_unknown_lines():
    summary = parse_credential_status_reply(
        raw_text="""
        ```text
        chief-of-staff-slack-bot-token=loaded | Loaded in profile env.
        chief-of-staff-llm-provider-credential: deferred # wait until final
        missing-requirement=loaded
        not a status line
        ```
        """,
        secret_requirements=REQUIREMENTS,
    )

    assert summary["updates"] == {
        "chief-of-staff-slack-bot-token": {
            "status": "loaded",
            "notes": "Loaded in profile env.",
        },
        "chief-of-staff-llm-provider-credential": {
            "status": "deferred",
            "notes": "",
        },
    }
    assert summary["imported"] == 2
    assert summary["unknown_ids"] == ["missing-requirement"]
    assert summary["invalid_statuses"] == []
    assert summary["ignored_lines"] == ["not a status line"]


def test_parse_credential_status_reply_reports_invalid_statuses():
    summary = parse_credential_status_reply(
        raw_text="chief-of-staff-slack-bot-token=done",
        secret_requirements=REQUIREMENTS,
    )

    assert summary["updates"] == {}
    assert summary["invalid_statuses"] == ["chief-of-staff-slack-bot-token"]


def test_credential_status_import_redirect_summarizes_parse_result():
    redirect = credential_status_import_redirect(
        {
            "imported": 2,
            "unknown_ids": ["missing"],
            "invalid_statuses": ["bad"],
            "ignored_lines": ["not status"],
        }
    )

    assert redirect == (
        "/setup/messaging?credential_imported=2&credential_unknown=1"
        "&credential_invalid=1&credential_ignored=1#secret-status"
    )
