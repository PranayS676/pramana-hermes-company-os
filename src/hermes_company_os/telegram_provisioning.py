from __future__ import annotations

import json

from hermes_company_os.telegram_artifacts import (
    TELEGRAM_COMMANDS,
    suggested_bot_username,
)

TELEGRAM_BOT_API_DOCS = "https://core.telegram.org/bots/api"


def telegram_provisioning_payload(
    *,
    setup_values: dict[str, str],
) -> dict:
    founder_user = setup_values.get("founder_telegram_user_id", "")
    home_chat = setup_values.get("telegram_home_channel", "") or founder_user
    return {
        "title": "Telegram Provisioning Pack",
        "credential_boundary": (
            "This pack contains BotFather setup guidance, Bot API method names, "
            "bot command descriptions, and a local runner shape only. It does not "
            "store Telegram bot tokens, request headers, webhook secrets, chat "
            "history, message logs, or provider credentials. The runner reads a "
            "token from a local environment variable only when explicitly run with "
            "-Execute."
        ),
        "owner_profile": "chief-of-staff",
        "bot_identity": {
            "display_name": "Hermes Chief of Staff",
            "suggested_username": suggested_bot_username(setup_values),
            "purpose": "Urgent founder alerts for approvals, blockers, and failed runs.",
        },
        "founder_telegram_user_id": founder_user,
        "telegram_home_chat": home_chat,
        "founder_user_id_captured": bool(founder_user.strip()),
        "home_chat_captured": bool(home_chat.strip()),
        "commands": [
            {"command": command, "description": description}
            for command, description in TELEGRAM_COMMANDS
        ],
        "bot_api_methods": {
            "check_bot": "getMe",
            "register_commands": "setMyCommands",
            "send_test": "sendMessage",
        },
        "runner": {
            "route": "/setup/telegram-provisioning.ps1",
            "default_mode": "dry_run",
            "token_environment_key": "HERMES_TELEGRAM_BOT_TOKEN",
            "chat_id_argument": "ChatId",
            "post_dashboard_status": (
                "post verified status to "
                "/setup/messaging-checks/chief-of-staff-telegram-urgent-alert"
            ),
        },
        "entry_points": {
            "telegram_plan": "/setup/telegram-plan.md",
            "botfather": "/setup/telegram-botfather.md",
            "recipient_template": "/setup/telegram-recipient-template.md",
            "telegram_policy": "/setup/telegram-policy.md",
            "telegram_policy_json": "/setup/telegram-policy.json",
            "messaging_verification": "/setup#messaging-verification",
            "gateway_operations": "/setup/gateway-operations.md",
        },
        "official_docs": {
            "bot_api": TELEGRAM_BOT_API_DOCS,
            "methods": [
                "getMe",
                "setMyCommands",
                "sendMessage",
            ],
        },
    }


