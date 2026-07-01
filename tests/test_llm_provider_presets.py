import json

from hermes_company_os.llm_provider_presets import (
    llm_preset_preferences,
    llm_provider_presets_json,
    llm_provider_presets_markdown,
    llm_provider_presets_payload,
)

AGENTS = [
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
    },
    {
        "id": "research-agent",
        "name": "Research Agent",
    },
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
    },
]


MODEL_PREFERENCES = [
    {
        "agent_id": "chief-of-staff",
        "agent_name": "Chief of Staff",
        "provider": "openai-codex",
        "model": "gpt-5-codex",
        "status": "planned",
    }
]


def test_llm_provider_presets_payload_lists_current_and_presets():
    payload = llm_provider_presets_payload(
        agents=AGENTS,
        model_preferences=MODEL_PREFERENCES,
    )

    assert payload["title"] == "LLM Provider Presets"
    assert payload["verification_last"] is True
    assert payload["current"][0]["provider"] == "openai-codex"
    assert payload["current"][1]["status"] == "missing"
    assert {preset["id"] for preset in payload["presets"]} == {
        "codex-company-default",
        "openrouter-cost-efficient-company",
        "openrouter-research-heavy",
        "local-ollama-dry-run",
    }


def test_llm_provider_presets_markdown_is_no_secret_and_actionable():
    markdown = llm_provider_presets_markdown(
        agents=AGENTS,
        model_preferences=MODEL_PREFERENCES,
    )

    assert "LLM Provider Presets" in markdown
    assert "/setup/llm-provider-presets/codex-company-default" in markdown
    assert "Final Verification Still Last" in markdown
    assert "OPENROUTER_API_KEY" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown


def test_llm_provider_presets_json_is_structured():
    payload = json.loads(
        llm_provider_presets_json(
            agents=AGENTS,
            model_preferences=MODEL_PREFERENCES,
        )
    )

    assert payload["entry_points"]["manual_preferences"] == "/setup/models#models"
    assert payload["presets"][0]["profiles"]


def test_llm_preset_preferences_applies_role_overrides():
    preferences = llm_preset_preferences("openrouter-research-heavy", AGENTS)
    research = next(item for item in preferences if item["agent_id"] == "research-agent")
    chief = next(item for item in preferences if item["agent_id"] == "chief-of-staff")

    assert research["provider"] == "openrouter"
    assert research["model"] == "anthropic/claude-sonnet-4"
    assert research["fallback_provider"] == "openai-codex"
    assert chief["provider"] == "openai-codex"
    assert all("Credentials remain external" in item["notes"] for item in preferences)


def test_cost_efficient_preset_uses_openrouter_and_role_specific_models():
    agents = [
        {
            "id": "chief-of-staff",
            "name": "Chief of Staff",
        },
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
        },
        {
            "id": "marketing-agent",
            "name": "Marketing Agent",
        },
    ]

    preferences = llm_preset_preferences("openrouter-cost-efficient-company", agents)
    by_agent = {item["agent_id"]: item for item in preferences}

    assert by_agent["chief-of-staff"]["provider"] == "openrouter"
    assert by_agent["chief-of-staff"]["model"] == "google/gemini-2.5-flash-lite"
    assert by_agent["engineering-manager"]["model"] == "deepseek/deepseek-chat-v3.1"
    assert by_agent["engineering-manager"]["fallback_model"] == (
        "anthropic/claude-haiku-4.5"
    )
    assert by_agent["marketing-agent"]["model"] == "google/gemini-2.5-flash-lite"
    assert all(item["auth_method"] == "profile_env" for item in preferences)
    assert all(item["status"] == "needs_secret" for item in preferences)


def test_llm_preset_preferences_rejects_unknown_preset():
    try:
        llm_preset_preferences("missing-preset", AGENTS)
    except KeyError as exc:
        assert exc.args == ("missing-preset",)
    else:
        raise AssertionError("Expected KeyError")
