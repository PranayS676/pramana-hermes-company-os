from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.llm_artifacts import provider_requirements


def llm_provisioning_payload(
    *,
    model_preferences: list[dict],
    secret_requirements: list[dict],
    integrations: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
) -> dict:
    llm_secret_status = {
        item["owner_agent_id"]: item["status"]
        for item in secret_requirements
        if item["category"] == "llm" and item["owner_agent_id"]
    }
    active_schedule_checks = [
        check for check in schedule_checks if check.get("schedule_active", 1)
    ]
    profiles = [
        _profile(preference, llm_secret_status.get(preference["agent_id"], "missing"))
        for preference in model_preferences
    ]
    return {
        "title": "LLM Provisioning Pack",
        "credential_boundary": (
            "This pack contains provider names, model names, expected environment "
            "key names, starter routes, and final verification commands only. It "
            "does not include provider API-key values, OAuth payloads, local "
            "endpoint secrets, Slack tokens, Telegram bot tokens, request headers, "
            "profile outputs, or raw logs."
        ),
        "verification_last": True,
        "last_phase_reason": (
            "LLM verification should happen after profiles, messaging, scheduling, "
            "and Kanban are ready enough to support real profile smoke checks."
        ),
        "profiles": profiles,
        "status": {
            "model_preferences": _status_counts(model_preferences),
            "llm_credentials": _status_counts(
                [
                    item
                    for item in secret_requirements
                    if item["category"] == "llm"
                ]
            ),
        },
        "prior_gates": {
            "messaging": _gate(messaging_checks),
            "schedule": _gate(active_schedule_checks),
            "kanban": _gate(kanban_checks),
            "llm_integration": _integration_status(integrations, "llm-provider"),
        },
        "runner": {
            "route": "/setup/llm-provisioning.ps1",
            "default_mode": "dry_run",
            "download_directory": ".\\llm-starters",
            "execute_actions": [
                "Download starter env/config files",
                "Run profile model pickers",
            ],
        },
        "entry_points": {
            "provider_presets": "/setup/llm-provider-presets.md",
            "credentials_matrix": "/setup/llm-credentials.md",
            "finalization": "/setup/llm-finalize.md",
            "finalization_runner": "/setup/llm-finalize.ps1",
            "secret_audit": "/setup/secret-audit.ps1",
            "smoke_drill": "/setup/llm-smoke.md",
            "profile_smoke": "/setup/profiles#profile-smoke",
            "profile_acceptance": "/setup/profile-acceptance.md",
        },
    }


