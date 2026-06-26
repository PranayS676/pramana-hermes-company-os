from hermes_company_os.config_templates import (
    profile_config_template,
    profile_live_config_template,
)


def test_profile_config_template_uses_saved_model_choice():
    template = profile_config_template(
        {"name": "Engineering Manager"},
        {
            "llm_provider": "openai-codex",
            "llm_model": "gpt-5-codex",
        },
    )

    assert 'provider: "openai-codex"' in template
    assert 'model: "gpt-5-codex"' in template
    assert "fallback_providers:" in template


def test_profile_config_template_prefers_profile_model_preference():
    template = profile_config_template(
        {"name": "Research Agent"},
        {
            "llm_provider": "openai-codex",
            "llm_model": "gpt-5-codex",
        },
        {
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "openai-codex",
            "fallback_model": "gpt-5-codex",
            "auth_method": "profile_env",
            "status": "needs_secret",
            "notes": "Research profile preference.",
        },
    )

    assert 'provider: "openrouter"' in template
    assert 'model: "anthropic/claude-sonnet-4"' in template
    assert 'provider: "openai-codex"' in template
    assert 'model: "gpt-5-codex"' in template
    assert "# Auth method: profile_env" in template
    assert "# Status: needs_secret" in template


def test_profile_live_config_template_uses_hermes_runtime_shape_without_placeholders():
    template = profile_live_config_template(
        {"name": "Engineering Manager"},
        {},
        {
            "provider": "openai-codex",
            "model": "gpt-5-codex",
            "fallback_provider": "",
            "fallback_model": "",
            "notes": "Credentials remain external.",
        },
    )

    assert "# Hermes Company OS live starter config for Engineering Manager" in template
    assert 'provider: "openai-codex"' in template
    assert 'default: "gpt-5-codex"' in template
    assert "fallback_model:" not in template
    assert "REPLACE_WITH" not in template


def test_profile_live_config_template_adds_real_fallback_only_when_configured():
    template = profile_live_config_template(
        {"name": "Research Agent"},
        {},
        {
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "openai-codex",
            "fallback_model": "gpt-5-codex",
            "notes": "",
        },
    )

    assert 'provider: "openrouter"' in template
    assert 'default: "anthropic/claude-sonnet-4"' in template
    assert "fallback_model:" in template
    assert 'provider: "openai-codex"' in template
    assert 'model: "gpt-5-codex"' in template
    assert 'data_collection: "deny"' in template
