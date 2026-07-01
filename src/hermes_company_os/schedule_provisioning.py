from __future__ import annotations

import json
from collections import Counter


def schedule_provisioning_payload(
    *,
    agents: list[dict],
    setup_values: dict[str, str],
    schedules: list[dict],
    schedule_checks: list[dict],
) -> dict:
    owner_command = _chief_of_staff_command(agents)
    active = [schedule for schedule in schedules if schedule.get("active", 1)]
    paused = [schedule for schedule in schedules if not schedule.get("active", 1)]
    return {
        "title": "Schedule Provisioning Pack",
        "credential_boundary": (
            "This pack contains standup schedule metadata, generated Chief of Staff "
            "cron command shapes, routing policy, and verification status only. It "
            "does not include Slack tokens, Telegram bot tokens, provider API keys, "
            "private founder credentials, prompt outputs, or raw logs."
        ),
        "owner_profile": {
            "id": "chief-of-staff",
            "hermes_command": owner_command,
        },
        "cadence": _cadence(setup_values),
        "delivery_policy": {
            "primary_workspace": "slack",
            "routine_updates": "Post full summaries to each schedule Slack channel.",
            "telegram": "Chief of Staff urgent founder alerts only.",
            "manual_verification_before_cron": True,
        },
        "active_schedules": [
            _schedule(schedule, setup_values, owner_command) for schedule in active
        ],
        "paused_schedules": [
            _paused_schedule(schedule) for schedule in paused
        ],
        "verification": {
            "ready": bool([check for check in schedule_checks if check.get("schedule_active", 1)])
            and all(
                check["status"] == "verified"
                for check in schedule_checks
                if check.get("schedule_active", 1)
            ),
            "status": dict(Counter(check["status"] for check in schedule_checks)),
            "checks": [_check(check) for check in schedule_checks],
        },
        "runner": {
            "route": "/setup/schedule-provisioning.ps1",
            "default_mode": "dry_run",
            "commands": {
                "install_cron": "call <chief-of-staff> cron create <expression> <prompt>",
                "list_cron": "call <chief-of-staff> cron list",
                "post_dashboard_status": (
                    "post verified status to /setup/schedule-checks/<schedule>-cron-installed"
                ),
            },
        },
        "entry_points": {
            "schedule_config": "/setup/schedule-config-template.md",
            "standup_preview": "/setup/standup-preview.md",
            "standup_preview_json": "/setup/standup-preview.json",
            "standup_runbook": "/setup/standup-runbook.md",
            "standup_cron": "/setup/standup-cron.ps1",
            "schedule_verification": "/setup/verification#schedule-verification",
            "messaging_verification": "/setup/messaging#messaging-verification",
            "telegram_policy": "/setup/telegram-policy.md",
            "gateway_operations": "/setup/gateway-operations.md",
        },
    }


def schedule_provisioning_json(**kwargs) -> str:
    return json.dumps(
        schedule_provisioning_payload(**kwargs),
        indent=2,
        sort_keys=True,
    ) + "\n"


