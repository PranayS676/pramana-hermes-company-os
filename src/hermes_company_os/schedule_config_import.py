from __future__ import annotations

import json
import re

SCHEDULE_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\.([A-Za-z0-9_]+)\s*(?:=|:)\s*(.*?)\s*$")
TIMEZONE = re.compile(r"^[A-Za-z][A-Za-z0-9_./+-]*$")
SLACK_TARGET = re.compile(r"^(#[a-z0-9][a-z0-9_-]{1,79}|[CGD][A-Z0-9]{2,})$")
SCHEDULE_FIELDS = {
    "name",
    "hour",
    "minute",
    "timezone",
    "slack_channel",
    "telegram_policy",
    "active",
}


def schedule_config_template_markdown(schedules: list[dict]) -> str:
    lines = [
        "# Schedule Configuration Reply Template",
        "",
        "Use this before cron setup to adjust the daily Chief of Staff standups. "
        "This stores only schedule metadata: no Slack tokens, Telegram tokens, "
        "provider API keys, private prompt output, or logs.",
        "",
        "## JSON Reply Template",
        "",
        "```json",
        json.dumps(
            {"schedules": [_schedule_template(schedule) for schedule in schedules]},
            indent=2,
        ),
        "```",
        "",
        "## Line Reply Template",
        "",
        "```text",
    ]
    for schedule in schedules:
        lines.extend(
            [
                f"{schedule['id']}.name={schedule['name']}",
                f"{schedule['id']}.hour={schedule['hour']}",
                f"{schedule['id']}.minute={schedule['minute']}",
                f"{schedule['id']}.timezone={schedule['timezone']}",
                f"{schedule['id']}.slack_channel={schedule['slack_channel']}",
                f"{schedule['id']}.telegram_policy={schedule['telegram_policy']}",
                f"{schedule['id']}.active={'yes' if schedule['active'] else 'no'}",
            ]
        )
    lines.extend(
        [
            "```",
            "",
            "## Schedules",
            "",
        ]
    )
    for schedule in schedules:
        lines.append(
            f"- `{schedule['id']}`: {schedule['name']} at "
            f"`{int(schedule['hour']):02d}:{int(schedule['minute']):02d}` "
            f"`{schedule['timezone']}`"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#schedule-config-import`",
            "- Schedule provisioning: `/setup/schedule-provisioning.md`",
            "- Standup preview: `/setup/standup-preview.md`",
            "",
        ]
    )
    return "\n".join(lines)


def schedule_config_template_json(schedules: list[dict]) -> str:
    payload = {
        "title": "Schedule Configuration Reply Template",
        "credential_boundary": (
            "Schedule metadata only. Do not include Slack tokens, Telegram tokens, "
            "provider API keys, private prompt output, or logs."
        ),
        "entry_points": {
            "bulk_import": "/setup#schedule-config-import",
            "schedule_provisioning": "/setup/schedule-provisioning.md",
            "standup_preview": "/setup/standup-preview.md",
            "schedule_verification": "/setup#schedule-verification",
        },
        "allowed_fields": sorted(SCHEDULE_FIELDS),
        "schedules": [_schedule_template(schedule) for schedule in schedules],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_schedule_config_reply(raw_text: str, schedules: list[dict]) -> dict:
    schedules_by_id = {schedule["id"]: schedule for schedule in schedules}
    updates_by_id: dict[str, dict] = {}
    unknown_schedules: list[str] = []
    invalid_schedules: list[str] = []
    invalid_fields: list[str] = []
    ignored_lines: list[str] = []
    parse_error = ""

    entries = _json_entries(raw_text)
    if entries is None:
        entries = _line_entries(raw_text, ignored_lines)
    elif entries == "__parse_error__":
        parse_error = "Reply must be valid JSON or schedule.field=value lines."
        entries = []

    for schedule_id, field, raw_value in entries:
        if schedule_id not in schedules_by_id:
            unknown_schedules.append(schedule_id)
            continue
        if field not in SCHEDULE_FIELDS:
            invalid_fields.append(f"{schedule_id}.{field}")
            continue
        updates_by_id.setdefault(schedule_id, {})[field] = _strip_inline_comment(
            str(raw_value)
        ).strip()

    merged_updates: dict[str, dict] = {}
    for schedule_id, fields in updates_by_id.items():
        current = schedules_by_id[schedule_id]
        merged = {
            "schedule_id": schedule_id,
            "name": fields.get("name", current["name"]),
            "hour": fields.get("hour", current["hour"]),
            "minute": fields.get("minute", current["minute"]),
            "timezone": fields.get("timezone", current["timezone"]),
            "slack_channel": fields.get("slack_channel", current["slack_channel"]),
            "telegram_policy": fields.get(
                "telegram_policy",
                current["telegram_policy"],
            ),
            "active": fields.get("active", current["active"]),
        }
        normalized, invalid = _normalize_schedule(merged)
        if invalid:
            invalid_schedules.append(schedule_id)
            invalid_fields.extend([f"{schedule_id}.{field}" for field in invalid])
            continue
        merged_updates[schedule_id] = normalized

    return {
        "updates": merged_updates,
        "imported": len(merged_updates),
        "unknown_schedules": sorted(set(unknown_schedules)),
        "invalid_schedules": sorted(set(invalid_schedules)),
        "invalid_fields": sorted(set(invalid_fields)),
        "ignored_lines": ignored_lines,
        "parse_error": parse_error,
    }


def schedule_config_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"schedule_config_imported={summary['imported']}"
        f"&schedule_config_unknown={len(summary['unknown_schedules'])}"
        f"&schedule_config_invalid={len(summary['invalid_fields'])}"
        f"&schedule_config_ignored={len(summary['ignored_lines'])}"
        "#schedule-config-import"
    )


