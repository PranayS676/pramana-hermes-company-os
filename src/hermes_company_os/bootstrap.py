from __future__ import annotations

from hermes_company_os.activation import cron_commands
from hermes_company_os.config_templates import profile_config_template
from hermes_company_os.env_templates import profile_env_template
from hermes_company_os.hermes_paths import powershell_hermes_home_param


def powershell_bootstrap(
    agents: list[dict],
    setup_values: dict[str, str] | None = None,
    schedules: list[dict] | None = None,
    model_preferences: dict[str, dict] | None = None,
) -> str:
    values = setup_values or {}
    preferences = model_preferences or {}
    profile_commands = "\n".join(
        _profile_block(agent, values, preferences.get(agent["id"])) for agent in agents
    )
    cron = "\n".join(cron_commands(values, schedules))
    return f"""# Hermes Company OS bootstrap
# Run this after Hermes is installed.
# It creates starter profiles and writes SOUL.md plus no-secret starter files.
# This script does not write LLM API keys, Slack tokens, or Telegram tokens.
# Review .env.example and config.yaml.example inside each profile before copying
# values into live .env or config.yaml files.

$HermesHome = {powershell_hermes_home_param()}
$ProfileRoot = Join-Path $HermesHome "profiles"

{profile_commands}

# Initialize the shared Hermes Kanban board.
hermes kanban init
hermes kanban diagnostics --json

# Create standup cron jobs after Slack and Telegram gateways are configured.
# The prompts keep Slack as the main workspace and Telegram urgent-only.
{cron}
"""


def _profile_block(
    agent: dict,
    setup_values: dict[str, str],
    model_preference: dict | None,
) -> str:
    description = _escape_double_quoted(agent["description"])
    soul = _powershell_literal(agent["soul"])
    env_template = _powershell_literal(profile_env_template(agent, setup_values))
    config_template = _powershell_literal(
        profile_config_template(agent, setup_values, model_preference)
    )
    return f"""
$profilePath = Join-Path $ProfileRoot '{agent['id']}'
if (-not (Test-Path $profilePath)) {{
  hermes profile create {agent['id']} --description "{description}"
}}
New-Item -ItemType Directory -Path $profilePath -Force | Out-Null

$soulPath = Join-Path $profilePath 'SOUL.md'
@'
{soul}
'@ | Set-Content -Path $soulPath -Encoding UTF8

$envExamplePath = Join-Path $profilePath '.env.example'
@'
{env_template}
'@ | Set-Content -Path $envExamplePath -Encoding UTF8

$configExamplePath = Join-Path $profilePath 'config.yaml.example'
@'
{config_template}
'@ | Set-Content -Path $configExamplePath -Encoding UTF8
"""


def _escape_double_quoted(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')


def _powershell_literal(value: str) -> str:
    return value.replace("'@", "' @")


def profile_setup_commands(agents: list[dict]) -> list[dict]:
    commands = []
    for agent in agents:
        commands.append(
            {
                "agent": agent["name"],
                "profile_id": agent["id"],
                "create": (
                    f'hermes profile create {agent["id"]} '
                    f'--description "{_escape_double_quoted(agent["description"])}"'
                ),
                "setup": f"{agent['hermes_command']} setup",
                "gateway_setup": f"{agent['hermes_command']} gateway setup",
                "gateway_start": f"{agent['hermes_command']} gateway start",
                "gateway_install": f"{agent['hermes_command']} gateway install",
            }
        )
    return commands
