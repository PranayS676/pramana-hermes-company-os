from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.llm_artifacts import provider_requirements
from hermes_company_os.smoke_checks import profile_smoke_prompt


def llm_smoke_payload(
    *,
    agents: list[dict],
    model_preferences: list[dict],
    secret_requirements: list[dict],
) -> dict:
    agents_by_id = {agent["id"]: agent for agent in agents}
    llm_secret_status = {
        item["owner_agent_id"]: item["status"]
        for item in secret_requirements
        if item["category"] == "llm" and item["owner_agent_id"]
    }
    profiles = [
        _profile_smoke_entry(
            agent=agents_by_id[preference["agent_id"]],
            preference=preference,
            credential_status=llm_secret_status.get(preference["agent_id"], "missing"),
        )
        for preference in model_preferences
        if preference["agent_id"] in agents_by_id
    ]
    return {
        "title": "LLM Smoke Drill Pack",
        "credential_boundary": (
            "This artifact contains provider names, expected environment key names, "
            "smoke prompts, and status metadata only. It does not include provider "
            "API-key values, OAuth tokens, Slack tokens, or Telegram bot tokens."
        ),
        "verification_last": True,
        "activation_order": [
            "Complete Hermes profiles and starter personality artifacts.",
            "Complete Slack and Telegram setup.",
            "Verify scheduling and Kanban handoff.",
            "Load provider credentials into real Hermes profile .env files.",
            "Run `/setup/secret-audit.ps1 -AuditLlm`.",
            "Run one `/setup/profiles#profile-smoke` check per profile.",
            "Run role acceptance prompts from `/setup/profile-acceptance.md`.",
        ],
        "expected_response_schema": [
            "- profile_ready: yes/no",
            "- identity_check: one sentence confirming this profile's role",
            "- next_action: one practical next setup check for this profile",
        ],
        "status": {
            "models": _status_counts(model_preferences),
            "llm_credentials": _status_counts(
                [
                    item
                    for item in secret_requirements
                    if item["category"] == "llm"
                ]
            ),
        },
        "profiles": profiles,
        "entry_points": {
            "llm_credentials": "/setup/llm-credentials.md",
            "llm_finalization": "/setup/llm-finalize.md",
            "secret_audit": "/setup/secret-audit.ps1",
            "profile_acceptance": "/setup/profile-acceptance.md",
            "setup_smoke_section": "/setup/profiles#profile-smoke",
        },
    }


def llm_smoke_json(**kwargs) -> str:
    return json.dumps(llm_smoke_payload(**kwargs), indent=2, sort_keys=True)


def llm_smoke_markdown(**kwargs) -> str:
    payload = llm_smoke_payload(**kwargs)
    lines = [
        "# LLM Smoke Drill Pack",
        "",
        "Use this after provider credentials are loaded into the real Hermes profiles, "
        "but before running the first company idea live.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Activation Order",
        "",
    ]
    for index, step in enumerate(payload["activation_order"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(
        [
            "",
            "## Expected Response Schema",
            "",
            *payload["expected_response_schema"],
            "",
            "## Status",
            "",
            f"- Model preference status: {_format_counts(payload['status']['models'])}",
            (
                "- LLM credential status: "
                f"{_format_counts(payload['status']['llm_credentials'])}"
            ),
            "",
            "## Profile Smoke Prompts",
            "",
        ]
    )
    for profile in payload["profiles"]:
        lines.extend(
            [
                f"### {profile['agent_name']}",
                "",
                f"- Profile command: `{profile['hermes_command']}`",
                f"- Provider/model: `{profile['provider']}` / `{profile['model']}`",
                f"- Expected env keys: {_inline_values(profile['expected_env_keys'])}",
                f"- Credential status: `{profile['credential_status']}`",
                f"- Model status: `{profile['model_status']}`",
                f"- Smoke route: `{profile['smoke_route']}`",
                "",
                "```text",
                profile["prompt"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Completion Criteria",
            "",
            "- Every expected provider key name is present in the real Hermes profile runtime.",
            "- Every profile smoke check returns the expected three-line schema.",
            "- Every model preference is marked `verified`.",
            "- Every LLM external secret requirement is marked `verified`.",
            "- `llm-provider` integration is marked `configured`.",
            "",
        ]
    )
    return "\n".join(lines)


def _profile_smoke_entry(
    *,
    agent: dict,
    preference: dict,
    credential_status: str,
) -> dict:
    expected_keys = _expected_keys(preference)
    return {
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "role": agent["role"],
        "hermes_command": preference["hermes_command"],
        "provider": preference["provider"],
        "model": preference["model"],
        "fallback_provider": preference["fallback_provider"],
        "fallback_model": preference["fallback_model"],
        "expected_env_keys": expected_keys,
        "credential_status": credential_status,
        "model_status": preference["status"],
        "smoke_route": f"/setup/profile-smoke/{agent['id']}",
        "prompt": profile_smoke_prompt(agent, preference),
    }


def _expected_keys(preference: dict) -> list[str]:
    primary = provider_requirements(preference["provider"])
    keys = list(primary["env"])
    if preference.get("fallback_provider"):
        fallback = provider_requirements(preference["fallback_provider"])
        keys.extend(fallback["env"])
    return list(dict.fromkeys(keys))


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _inline_values(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)