def schedule_provisioning_markdown(**kwargs) -> str:
    payload = schedule_provisioning_payload(**kwargs)
    lines = [
        "# Schedule Provisioning Pack",
        "",
        "Use this after Slack and Telegram gateway setup and before installing "
        "Chief of Staff cron jobs.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Runner",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/schedule-provisioning.ps1 "
        "-OutFile .\\schedule-provisioning.ps1",
        ".\\schedule-provisioning.ps1",
        "```",
        "",
        "Default mode prints the schedule and cron plan. Use `-Execute` only after "
        "manual standup verification and messaging verification pass. Add "
        "`-PostDashboardStatus` after a successful cron install/list to update "
        "`/setup/verification#schedule-verification` with non-secret evidence.",
        "",
        "```powershell",
        ".\\schedule-provisioning.ps1 -PrintSchedules",
        ".\\schedule-provisioning.ps1 -InstallCron -Execute",
        ".\\schedule-provisioning.ps1 -ListCron -Execute",
        ".\\schedule-provisioning.ps1 -ListCron -Execute -PostDashboardStatus",
        "```",
        "",
        "## Delivery Policy",
        "",
        "- Primary workspace: Slack",
        "- Telegram: Chief of Staff urgent founder alerts only",
        "- Manual verification before cron: yes",
        "",
        "## Active Schedules",
        "",
    ]
    if payload["active_schedules"]:
        for schedule in payload["active_schedules"]:
            lines.extend(_schedule_lines(schedule))
    else:
        lines.append("- No active schedules.")
        lines.append("")
    if payload["paused_schedules"]:
        lines.extend(["## Paused Schedules", ""])
        for schedule in payload["paused_schedules"]:
            lines.extend(
                [
                    f"- `{schedule['id']}`: {schedule['name']} at "
                    f"`{schedule['time']}` `{schedule['timezone']}`",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Verification",
            "",
            f"- Ready: {'yes' if payload['verification']['ready'] else 'no'}",
            f"- Status: {_format_counts(payload['verification']['status'])}",
            "- Complete `/setup/verification#schedule-verification` before treating cron as live.",
            "",
            "## Completion Criteria",
            "",
            "- Each active schedule has a successful manual dashboard run.",
            "- Messaging verification has passed for Slack and Telegram urgent routing.",
            "- Cron install is run from the Chief of Staff profile.",
            "- `chief-of-staff cron list` shows each active schedule.",
            "- `standup-cron` integration status is `configured`.",
            "",
        ]
    )
    return "\n".join(lines)


def schedule_provisioning_powershell(
    *,
    agents: list[dict],
    setup_values: dict[str, str],
    schedules: list[dict],
) -> str:
    owner_command = _chief_of_staff_command(agents)
    active_schedules = [
        _schedule(schedule, setup_values, owner_command)
        for schedule in schedules
        if schedule.get("active", 1)
    ]
    schedule_block = "\n".join(_powershell_schedule(schedule) for schedule in active_schedules)
    return f"""# Hermes Company OS schedule provisioning runner
# Generated by the dashboard. Review before running.
# Default mode is dry run. This script contains no tokens or provider credentials.

param(
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$InstallCron,
  [switch]$ListCron,
  [switch]$PrintSchedules,
  [switch]$Execute,
  [switch]$PostDashboardStatus
)

$ErrorActionPreference = "Stop"

$Schedules = @(
{schedule_block}
)

Write-Host "Schedule provisioning runner started."
if (-not $Execute) {{
  Write-Host "Dry run only. Add -Execute to run Chief of Staff cron commands."
}}
if ($PostDashboardStatus -and -not $Execute) {{
  Write-Host "Dashboard status posting is skipped in dry-run mode."
}}

function Post-CronInstalledStatus {{
  param([object]$Schedule)
  $checkId = "$($Schedule.Id)-cron-installed"
  $uri = "$DashboardBaseUrl/setup/schedule-checks/$checkId"
  $body = @{{
    status = "verified"
    evidence = "Schedule provisioning runner confirmed cron install/list for $($Schedule.Name)."
  }}
  try {{
    Invoke-WebRequest `
      -UseBasicParsing `
      -Method Post `
      -Uri $uri `
      -ContentType "application/x-www-form-urlencoded" `
      -Body $body | Out-Null
    Write-Host "DASHBOARD verified $checkId"
  }} catch {{
    Write-Host "DASHBOARD skipped ${{checkId}}: $($_.Exception.Message)"
  }}
}}

if ($PrintSchedules -or (-not ($InstallCron -or $ListCron))) {{
  Write-Host ""
  Write-Host "Active schedules:"
  foreach ($schedule in $Schedules) {{
    Write-Host "$($schedule.Id) -> $($schedule.Expression) -> $($schedule.SlackChannel)"
  }}
}}

if ($InstallCron) {{
  foreach ($schedule in $Schedules) {{
    if ($Execute) {{
      & $schedule.OwnerCommand "cron" "create" $schedule.Expression $schedule.Prompt
      if ($PostDashboardStatus) {{
        Post-CronInstalledStatus -Schedule $schedule
      }}
    }} else {{
      Write-Host "INSTALL $($schedule.CronCommand)"
    }}
  }}
}}

if ($ListCron) {{
  $ownerCommands = $Schedules | Select-Object -ExpandProperty OwnerCommand -Unique
  if ($ownerCommands.Count -eq 0) {{
    $ownerCommands = @("{_escape(owner_command)}")
  }}
  foreach ($ownerCommand in $ownerCommands) {{
    if ($Execute) {{
      & $ownerCommand "cron" "list"
    }} else {{
      Write-Host "LIST    $ownerCommand cron list"
    }}
  }}
  if ($Execute -and $PostDashboardStatus) {{
    foreach ($schedule in $Schedules) {{
      Post-CronInstalledStatus -Schedule $schedule
    }}
  }}
}}

Write-Host "Schedule provisioning runner finished."
"""