def telegram_provisioning_json(**kwargs) -> str:
    return json.dumps(telegram_provisioning_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def telegram_provisioning_markdown(**kwargs) -> str:
    payload = telegram_provisioning_payload(**kwargs)
    founder_user = payload["founder_telegram_user_id"] or "not captured"
    home_chat = payload["telegram_home_chat"] or "not captured"
    lines = [
        "# Telegram Provisioning Pack",
        "",
        "Use this after creating the Chief of Staff bot in BotFather and before "
        "Telegram urgent-alert verification. It keeps Telegram urgent-only and "
        "Chief-of-Staff-owned.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Runner",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/telegram-provisioning.ps1 "
        "-OutFile .\\telegram-provisioning.ps1",
        ".\\telegram-provisioning.ps1",
        "```",
        "",
        "Default mode prints the Bot API plan only. To call Telegram, load the bot "
        "token into your local shell environment, pass `-Execute`, and provide the "
        "founder or home chat ID when sending a test.",
        "",
        "```powershell",
        ".\\telegram-provisioning.ps1 -CheckBot -Execute",
        ".\\telegram-provisioning.ps1 -RegisterCommands -Execute",
        ".\\telegram-provisioning.ps1 -SendTest -ChatId <chat_id> -Execute",
        ".\\telegram-provisioning.ps1 -SendTest -ChatId <chat_id> -Execute "
        "-PostDashboardStatus",
        "```",
        "",
        "Add `-PostDashboardStatus` after a successful urgent send test to mark the "
        "Chief of Staff Telegram alert check verified. The dashboard still requires "
        "the external Telegram credential status to be loaded first.",
        "",
        "## Bot Identity",
        "",
        f"- Display name: `{payload['bot_identity']['display_name']}`",
        f"- Suggested username: `{payload['bot_identity']['suggested_username']}`",
        "- Owner profile: `chief-of-staff`",
        f"- Founder Telegram user ID: `{founder_user}`",
        f"- Home chat: `{home_chat}`",
        "",
        "## Bot API Methods",
        "",
        f"- Check bot identity: `{payload['bot_api_methods']['check_bot']}`",
        f"- Register commands: `{payload['bot_api_methods']['register_commands']}`",
        f"- Send optional urgent test: `{payload['bot_api_methods']['send_test']}`",
        "",
        "## Commands",
        "",
        "```text",
        *[
            f"{command['command']} - {command['description']}"
            for command in payload["commands"]
        ],
        "```",
        "",
        "## Verification",
        "",
        "- BotFather bot exists and the token is loaded only in the local shell or "
        "Chief of Staff Hermes profile environment.",
        "- `getMe` succeeds.",
        "- `setMyCommands` succeeds for the command list above.",
        "- Optional urgent test sends one short founder alert to the configured chat.",
        "- Routine updates still stay in Slack only.",
        "- `/setup#messaging-verification` records non-secret evidence for the "
        "Chief of Staff Telegram urgent-alert check.",
        "",
        "## Official Reference",
        "",
        f"- Telegram Bot API: {payload['official_docs']['bot_api']}",
        "",
    ]
    return "\n".join(lines)


def telegram_provisioning_powershell(
    *,
    setup_values: dict[str, str],
) -> str:
    payload = telegram_provisioning_payload(setup_values=setup_values)
    commands = "\n".join(_powershell_command(command) for command in payload["commands"])
    default_chat = _escape(payload["telegram_home_chat"])
    return f"""# Hermes Company OS Telegram provisioning runner
# Generated by the dashboard. Review before running.
# Default mode is dry run. No token values are printed.

param(
  [switch]$CheckBot,
  [switch]$RegisterCommands,
  [switch]$SendTest,
  [switch]$Execute,
  [string]$TokenEnvironmentKey = "HERMES_TELEGRAM_BOT_TOKEN",
  [string]$ChatId = "{default_chat}",
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$PostDashboardStatus
)

$ErrorActionPreference = "Stop"

$Commands = @(
{commands}
)

function Get-LocalTelegramToken {{
  $token = [Environment]::GetEnvironmentVariable($TokenEnvironmentKey)
  if ([string]::IsNullOrWhiteSpace($token)) {{
    throw "Missing local Telegram token environment variable: $TokenEnvironmentKey"
  }}
  return $token
}}

function Invoke-TelegramApi {{
  param(
    [string]$Method,
    [hashtable]$Body,
    [string]$Token
  )
  $uri = "https://api.telegram.org/bot$Token/$Method"
  $request = @{{
    Uri = $uri
    Method = "Post"
    ContentType = "application/json; charset=utf-8"
  }}
  if ($null -ne $Body) {{
    $request.Body = $Body | ConvertTo-Json -Depth 8 -Compress
  }}
  $response = Invoke-RestMethod @request
  if (-not $response.ok) {{
    throw "Telegram Bot API $Method failed"
  }}
  return $response
}}

Write-Host "Telegram provisioning runner started."
if (-not $Execute) {{
  Write-Host "Dry run only. Add -Execute to call Telegram Bot API methods."
}}
if ($PostDashboardStatus -and -not $Execute) {{
  Write-Host "Dashboard status posting is skipped in dry-run mode."
}}

$token = ""
if ($Execute) {{
  $token = Get-LocalTelegramToken
}}

function Post-TelegramUrgentAlertStatus {{
  $uri = "$DashboardBaseUrl/setup/messaging-checks/chief-of-staff-telegram-urgent-alert"
  $body = @{{
    status = "verified"
    evidence = "Telegram provisioning runner sent urgent founder alert test."
  }}
  try {{
    Invoke-WebRequest `
      -UseBasicParsing `
      -Method Post `
      -Uri $uri `
      -ContentType "application/x-www-form-urlencoded" `
      -Body $body | Out-Null
    Write-Host "DASHBOARD verified chief-of-staff-telegram-urgent-alert"
  }} catch {{
    Write-Host "DASHBOARD skipped chief-of-staff-telegram-urgent-alert: $($_.Exception.Message)"
  }}
}}

if ($CheckBot) {{
  if ($Execute) {{
    $response = Invoke-TelegramApi -Method "getMe" -Token $token -Body $null
    Write-Host "CHECKED getMe username=$($response.result.username)"
  }} else {{
    Write-Host "CHECK   getMe"
  }}
}}

if ($RegisterCommands) {{
  if ($Execute) {{
    Invoke-TelegramApi `
      -Method "setMyCommands" `
      -Token $token `
      -Body @{{ commands = $Commands }} `
      | Out-Null
    Write-Host "COMMANDS registered count=$($Commands.Count)"
  }} else {{
    Write-Host "COMMANDS setMyCommands count=$($Commands.Count)"
  }}
}}

if ($SendTest) {{
  if ([string]::IsNullOrWhiteSpace($ChatId)) {{
    Write-Host "DEFER   ChatId is required for sendMessage"
  }} elseif ($Execute) {{
    Invoke-TelegramApi `
      -Method "sendMessage" `
      -Token $token `
      -Body @{{
        chat_id = $ChatId
        text = "URGENT TEST: Hermes Chief of Staff Telegram alert path is configured."
        disable_web_page_preview = $true
      }} `
      | Out-Null
    Write-Host "SENT    sendMessage chat_id=$ChatId"
    if ($PostDashboardStatus) {{
      Post-TelegramUrgentAlertStatus
    }}
  }} else {{
    Write-Host "SEND    sendMessage chat_id=$ChatId"
  }}
}}

if (-not ($CheckBot -or $RegisterCommands -or $SendTest)) {{
  Write-Host "Plan:"
  Write-Host "- getMe checks token and bot identity."
  Write-Host "- setMyCommands registers urgent founder commands."
  Write-Host "- sendMessage can send one optional urgent test to the founder/home chat."
}}

Write-Host "Telegram provisioning runner finished. Token values were not printed."
"""


def _powershell_command(command: dict) -> str:
    return f"""  [pscustomobject]@{{
    command = "{_escape(command['command'])}"
    description = "{_escape(command['description'])}"
  }}"""


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