def llm_provisioning_json(**kwargs) -> str:
    return json.dumps(llm_provisioning_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def llm_provisioning_markdown(**kwargs) -> str:
    payload = llm_provisioning_payload(**kwargs)
    lines = [
        "# LLM Provisioning Pack",
        "",
        "Use this only as the last setup phase, after profile creation, Slack, "
        "Telegram, scheduling, and Kanban are ready for live smoke checks.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Why Last",
        "",
        payload["last_phase_reason"],
        "",
        "## Runner",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/llm-provisioning.ps1 "
        "-OutFile .\\llm-provisioning.ps1",
        ".\\llm-provisioning.ps1",
        "```",
        "",
        "Default mode prints the profile/provider plan. Use `-Execute` only when "
        "you want to download no-secret starter files or run local model pickers.",
        "",
        "```powershell",
        ".\\llm-provisioning.ps1 -PrintProfiles",
        ".\\llm-provisioning.ps1 -DownloadStarters -Execute",
        ".\\llm-provisioning.ps1 -RunModelPicker -Execute",
        "```",
        "",
        "## Prior Gates",
        "",
        f"- Messaging: {_format_gate(payload['prior_gates']['messaging'])}",
        f"- Schedule: {_format_gate(payload['prior_gates']['schedule'])}",
        f"- Kanban: {_format_gate(payload['prior_gates']['kanban'])}",
        f"- LLM integration: `{payload['prior_gates']['llm_integration']}`",
        "",
        "## Entry Points",
        "",
    ]
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.extend(
        [
            "",
            "## Profile Matrix",
            "",
        ]
    )
    for profile in payload["profiles"]:
        lines.extend(
            [
                f"### {profile['agent_name']}",
                "",
                f"- Profile command: `{profile['hermes_command']}`",
                f"- Provider/model: `{profile['provider']}` / `{profile['model']}`",
                f"- Fallback: `{profile['fallback_provider'] or 'none'}` / "
                f"`{profile['fallback_model'] or 'none'}`",
                f"- Expected key names: {_inline_values(profile['expected_env_keys'])}",
                f"- Credential status: `{profile['credential_status']}`",
                f"- Model status: `{profile['model_status']}`",
                f"- Env starter: `{profile['env_starter']}`",
                f"- Config starter: `{profile['config_starter']}`",
                f"- Smoke route: `{profile['smoke_route']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Completion Criteria",
            "",
            "- Every expected provider key name is present in the real Hermes profile runtime.",
            "- `/setup/secret-audit.ps1 -AuditLlm` passes without printing values.",
            "- Every profile smoke check passes in `/setup/profiles#profile-smoke`.",
            "- Every model preference is marked `verified`.",
            "- Every LLM credential requirement is marked `verified`.",
            "- `llm-provider` integration status is `configured`.",
            "",
        ]
    )
    return "\n".join(lines)


def llm_provisioning_powershell(model_preferences: list[dict]) -> str:
    profile_block = "\n".join(
        _powershell_profile(_profile(preference, "unknown"))
        for preference in model_preferences
    )
    return f"""# Hermes Company OS LLM provisioning runner
# Generated by the dashboard. Review before running.
# Default mode is dry run. This script never prints provider credential values.

param(
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [string]$OutputDirectory = ".\\llm-starters",
  [switch]$PrintProfiles,
  [switch]$DownloadStarters,
  [switch]$RunModelPicker,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

$Profiles = @(
{profile_block}
)

Write-Host "LLM provisioning runner started."
if (-not $Execute) {{
  Write-Host "Dry run only. Add -Execute to download starters or run model pickers."
}}

if ($PrintProfiles -or (-not ($DownloadStarters -or $RunModelPicker))) {{
  Write-Host ""
  Write-Host "Profile provider matrix:"
  foreach ($profile in $Profiles) {{
    Write-Host "$($profile.AgentId): $($profile.Provider)/$($profile.Model)"
    Write-Host "  expected keys: $($profile.ExpectedKeys -join ', ')"
    Write-Host "  smoke route: $($profile.SmokeRoute)"
  }}
}}

if ($DownloadStarters) {{
  foreach ($profile in $Profiles) {{
    $profileDirectory = Join-Path $OutputDirectory $profile.AgentId
    if ($Execute) {{
      New-Item -ItemType Directory -Force -Path $profileDirectory | Out-Null
      Invoke-WebRequest -UseBasicParsing `
        -Uri "$DashboardBaseUrl$($profile.EnvStarter)" `
        -OutFile (Join-Path $profileDirectory "llm.env.example")
      Invoke-WebRequest -UseBasicParsing `
        -Uri "$DashboardBaseUrl$($profile.ConfigStarter)" `
        -OutFile (Join-Path $profileDirectory "config.yaml.example")
      Write-Host "DOWNLOADED $($profile.AgentId) starters"
    }} else {{
      Write-Host "DOWNLOAD $($profile.AgentId) -> $profileDirectory"
    }}
  }}
}}

if ($RunModelPicker) {{
  foreach ($profile in $Profiles) {{
    if ($Execute) {{
      Invoke-Expression "$($profile.HermesCommand) model"
    }} else {{
      Write-Host "MODEL    $($profile.HermesCommand) model"
    }}
  }}
}}

Write-Host "LLM provisioning runner finished."
Write-Host "Credentials still load outside this dashboard and verification remains last."
"""


def _profile(preference: dict, credential_status: str) -> dict:
    expected_keys = _expected_keys(preference)
    agent_id = preference["agent_id"]
    return {
        "agent_id": agent_id,
        "agent_name": preference["agent_name"],
        "hermes_command": preference["hermes_command"],
        "provider": preference["provider"],
        "model": preference["model"],
        "fallback_provider": preference["fallback_provider"],
        "fallback_model": preference["fallback_model"],
        "auth_method": preference["auth_method"],
        "expected_env_keys": expected_keys,
        "credential_status": credential_status,
        "model_status": preference["status"],
        "env_starter": f"/setup/profile-llm-env/{agent_id}.env",
        "config_starter": f"/setup/profile-config/{agent_id}.yaml",
        "model_picker_command": f"{preference['hermes_command']} model",
        "smoke_route": f"/setup/profile-smoke/{agent_id}",
    }


def _expected_keys(preference: dict) -> list[str]:
    keys = list(provider_requirements(preference["provider"])["env"])
    if preference.get("fallback_provider"):
        keys.extend(provider_requirements(preference["fallback_provider"])["env"])
    return list(dict.fromkeys(keys))


def _gate(checks: list[dict]) -> dict:
    return {
        "ready": bool(checks) and all(check["status"] == "verified" for check in checks),
        "status": _status_counts(checks),
        "total": len(checks),
    }


def _integration_status(integrations: list[dict], integration_id: str) -> str:
    for integration in integrations:
        if integration["id"] == integration_id:
            return integration["status"]
    return "missing"


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_gate(gate: dict) -> str:
    status = _format_counts(gate["status"])
    return f"ready={gate['ready']}, total={gate['total']}, status={status}"


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _inline_values(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _powershell_profile(profile: dict) -> str:
    keys = ", ".join(f'"{_escape(key)}"' for key in profile["expected_env_keys"])
    return f"""  [pscustomobject]@{{
    AgentId = "{_escape(profile['agent_id'])}"
    AgentName = "{_escape(profile['agent_name'])}"
    HermesCommand = "{_escape(profile['hermes_command'])}"
    Provider = "{_escape(profile['provider'])}"
    Model = "{_escape(profile['model'])}"
    ExpectedKeys = @({keys})
    EnvStarter = "{_escape(profile['env_starter'])}"
    ConfigStarter = "{_escape(profile['config_starter'])}"
    SmokeRoute = "{_escape(profile['smoke_route'])}"
  }}"""


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
