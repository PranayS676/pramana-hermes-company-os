from __future__ import annotations

import json

from hermes_company_os.llm_artifacts import provider_requirements

LLM_PROVIDER_PRESETS = {
    "codex-company-default": {
        "label": "Codex Company Default",
        "description": (
            "Use the Codex-backed starter model for every Hermes profile. This is "
            "the safest default when the founder wants Codex as the main LLM path."
        ),
        "auth_method": "deferred_profile_secret",
        "status": "planned",
        "defaults": {
            "provider": "openai-codex",
            "model": "gpt-5-codex",
            "fallback_provider": "",
            "fallback_model": "",
        },
        "overrides": {},
    },
    "openrouter-research-heavy": {
        "label": "OpenRouter Research Heavy",
        "description": (
            "Use OpenRouter routing for research, architecture, and critique-heavy "
            "profiles while leaving operational profiles on the Codex default."
        ),
        "auth_method": "profile_env",
        "status": "needs_secret",
        "defaults": {
            "provider": "openai-codex",
            "model": "gpt-5-codex",
            "fallback_provider": "",
            "fallback_model": "",
        },
        "overrides": {
            "research-agent": {
                "provider": "openrouter",
                "model": "anthropic/claude-sonnet-4",
                "fallback_provider": "openai-codex",
                "fallback_model": "gpt-5-codex",
            },
            "engineering-manager": {
                "provider": "openrouter",
                "model": "anthropic/claude-sonnet-4",
                "fallback_provider": "openai-codex",
                "fallback_model": "gpt-5-codex",
            },
            "qa-critic": {
                "provider": "openrouter",
                "model": "anthropic/claude-sonnet-4",
                "fallback_provider": "openai-codex",
                "fallback_model": "gpt-5-codex",
            },
        },
    },
    "openrouter-cost-efficient-company": {
        "label": "OpenRouter Cost-Efficient Company",
        "description": (
            "Use one OpenRouter credential per profile with inexpensive models for "
            "routine company operations, coding plans, research drafts, marketing, "
            "and QA. Keep premium Sonnet/Codex-class models as manual escalation "
            "only for high-risk architecture, hard debugging, or final launch review."
        ),
        "auth_method": "profile_env",
        "status": "needs_secret",
        "defaults": {
            "provider": "openrouter",
            "model": "google/gemini-2.5-flash-lite",
            "fallback_provider": "openrouter",
            "fallback_model": "google/gemini-2.5-flash",
        },
        "overrides": {
            "product-manager": {
                "model": "google/gemini-2.5-flash",
                "fallback_model": "anthropic/claude-haiku-4.5",
            },
            "research-agent": {
                "model": "google/gemini-2.5-flash",
                "fallback_model": "deepseek/deepseek-chat-v3.1",
            },
            "engineering-manager": {
                "model": "deepseek/deepseek-chat-v3.1",
                "fallback_model": "anthropic/claude-haiku-4.5",
            },
            "backend-engineer": {
                "model": "deepseek/deepseek-chat-v3.1",
                "fallback_model": "google/gemini-2.5-flash",
            },
            "frontend-engineer": {
                "model": "deepseek/deepseek-chat-v3.1",
                "fallback_model": "google/gemini-2.5-flash",
            },
            "cloud-infra-agent": {
                "model": "deepseek/deepseek-chat-v3.1",
                "fallback_model": "google/gemini-2.5-flash",
            },
            "test-automation-agent": {
                "model": "deepseek/deepseek-chat-v3.1",
                "fallback_model": "google/gemini-2.5-flash",
            },
            "qa-critic": {
                "model": "deepseek/deepseek-chat-v3.1",
                "fallback_model": "anthropic/claude-haiku-4.5",
            },
        },
    },
    "local-ollama-dry-run": {
        "label": "Local Ollama Dry Run",
        "description": (
            "Use a local Ollama endpoint for offline setup rehearsals before hosted "
            "provider credentials are loaded."
        ),
        "auth_method": "local_endpoint",
        "status": "needs_secret",
        "defaults": {
            "provider": "local-ollama",
            "model": "llama3.1",
            "fallback_provider": "",
            "fallback_model": "",
        },
        "overrides": {},
    },
}