def _schedule_template(schedule: dict) -> dict:
    return {
        "id": schedule["id"],
        "name": schedule["name"],
        "hour": int(schedule["hour"]),
        "minute": int(schedule["minute"]),
        "timezone": schedule["timezone"],
        "slack_channel": schedule["slack_channel"],
        "telegram_policy": schedule["telegram_policy"],
        "active": bool(schedule["active"]),
    }


def _json_entries(raw_text: str) -> list[tuple[str, str, object]] | str | None:
    stripped = raw_text.strip()
    if not stripped.startswith(("{", "[")):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return "__parse_error__"

    if isinstance(payload, dict):
        if isinstance(payload.get("schedules"), list):
            return _schedule_list_entries(payload["schedules"])
        if all(isinstance(value, dict) for value in payload.values()):
            return [
                (str(schedule_id), str(field), value)
                for schedule_id, fields in payload.items()
                for field, value in fields.items()
            ]
        return "__parse_error__"
    if isinstance(payload, list):
        return _schedule_list_entries(payload)
    return "__parse_error__"


def _schedule_list_entries(rows: list) -> list[tuple[str, str, object]]:
    entries: list[tuple[str, str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        schedule_id = row.get("id") or row.get("schedule_id")
        if not schedule_id:
            continue
        for field, value in row.items():
            if field in {"id", "schedule_id"}:
                continue
            entries.append((str(schedule_id), str(field), value))
    return entries


def _line_entries(
    raw_text: str,
    ignored_lines: list[str],
) -> list[tuple[str, str, object]]:
    entries: list[tuple[str, str, object]] = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("```"):
            continue
        match = SCHEDULE_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        schedule_id, field, value = match.groups()
        entries.append((schedule_id, field, value))
    return entries


def _normalize_schedule(schedule: dict) -> tuple[dict, list[str]]:
    invalid: list[str] = []
    name = str(schedule["name"]).strip()
    timezone = str(schedule["timezone"]).strip()
    slack_channel = str(schedule["slack_channel"]).strip()
    telegram_policy = str(schedule["telegram_policy"]).strip()
    hour = _parse_int(schedule["hour"])
    minute = _parse_int(schedule["minute"])
    active = _parse_bool(schedule["active"])

    if not name:
        invalid.append("name")
    if hour is None or hour < 0 or hour > 23:
        invalid.append("hour")
    if minute is None or minute < 0 or minute > 59:
        invalid.append("minute")
    if not timezone or not TIMEZONE.fullmatch(timezone):
        invalid.append("timezone")
    if not slack_channel or not SLACK_TARGET.fullmatch(slack_channel):
        invalid.append("slack_channel")
    if active is None:
        invalid.append("active")

    return (
        {
            "name": name,
            "hour": hour if hour is not None else 0,
            "minute": minute if minute is not None else 0,
            "timezone": timezone,
            "slack_channel": slack_channel,
            "telegram_policy": telegram_policy,
            "active": bool(active),
        },
        invalid,
    )


def _parse_int(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "active"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "paused", "inactive"}:
        return False
    return None


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()
