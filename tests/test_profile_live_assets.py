import json

from hermes_company_os.profile_live_assets import (
    profile_live_assets_json,
    profile_live_assets_markdown,
    profile_live_assets_payload,
    profile_live_assets_powershell,
    profile_live_context_markdown,
    profile_live_prompts_markdown,
    profile_live_rules_markdown,
)
from hermes_company_os.secret_guard import secret_violations

AGENT = {
    "id": "engineering-manager",
    "name": "Engineering Manager",
    "role": "Engineering",
    "slack_channel": "#engineering",
    "telegram_policy": "No direct Telegram unless escalated by Chief of Staff",
    "hermes_command": "engineering-manager",
    "description": "Creates ambitious architecture plans.",
    "soul": "Think big about architecture, AWS, and tests.",
    "capabilities": ["architecture", "distributed systems", "e2e testing"],
}


def test_profile_live_assets_exports_no_secret_apply_pack():
    kwargs = {
        "agents": [AGENT],
        "model_preferences": [
            {
                "agent_id": "engineering-manager",
                "provider": "openai-codex",
                "model": "gpt-5-codex",
            }
        ],
    }

    payload = profile_live_assets_payload(**kwargs)
    markdown = profile_live_assets_markdown(**kwargs)
    exported = json.loads(profile_live_assets_json(**kwargs))
    script = profile_live_assets_powershell([AGENT])
    raw = json.dumps(payload) + markdown + json.dumps(exported) + script

    assert payload["files"] == [
        "config.yaml",
        "COMPANY_CONTEXT.md",
        "PROMPTS.md",
        "OPERATING_RULES.md",
    ]
    assert payload["entry_points"]["script"] == "/setup/profile-live-assets.ps1"
    assert "/setup/profile-live-config/engineering-manager.yaml" in raw
    assert "Invoke-WebRequest" in script
    assert "WROTE $($profile.Id) config.yaml" in script
    assert ".env values" in script
    assert secret_violations({"raw": raw}) == []


def test_profile_live_markdown_assets_capture_company_rules_without_secrets():
    context = profile_live_context_markdown(
        agent=AGENT,
        agents=[AGENT],
        relationships=[
            {
                "manager_name": "Engineering Manager",
                "member_name": "Backend Engineer",
                "responsibility": "Own APIs and integration tests.",
            }
        ],
        schedules=[
            {
                "name": "Morning Standup",
                "hour": 9,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "active": 1,
            }
        ],
        setup_values={"founder_name": "Masad", "timezone": "America/New_York"},
    )
    prompts = profile_live_prompts_markdown(
        AGENT,
        {"provider": "openai-codex", "model": "gpt-5-codex"},
    )
    rules = profile_live_rules_markdown(AGENT)
    raw = context + prompts + rules

    assert "Slack is the main company workspace." in context
    assert "T2 Public Beta" in context
    assert "09:00 America/New_York" in context
    assert "Founder Intake Prompt" in prompts
    assert "smallest safe version" in prompts
    assert "PROOF-BLOCKED" in prompts
    assert "testing" in prompts
    assert "Credential Boundary" in rules
    assert "Shared Cross-Agent Rules" in rules
    assert "PM owns product bet" in rules
    assert secret_violations({"raw": raw}) == []


def test_profile_live_assets_include_role_specific_doctrine_without_secrets():
    frontend_agent = {
        "id": "frontend-engineer",
        "name": "Frontend Engineer",
        "role": "Engineering",
        "slack_channel": "#engineering",
        "telegram_policy": "No direct Telegram unless escalated by Chief of Staff",
        "hermes_command": "frontend-engineer",
        "description": "Builds production-grade React UI plans.",
        "soul": "Own React UI quality.",
        "capabilities": ["React frontend architecture", "accessibility implementation"],
    }

    prompts = profile_live_prompts_markdown(
        frontend_agent,
        {"provider": "openai-codex", "model": "gpt-5-codex"},
    )
    rules = profile_live_rules_markdown(frontend_agent)
    raw = prompts + rules

    assert "UI-change tier" in prompts
    assert "UI3/UI4" in prompts
    assert "Customize proven primitives" in rules
    assert "High-risk UI gets QA/Critic" in rules
    assert secret_violations({"raw": raw}) == []
