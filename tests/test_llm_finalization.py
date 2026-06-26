from hermes_company_os.llm_finalization import (
    llm_finalization_markdown,
    llm_finalization_powershell,
)
from hermes_company_os.secret_guard import secret_violations

PREFERENCES = [
    {
        "agent_id": "chief-of-staff",
        "agent_name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4",
        "fallback_provider": "openai-codex",
        "fallback_model": "gpt-5-codex",
        "status": "ready_for_verification",
    },
    {
        "agent_id": "research-agent",
        "agent_name": "Research Agent",
        "hermes_command": "research-agent",
        "provider": "local-ollama",
        "model": "llama3.1",
        "fallback_provider": "",
        "fallback_model": "",
        "status": "planned",
    },
]


def test_llm_finalization_markdown_lists_profiles_keys_and_last_phase():
    markdown = llm_finalization_markdown(PREFERENCES)

    assert "LLM Finalization Runner" in markdown
    assert "`openrouter` / `anthropic/claude-sonnet-4`" in markdown
    assert "`OPENROUTER_API_KEY`" in markdown
    assert "`OPENAI_API_KEY`" in markdown
    assert "`OLLAMA_BASE_URL`" in markdown
    assert "/setup/profile-smoke/chief-of-staff" in markdown
    assert "Run this only after profiles, Slack, Telegram" in markdown
    assert "sk-" not in markdown
    assert secret_violations({"markdown": markdown}) == []


def test_llm_finalization_powershell_audits_and_runs_optional_smoke_checks():
    script = llm_finalization_powershell(PREFERENCES)

    assert "Hermes Company OS LLM finalization runner" in script
    assert "/setup/secret-audit.ps1" in script
    assert "-AuditLlm" in script
    assert "PostDashboardStatus" in script
    assert "chief-of-staff model" in script
    assert 'Invoke-DashboardPost "/setup/profile-smoke/chief-of-staff"' in script
    assert "OPENROUTER_API_KEY" in script
    assert "OPENAI_API_KEY" in script
    assert "OLLAMA_BASE_URL" in script
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
    assert secret_violations({"script": script}) == []
