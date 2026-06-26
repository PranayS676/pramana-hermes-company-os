from __future__ import annotations

import json
from typing import Any

EDITABLE_PROFILE_FIELDS = {
    "description",
    "soul",
    "capabilities",
    "slack_channel",
    "telegram_policy",
    "hermes_command",
}


def profile_personalization_template_markdown(agents: list[dict]) -> str:
    return "\n".join(
        [
            "# Profile Personalization Reply Template",
            "",
            "Use this when you want to revise starter Hermes profile descriptions, "
            "SOUL text, capabilities, routing channels, escalation policy, or command "
            "aliases in bulk. This template is no-secret; do not paste Slack tokens, "
            "Telegram bot tokens, provider keys, OAuth payloads, request headers, "
            "private logs, or raw profile outputs.",
            "",
            "## Reply Template",
            "",
            "```json",
            profile_personalization_template_json(agents).strip(),
            "```",
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup#profile-personalization-import`",
            "- Profile artifacts: `/setup/profile-artifacts.md`",
            "- Profile acceptance: `/setup/profile-acceptance.md`",
            "",
        ]
    )


def profile_personalization_template_json(agents: list[dict]) -> str:
    payload = {
        "title": "Profile Personalization Reply Template",
        "credential_boundary": (
            "No-secret profile metadata only. Do not include Slack tokens, Telegram "
            "bot tokens, provider keys, OAuth payloads, request headers, private "
            "logs, or raw profile outputs."
        ),
        "entry_points": {
            "bulk_import": "/setup#profile-personalization-import",
            "profile_artifacts": "/setup/profile-artifacts.md",
            "profile_acceptance": "/setup/profile-acceptance.md",
        },
        "editable_fields": sorted(EDITABLE_PROFILE_FIELDS),
        "profiles": [
            {
                "id": agent["id"],
                "description": agent["description"],
                "soul": agent["soul"],
                "capabilities": agent["capabilities"],
                "slack_channel": agent["slack_channel"],
                "telegram_policy": agent["telegram_policy"],
                "hermes_command": agent["hermes_command"],
            }
            for agent in agents
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_profile_personalization_reply(raw_text: str, agents: list[dict]) -> dict:
    known_ids = {agent["id"] for agent in agents}
    try:
        payload = json.loads(_strip_markdown_fence(raw_text))
    except json.JSONDecodeError as exc:
        return _empty_summary(parse_error=f"Invalid JSON: {exc.msg}")

    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        return _empty_summary(parse_error="Expected a JSON object with a profiles list.")

    updates: dict[str, dict] = {}
    unknown_ids: list[str] = []
    invalid_profiles: list[str] = []
    ignored_fields: list[str] = []

    for index, raw_profile in enumerate(payload["profiles"], start=1):
        fallback_id = f"profile-{index}"
        if not isinstance(raw_profile, dict):
            invalid_profiles.append(fallback_id)
            continue
        profile_id = str(raw_profile.get("id", "")).strip()
        if not profile_id:
            invalid_profiles.append(fallback_id)
            continue
        if profile_id not in known_ids:
            unknown_ids.append(profile_id)
            continue

        unknown_fields = sorted(set(raw_profile) - EDITABLE_PROFILE_FIELDS - {"id"})
        ignored_fields.extend(f"{profile_id}.{field}" for field in unknown_fields)

        update: dict[str, Any] = {}
        invalid = False
        for field in sorted(EDITABLE_PROFILE_FIELDS):
            if field not in raw_profile:
                continue
            value = raw_profile[field]
            if field == "capabilities":
                parsed = _parse_capabilities(value)
                if not parsed:
                    invalid = True
                    continue
                update[field] = parsed
            elif isinstance(value, str) and value.strip():
                update[field] = value.strip()
            else:
                invalid = True

        if invalid or not update:
            invalid_profiles.append(profile_id)
            updates.pop(profile_id, None)
            continue
        updates[profile_id] = update

    return {
        "updates": updates,
        "imported": len(updates),
        "unknown_ids": sorted(set(unknown_ids)),
        "invalid_profiles": sorted(set(invalid_profiles)),
        "ignored_fields": sorted(set(ignored_fields)),
        "parse_error": "",
    }


def profile_personalization_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"profile_personalization_imported={summary['imported']}"
        f"&profile_personalization_unknown={len(summary['unknown_ids'])}"
        f"&profile_personalization_invalid={len(summary['invalid_profiles'])}"
        f"&profile_personalization_ignored={len(summary['ignored_fields'])}"
        "#profile-personalization-import"
    )


def _empty_summary(parse_error: str) -> dict:
    return {
        "updates": {},
        "imported": 0,
        "unknown_ids": [],
        "invalid_profiles": [],
        "ignored_fields": [],
        "parse_error": parse_error,
    }


def _parse_capabilities(value: object) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        raw_items = value
    else:
        return []
    return [
        str(item).strip()
        for item in raw_items
        if isinstance(item, str) and str(item).strip()
    ]


def _strip_markdown_fence(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    lines = cleaned.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
