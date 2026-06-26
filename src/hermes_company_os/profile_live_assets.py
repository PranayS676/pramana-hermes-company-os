from __future__ import annotations

import json

from hermes_company_os.hermes_paths import powershell_hermes_home_param
from hermes_company_os.profile_doctrine import (
    LAUNCH_TIERS,
    PROOF_TAGS,
    SHARED_OPERATING_RULES,
    SHARED_PROMPT_RULES,
    doctrine_for,
)


def profile_live_context_markdown(
    *,
    agent: dict,
    agents: list[dict],
    relationships: list[dict],
    schedules: list[dict],
    setup_values: dict[str, str],
) -> str:
    founder_name = setup_values.get("founder_name", "").strip() or "Founder"
    timezone = setup_values.get("timezone", "").strip() or "America/New_York"
    agent_lines = "\n".join(
        f"- {item['name']} (`{item['id']}`): {item['role']}; Slack `{item['slack_channel']}`"
        for item in agents
    )
    relationship_lines = "\n".join(
        f"- {item['manager_name']} manages {item['member_name']}: {item['responsibility']}"
        for item in relationships
    ) or "- No explicit manager/member relationships configured."
    schedule_lines = "\n".join(
        f"- {item['name']}: {item['hour']:02d}:{item['minute']:02d} {item['timezone']} "
        f"to `{item['slack_channel']}`; active={bool(item['active'])}"
        for item in schedules
    )
    launch_tier_lines = "\n".join(f"- {tier}" for tier in LAUNCH_TIERS)
    return f"""# Company Context

Profile: {agent['name']} (`{agent['id']}`)
Founder: {founder_name}
Primary timezone: {timezone}

## Operating Model

- Slack is the main company workspace.
- Telegram is urgent-only for founder alerts, failed runs, blockers, or approvals.
- Hermes Kanban is the task source of truth once initialized.
- LLM provider credentials, Slack tokens, and Telegram bot tokens remain external.
- The first real company idea starts only after profile acceptance and launch gates pass.

## Launch Tiers

{launch_tier_lines}

## Profile Roster

{agent_lines}

## Delegation Map

{relationship_lines}

## Standups

{schedule_lines}
""".strip() + "\n"


def profile_live_prompts_markdown(agent: dict, model_preference: dict | None) -> str:
    preference = model_preference or {}
    provider = preference.get("provider") or "openai-codex"
    model = preference.get("model") or "gpt-5-codex"
    capabilities = "\n".join(f"- {item}" for item in agent["capabilities"])
    doctrine = doctrine_for(agent["id"]) or {}
    shared_rules = _markdown_bullets(SHARED_PROMPT_RULES)
    role_rules = _markdown_bullets(doctrine.get("prompt_rules", []))
    proof_tags = _markdown_bullets(PROOF_TAGS)
    return f"""# Profile Prompt Pack

## Identity Prompt

You are {agent['name']}, a Hermes profile in the founder's AI company.

Role:
{agent['description']}

Soul:
{agent['soul']}

Capabilities:
{capabilities}

Model preference:
- Provider: `{provider}`
- Model: `{model}`
- Credential status: deferred until final LLM verification

## Shared Response Rules

{shared_rules}

## Role-Specific Response Rules

{role_rules}

## Proof Tags

Use these tags when claims, research, marketing, launch decisions, or founder
decisions depend on evidence:

{proof_tags}

## Founder Intake Prompt

When the founder provides an idea, return:

1. Clarifying questions that materially change execution.
2. A short plan for your role.
3. Required handoffs to other profiles.
4. Kanban tasks you would create.
5. Risks or acceptance checks before implementation.
""".strip() + "\n"


def profile_live_rules_markdown(agent: dict) -> str:
    doctrine = doctrine_for(agent["id"]) or {}
    shared_rules = _markdown_bullets(SHARED_OPERATING_RULES)
    role_rules = _markdown_bullets(doctrine.get("operating_rules", []))
    return f"""# Operating Rules

Profile: {agent['name']} (`{agent['id']}`)

## Credential Boundary

- Do not write or request raw LLM API keys, Slack bot tokens, Slack app tokens,
  Telegram bot tokens, OAuth payloads, auth cookies, private headers, or profile
  `.env` contents in dashboard-visible output.
- Use placeholders in documentation and require live credentials to be loaded
  directly into Hermes profile runtime files or provider auth stores.
- Verification can record only status, timestamps, labels, and non-secret evidence.

## Communication

- Slack is the default workspace.
- Telegram is urgent-only and should be routed through Chief of Staff unless explicitly overridden.
- Founder decisions should be clearly labeled as approve, reject, defer, or needs input.

## Shared Cross-Agent Rules

{shared_rules}

## Role-Specific Rules

{role_rules}

## Work Quality

- Prefer durable plans and docs before implementation.
- Keep tests proportional to risk.
- For engineering changes, define unit, integration, E2E, acceptance, and
  rollback checks where relevant.
- For research, cite sources and distinguish confirmed facts from inference.
- For product, prefer fewer visible controls and clearer user workflows.
""".strip() + "\n"


