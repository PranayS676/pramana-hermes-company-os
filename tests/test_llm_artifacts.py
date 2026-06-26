from hermes_company_os.llm_artifacts import (
    llm_credentials_plan_markdown,
    profile_llm_env_template,
    provider_requirements,
)


def test_provider_requirements_resolves_known_and_custom_providers():
    assert provider_requirements("openai-codex")["env"] == ["OPENAI_API_KEY"]
    assert provider_requirements("OpenRouter")["env"] == ["OPENROUTER_API_KEY"]
    assert provider_requirements("local-ollama")["env"] == ["OLLAMA_BASE_URL"]
    assert provider_requirements("custom")["env"] == ["PROVIDER_API_KEY_OR_OAUTH"]


def test_profile_llm_env_template_contains_only_llm_placeholders():
    template = profile_llm_env_template(
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "hermes_command": "engineering-manager",
        },
        {
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "openai-codex",
            "fallback_model": "gpt-5-codex",
            "auth_method": "profile_env",
            "status": "needs_secret",
        },
    )

    assert "OPENROUTER_API_KEY=REPLACE_WITH_OPENROUTER_API_KEY" in template
    assert "OPENAI_API_KEY=REPLACE_WITH_OPENAI_API_KEY" in template
    assert "# Provider: openrouter" in template
    assert "# Fallback provider: openai-codex" in template
    assert "`engineering-manager model`" in template
    assert "SLACK_BOT_TOKEN" not in template
    assert "TELEGRAM_BOT_TOKEN" not in template
    assert "xoxb-" not in template
    assert "xapp-" not in template
    assert "sk-" not in template


def test_llm_credentials_plan_lists_profile_routes_and_activation_order():
    plan = llm_credentials_plan_markdown(
        [
            {
                "agent_id": "research-agent",
                "agent_name": "Research Agent",
                "hermes_command": "research-agent",
                "provider": "openai-codex",
                "model": "gpt-5-codex",
                "fallback_provider": "",
                "fallback_model": "",
                "auth_method": "deferred_profile_secret",
                "status": "planned",
            }
        ]
    )

    assert "LLM Credential Setup Matrix" in plan
    assert "`openai-codex` / `gpt-5-codex`" in plan
    assert "`OPENAI_API_KEY`" in plan
    assert "/setup/profile-llm-env/research-agent.env" in plan
    assert "/setup/profile-config/research-agent.yaml" in plan
    assert "Finish Slack, Telegram, schedule, and Kanban setup first." in plan
    assert "Do not paste credential values" in plan