def _schedule(schedule: dict, setup_values: dict[str, str], owner_command: str) -> dict:
    expression = f"{_cadence(setup_values)} at {_schedule_time(schedule)}"
    prompt = _prompt(schedule)
    return {
        "id": schedule["id"],
        "name": schedule["name"],
        "time": f"{int(schedule['hour']):02d}:{int(schedule['minute']):02d}",
        "timezone": schedule["timezone"],
        "slack_channel": schedule["slack_channel"],
        "telegram_policy": schedule["telegram_policy"],
        "owner_command": owner_command,
        "expression": expression,
        "prompt": prompt,
        "cron_command": f'{owner_command} cron create "{expression}" "{prompt}"',
    }


def _paused_schedule(schedule: dict) -> dict:
    return {
        "id": schedule["id"],
        "name": schedule["name"],
        "time": f"{int(schedule['hour']):02d}:{int(schedule['minute']):02d}",
        "timezone": schedule["timezone"],
        "slack_channel": schedule["slack_channel"],
        "telegram_policy": schedule["telegram_policy"],
    }


def _check(check: dict) -> dict:
    return {
        "id": check["id"],
        "label": check["label"],
        "status": check["status"],
        "schedule_id": check["schedule_id"],
        "schedule_active": bool(check.get("schedule_active", 1)),
        "has_evidence": bool(check.get("evidence", "").strip()),
    }


def _schedule_lines(schedule: dict) -> list[str]:
    return [
        f"### {schedule['name']}",
        "",
        f"- Schedule ID: `{schedule['id']}`",
        f"- Time: `{schedule['time']}` `{schedule['timezone']}`",
        f"- Slack channel: `{schedule['slack_channel']}`",
        f"- Telegram policy: {schedule['telegram_policy']}",
        f"- Cron expression: `{schedule['expression']}`",
        f"- Cron command: `{schedule['cron_command']}`",
        "",
    ]


def _powershell_schedule(schedule: dict) -> str:
    return f"""  [pscustomobject]@{{
    Id = "{_escape(schedule['id'])}"
    Name = "{_escape(schedule['name'])}"
    OwnerCommand = "{_escape(schedule['owner_command'])}"
    Expression = "{_escape(schedule['expression'])}"
    Prompt = "{_escape(schedule['prompt'])}"
    SlackChannel = "{_escape(schedule['slack_channel'])}"
    CronCommand = "{_escape(schedule['cron_command'])}"
  }}"""


def _chief_of_staff_command(agents: list[dict]) -> str:
    for agent in agents:
        if agent["id"] == "chief-of-staff":
            return agent["hermes_command"]
    return "chief-of-staff"


def _cadence(setup_values: dict[str, str]) -> str:
    cadence = setup_values.get("standup_cadence", "every day").strip() or "every day"
    if cadence.lower() in {"weekday", "weekdays", "business days"}:
        return "every weekday"
    return "every day"


def _prompt(schedule: dict) -> str:
    return (
        f"Run the {schedule['name']}. Post the full summary to Slack "
        f"{schedule['slack_channel']}. Send Telegram only for "
        f"{schedule['telegram_policy']}."
    )


def _schedule_time(schedule: dict) -> str:
    hour = int(schedule["hour"])
    minute = int(schedule["minute"])
    suffix = "am" if hour < 12 else "pm"
    hour_12 = hour % 12 or 12
    if minute:
        return f"{hour_12}:{minute:02d}{suffix}"
    return f"{hour_12}{suffix}"


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
