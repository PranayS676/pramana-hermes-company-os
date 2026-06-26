from __future__ import annotations

import json
import re

from hermes_company_os.slack_workspace import CHANNEL_INPUTS, slack_workspace_matrix

CHANNEL_LINE = re.compile(r"^\s*([#A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
SLACK_CHANNEL_ID = re.compile(r"^[CGD][A-Z0-9]{2,}$")


def slack_channel_template_markdown(
    agents: list[dict],
    setup_values: dict[str, str],
) -> str:
    channels = _template_channels(agents, setup_values)
    lines = [
        "# Slack Channel ID Reply Template",
        "",
        "Use this after creating Slack channels manually or with the provisioning "
        "runner. Paste only Slack channel IDs; do not paste Slack bot tokens, app "
        "tokens, OAuth payloads, request headers, or logs.",
        "",
        "## JSON Reply Template",
        "",
        "```json",
        json.dumps({"channel_ids": _template_values(channels)}, indent=2, sort_keys=True),
        "```",
        "",
        "## Line Reply Template",
        "",
        "```text",
    ]
    for channel in channels:
        lines.append(f"{channel['input_key']}={channel['value']}")
    lines.extend(
        [
            "```",
            "",
            "## Channels",
            "",
        ]
    )
    for channel in channels:
        required = "required" if channel["required"] else "optional"
        lines.append(
            f"- `{channel['input_key']}` / `{channel['channel_name']}`: "
            f"{required} - {channel['purpose']}"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#slack-channel-import`",
            "- Slack workspace matrix: `/setup/slack-workspace.md`",
            "- Slack provisioning runner: `/setup/slack-provisioning.ps1`",
            "",
        ]
    )
    return "\n".join(lines)


def slack_channel_template_json(
    agents: list[dict],
    setup_values: dict[str, str],
) -> str:
    channels = _template_channels(agents, setup_values)
    payload = {
        "title": "Slack Channel ID Reply Template",
        "credential_boundary": (
            "Only Slack channel IDs are accepted. Do not include Slack bot "
            "tokens, app tokens, OAuth payloads, request headers, or logs."
        ),
        "accepted_id_pattern": "^[CGD][A-Z0-9]{2,}$",
        "entry_points": {
            "bulk_import": "/setup#slack-channel-import",
            "slack_workspace": "/setup/slack-workspace.md",
            "slack_provisioning": "/setup/slack-provisioning.md",
            "invite_matrix": "/setup/slack-invite-matrix.json",
        },
        "channel_ids": _template_values(channels),
        "channels": channels,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_slack_channel_reply(raw_text: str) -> dict:
    aliases = _channel_aliases()
    updates: dict[str, str] = {}
    unknown_keys: list[str] = []
    invalid_channel_ids: list[str] = []
    ignored_lines: list[str] = []
    parse_error = ""

    entries = _json_entries(raw_text)
    if entries is None:
        entries = _line_entries(raw_text, ignored_lines)
    elif entries == "__parse_error__":
        parse_error = "Reply must be valid JSON or channel=value lines."
        entries = []

    for raw_key, raw_value in entries:
        input_key = aliases.get(raw_key)
        if input_key is None:
            unknown_keys.append(raw_key)
            continue
        value = _strip_inline_comment(str(raw_value)).strip()
        if not value or _is_placeholder(value):
            ignored_lines.append(f"{input_key}=<empty>")
            continue
        if not SLACK_CHANNEL_ID.fullmatch(value):
            invalid_channel_ids.append(input_key)
            updates.pop(input_key, None)
            continue
        updates[input_key] = value

    return {
        "values": updates,
        "imported": len(updates),
        "unknown_keys": sorted(set(unknown_keys)),
        "invalid_channel_ids": sorted(set(invalid_channel_ids)),
        "ignored_lines": ignored_lines,
        "parse_error": parse_error,
    }


def slack_channel_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"slack_channel_imported={summary['imported']}"
        f"&slack_channel_unknown={len(summary['unknown_keys'])}"
        f"&slack_channel_invalid={len(summary['invalid_channel_ids'])}"
        f"&slack_channel_ignored={len(summary['ignored_lines'])}"
        "#slack-channel-import"
    )


def _template_channels(agents: list[dict], setup_values: dict[str, str]) -> list[dict]:
    channels = []
    for channel in slack_workspace_matrix(agents, setup_values):
        channels.append(
            {
                "channel_name": channel["channel_name"],
                "input_key": channel["input_key"],
                "required": channel["required"],
                "purpose": channel["purpose"],
                "value": channel["channel_id"].strip()
                or _placeholder(channel["channel_name"]),
            }
        )
    return channels


def _template_values(channels: list[dict]) -> dict[str, str]:
    return {channel["input_key"]: channel["value"] for channel in channels}


def _json_entries(raw_text: str) -> list[tuple[str, str]] | str | None:
    stripped = raw_text.strip()
    if not stripped.startswith(("{", "[")):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return "__parse_error__"
    if isinstance(payload, dict):
        if isinstance(payload.get("channel_ids"), dict):
            return [
                (str(channel_key), str(value))
                for channel_key, value in payload["channel_ids"].items()
            ]
        if isinstance(payload.get("channels"), list):
            return _channel_list_entries(payload["channels"])
        return [(str(channel_key), str(value)) for channel_key, value in payload.items()]
    if isinstance(payload, list):
        return _channel_list_entries(payload)
    return "__parse_error__"


def _channel_list_entries(rows: list) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        channel_key = (
            row.get("input_key")
            or row.get("channel_name")
            or row.get("name")
            or row.get("id")
        )
        value = row.get("channel_id") or row.get("value") or ""
        if channel_key:
            entries.append((str(channel_key), str(value)))
    return entries


def _line_entries(raw_text: str, ignored_lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("# ") or cleaned.startswith("```"):
            continue
        match = CHANNEL_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        entries.append((match.group(1), match.group(2)))
    return entries


def _channel_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for channel in CHANNEL_INPUTS:
        input_key = channel["input_key"]
        name = channel["name"]
        aliases[input_key] = input_key
        aliases[name] = input_key
        aliases[name.lstrip("#")] = input_key
        aliases[name.lstrip("#").replace("-", "_")] = input_key
    return aliases


def _placeholder(channel_name: str) -> str:
    constant = re.sub(r"[^A-Z0-9]+", "_", channel_name.upper()).strip("_")
    return f"C_REPLACE_WITH_{constant}_CHANNEL_ID"


def _is_placeholder(value: str) -> bool:
    return value.startswith(("C_REPLACE_WITH_", "G_REPLACE_WITH_", "D_REPLACE_WITH_"))


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()
