import json

from hermes_company_os.profile_acceptance_import import (
    parse_profile_acceptance_reply,
    profile_acceptance_import_redirect,
    profile_acceptance_template_json,
    profile_acceptance_template_markdown,
)
from hermes_company_os.secret_guard import secret_violations

CHECKS = [
    {
        "id": "engineering-manager-acceptance-1",
        "agent_id": "engineering-manager",
        "agent_name": "Engineering Manager",
        "title": "Architecture and test plan",
        "hermes_command": "engineering-manager",
        "status": "needed",
        "evidence": "",
    },
    {
        "id": "product-manager-acceptance-1",
        "agent_id": "product-manager",
        "agent_name": "Product Manager",
        "title": "Less-is-more PRD",
        "hermes_command": "product-manager",
        "status": "failed",
        "evidence": "Too many controls.",
    },
]


def test_profile_acceptance_template_exports_no_secret_reply_format():
    markdown = profile_acceptance_template_markdown(CHECKS)
    payload = json.loads(profile_acceptance_template_json(CHECKS))
    raw = markdown + json.dumps(payload)

    assert "Profile Acceptance Reply Template" in markdown
    assert (
        "engineering-manager-acceptance-1=needed | non-secret acceptance evidence"
        in markdown
    )
    assert payload["allowed_statuses"] == [
        "blocked",
        "deferred",
        "failed",
        "needed",
        "verified",
    ]
    assert payload["entry_points"]["bulk_import"] == (
        "/setup/profiles#profile-acceptance-tracking"
    )
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_parse_profile_acceptance_reply_collects_updates_and_rejects_bad_status():
    summary = parse_profile_acceptance_reply(
        """
        engineering-manager-acceptance-1=verified | Strong architecture and tests.
        product-manager-acceptance-1: failed | Added too many buttons.
        unknown-check=verified
        engineering-manager-acceptance-1=done
        not a status line
        """,
        CHECKS,
    )

    assert summary["updates"] == {
        "product-manager-acceptance-1": {
            "status": "failed",
            "evidence": "Added too many buttons.",
        }
    }
    assert summary["unknown_ids"] == ["unknown-check"]
    assert summary["invalid_statuses"] == ["engineering-manager-acceptance-1"]
    assert summary["ignored_lines"] == ["not a status line"]


def test_parse_profile_acceptance_reply_supports_inline_comments():
    summary = parse_profile_acceptance_reply(
        "engineering-manager-acceptance-1=deferred # wait for LLM finalization",
        CHECKS,
    )

    assert summary["updates"] == {
        "engineering-manager-acceptance-1": {"status": "deferred", "evidence": ""}
    }


def test_profile_acceptance_import_redirect_targets_acceptance_panel():
    redirect = profile_acceptance_import_redirect(
        {
            "imported": 2,
            "unknown_ids": ["missing"],
            "invalid_statuses": ["bad"],
            "ignored_lines": ["ignored"],
        }
    )

    assert redirect == (
        "/setup/profiles?profile_acceptance_imported=2&profile_acceptance_unknown=1"
        "&profile_acceptance_invalid=1&profile_acceptance_ignored=1"
        "#profile-acceptance-tracking"
    )
