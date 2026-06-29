from __future__ import annotations

import json
import re

from hermes_company_os.setup_import_parsing import (
    parse_status_value as _parse_status_value,
)

STATUS_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
ALLOWED_KANBAN_VERIFICATION_STATUSES = {
    "needed",
    "verified",
    "blocked",
    "deferred",
}


def kanban_verification_template_markdown(kanban_checks: list[dict]) -> str:
    lines = [
        "# Kanban Verification Reply Template",
        "",
        "Use this after Hermes Kanban board initialization, diagnostics, and one "
        "dashboard task creation drill. This template records status and non-secret "
        "evidence only; do not paste tokens, provider keys, request headers, private "
        "task payloads, or raw logs.",
        "",
        "## Reply Template",
        "",
        "```text",
    ]
    for check in kanban_checks:
        lines.append(f"{check['id']}={check['status']} | non-secret Kanban evidence")
    lines.extend(
        [
            "```",
            "",
            "## Status Values",
            "",
            "- `needed`: Kanban check has not run yet.",
            "- `verified`: board, diagnostics, or task creation behavior was observed.",
            "- `blocked`: check cannot proceed because of an external issue.",
            "- `deferred`: intentionally held until a later phase.",
            "",
            "## Checks",
            "",
        ]
    )
    for check in kanban_checks:
        lines.append(
            f"- `{check['id']}`: {check['label']} ({check['check_type']})"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#kanban-verification`",
            "- Kanban provisioning: `/setup/kanban-provisioning.md`",
            "- Kanban runbook: `/setup/kanban-runbook.md`",
            "",
        ]
    )
    return "\n".join(lines)


def kanban_verification_template_json(kanban_checks: list[dict]) -> str:
    payload = {
        "title": "Kanban Verification Reply Template",
        "credential_boundary": (
            "Status and non-secret evidence only. Do not include tokens, provider "
            "keys, request headers, private task payloads, or raw logs."
        ),
        "allowed_statuses": sorted(ALLOWED_KANBAN_VERIFICATION_STATUSES),
        "entry_points": {
            "bulk_import": "/setup#kanban-verification",
            "kanban_provisioning": "/setup/kanban-provisioning.md",
            "kanban_runbook": "/setup/kanban-runbook.md",
        },
        "checks": [
            {
                "id": check["id"],
                "label": check["label"],
                "check_type": check["check_type"],
                "status": check["status"],
            }
            for check in kanban_checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_kanban_verification_reply(
    raw_text: str,
    kanban_checks: list[dict],
) -> dict:
    known_ids = {item["id"] for item in kanban_checks}
    updates: dict[str, dict] = {}
    unknown_ids: list[str] = []
    invalid_statuses: list[str] = []
    ignored_lines: list[str] = []

    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("```"):
            continue
        match = STATUS_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        check_id, raw_value = match.groups()
        if check_id not in known_ids:
            unknown_ids.append(check_id)
            continue
        status, evidence = _parse_status_value(raw_value)
        if status not in ALLOWED_KANBAN_VERIFICATION_STATUSES:
            invalid_statuses.append(check_id)
            updates.pop(check_id, None)
            continue
        updates[check_id] = {"status": status, "evidence": evidence}

    return {
        "updates": updates,
        "imported": len(updates),
        "unknown_ids": sorted(set(unknown_ids)),
        "invalid_statuses": sorted(set(invalid_statuses)),
        "ignored_lines": ignored_lines,
    }


def kanban_verification_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"kanban_imported={summary['imported']}"
        f"&kanban_unknown={len(summary['unknown_ids'])}"
        f"&kanban_invalid={len(summary['invalid_statuses'])}"
        f"&kanban_ignored={len(summary['ignored_lines'])}"
        "#kanban-verification"
    )
