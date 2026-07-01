from __future__ import annotations

import json
from typing import Any

ALLOWED_LLM_PREFERENCE_STATUSES = {
    "planned",
    "needs_secret",
    "ready_for_verification",
}
EDITABLE_LLM_PREFERENCE_FIELDS = {
    "provider",
    "model",
    "fallback_provider",
    "fallback_model",
    "auth_method",
    "status",
    "notes",
}


def llm_preference_template_markdown(model_preferences: list[dict]) -> str:
    return "\n".join(
        [
            "# LLM Preference Reply Template",
            "",
            "Use this before final credential loading to revise provider and model "
            "metadata across Hermes profiles in bulk. This template is no-secret; "
            "do not paste provider API keys, OAuth payloads, request headers, "
            "endpoint credentials, tokens, private logs, or raw profile outputs.",
            "",
            "## Reply Template",
            "",
            "```json",
            llm_preference_template_json(model_preferences).strip(),
            "```",
            "",
            "## Status Values",
            "",
            "- `planned`: provider/model choice is still a plan.",
            "- `needs_secret`: provider/model chosen, credential still external.",
            "- `ready_for_verification`: credential was loaded externally; smoke check next.",
            "- `verified`: not accepted here; profile smoke checks mark verification.",
            "",
            "## Where To Paste",
            "",
            "- Bulk import: `/setup/models#llm-preference-import`",
            "- Provider presets: `/setup/llm-provider-presets.md`",
            "- LLM provisioning: `/setup/llm-provisioning.md`",
            "",
        ]
    )


def llm_preference_template_json(model_preferences: list[dict]) -> str:
    payload = {
        "title": "LLM Preference Reply Template",
        "credential_boundary": (
            "Provider/model metadata only. Do not include provider API keys, OAuth "
            "payloads, request headers, endpoint credentials, tokens, private logs, "
            "or raw profile outputs."
        ),
        "verification_last": True,
        "allowed_statuses": sorted(ALLOWED_LLM_PREFERENCE_STATUSES),
        "editable_fields": sorted(EDITABLE_LLM_PREFERENCE_FIELDS),
        "entry_points": {
            "bulk_import": "/setup/models#llm-preference-import",
            "provider_presets": "/setup/llm-provider-presets.md",
            "llm_provisioning": "/setup/llm-provisioning.md",
            "profile_smoke": "/setup/profiles#profile-smoke",
        },
        "preferences": [
            {
                "agent_id": preference["agent_id"],
                "agent_name": preference["agent_name"],
                "provider": preference["provider"],
                "model": preference["model"],
                "fallback_provider": preference["fallback_provider"],
                "fallback_model": preference["fallback_model"],
                "auth_method": preference["auth_method"],
                "status": _safe_status(preference["status"]),
                "notes": preference["notes"],
            }
            for preference in model_preferences
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_llm_preference_reply(raw_text: str, model_preferences: list[dict]) -> dict:
    known_ids = {preference["agent_id"] for preference in model_preferences}
    try:
        payload = json.loads(_strip_markdown_fence(raw_text))
    except json.JSONDecodeError as exc:
        return _empty_summary(parse_error=f"Invalid JSON: {exc.msg}")

    if not isinstance(payload, dict) or not isinstance(payload.get("preferences"), list):
        return _empty_summary(parse_error="Expected a JSON object with a preferences list.")

    updates: dict[str, dict] = {}
    unknown_ids: list[str] = []
    invalid_preferences: list[str] = []
    ignored_fields: list[str] = []

    for index, raw_preference in enumerate(payload["preferences"], start=1):
        fallback_id = f"preference-{index}"
        if not isinstance(raw_preference, dict):
            invalid_preferences.append(fallback_id)
            continue
        agent_id = str(raw_preference.get("agent_id", "")).strip()
        if not agent_id:
            invalid_preferences.append(fallback_id)
            continue
        if agent_id not in known_ids:
            unknown_ids.append(agent_id)
            continue

        unknown_fields = sorted(set(raw_preference) - EDITABLE_LLM_PREFERENCE_FIELDS - {"agent_id"})
        ignored_fields.extend(f"{agent_id}.{field}" for field in unknown_fields)

        update: dict[str, Any] = {}
        invalid = False
        for field in sorted(EDITABLE_LLM_PREFERENCE_FIELDS):
            if field not in raw_preference:
                continue
            value = raw_preference[field]
            if field in {"fallback_provider", "fallback_model", "notes"}:
                update[field] = "" if value is None else str(value).strip()
                continue
            if not isinstance(value, str) or not value.strip():
                invalid = True
                continue
            cleaned = value.strip()
            if field == "status" and cleaned not in ALLOWED_LLM_PREFERENCE_STATUSES:
                invalid = True
                continue
            update[field] = cleaned

        if invalid or not update:
            invalid_preferences.append(agent_id)
            updates.pop(agent_id, None)
            continue
        updates[agent_id] = update

    return {
        "updates": updates,
        "imported": len(updates),
        "unknown_ids": sorted(set(unknown_ids)),
        "invalid_preferences": sorted(set(invalid_preferences)),
        "ignored_fields": sorted(set(ignored_fields)),
        "parse_error": "",
    }


def llm_preference_import_redirect(summary: dict) -> str:
    return (
        "/setup/models?"
        f"llm_preference_imported={summary['imported']}"
        f"&llm_preference_unknown={len(summary['unknown_ids'])}"
        f"&llm_preference_invalid={len(summary['invalid_preferences'])}"
        f"&llm_preference_ignored={len(summary['ignored_fields'])}"
        "#llm-preference-import"
    )


def _empty_summary(parse_error: str) -> dict:
    return {
        "updates": {},
        "imported": 0,
        "unknown_ids": [],
        "invalid_preferences": [],
        "ignored_fields": [],
        "parse_error": parse_error,
    }


def _safe_status(status: str) -> str:
    if status == "verified":
        return "ready_for_verification"
    return status


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
