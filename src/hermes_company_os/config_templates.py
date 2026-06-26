from __future__ import annotations


def profile_config_template(
    agent: dict,
    setup_values: dict[str, str] | None = None,
    model_preference: dict | None = None,
) -> str:
    values = setup_values or {}
    preference = model_preference or {}
    provider = preference.get("provider") or values.get("llm_provider") or "REPLACE_WITH_PROVIDER"
    model = preference.get("model") or values.get("llm_model") or "REPLACE_WITH_MODEL"
    fallback_provider = preference.get("fallback_provider") or "REPLACE_WITH_FALLBACK_PROVIDER"
    fallback_model = preference.get("fallback_model") or "REPLACE_WITH_FALLBACK_MODEL"
    lines = [
        f"# Hermes config.yaml starter for {agent['name']}",
        "# Model selection is normally finalized with the Hermes `model` command.",
        "# API keys stay in the profile .env file.",
        f"# Auth method: {preference.get('auth_method') or 'deferred_profile_secret'}",
        f"# Status: {preference.get('status') or 'planned'}",
        "",
        "model:",
        f"  provider: {_yaml_string(provider)}",
        f"  model: {_yaml_string(model)}",
        "",
        "# Optional fallback policy. Keep this empty until provider choice is final.",
        "fallback_providers:",
        f"  - provider: {_yaml_string(fallback_provider)}",
        f"    model: {_yaml_string(fallback_model)}",
        "",
        "# Useful when routing through aggregators such as OpenRouter.",
        "provider_routing:",
        "  data_collection: \"deny\"",
        "",
    ]
    notes = preference.get("notes", "").strip()
    if notes:
        lines.extend(["# Notes", f"# {notes}", ""])
    return "\n".join(lines)


def profile_live_config_template(
    agent: dict,
    setup_values: dict[str, str] | None = None,
    model_preference: dict | None = None,
) -> str:
    values = setup_values or {}
    preference = model_preference or {}
    provider = preference.get("provider") or values.get("llm_provider") or "openai-codex"
    model = preference.get("model") or values.get("llm_model") or "gpt-5-codex"
    fallback_provider = preference.get("fallback_provider", "").strip()
    fallback_model = preference.get("fallback_model", "").strip()
    lines = [
        f"# Hermes Company OS live starter config for {agent['name']}",
        "# Non-secret file: provider credentials stay in this profile's .env or Hermes auth store.",
        "# Generated from dashboard model preferences; safe to overwrite before",
        "# final LLM verification.",
        "",
        "model:",
        f"  provider: {_yaml_string(provider)}",
        f"  default: {_yaml_string(model)}",
        "",
    ]
    if fallback_provider and fallback_model:
        lines.extend(
            [
                "fallback_model:",
                f"  provider: {_yaml_string(fallback_provider)}",
                f"  model: {_yaml_string(fallback_model)}",
                "",
            ]
        )
    if provider == "openrouter" or fallback_provider == "openrouter":
        lines.extend(
            [
                "provider_routing:",
                '  data_collection: "deny"',
                "",
            ]
        )
    notes = preference.get("notes", "").strip()
    if notes:
        lines.extend(["# Notes", f"# {notes}", ""])
    return "\n".join(lines)


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
