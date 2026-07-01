from __future__ import annotations

import json
from collections import Counter, defaultdict


def gateway_operations_payload(
    *,
    agents: list[dict],
    messaging_checks: list[dict],
    integrations: list[dict],
    secret_requirements: list[dict],
) -> dict:
    checks_by_agent = defaultdict(list)
    for check in messaging_checks:
        checks_by_agent[check["owner_agent_id"]].append(_messaging_check(check))
    secrets_by_agent = defaultdict(list)
    for requirement in secret_requirements:
        if requirement["category"] in {"slack", "telegram"} and requirement.get(
            "owner_agent_id"
        ):
            secrets_by_agent[requirement["owner_agent_id"]].append(
                _secret_requirement(requirement)
            )
    return {
        "title": "Hermes Gateway Operations",
        "credential_boundary": (
            "This artifact includes profile command aliases, gateway commands, "
            "status metadata, and setup route links only. It does not include Slack "
            "tokens, Telegram bot tokens, OAuth payloads, request headers, private "
            "endpoints, or verification evidence text."
        ),
        "default_policy": (
            "Run command checks first. Run interactive gateway setup only after "
            "profile env files contain external credentials. Prefer service install "
            "for ongoing Slack/Telegram operation."
        ),
        "profiles": [
            _profile(agent, checks_by_agent[agent["id"]], secrets_by_agent[agent["id"]])
            for agent in agents
        ],
        "messaging_status": {
            "checks": dict(Counter(check["status"] for check in messaging_checks)),
            "secrets": dict(Counter(item["status"] for item in secret_requirements)),
            "integrations": dict(Counter(item["status"] for item in integrations)),
        },
        "phases": [
            {
                "id": "check_commands",
                "command": ".\\gateway-operations.ps1 -CheckCommands",
                "purpose": "Confirm all Hermes profile command aliases are on PATH.",
            },
            {
                "id": "setup_gateways",
                "command": ".\\gateway-operations.ps1 -Setup -PostDashboardStatus",
                "purpose": "Run interactive gateway setup for each profile.",
            },
            {
                "id": "install_services",
                "command": ".\\gateway-operations.ps1 -InstallService -PostDashboardStatus",
                "purpose": "Install persistent gateway services where Hermes supports it.",
            },
            {
                "id": "start_foreground",
                "command": ".\\gateway-operations.ps1 -Start",
                "purpose": "Start gateways in the foreground for manual smoke checks.",
            },
        ],
        "entry_points": {
            "profile_artifacts": "/setup/profile-artifacts.md",
            "credential_loading": "/setup/credential-loading.md",
            "secret_audit": "/setup/secret-audit.md",
            "messaging_drill": "/setup/messaging-drill.md",
            "messaging_verification": "/setup/messaging#messaging-verification",
            "verification_evidence": "/setup/verification-evidence.md",
            "live_verification": "/setup/live-verification.md",
        },
    }


