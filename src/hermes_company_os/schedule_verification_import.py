from __future__ import annotations

import json
import re

STATUS_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
ALLOWED_SCHEDULE_VERIFICATION_STATUSES = {
    "needed",
    "verified",
    "blocked",
    "deferred",
}


def schedule_verification_template_markdown(schedule_checks: list[dict]) -> str:
    lines = [
        "# Schedule Verification Reply Template",
        "",
        "Use this after manual standup runs and Chief of Staff cron install/list "
        "checks. This template records status and non-secret evidence only; do not "
        "paste Slack tokens, Telegram bot tokens, provider keys, request headers, "
        "private chat logs, or raw profile outputs.",
        "",
        "## Reply Template",
        "",
        "```text",
    ]
    for check in schedule_checks:
        lines.append(f"{check['id']}={check['status']} | non-secret schedule evidence")
    lines.extend(
        [
            "```",
            "",
            "## Status Values",
            "",
            "- `needed`: schedule check has not run yet.",
            "- `verified`: manual standup or cron/list behavior was observed.",
            "- `blocked`: check cannot proceed because of an external issue.",
            "- `deferred`: intentionally held until a later phase.",
            "",
            "## Checks",
            "",
        ]
    )
    for check in schedule_checks:
        lines.append(
            f"- `{check['id']}`: {check['label']} "
            f"({check['schedule_name']} / {check['check_type']})"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#schedule-verification`",
            "- Schedule provisioning: `/setup/schedule-provisioning.md`",
            "- Standup runbook: `/setup/standup-runbook.md`",
            "",
        ]
    )
    return "\n".join(lines)


def schedule_verification_template_json(schedule_checks: list[dict]) -> str:
    payload = {
        "title": "Schedule Verification Reply Template",
        "credential_boundary": (
            "Status and non-secret evidence only. Do not include Slack tokens, "
            "Telegram bot tokens, provider keys, request headers, private chat "
            "logs, or raw profile outputs."
        ),
        "allowed_statuses": sorted(ALLOWED_SCHEDULE_VERIFICATION_STATUSES),
        "entry_points": {
            "bulk_import": "/setup#schedule-verification",
            "schedule_provisioning": "/setup/schedule-provisioning.md",
            "standup_runbook": "/setup/standup-runbook.md",
        },
        "checks": [
            {
                "id": check["id"],
                "label": check["label"],
                "schedule_id": check["schedule_id"],
                "schedule_name": check["schedule_name"],
                "check_type": check["check_type"],
                "status": check["status"],
                "schedule_active": bool(check.get("schedule_active", 1)),
            }
            for check in schedule_checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_schedule_verification_reply(
    raw_text: str,
    schedule_checks: list[dict],
) -> dict:
    known_ids = {item["id"] for item in schedule_checks}
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
        if status not in ALLOWED_SCHEDULE_VERIFICATION_STATUSES:
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


def schedule_verification_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"schedule_imported={summary['imported']}"
        f"&schedule_unknown={len(summary['unknown_ids'])}"
        f"&schedule_invalid={len(summary['invalid_statuses'])}"
        f"&schedule_ignored={len(summary['ignored_lines'])}"
        "#schedule-verification"
    )


def _parse_status_value(value: str) -> tuple[str, str]:
    status_part, separator, evidence = value.partition("|")
    status = _strip_inline_comment(status_part).strip().lower()
    return status, evidence.strip() if separator else ""


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()
