import json

from hermes_company_os.llm_provisioning import (
    llm_provisioning_json,
    llm_provisioning_markdown,
    llm_provisioning_payload,
    llm_provisioning_powershell,
)
from hermes_company_os.secret_guard import secret_violations

MODEL_PREFERENCES = [
    {
        "agent_id": "chief-of-staff",
        "agent_name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4",
        "fallback_provider": "openai-codex",
        "fallback_model": "gpt-5-codex",
        "auth_method": "profile_env",
        "status": "needs_secret",
    },
    {
        "agent_id": "research-agent",
        "agent_name": "Research Agent",
        "hermes_command": "research-agent",
        "provider": "local-ollama",
        "model": "llama3.1",
        "fallback_provider": "",
        "fallback_model": "",
        "auth_method": "local_endpoint",
        "status": "planned",
    },
]

SECRET_REQUIREMENTS = [
    {
        "owner_agent_id": "chief-of-staff",
        "category": "llm",
        "status": "needed",
    },
    {
        "owner_agent_id": "research-agent",
        "category": "llm",
        "status": "deferred",
    },
]
INTEGRATIONS = [{"id": "llm-provider", "status": "deferred"}]
MESSAGING_CHECKS = [{"status": "verified"}]
SCHEDULE_CHECKS = [{"status": "verified", "schedule_active": 1}]
KANBAN_CHECKS = [{"status": "verified"}]


def test_llm_provisioning_payload_maps_profiles_and_gates():
    payload = llm_provisioning_payload(
        model_preferences=MODEL_PREFERENCES,
        secret_requirements=SECRET_REQUIREMENTS,
        integrations=INTEGRATIONS,
        messaging_checks=MESSAGING_CHECKS,
        schedule_checks=SCHEDULE_CHECKS,
        kanban_checks=KANBAN_CHECKS,
    )

    assert payload["title"] == "LLM Provisioning Pack"
    assert payload["verification_last"] is True
    assert payload["profiles"][0]["expected_env_keys"] == [
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
    ]
    assert payload["profiles"][1]["expected_env_keys"] == ["OLLAMA_BASE_URL"]
    assert payload["prior_gates"]["messaging"]["ready"] is True
    assert payload["prior_gates"]["schedule"]["ready"] is True
    assert payload["prior_gates"]["kanban"]["ready"] is True
    assert payload["prior_gates"]["llm_integration"] == "deferred"
    assert payload["runner"]["route"] == "/setup/llm-provisioning.ps1"


def test_llm_provisioning_markdown_json_and_script_are_no_secret():
    kwargs = {
        "model_preferences": MODEL_PREFERENCES,
        "secret_requirements": SECRET_REQUIREMENTS,
        "integrations": INTEGRATIONS,
        "messaging_checks": MESSAGING_CHECKS,
        "schedule_checks": SCHEDULE_CHECKS,
        "kanban_checks": KANBAN_CHECKS,
    }

    markdown = llm_provisioning_markdown(**kwargs)
    payload = json.loads(llm_provisioning_json(**kwargs))
    script = llm_provisioning_powershell(MODEL_PREFERENCES)
    raw = "\n".join([markdown, json.dumps(payload), script])

    assert "LLM Provisioning Pack" in markdown
    assert "Why Last" in markdown
    assert "/setup/llm-finalize.ps1" in markdown
    assert payload["entry_points"]["credentials_matrix"] == "/setup/llm-credentials.md"
    assert "Hermes Company OS LLM provisioning runner" in script
    assert "DownloadStarters" in script
    assert "RunModelPicker" in script
    assert "llm.env.example" in script
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []
