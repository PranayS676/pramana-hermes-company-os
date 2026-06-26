from __future__ import annotations

PROVIDER_CREDENTIALS = {
    "anthropic": {
        "label": "Anthropic",
        "env": ["ANTHROPIC_API_KEY"],
        "notes": "Use for Claude-family routing when the Hermes profile supports it.",
    },
    "azure-openai": {
        "label": "Azure OpenAI",
        "env": [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
        ],
        "notes": "Use when model access is through an Azure OpenAI deployment.",
    },
    "local-ollama": {
        "label": "Local Ollama",
        "env": ["OLLAMA_BASE_URL"],
        "notes": "Use for a local model endpoint; no hosted API key is expected.",
    },
    "ollama": {
        "label": "Ollama",
        "env": ["OLLAMA_BASE_URL"],
        "notes": "Use for a local model endpoint; no hosted API key is expected.",
    },
    "openai": {
        "label": "OpenAI",
        "env": ["OPENAI_API_KEY"],
        "notes": "Use for OpenAI API-key based profile authentication.",
    },
    "openai-codex": {
        "label": "OpenAI Codex",
        "env": ["OPENAI_API_KEY"],
        "notes": "Starter preference for Codex-backed Hermes profiles.",
    },
    "openrouter": {
        "label": "OpenRouter",
        "env": ["OPENROUTER_API_KEY"],
        "notes": "Use when routing multiple hosted models through OpenRouter.",
    },
}

GENERIC_CREDENTIAL = {
    "label": "Custom Provider",
    "env": ["PROVIDER_API_KEY_OR_OAUTH"],
    "notes": "Use the provider-specific credential expected by this Hermes profile.",
}


def llm_credentials_plan_markdown(model_preferences: list[dict]) -> str:
    lines = [
        "# LLM Credential Setup Matrix",
        "",
        "LLM credentials are intentionally last. This artifact maps profile model "
        "preferences to the profile-local environment keys that need to be loaded "
        "outside this dashboard.",
        "",
        "## Provider Catalog",
        "",
    ]
    for provider_id in sorted(PROVIDER_CREDENTIALS):
        provider = PROVIDER_CREDENTIALS[provider_id]
        lines.extend(
            [
                f"### {provider['label']} (`{provider_id}`)",
                "",
                f"- Environment keys: {_inline_values(provider['env'])}",
                f"- Notes: {provider['notes']}",
                "",
            ]
        )
    lines.extend(["## Profile Credential Matrix", ""])
    for preference in model_preferences:
        provider = provider_requirements(preference["provider"])
        fallback = (
            provider_requirements(preference["fallback_provider"])
            if preference["fallback_provider"]
            else None
        )
        lines.extend(
            [
                f"### {preference['agent_name']}",
                "",
                f"- Profile command: `{preference['hermes_command']}`",
                f"- Primary provider/model: `{preference['provider']}` / `{preference['model']}`",
                f"- Primary env keys: {_inline_values(provider['env'])}",
                (
                    "- Fallback provider/model: "
                    f"`{preference['fallback_provider']}` / `{preference['fallback_model']}`"
                    if fallback
                    else "- Fallback provider/model: not set"
                ),
                (
                    f"- Fallback env keys: {_inline_values(fallback['env'])}"
                    if fallback
                    else "- Fallback env keys: not required yet"
                ),
                f"- LLM-only env starter: `/setup/profile-llm-env/{preference['agent_id']}.env`",
                f"- Config starter: `/setup/profile-config/{preference['agent_id']}.yaml`",
                "- Dashboard verification: `/setup#profile-smoke`",
                f"- Current status: `{preference['status']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Activation Order",
            "",
            "1. Finish Slack, Telegram, schedule, and Kanban setup first.",
            "2. Pick the provider/model per profile in `/setup#models`.",
            "3. Review `/setup/profile-config/<profile>.yaml` for every profile.",
            "4. Add only the needed provider env keys to each real Hermes profile `.env`.",
            "5. Run `<profile> model` if Hermes needs interactive provider selection.",
            "6. Mark the matching LLM credential status `loaded` in `/setup#secret-status`.",
            "7. Run `/setup#profile-smoke` for each profile.",
            "8. Treat LLM integration as complete only when every profile smoke check passes.",
            "",
            "## No-Secret Rule",
            "",
            "- This dashboard stores provider/model names, auth method labels, and status only.",
            "- API keys, OAuth refresh tokens, and local endpoint credentials stay in the "
            "real Hermes profile runtime.",
            "- Do not paste credential values into notes, evidence, project ideas, or prompts.",
            "",
        ]
    )
    return "\n".join(lines)


def profile_llm_env_template(agent: dict, preference: dict | None = None) -> str:
    resolved = preference or {
        "provider": "REPLACE_WITH_PROVIDER",
        "model": "REPLACE_WITH_MODEL",
        "fallback_provider": "",
        "fallback_model": "",
        "auth_method": "deferred_profile_secret",
        "status": "planned",
    }
    primary = provider_requirements(resolved["provider"])
    fallback = (
        provider_requirements(resolved["fallback_provider"])
        if resolved.get("fallback_provider")
        else None
    )
    keys = list(dict.fromkeys([*primary["env"], *(fallback["env"] if fallback else [])]))
    lines = [
        f"# LLM credential starter for {agent['name']}",
        "# Store these values only in the real Hermes profile .env file.",
        "# This generated starter intentionally contains placeholders, not secrets.",
        "",
        f"# Provider: {resolved['provider']}",
        f"# Model: {resolved['model']}",
        f"# Auth method: {resolved.get('auth_method') or 'deferred_profile_secret'}",
        f"# Status: {resolved.get('status') or 'planned'}",
        "",
    ]
    for key in keys:
        lines.append(f"{key}=REPLACE_WITH_{key}")
    if fallback:
        lines.extend(
            [
                "",
                f"# Fallback provider: {resolved['fallback_provider']}",
                f"# Fallback model: {resolved.get('fallback_model') or 'REPLACE_WITH_MODEL'}",
            ]
        )
    lines.extend(
        [
            "",
            "# After loading credentials externally:",
            f"# 1. Run `{agent['hermes_command']} model` if Hermes requires provider selection.",
            "# 2. Use `/setup#profile-smoke` to verify this profile.",
            "",
        ]
    )
    return "\n".join(lines)


def provider_requirements(provider_id: str) -> dict:
    normalized = provider_id.strip().lower()
    return PROVIDER_CREDENTIALS.get(normalized, GENERIC_CREDENTIAL)


def _inline_values(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)