def profile_live_assets_payload(
    *,
    agents: list[dict],
    model_preferences: list[dict],
) -> dict:
    preferences = {item["agent_id"]: item for item in model_preferences}
    return {
        "title": "Hermes Live Starter Profile Assets",
        "credential_boundary": (
            "This pack writes only non-secret live starter files: config.yaml, "
            "COMPANY_CONTEXT.md, PROMPTS.md, and OPERATING_RULES.md. It does not "
            "write .env values, API keys, Slack tokens, Telegram tokens, OAuth "
            "payloads, auth stores, or private logs."
        ),
        "files": [
            "config.yaml",
            "COMPANY_CONTEXT.md",
            "PROMPTS.md",
            "OPERATING_RULES.md",
        ],
        "profiles": [
            {
                "id": agent["id"],
                "name": agent["name"],
                "command": agent["hermes_command"],
                "config": f"/setup/profile-live-config/{agent['id']}.yaml",
                "context": f"/setup/profile-live-context/{agent['id']}.md",
                "prompts": f"/setup/profile-live-prompts/{agent['id']}.md",
                "rules": f"/setup/profile-live-rules/{agent['id']}.md",
                "provider": preferences.get(agent["id"], {}).get("provider", ""),
                "model": preferences.get(agent["id"], {}).get("model", ""),
            }
            for agent in agents
        ],
        "entry_points": {
            "markdown": "/setup/profile-live-assets.md",
            "json": "/setup/profile-live-assets.json",
            "script": "/setup/profile-live-assets.ps1",
            "installation_audit": "/setup/profile-installation.ps1",
            "profile_smoke": "/setup#profile-smoke",
        },
    }


def profile_live_assets_json(**kwargs) -> str:
    return json.dumps(profile_live_assets_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def profile_live_assets_markdown(**kwargs) -> str:
    payload = profile_live_assets_payload(**kwargs)
    lines = [
        "# Hermes Live Starter Profile Assets",
        "",
        "Use this after starter profiles exist and before final credentials are loaded.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Apply Command",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/profile-live-assets.ps1 "
        "-OutFile .\\profile-live-assets.ps1",
        ".\\profile-live-assets.ps1",
        "```",
        "",
        "## Files Written",
        "",
    ]
    for file_name in payload["files"]:
        lines.append(f"- `{file_name}`")
    lines.extend(["", "## Profiles", ""])
    for profile in payload["profiles"]:
        lines.extend(
            [
                f"### {profile['name']}",
                "",
                f"- Profile ID: `{profile['id']}`",
                f"- Command alias: `{profile['command']}`",
                f"- Model: `{profile['provider']}` / `{profile['model']}`",
                f"- Config: `{profile['config']}`",
                f"- Context: `{profile['context']}`",
                f"- Prompts: `{profile['prompts']}`",
                f"- Rules: `{profile['rules']}`",
                "",
            ]
        )
    return "\n".join(lines)


def profile_live_assets_powershell(agents: list[dict]) -> str:
    profile_block = "\n".join(_profile_powershell(agent) for agent in agents)
    return f"""# Hermes Company OS live starter profile assets
# Generated by the dashboard. Review before running.
# This writes only non-secret starter files. It does not read or write .env values.

param(
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [string]$HermesHome = {powershell_hermes_home_param()},
  [string]$ProfileRoot = (Join-Path $HermesHome "profiles")
)

$ErrorActionPreference = "Stop"

$Profiles = @(
{profile_block}
)

foreach ($profile in $Profiles) {{
  $profilePath = Join-Path $ProfileRoot $profile.Id
  if (-not (Test-Path -LiteralPath $profilePath)) {{
    throw (
      "Missing Hermes profile directory: $($profile.Id). " +
      "Run /setup/profile-apply/$($profile.Id).ps1 first."
    )
  }}

  Invoke-WebRequest -UseBasicParsing `
    -Uri "$DashboardBaseUrl/setup/profile-live-config/$($profile.Id).yaml" `
    -OutFile (Join-Path $profilePath "config.yaml")
  Invoke-WebRequest -UseBasicParsing `
    -Uri "$DashboardBaseUrl/setup/profile-live-context/$($profile.Id).md" `
    -OutFile (Join-Path $profilePath "COMPANY_CONTEXT.md")
  Invoke-WebRequest -UseBasicParsing `
    -Uri "$DashboardBaseUrl/setup/profile-live-prompts/$($profile.Id).md" `
    -OutFile (Join-Path $profilePath "PROMPTS.md")
  Invoke-WebRequest -UseBasicParsing `
    -Uri "$DashboardBaseUrl/setup/profile-live-rules/$($profile.Id).md" `
    -OutFile (Join-Path $profilePath "OPERATING_RULES.md")

  Write-Host "WROTE $($profile.Id) config.yaml COMPANY_CONTEXT.md PROMPTS.md OPERATING_RULES.md"
}}

Write-Host ""
Write-Host "Live starter assets applied. Credential files were not touched."
"""


def _profile_powershell(agent: dict) -> str:
    return f"""  [pscustomobject]@{{
    Id = "{_escape(agent['id'])}"
    Name = "{_escape(agent['name'])}"
  }}"""


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')


def _markdown_bullets(items: list[str]) -> str:
    if not items:
        return "- No role-specific doctrine configured."
    return "\n".join(f"- {item}" for item in items)
