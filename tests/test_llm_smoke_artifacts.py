import json

from fastapi.testclient import TestClient

from hermes_company_os.llm_smoke_artifacts import llm_smoke_json, llm_smoke_markdown
from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def test_llm_smoke_routes_export_prompts_and_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/llm-smoke.md")
    response = client.get("/setup/llm-smoke.json")

    assert markdown.status_code == 200
    assert "LLM Smoke Drill Pack" in markdown.text
    assert "Expected Response Schema" in markdown.text
    assert "Chief of Staff" in markdown.text
    assert "profile_ready: yes/no" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "LLM Smoke Drill Pack"
    assert payload["verification_last"] is True
    assert payload["entry_points"]["secret_audit"] == "/setup/secret-audit.ps1"
    assert payload["profiles"][0]["smoke_route"] == "/setup/profile-smoke/chief-of-staff"
    assert "OPENAI_API_KEY" in payload["profiles"][0]["expected_env_keys"]

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []


def test_llm_smoke_helpers_include_fallback_keys_and_prompt_schema():
    agents = [
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "role": "Engineering",
            "capabilities": ["architecture", "E2E testing"],
        }
    ]
    model_preferences = [
        {
            "agent_id": "engineering-manager",
            "agent_name": "Engineering Manager",
            "hermes_command": "engineering-manager",
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "openai-codex",
            "fallback_model": "gpt-5-codex",
            "status": "ready_for_verification",
        }
    ]
    secret_requirements = [
        {
            "owner_agent_id": "engineering-manager",
            "category": "llm",
            "status": "loaded",
            "notes": "Private note should not appear.",
        }
    ]

    payload = json.loads(
        llm_smoke_json(
            agents=agents,
            model_preferences=model_preferences,
            secret_requirements=secret_requirements,
        )
    )
    markdown = llm_smoke_markdown(
        agents=agents,
        model_preferences=model_preferences,
        secret_requirements=secret_requirements,
    )

    profile = payload["profiles"][0]
    assert profile["expected_env_keys"] == ["OPENROUTER_API_KEY", "OPENAI_API_KEY"]
    assert profile["credential_status"] == "loaded"
    assert profile["model_status"] == "ready_for_verification"
    assert "profile_ready: yes/no" in profile["prompt"]
    assert "Private note should not appear" not in json.dumps(payload)
    assert "OPENROUTER_API_KEY" in markdown
    assert "Run `/setup/secret-audit.ps1 -AuditLlm`" in markdown
