import json

from hermes_company_os.kanban_verification_import import (
    kanban_verification_import_redirect,
    kanban_verification_template_json,
    kanban_verification_template_markdown,
    parse_kanban_verification_reply,
)
from hermes_company_os.secret_guard import secret_violations

CHECKS = [
    {
        "id": "kanban-board-initialized",
        "label": "Kanban board initialized",
        "check_type": "board_init",
        "status": "needed",
        "evidence": "",
    },
    {
        "id": "kanban-diagnostics-pass",
        "label": "Kanban diagnostics pass",
        "check_type": "diagnostics",
        "status": "needed",
        "evidence": "",
    },
]


def test_kanban_verification_template_exports_no_secret_reply_format():
    markdown = kanban_verification_template_markdown(CHECKS)
    payload = json.loads(kanban_verification_template_json(CHECKS))
    raw = markdown + json.dumps(payload)

    assert "Kanban Verification Reply Template" in markdown
    assert "kanban-board-initialized=needed | non-secret Kanban evidence" in markdown
    assert payload["allowed_statuses"] == [
        "blocked",
        "deferred",
        "needed",
        "verified",
    ]
    assert payload["entry_points"]["bulk_import"] == "/setup#kanban-verification"
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_parse_kanban_verification_reply_collects_updates_and_bad_status():
    summary = parse_kanban_verification_reply(
        """
        kanban-board-initialized=verified | Board initialized.
        kanban-diagnostics-pass: blocked | Diagnostics command unavailable.
        unknown-check=verified
        kanban-board-initialized=done
        not a status line
        """,
        CHECKS,
    )

    assert summary["updates"] == {
        "kanban-diagnostics-pass": {
            "status": "blocked",
            "evidence": "Diagnostics command unavailable.",
        }
    }
    assert summary["unknown_ids"] == ["unknown-check"]
    assert summary["invalid_statuses"] == ["kanban-board-initialized"]
    assert summary["ignored_lines"] == ["not a status line"]


def test_kanban_verification_import_redirect_targets_kanban_panel():
    redirect = kanban_verification_import_redirect(
        {
            "imported": 2,
            "unknown_ids": ["missing"],
            "invalid_statuses": ["bad"],
            "ignored_lines": ["ignored"],
        }
    )

    assert redirect == (
        "/setup?kanban_imported=2&kanban_unknown=1"
        "&kanban_invalid=1&kanban_ignored=1#kanban-verification"
    )
