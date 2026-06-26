import json

from hermes_company_os.profile_personalization_import import (
    parse_profile_personalization_reply,
    profile_personalization_import_redirect,
    profile_personalization_template_json,
    profile_personalization_template_markdown,
)
from hermes_company_os.secret_guard import secret_violations

AGENTS = [
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "description": "Builds architecture.",
        "soul": "Think big.",
        "capabilities": ["architecture", "testing"],
        "slack_channel": "#engineering",
        "telegram_policy": "urgent only",
        "hermes_command": "engineering-manager",
    },
    {
        "id": "product-manager",
        "name": "Product Manager",
        "description": "Owns product scope.",
        "soul": "Less is more.",
        "capabilities": ["prd", "scope"],
        "slack_channel": "#product",
        "telegram_policy": "urgent only",
        "hermes_command": "product-manager",
    },
]


def test_profile_personalization_template_exports_no_secret_json():
    markdown = profile_personalization_template_markdown(AGENTS)
    payload = json.loads(profile_personalization_template_json(AGENTS))
    raw = markdown + json.dumps(payload)

    assert "Profile Personalization Reply Template" in markdown
    assert payload["entry_points"]["bulk_import"] == (
        "/setup#profile-personalization-import"
    )
    assert "description" in payload["editable_fields"]
    assert payload["profiles"][0]["id"] == "engineering-manager"
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_parse_profile_personalization_reply_collects_partial_updates():
    summary = parse_profile_personalization_reply(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "engineering-manager",
                        "description": "Builds ambitious distributed systems.",
                        "capabilities": [
                            "distributed systems",
                            "aws architecture",
                            "e2e testing",
                        ],
                    },
                    {
                        "id": "product-manager",
                        "slack_channel": "#product-strategy",
                        "telegram_policy": "Telegram only for launch blockers.",
                    },
                ]
            }
        ),
        AGENTS,
    )

    assert summary["updates"]["engineering-manager"] == {
        "description": "Builds ambitious distributed systems.",
        "capabilities": [
            "distributed systems",
            "aws architecture",
            "e2e testing",
        ],
    }
    assert summary["updates"]["product-manager"] == {
        "slack_channel": "#product-strategy",
        "telegram_policy": "Telegram only for launch blockers.",
    }
    assert summary["imported"] == 2
    assert summary["parse_error"] == ""


def test_parse_profile_personalization_reply_reports_bad_payloads():
    summary = parse_profile_personalization_reply(
        json.dumps(
            {
                "profiles": [
                    {"id": "missing-agent", "description": "Unknown."},
                    {"id": "engineering-manager", "description": ""},
                    {"id": "product-manager", "name": "Ignored only"},
                    "not an object",
                ]
            }
        ),
        AGENTS,
    )

    assert summary["updates"] == {}
    assert summary["unknown_ids"] == ["missing-agent"]
    assert summary["invalid_profiles"] == [
        "engineering-manager",
        "product-manager",
        "profile-4",
    ]
    assert summary["ignored_fields"] == ["product-manager.name"]


def test_parse_profile_personalization_reply_supports_markdown_fence():
    summary = parse_profile_personalization_reply(
        """```json
        {"profiles":[{"id":"engineering-manager","capabilities":"aws, testing"}]}
        ```""",
        AGENTS,
    )

    assert summary["updates"] == {
        "engineering-manager": {"capabilities": ["aws", "testing"]}
    }


def test_profile_personalization_import_redirect_targets_import_panel():
    redirect = profile_personalization_import_redirect(
        {
            "imported": 2,
            "unknown_ids": ["missing"],
            "invalid_profiles": ["bad"],
            "ignored_fields": ["name"],
        }
    )

    assert redirect == (
        "/setup?profile_personalization_imported=2"
        "&profile_personalization_unknown=1"
        "&profile_personalization_invalid=1"
        "&profile_personalization_ignored=1"
        "#profile-personalization-import"
    )
