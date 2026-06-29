from __future__ import annotations

import json
import re

from hermes_company_os.setup_import_parsing import (
    parse_status_value as _parse_status_value,
)

STATUS_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
ALLOWED_CREDENTIAL_STATUSES = {"needed", "loaded", "verified", "deferred"}


def credential_status_template_markdown(secret_requirements: list[dict]) -> str:
    lines = [
        "# External Credential Status Template",
        "",
        "Use this after loading Slack, Telegram, or LLM credentials into real "
        "Hermes profile environments. This template records status only; do not "
        "paste token values, API keys, OAuth payloads, request headers, private "
        "endpoint credentials, or raw logs.",
        "",
        "## Reply Template",
        "",
        "```text",
    ]
    for item in secret_requirements:
        lines.append(f"{item['id']}={item['status']} | status note only")
    lines.extend(
        [
            "```",
            "",
            "## Status Values",
            "",
            "- `needed`: credential has not been loaded yet.",
            "- `loaded`: credential was loaded externally into the destination profile.",
            "- `verified`: credential was loaded and later verified by a live check.",
            "- `deferred`: intentionally held until a later phase.",
            "",
            "## Credential Destinations",
            "",
        ]
    )
    for item in secret_requirements:
        owner = item.get("owner_name") or item.get("owner_agent_id") or "unassigned"
        lines.append(
            f"- `{item['id']}`: {item['label']} for {owner} -> "
            f"{item['destination']} (`{item['environment_key']}`)"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk status import: `/setup#credential-status-import`",
            "- Manual status editing: `/setup#secret-status`",
            "- Final verification: `/setup/live-verification.md`",
            "",
        ]
    )
    return "\n".join(lines)


def credential_status_template_json(secret_requirements: list[dict]) -> str:
    payload = {
        "title": "External Credential Status Template",
        "credential_boundary": (
            "Status metadata only. Do not include Slack tokens, Telegram bot tokens, "
            "provider API keys, OAuth payloads, request headers, private endpoint "
            "credentials, or raw logs."
        ),
        "allowed_statuses": sorted(ALLOWED_CREDENTIAL_STATUSES),
        "entry_points": {
            "bulk_import": "/setup#credential-status-import",
            "manual_status": "/setup#secret-status",
            "live_verification": "/setup/live-verification.md",
        },
        "requirements": [
            {
                "id": item["id"],
                "category": item["category"],
                "label": item["label"],
                "owner": item.get("owner_name") or item.get("owner_agent_id") or "",
                "environment_key": item["environment_key"],
                "destination": item["destination"],
                "status": item["status"],
            }
            for item in secret_requirements
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_credential_status_reply(raw_text: str, secret_requirements: list[dict]) -> dict:
    known_ids = {item["id"] for item in secret_requirements}
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
        requirement_id, raw_value = match.groups()
        if requirement_id not in known_ids:
            unknown_ids.append(requirement_id)
            continue
        status, notes = _parse_status_value(raw_value)
        if status not in ALLOWED_CREDENTIAL_STATUSES:
            invalid_statuses.append(requirement_id)
            continue
        updates[requirement_id] = {"status": status, "notes": notes}

    return {
        "updates": updates,
        "imported": len(updates),
        "unknown_ids": sorted(set(unknown_ids)),
        "invalid_statuses": sorted(set(invalid_statuses)),
        "ignored_lines": ignored_lines,
    }


def credential_status_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"credential_imported={summary['imported']}"
        f"&credential_unknown={len(summary['unknown_ids'])}"
        f"&credential_invalid={len(summary['invalid_statuses'])}"
        f"&credential_ignored={len(summary['ignored_lines'])}"
        "#secret-status"
    )
