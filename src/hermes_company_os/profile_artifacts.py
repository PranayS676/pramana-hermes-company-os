from __future__ import annotations

import json

from hermes_company_os.hermes_paths import powershell_hermes_home_param


def profile_artifacts_markdown(agents: list[dict]) -> str:
    sections = [
        "# Hermes Company OS Profile Artifacts",
        "",
        "Review these starter values before writing them into Hermes profile homes.",
        "",
    ]
    for agent in agents:
        sections.extend(
            [
                f"## {agent['name']}",
                "",
                f"- Profile ID: `{agent['id']}`",
                f"- Slack channel: `{agent['slack_channel']}`",
                f"- Hermes command: `{agent['hermes_command']}`",
                "",
                "Description:",
                "",
                agent["description"],
                "",
                "Capabilities:",
                "",
                *[f"- {capability}" for capability in agent.get("capabilities", [])],
                "",
                "SOUL.md:",
                "",
                "```markdown",
                agent["soul"],
                "```",
                "",
            ]
        )
    return "\n".join(sections)


def profile_soul_markdown(agent: dict) -> str:
    return agent["soul"].strip() + "\n"


def profile_manifest_json(agent: dict) -> str:
    manifest = {
        "id": agent["id"],
        "name": agent["name"],
        "role": agent["role"],
        "description": agent["description"],
        "soul_file": "SOUL.md",
        "capabilities": agent["capabilities"],
        "routing": {
            "hermes_command": agent["hermes_command"],
            "slack_channel": agent["slack_channel"],
            "telegram_policy": agent["telegram_policy"],
        },
        "setup_exports": {
            "profile_env": f"/setup/profile-env/{agent['id']}.env",
            "profile_llm_env": f"/setup/profile-llm-env/{agent['id']}.env",
            "profile_config": f"/setup/profile-config/{agent['id']}.yaml",
            "slack_manifest": f"/setup/slack-manifest/{agent['id']}.json",
            "profile_apply_script": f"/setup/profile-apply/{agent['id']}.ps1",
        },
    }
    return json.dumps(manifest, indent=2) + "\n"


def profile_apply_powershell(agent: dict) -> str:
    description = _escape_double_quoted(agent["description"])
    soul = _powershell_literal(profile_soul_markdown(agent))
    manifest = _powershell_literal(profile_manifest_json(agent))
    capabilities = _powershell_literal(json.dumps(agent["capabilities"], indent=2) + "\n")
    return f"""# Hermes Company OS profile apply script for {agent['name']}
# Run after Hermes is installed.
# This writes starter identity and no-secret starter files only.
# It does not write Slack, Telegram, or LLM secrets.
# Review env/config exports before copying values into live profile files:
# - /setup/profile-env/{agent['id']}.env
# - /setup/profile-llm-env/{agent['id']}.env
# - /setup/profile-config/{agent['id']}.yaml

param(
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002"
)

$HermesHome = {powershell_hermes_home_param()}
$ProfileRoot = Join-Path $HermesHome "profiles"
$profilePath = Join-Path $ProfileRoot '{agent['id']}'
if (-not (Test-Path $profilePath)) {{
  hermes profile create {agent['id']} --description "{description}"
}}
New-Item -ItemType Directory -Path $profilePath -Force | Out-Null

$soulPath = Join-Path $profilePath 'SOUL.md'
@'
{soul}
'@ | Set-Content -Path $soulPath -Encoding UTF8

$capabilitiesPath = Join-Path $profilePath 'capabilities.json'
@'
{capabilities}
'@ | Set-Content -Path $capabilitiesPath -Encoding UTF8

$manifestPath = Join-Path $profilePath 'profile-manifest.json'
@'
{manifest}
'@ | Set-Content -Path $manifestPath -Encoding UTF8

$envExamplePath = Join-Path $profilePath '.env.example'
Invoke-WebRequest -UseBasicParsing `
  -Uri "$DashboardBaseUrl/setup/profile-env/{agent['id']}.env" `
  -OutFile $envExamplePath

$configExamplePath = Join-Path $profilePath 'config.yaml.example'
Invoke-WebRequest -UseBasicParsing `
  -Uri "$DashboardBaseUrl/setup/profile-config/{agent['id']}.yaml" `
  -OutFile $configExamplePath
"""


def _escape_double_quoted(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')


def _powershell_literal(value: str) -> str:
    return value.replace("'@", "' @")
