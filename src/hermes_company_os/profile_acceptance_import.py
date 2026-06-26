from __future__ import annotations

import json
import re

STATUS_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
ALLOWED_PROFILE_ACCEPTANCE_STATUSES = {
    "needed",
    "verified",
    "failed",
    "blocked",
    "deferred",
}


def profile_acceptance_template_markdown(acceptance_checks: list[dict]) -> str:
    lines = [
        "# Profile Acceptance Reply Template",
        "",
        "Use this after running the role-specific prompts from "
        "`/setup/profile-acceptance.md` through the matching Hermes profiles. This "
        "template records status and non-secret evidence only; do not paste provider "
        "keys, tokens, request headers, raw transcripts, or private logs.",
        "",
        "## Reply Template",
        "",
        "```text",
    ]
    for check in acceptance_checks:
        lines.append(f"{check['id']}={check['status']} | non-secret acceptance evidence")
    lines.extend(
        [
            "```",
            "",
            "## Status Values",
            "",
            "- `needed`: acceptance prompt has not run yet.",
            "- `verified`: the profile response met the expected role signals.",
            "- `failed`: the profile response hit failure signals or needs tuning.",
            "- `blocked`: the check cannot proceed because of an external issue.",
            "- `deferred`: intentionally held until a later phase.",
            "",
            "## Checks",
            "",
        ]
    )
    for check in acceptance_checks:
        lines.append(
            f"- `{check['id']}`: {check['agent_name']} - {check['title']} "
            f"(`{check['hermes_command']}`)"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#profile-acceptance-tracking`",
            "- Acceptance suite: `/setup/profile-acceptance.md`",
            "- Evidence summary: `/setup/verification-evidence.md`",
            "",
        ]
    )
    return "\n".join(lines)


def profile_acceptance_template_json(acceptance_checks: list[dict]) -> str:
    payload = {
        "title": "Profile Acceptance Reply Template",
        "credential_boundary": (
            "Status and non-secret evidence only. Do not include provider keys, "
            "tokens, request headers, raw transcripts, or private logs."
        ),
        "allowed_statuses": sorted(ALLOWED_PROFILE_ACCEPTANCE_STATUSES),
        "entry_points": {
            "bulk_import": "/setup#profile-acceptance-tracking",
            "acceptance_suite": "/setup/profile-acceptance.md",
            "verification_evidence": "/setup/verification-evidence.md",
        },
        "checks": [
            {
                "id": check["id"],
                "agent_id": check["agent_id"],
                "agent_name": check["agent_name"],
                "title": check["title"],
                "hermes_command": check["hermes_command"],
                "status": check["status"],
            }
            for check in acceptance_checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_profile_acceptance_reply(
    raw_text: str,
    acceptance_checks: list[dict],
) -> dict:
    known_ids = {item["id"] for item in acceptance_checks}
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
        if status not in ALLOWED_PROFILE_ACCEPTANCE_STATUSES:
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


def profile_acceptance_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"profile_acceptance_imported={summary['imported']}"
        f"&profile_acceptance_unknown={len(summary['unknown_ids'])}"
        f"&profile_acceptance_invalid={len(summary['invalid_statuses'])}"
        f"&profile_acceptance_ignored={len(summary['ignored_lines'])}"
        "#profile-acceptance-tracking"
    )


def _parse_status_value(value: str) -> tuple[str, str]:
    status_part, separator, evidence = value.partition("|")
    status = _strip_inline_comment(status_part).strip().lower()
    return status, evidence.strip() if separator else ""


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()
