from __future__ import annotations

import json
import re

from hermes_company_os.slack_provisioning import (
    slack_bot_user_input_key,
    slack_bot_user_map_template,
)

PROFILE_LINE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*(?:=|:)\s*(.*?)\s*$")
SLACK_USER_ID = re.compile(r"^[UW][A-Z0-9]{3,}$")


def slack_bot_user_template_markdown(
    agents: list[dict],
    setup_values: dict[str, str] | None = None,
) -> str:
    map_template = slack_bot_user_map_template(agents, setup_values)
    lines = [
        "# Slack Bot User ID Reply Template",
        "",
        "Use this after creating or installing separate Slack apps for each Hermes "
        "profile. Paste only Slack bot user IDs, not bot tokens, app tokens, OAuth "
        "payloads, request headers, or logs.",
        "",
        "## JSON Reply Template",
        "",
        "```json",
        json.dumps({"bot_user_ids": map_template}, indent=2, sort_keys=True),
        "```",
        "",
        "## Line Reply Template",
        "",
        "```text",
    ]
    for agent in agents:
        lines.append(f"{agent['id']}={map_template[agent['id']]}")
    lines.extend(
        [
            "```",
            "",
            "## Profiles",
            "",
        ]
    )
    for agent in agents:
        lines.append(
            f"- `{agent['id']}`: {agent['name']} -> "
            f"`{slack_bot_user_input_key(agent['id'])}`"
        )
    lines.extend(
        [
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#slack-bot-user-import`",
            "- Generated map: `/setup/slack-bot-user-map.json`",
            "- Slack provisioning runner: `/setup/slack-provisioning.ps1`",
            "",
        ]
    )
    return "\n".join(lines)


def slack_bot_user_template_json(
    agents: list[dict],
    setup_values: dict[str, str] | None = None,
) -> str:
    map_template = slack_bot_user_map_template(agents, setup_values)
    payload = {
        "title": "Slack Bot User ID Reply Template",
        "credential_boundary": (
            "Only Slack bot user IDs are accepted. Do not include Slack bot "
            "tokens, app tokens, OAuth payloads, request headers, or logs."
        ),
        "entry_points": {
            "bulk_import": "/setup#slack-bot-user-import",
            "bot_user_map": "/setup/slack-bot-user-map.json",
            "slack_provisioning": "/setup/slack-provisioning.md",
        },
        "accepted_id_pattern": "^[UW][A-Z0-9]{3,}$",
        "bot_user_ids": [
            {
                "agent_id": agent["id"],
                "agent_name": agent["name"],
                "input_key": slack_bot_user_input_key(agent["id"]),
                "value": map_template[agent["id"]],
            }
            for agent in agents
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_slack_bot_user_reply(raw_text: str, agents: list[dict]) -> dict:
    known_profiles = {agent["id"] for agent in agents}
    updates: dict[str, str] = {}
    unknown_profiles: list[str] = []
    invalid_user_ids: list[str] = []
    ignored_lines: list[str] = []
    parse_error = ""

    entries = _json_entries(raw_text)
    if entries is None:
        entries = _line_entries(raw_text, ignored_lines)
    elif entries == "__parse_error__":
        parse_error = "Reply must be valid JSON or profile=value lines."
        entries = []

    for profile_id, raw_value in entries:
        if profile_id not in known_profiles:
            unknown_profiles.append(profile_id)
            continue
        value = _strip_inline_comment(str(raw_value)).strip()
        if not value or _is_placeholder(value):
            ignored_lines.append(f"{profile_id}=<empty>")
            continue
        if not SLACK_USER_ID.fullmatch(value):
            invalid_user_ids.append(profile_id)
            updates.pop(slack_bot_user_input_key(profile_id), None)
            continue
        updates[slack_bot_user_input_key(profile_id)] = value

    return {
        "values": updates,
        "imported": len(updates),
        "unknown_profiles": sorted(set(unknown_profiles)),
        "invalid_user_ids": sorted(set(invalid_user_ids)),
        "ignored_lines": ignored_lines,
        "parse_error": parse_error,
    }


def slack_bot_user_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"slack_bot_user_imported={summary['imported']}"
        f"&slack_bot_user_unknown={len(summary['unknown_profiles'])}"
        f"&slack_bot_user_invalid={len(summary['invalid_user_ids'])}"
        f"&slack_bot_user_ignored={len(summary['ignored_lines'])}"
        "#slack-bot-user-import"
    )


def _json_entries(raw_text: str) -> list[tuple[str, str]] | str | None:
    stripped = raw_text.strip()
    if not stripped.startswith(("{", "[")):
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return "__parse_error__"

    if isinstance(payload, dict):
        if isinstance(payload.get("bot_user_ids"), dict):
            return [
                (str(profile_id), str(value))
                for profile_id, value in payload["bot_user_ids"].items()
            ]
        if isinstance(payload.get("bot_user_ids"), list):
            return _profile_list_entries(payload["bot_user_ids"])
        if isinstance(payload.get("profiles"), list):
            return _profile_list_entries(payload["profiles"])
        return [(str(profile_id), str(value)) for profile_id, value in payload.items()]
    if isinstance(payload, list):
        return _profile_list_entries(payload)
    return "__parse_error__"


def _profile_list_entries(rows: list) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        profile_id = row.get("agent_id") or row.get("profile_id") or row.get("id")
        value = (
            row.get("bot_user_id")
            or row.get("slack_bot_user_id")
            or row.get("value")
            or ""
        )
        if profile_id:
            entries.append((str(profile_id), str(value)))
    return entries


def _line_entries(raw_text: str, ignored_lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("```"):
            continue
        match = PROFILE_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        entries.append((match.group(1), match.group(2)))
    return entries


def _is_placeholder(value: str) -> bool:
    return value.startswith("U_REPLACE_WITH_") or value == "REPLACE_ME"


def _strip_inline_comment(value: str) -> str:
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()