def gateway_operations_json(**kwargs) -> str:
    return json.dumps(gateway_operations_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def gateway_operations_markdown(**kwargs) -> str:
    payload = gateway_operations_payload(**kwargs)
    lines = [
        "# Hermes Gateway Operations",
        "",
        "Use this after profile starter files exist and Slack/Telegram credentials "
        "are loaded into the real Hermes profile environments.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Default Policy",
        "",
        f"- {payload['default_policy']}",
        "",
        "## Commands",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/gateway-operations.ps1 "
        "-OutFile .\\gateway-operations.ps1",
        ".\\gateway-operations.ps1 -CheckCommands",
        ".\\gateway-operations.ps1 -Setup",
        ".\\gateway-operations.ps1 -Setup -PostDashboardStatus",
        ".\\gateway-operations.ps1 -InstallService",
        ".\\gateway-operations.ps1 -Start",
        "```",
        "",
        "`-PostDashboardStatus` records the matching Slack gateway check as `loaded` "
        "after a gateway command succeeds. DM replies, channel mentions, and Telegram "
        "urgent alerts still require separate live verification.",
        "",
        "## Profile Gateway Matrix",
        "",
    ]
    for profile in payload["profiles"]:
        lines.extend(
            [
                f"### {profile['name']}",
                "",
                f"- Profile command: `{profile['command']}`",
                f"- Env starter: `{profile['env_starter']}`",
                f"- Slack manifest: `{profile['slack_manifest']}`",
                f"- Setup: `{profile['commands']['setup']}`",
                f"- Start: `{profile['commands']['start']}`",
                f"- Install service: `{profile['commands']['install']}`",
                f"- External credential statuses: {_format_counts(profile['secret_status'])}",
                f"- Messaging checks: {_format_counts(profile['messaging_status'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Verification After Gateways Start",
            "",
            "- Complete Slack gateway, Slack DM, Slack channel mention, and Telegram "
            "urgent-alert checks in `/setup/messaging#messaging-verification`.",
            "- Then review `/setup/verification-evidence.md` before proceeding to "
            "Kanban, standups, and final LLM verification.",
            "",
        ]
    )
    return "\n".join(lines)


def gateway_operations_powershell(agents: list[dict]) -> str:
    profile_block = "\n".join(_profile_powershell(agent) for agent in agents)
    return f"""# Hermes Company OS gateway operations
# Generated by the dashboard. Review before running.
# This script contains no Slack tokens, Telegram bot tokens, or provider keys.

param(
  [switch]$CheckCommands,
  [switch]$Setup,
  [switch]$Start,
  [switch]$InstallService,
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$PostDashboardStatus
)

$ErrorActionPreference = "Stop"

if (-not ($CheckCommands -or $Setup -or $Start -or $InstallService)) {{
  $CheckCommands = $true
}}

$Profiles = @(
{profile_block}
)

function Get-CommandName {{
  param([string]$CommandLine)
  return ($CommandLine -split "\\s+")[0]
}}

function Invoke-GatewayAction {{
  param(
    [pscustomobject]$Profile,
    [string]$Action
  )
  $commandLine = "$($Profile.Command) gateway $Action"
  Write-Host ""
  Write-Host "==> $($Profile.Name): $commandLine"
  Invoke-Expression $commandLine
}}

function Post-MessagingGatewayStatus {{
  param(
    [pscustomobject]$Profile,
    [string]$Action
  )
  $checkId = "$($Profile.Id)-slack-gateway"
  $uri = "$DashboardBaseUrl/setup/messaging-checks/$checkId"
  $body = @{{
    status = "loaded"
    evidence = "Gateway operations runner completed gateway $Action for $($Profile.Name)."
  }}
  try {{
    Invoke-WebRequest `
      -UseBasicParsing `
      -Method Post `
      -Uri $uri `
      -ContentType "application/x-www-form-urlencoded" `
      -Body $body | Out-Null
    Write-Host "DASHBOARD loaded $checkId"
  }} catch {{
    Write-Host "DASHBOARD skipped ${{checkId}}: $($_.Exception.Message)"
  }}
}}

if ($CheckCommands) {{
  foreach ($profile in $Profiles) {{
    $commandName = Get-CommandName $profile.Command
    if (Get-Command $commandName -ErrorAction SilentlyContinue) {{
      Write-Host "FOUND   $($profile.Id): $commandName"
    }} else {{
      Write-Host "MISSING $($profile.Id): $commandName"
    }}
  }}
}}

if ($Setup) {{
  foreach ($profile in $Profiles) {{
    Invoke-GatewayAction $profile "setup"
    if ($PostDashboardStatus) {{
      Post-MessagingGatewayStatus $profile "setup"
    }}
  }}
}}

if ($InstallService) {{
  foreach ($profile in $Profiles) {{
    Invoke-GatewayAction $profile "install"
    if ($PostDashboardStatus) {{
      Post-MessagingGatewayStatus $profile "install"
    }}
  }}
}}

if ($Start) {{
  Write-Host "Foreground gateway start may block this terminal."
  Write-Host "Use one terminal per profile if needed."
  foreach ($profile in $Profiles) {{
    Invoke-GatewayAction $profile "start"
    if ($PostDashboardStatus) {{
      Post-MessagingGatewayStatus $profile "start"
    }}
  }}
}}

Write-Host ""
Write-Host "Gateway operation finished. Complete /setup/messaging#messaging-verification next."
"""


def _profile(agent: dict, messaging_checks: list[dict], requirements: list[dict]) -> dict:
    command = agent["hermes_command"]
    return {
        "id": agent["id"],
        "name": agent["name"],
        "command": command,
        "slack_channel": agent["slack_channel"],
        "telegram_policy": agent["telegram_policy"],
        "env_starter": f"/setup/profile-env/{agent['id']}.env",
        "slack_manifest": f"/setup/slack-manifest/{agent['id']}.json",
        "commands": {
            "setup": f"{command} gateway setup",
            "start": f"{command} gateway start",
            "install": f"{command} gateway install",
        },
        "secret_status": dict(Counter(item["status"] for item in requirements)),
        "messaging_status": dict(Counter(item["status"] for item in messaging_checks)),
        "messaging_checks": messaging_checks,
    }


def _messaging_check(check: dict) -> dict:
    return {
        "id": check["id"],
        "platform": check["platform"],
        "label": check["label"],
        "status": check["status"],
        "has_evidence": bool(check.get("evidence", "").strip()),
    }


def _secret_requirement(requirement: dict) -> dict:
    return {
        "id": requirement["id"],
        "category": requirement["category"],
        "label": requirement["label"],
        "status": requirement["status"],
        "environment_key": requirement["environment_key"],
    }


def _profile_powershell(agent: dict) -> str:
    return f"""  [pscustomobject]@{{
    Id = "{_escape(agent['id'])}"
    Name = "{_escape(agent['name'])}"
    Command = "{_escape(agent['hermes_command'])}"
  }}"""


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
