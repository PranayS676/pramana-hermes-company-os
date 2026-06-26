from __future__ import annotations

import json
import re

TELEGRAM_RECIPIENT_KEYS = {
    "founder_telegram_user_id": {
        "label": "Founder Telegram user ID",
        "placeholder": "REPLACE_WITH_FOUNDER_TELEGRAM_USER_ID",
        "required": True,
    },
    "telegram_home_channel": {
        "label": "Urgent home chat or channel ID",
        "placeholder": "REPLACE_WITH_URGENT_HOME_CHAT_ID",
        "required": False,
    },
}
RECIPIENT_LINE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*(?:=|:)\s*(.*?)\s*$")
TELEGRAM_ID = re.compile(r"^-?\d+$")


def telegram_recipient_template_markdown(setup_values: dict[str, str]) -> str:
    values = _template_values(setup_values)
    lines = [
        "# Telegram Recipient ID Reply Template",
        "",
        "Use this after you know the founder Telegram user ID and optional urgent "
        "home chat or channel ID. Paste only numeric Telegram IDs; do not paste "
        "the BotFather token, bot API URLs, request headers, message logs, or "
        "screenshots.",
        "",
        "## JSON Reply Template",
        "",
        "```json",
        json.dumps(values, indent=2, sort_keys=True),
        "```",
        "",
        "## Line Reply Template",
        "",
        "```text",
    ]
    for key, value in values.items():
        lines.append(f"{key}={value}")
    lines.extend(
        [
            "```",
            "",
            "## Fields",
            "",
        ]
    )
    for key, meta in TELEGRAM_RECIPIENT_KEYS.items():
        required = "required" if meta["required"] else "optional"
        lines.append(f"- `{key}`: {meta['label']} ({required})")
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#telegram-recipient-import`",
            "- BotFather setup: `/setup/telegram-botfather.md`",
            "- Telegram provisioning: `/setup/telegram-provisioning.md`",
            "",
        ]
    )
    return "\n".join(lines)


def telegram_recipient_template_json(setup_values: dict[str, str]) -> str:
    values = _template_values(setup_values)
    payload = {
        "title": "Telegram Recipient ID Reply Template",
        "credential_boundary": (
            "Only numeric Telegram recipient IDs are accepted. Do not include "
            "BotFather tokens, bot API URLs, request headers, message logs, or "
            "screenshots."
        ),
        "accepted_id_pattern": "^-?\\d+$",
        "entry_points": {
            "bulk_import": "/setup#telegram-recipient-import",
            "botfather": "/setup/telegram-botfather.md",
            "telegram_provisioning": "/setup/telegram-provisioning.md",
            "telegram_policy": "/setup/telegram-policy.md",
        },
        "values": values,
        "fields": [
            {
                "key": key,
                "label": meta["label"],
                "required": meta["required"],
                "value": values[key],
            }
            for key, meta in TELEGRAM_RECIPIENT_KEYS.items()
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_telegram_recipient_reply(raw_text: str) -> dict:
    values: dict[str, str] = {}
    unknown_keys: list[str] = []
    invalid_keys: list[str] = []
    ignored_lines: list[str] = []
    parse_error = ""

    entries = _json_entries(raw_text)
    if entries is None:
        entries = _line_entries(raw_text, ignored_lines)
    elif entries == "__parse_error__":
        parse_error = "Reply must be valid JSON or key=value lines."
        entries = []

    for key, raw_value in entries:
        if key not in TELEGRAM_RECIPIENT_KEYS:
            unknown_keys.append(key)
            continue
        value = _strip_inline_comment(str(raw_value)).strip()
        if not value or _is_placeholder(value):
            ignored_lines.append(f"{key}=<empty>")
            continue
        if not TELEGRAM_ID.fullmatch(value):
            invalid_keys.append(key)
            values.pop(key, None)
            continue
        values[key] = value

    return {
        "values": values,
        "imported": len(values),
        "unknown_keys": sorted(set(unknown_keys)),
        "invalid_keys": sorted(set(invalid_keys)),
        "ignored_lines": ignored_lines,
        "parse_error": parse_error,
    }


def telegram_recipient_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"telegram_recipient_imported={summary['imported']}"
        f"&telegram_recipient_unknown={len(summary['unknown_keys'])}"
        f"&telegram_recipient_invalid={len(summary['invalid_keys'])}"
        f"&telegram_recipient_ignored={len(summary['ignored_lines'])}"
        "#telegram-recipient-import"
    )


def _template_values(setup_values: dict[str, str]) -> dict[str, str]:
    return {
        key: setup_values.get(key, "").strip() or meta["placeholder"]
        for key, meta in TELEGRAM_RECIPIENT_KEYS.items()
    }


def _json_entries(raw_text: str) -> list[tuple[str, str]] | str | None:
    stripped = raw_text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return "__parse_error__"
    if not isinstance(payload, dict):
        return "__parse_error__"
    if isinstance(payload.get("telegram_recipients"), dict):
        payload = payload["telegram_recipients"]
    elif isinstance(payload.get("values"), dict):
        payload = payload["values"]
    return [(str(key), str(value)) for key, value in payload.items()]


def _line_entries(raw_text: str, ignored_lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("```"):
            continue
        match = RECIPIENT_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        entries.append((match.group(1), match.group(2)))
    return entries


def _is_placeholder(value: str) -> bool:
    return value in {
        "REPLACE_WITH_USER_ID",
        "REPLACE_WITH_HOME_CHAT_ID",
        "REPLACE_WITH_FOUNDER_TELEGRAM_USER_ID",
        "REPLACE_WITH_URGENT_HOME_CHAT_ID",
    }


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()