def llm_provider_presets_payload(
    *,
    agents: list[dict],
    model_preferences: list[dict],
) -> dict:
    current = {item["agent_id"]: item for item in model_preferences}
    return {
        "title": "LLM Provider Presets",
        "credential_boundary": (
            "Presets update provider names, model names, auth method labels, and "
            "status metadata only. API keys, OAuth values, local endpoint secrets, "
            "and provider credentials remain outside this dashboard."
        ),
        "verification_last": True,
        "entry_points": {
            "manual_preferences": "/setup/models#models",
            "llm_credentials": "/setup/llm-credentials.md",
            "llm_smoke": "/setup/llm-smoke.md",
            "profile_smoke": "/setup/profiles#profile-smoke",
        },
        "current": [_current_preference(agent, current.get(agent["id"])) for agent in agents],
        "presets": [
            _preset_payload(preset_id, preset, agents)
            for preset_id, preset in LLM_PROVIDER_PRESETS.items()
        ],
    }


def llm_provider_presets_json(**kwargs) -> str:
    return json.dumps(llm_provider_presets_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def llm_provider_presets_markdown(**kwargs) -> str:
    payload = llm_provider_presets_payload(**kwargs)
    lines = [
        "# LLM Provider Presets",
        "",
        "Use this before final credential loading to choose a consistent provider "
        "strategy across Hermes profiles.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Current Preferences",
        "",
    ]
    for item in payload["current"]:
        lines.append(
            f"- {item['agent_name']}: `{item['provider']}` / `{item['model']}` "
            f"({item['status']})"
        )
    lines.extend(["", "## Presets", ""])
    for preset in payload["presets"]:
        lines.extend(
            [
                f"### {preset['label']} (`{preset['id']}`)",
                "",
                preset["description"],
                "",
                f"- Apply route: `/setup/llm-provider-presets/{preset['id']}`",
                f"- Status after apply: `{preset['status']}`",
                f"- Auth method: `{preset['auth_method']}`",
                "- Profile plan:",
            ]
        )
        for profile in preset["profiles"]:
            lines.append(
                f"  - {profile['agent_name']}: `{profile['provider']}` / "
                f"`{profile['model']}`; env keys {_inline_values(profile['env_keys'])}"
            )
        lines.append("")
    lines.extend(
        [
            "## Final Verification Still Last",
            "",
            "1. Apply a preset or edit `/setup/models#models` manually.",
            "2. Review `/setup/profile-config/<profile>.yaml` and "
            "`/setup/profile-llm-env/<profile>.env`.",
            "3. Load provider credentials into real Hermes profile files later.",
            "4. Run `/setup/secret-audit.ps1 -AuditLlm`.",
            "5. Run `/setup/profiles#profile-smoke` for every profile.",
            "",
        ]
    )
    return "\n".join(lines)


def llm_preset_preferences(preset_id: str, agents: list[dict]) -> list[dict]:
    if preset_id not in LLM_PROVIDER_PRESETS:
        raise KeyError(preset_id)
    preset = LLM_PROVIDER_PRESETS[preset_id]
    return [
        _preference_for_agent(agent, preset_id, preset)
        for agent in agents
    ]


def _preset_payload(preset_id: str, preset: dict, agents: list[dict]) -> dict:
    profiles = [_preference_for_agent(agent, preset_id, preset) for agent in agents]
    return {
        "id": preset_id,
        "label": preset["label"],
        "description": preset["description"],
        "auth_method": preset["auth_method"],
        "status": preset["status"],
        "profiles": [
            {
                "agent_id": profile["agent_id"],
                "agent_name": profile["agent_name"],
                "provider": profile["provider"],
                "model": profile["model"],
                "fallback_provider": profile["fallback_provider"],
                "fallback_model": profile["fallback_model"],
                "env_keys": _env_keys(profile),
            }
            for profile in profiles
        ],
    }


def _preference_for_agent(agent: dict, preset_id: str, preset: dict) -> dict:
    profile = {
        **preset["defaults"],
        **preset["overrides"].get(agent["id"], {}),
    }
    return {
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "provider": profile["provider"],
        "model": profile["model"],
        "fallback_provider": profile["fallback_provider"],
        "fallback_model": profile["fallback_model"],
        "auth_method": preset["auth_method"],
        "status": preset["status"],
        "notes": (
            f"Applied LLM preset {preset_id}. Credentials remain external and "
            "profile smoke verification is still last."
        ),
    }


def _current_preference(agent: dict, preference: dict | None) -> dict:
    if preference is None:
        return {
            "agent_id": agent["id"],
            "agent_name": agent["name"],
            "provider": "",
            "model": "",
            "status": "missing",
        }
    return {
        "agent_id": preference["agent_id"],
        "agent_name": preference["agent_name"],
        "provider": preference["provider"],
        "model": preference["model"],
        "status": preference["status"],
    }


def _env_keys(profile: dict) -> list[str]:
    keys = list(provider_requirements(profile["provider"])["env"])
    if profile["fallback_provider"]:
        keys.extend(provider_requirements(profile["fallback_provider"])["env"])
    return list(dict.fromkeys(keys))


def _inline_values(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)
