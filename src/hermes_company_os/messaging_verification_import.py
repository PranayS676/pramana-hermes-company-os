from __future__ import annotations

import json
import re

from hermes_company_os.setup_import_parsing import (
    parse_status_value as _parse_status_value,
)

STATUS_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
ALLOWED_MESSAGING_STATUSES = {"needed", "loaded", "verified", "blocked", "deferred"}


def messaging_verification_template_markdown(messaging_checks: list[dict]) -> str:
    lines = [
        "# Messaging Verification Reply Template",
        "",
        "Use this after running Slack DM, Slack channel mention, gateway, and "
        "Chief of Staff Telegram urgent-alert drills. This template records status "
        "and non-secret evidence only; do not paste tokens, request headers, private "
        "message logs, provider keys, or raw transcripts.",
        "",
        "## Reply Template",
        "",
        "```text",
    ]
    for check in messaging_checks:
        lines.append(f"{check['id']}={check['status']} | non-secret evidence")
    lines.extend(
        [
            "```",
            "",
            "## Status Values",
            "",
            "- `needed`: check has not run yet.",
            "- `loaded`: gateway setup/start is complete, but a live reply is not verified.",
            "- `verified`: live Slack or Telegram behavior was observed.",
            "- `blocked`: check cannot proceed because of an external issue.",
            "- `deferred`: intentionally held until a later phase.",
            "",
            "## Checks",
            "",
        ]
    )
    for check in messaging_checks:
        lines.append(
            f"- `{check['id']}`: {check['label']} ({check['platform']} / "
            f"{check['owner_name']})"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#messaging-verification`",
            "- Live verification runbook: `/setup/live-verification.md`",
            "- Evidence summary: `/setup/verification-evidence.md`",
            "",
        ]
    )
    return "\n".join(lines)


def messaging_verification_template_json(messaging_checks: list[dict]) -> str:
    payload = {
        "title": "Messaging Verification Reply Template",
        "credential_boundary": (
            "Status and non-secret evidence only. Do not include Slack tokens, "
            "Telegram bot tokens, request headers, private message logs, provider "
            "keys, or raw transcripts."
        ),
        "allowed_statuses": sorted(ALLOWED_MESSAGING_STATUSES),
        "entry_points": {
            "bulk_import": "/setup#messaging-verification",
            "live_verification": "/setup/live-verification.md",
            "verification_evidence": "/setup/verification-evidence.md",
        },
        "checks": [
            {
                "id": check["id"],
                "label": check["label"],
                "platform": check["platform"],
                "owner_agent_id": check["owner_agent_id"],
                "owner_name": check["owner_name"],
                "status": check["status"],
            }
            for check in messaging_checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_messaging_verification_reply(
    raw_text: str,
    messaging_checks: list[dict],
) -> dict:
    known_ids = {item["id"] for item in messaging_checks}
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
        if status not in ALLOWED_MESSAGING_STATUSES:
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


def messaging_verification_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"messaging_imported={summary['imported']}"
        f"&messaging_unknown={len(summary['unknown_ids'])}"
        f"&messaging_invalid={len(summary['invalid_statuses'])}"
        f"&messaging_ignored={len(summary['ignored_lines'])}"
        "#messaging-verification"
    )
