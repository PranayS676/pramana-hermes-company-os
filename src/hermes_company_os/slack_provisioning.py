from __future__ import annotations

import json
import re

from hermes_company_os.slack_workspace import slack_workspace_matrix

SLACK_DOCS = {
    "conversations_create": "https://docs.slack.dev/reference/methods/conversations.create",
    "conversations_invite": "https://docs.slack.dev/reference/methods/conversations.invite",
    "apps": "https://api.slack.com/apps",
}


def slack_provisioning_payload(*, agents: list[dict], setup_values: dict[str, str]) -> dict:
    channels = [
        _provisioning_channel(row)
        for row in slack_workspace_matrix(agents, setup_values)
    ]
    return {
        "title": "Slack Provisioning Pack",
        "credential_boundary": (
            "This pack contains Slack channel names, bot display names, app manifest "
            "routes, and command/API shapes only. It does not store Slack bot tokens, "
            "Slack app tokens, admin tokens, OAuth payloads, request headers, or logs. "
            "The PowerShell runner reads any execution token from a local environment "
            "variable only when explicitly run with -Execute."
        ),
        "workspace": setup_values.get("slack_workspace_name", ""),
        "founder_member_id_captured": bool(
            setup_values.get("founder_slack_member_id", "").strip()
        ),
        "channels": channels,
        "required_missing_channel_ids": [
            channel["input_key"]
            for channel in channels
            if channel["required"] and not channel["channel_id"]
        ],
        "bot_user_map_template": slack_bot_user_map_template(agents, setup_values),
        "runner": {
            "route": "/setup/slack-provisioning.ps1",
            "default_mode": "dry_run",
            "token_environment_key": "HERMES_SLACK_ADMIN_TOKEN",
            "bot_user_map_path": ".\\slack-bot-user-map.json",
            "post_dashboard_inputs": (
                "post created Slack channel IDs to /setup/inputs when explicitly enabled"
            ),
        },
        "entry_points": {
            "slack_plan": "/setup/slack-plan.md",
            "slack_manifests": "/setup/slack-manifests.json",
            "slack_workspace": "/setup/slack-workspace.md",
            "channel_template": "/setup/slack-channel-template.md",
            "invite_matrix_json": "/setup/slack-invite-matrix.json",
            "invite_matrix_csv": "/setup/slack-invite-matrix.csv",
            "bot_user_map": "/setup/slack-bot-user-map.json",
            "messaging_verification": "/setup#messaging-verification",
            "gateway_operations": "/setup/gateway-operations.md",
        },
        "official_docs": SLACK_DOCS,
    }


def slack_provisioning_json(**kwargs) -> str:
    return json.dumps(slack_provisioning_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def slack_bot_user_input_key(agent_id: str) -> str:
    return f"slack_bot_user_id_{agent_id.replace('-', '_')}"


def slack_bot_user_map_template(
    agents: list[dict],
    setup_values: dict[str, str] | None = None,
) -> dict:
    setup_values = setup_values or {}
    return {
        agent["id"]: setup_values.get(slack_bot_user_input_key(agent["id"]), "").strip()
        or f"U_REPLACE_WITH_{_constant_name(agent['name'])}_BOT_USER_ID"
        for agent in agents
    }


def slack_bot_user_map_template_json(
    agents: list[dict],
    setup_values: dict[str, str] | None = None,
) -> str:
    return (
        json.dumps(
            slack_bot_user_map_template(agents, setup_values),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def slack_provisioning_markdown(**kwargs) -> str:
    payload = slack_provisioning_payload(**kwargs)
    lines = [
        "# Slack Provisioning Pack",
        "",
        "Use this after reviewing the Slack app manifests and before Slack gateway "
        "verification. It keeps the separate-bot profile design but gives you one "
        "place to create channels, collect channel IDs, and invite profile bots.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Runner",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/slack-provisioning.ps1 "
        "-OutFile .\\slack-provisioning.ps1",
        ".\\slack-provisioning.ps1",
        "```",
        "",
        "Default mode prints the channel create and invite plan only. To call Slack "
        "Web API methods, load a Slack admin/user token into your local shell, keep "
        "bot user IDs in `slack-bot-user-map.json`, then run with `-Execute`.",
        "",
        "```powershell",
        ".\\slack-provisioning.ps1 -CreateChannels -Execute",
        ".\\slack-provisioning.ps1 -CreateChannels -Execute -PostDashboardInputs",
        ".\\slack-provisioning.ps1 -InviteBots -Execute",
        "```",
        "",
        "Add `-PostDashboardInputs` after successful channel creation to store returned "
        "Slack channel IDs in the safe dashboard input ledger.",
        "",
        "## Required Local Files",
        "",
        "- Bot user ID map template: `/setup/slack-bot-user-map.json`",
        "- Combined app manifest review: `/setup/slack-manifests.json`",
        "",
        "## Channels",
        "",
    ]
    for channel in payload["channels"]:
        channel_id = channel["channel_id"] or "not captured"
        required = "required" if channel["required"] else "optional"
        bot_names = ", ".join(bot["bot_display_name"] for bot in channel["bots"])
        lines.extend(
            [
                f"### {channel['channel_name']}",
                "",
                f"- API name: `{channel['api_name']}`",
                f"- Status: `{required}`",
                f"- Channel ID: `{channel_id}`",
                f"- Dashboard input: `{channel['input_key']}`",
                f"- Purpose: {channel['purpose']}",
                f"- Bots: {bot_names or 'none'}",
                "",
                "```text",
                *channel["manual_invite_commands"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Verification",
            "",
            "- Channel IDs returned by Slack are pasted into `/setup#inputs`.",
            "- Every separate profile app is installed in the Slack workspace.",
            "- Every profile bot user ID is copied into the local bot map if using API invites.",
            "- Every listed bot is invited to its required channels.",
            "- Slack gateway, DM, and channel mention checks are completed in "
            "`/setup#messaging-verification`.",
            "",
            "## Official Slack References",
            "",
            f"- conversations.create: {payload['official_docs']['conversations_create']}",
            f"- conversations.invite: {payload['official_docs']['conversations_invite']}",
            f"- App management: {payload['official_docs']['apps']}",
            "",
        ]
    )
    return "\n".join(lines)


def slack_provisioning_powershell(
    *,
    agents: list[dict],
    setup_values: dict[str, str],
) -> str:
    channels = [
        _powershell_channel(channel)
        for channel in slack_provisioning_payload(
            agents=agents,
            setup_values=setup_values,
        )["channels"]
    ]
    channel_block = "\n".join(channels)
    return f"""# Hermes Company OS Slack provisioning runner
# Generated by the dashboard. Review before running.
# Default mode is dry run. No token values are printed.

param(
  [switch]$CreateChannels,
  [switch]$InviteBots,
  [switch]$Execute,
  [string]$TokenEnvironmentKey = "HERMES_SLACK_ADMIN_TOKEN",
  [string]$BotUserMapPath = ".\\slack-bot-user-map.json",
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$PostDashboardInputs
)

$ErrorActionPreference = "Stop"

$Channels = @(
{channel_block}
)

function Get-LocalSlackToken {{
  $token = [Environment]::GetEnvironmentVariable($TokenEnvironmentKey)
  if ([string]::IsNullOrWhiteSpace($token)) {{
    throw "Missing local Slack token environment variable: $TokenEnvironmentKey"
  }}
  return $token
}}

function Invoke-SlackApi {{
  param(
    [string]$Method,
    [hashtable]$Body,
    [string]$Token
  )
  $response = Invoke-RestMethod `
    -Uri "https://slack.com/api/$Method" `
    -Method Post `
    -Headers @{{ Authorization = "Bearer $Token" }} `
    -ContentType "application/json; charset=utf-8" `
    -Body ($Body | ConvertTo-Json -Compress)
  if (-not $response.ok) {{
    throw "Slack API $Method failed: $($response.error)"
  }}
  return $response
}}

function Get-BotUserId {{
  param(
    [object]$BotUserMap,
    [string]$ProfileId
  )
  if ($null -eq $BotUserMap) {{
    return ""
  }}
  $property = $BotUserMap.PSObject.Properties[$ProfileId]
  if ($null -eq $property) {{
    return ""
  }}
  return [string]$property.Value
}}

Write-Host "Slack provisioning runner started."
if (-not $Execute) {{
  Write-Host "Dry run only. Add -Execute to call Slack Web API methods."
}}
if ($PostDashboardInputs -and -not $Execute) {{
  Write-Host "Dashboard input posting is skipped in dry-run mode."
}}

$token = ""
if ($Execute) {{
  $token = Get-LocalSlackToken
}}

function Post-DashboardInput {{
  param(
    [string]$Key,
    [string]$Value
  )
  if ([string]::IsNullOrWhiteSpace($Key) -or [string]::IsNullOrWhiteSpace($Value)) {{
    return
  }}
  $uri = "$DashboardBaseUrl/setup/inputs"
  $body = @{{}}
  $body[$Key] = $Value
  try {{
    Invoke-WebRequest `
      -UseBasicParsing `
      -Method Post `
      -Uri $uri `
      -ContentType "application/x-www-form-urlencoded" `
      -Body $body | Out-Null
    Write-Host "DASHBOARD input $Key=$Value"
  }} catch {{
    Write-Host "DASHBOARD skipped input ${{Key}}: $($_.Exception.Message)"
  }}
}}

if ($CreateChannels) {{
  foreach ($channel in $Channels) {{
    if (-not [string]::IsNullOrWhiteSpace($channel.ChannelId)) {{
      Write-Host "SKIP    $($channel.Name) channel ID already captured"
      continue
    }}
    if ($Execute) {{
      $response = Invoke-SlackApi `
        -Method "conversations.create" `
        -Token $token `
        -Body @{{ name = $channel.ApiName; is_private = $false }}
      Write-Host "CREATED $($channel.Name) id=$($response.channel.id)"
      if ($PostDashboardInputs) {{
        Post-DashboardInput -Key $channel.InputKey -Value $response.channel.id
      }}
    }} else {{
      Write-Host "CREATE  conversations.create name=$($channel.ApiName)"
    }}
  }}
}}

Write-Host ""
Write-Host "Manual Slack invite commands:"
foreach ($channel in $Channels) {{
  Write-Host "[$($channel.Name)]"
  foreach ($bot in $channel.Bots) {{
    Write-Host "/invite @$($bot.BotDisplayName)"
  }}
}}

if ($InviteBots) {{
  if (-not (Test-Path -LiteralPath $BotUserMapPath -PathType Leaf)) {{
    Write-Host "DEFER  bot user map missing: $BotUserMapPath"
  }} else {{
    $botUserMap = Get-Content -LiteralPath $BotUserMapPath -Raw | ConvertFrom-Json
    foreach ($channel in $Channels) {{
      if ([string]::IsNullOrWhiteSpace($channel.ChannelId)) {{
        Write-Host "DEFER  $($channel.Name) channel ID missing"
        continue
      }}
      $userIds = @()
      foreach ($bot in $channel.Bots) {{
        $userId = Get-BotUserId $botUserMap $bot.ProfileId
        if ([string]::IsNullOrWhiteSpace($userId)) {{
          Write-Host "DEFER  $($channel.Name) missing user ID for $($bot.ProfileId)"
        }} else {{
          $userIds += $userId
        }}
      }}
      if ($userIds.Count -eq 0) {{
        continue
      }}
      if ($Execute) {{
        Invoke-SlackApi `
          -Method "conversations.invite" `
          -Token $token `
          -Body @{{ channel = $channel.ChannelId; users = ($userIds -join ",") }} `
          | Out-Null
        Write-Host "INVITED $($channel.Name) users=$($userIds.Count)"
      }} else {{
        $message = "INVITE  conversations.invite channel=$($channel.ChannelId) "
        $message += "users=$($userIds.Count)"
        Write-Host $message
      }}
    }}
  }}
}}

Write-Host "Slack provisioning runner finished. Token values were not printed."
"""


def _provisioning_channel(row: dict) -> dict:
    return {
        "channel_name": row["channel_name"],
        "api_name": _api_channel_name(row["channel_name"]),
        "channel_id": row["channel_id"],
        "input_key": row["input_key"],
        "required": row["required"],
        "purpose": row["purpose"],
        "bots": row["bots"],
        "manual_invite_commands": row["invite_commands"],
        "create_method": "conversations.create",
        "invite_method": "conversations.invite",
    }


def _api_channel_name(channel_name: str) -> str:
    cleaned = channel_name.strip().removeprefix("#").lower()
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", cleaned)
    return re.sub(r"-+", "-", cleaned).strip("-")[:80]


def _powershell_channel(channel: dict) -> str:
    bots = "\n".join(_powershell_bot(bot) for bot in channel["bots"])
    required = "$true" if channel["required"] else "$false"
    return f"""  [pscustomobject]@{{
    Name = "{_escape(channel['channel_name'])}"
    ApiName = "{_escape(channel['api_name'])}"
    ChannelId = "{_escape(channel['channel_id'])}"
    InputKey = "{_escape(channel['input_key'])}"
    Required = {required}
    Purpose = "{_escape(channel['purpose'])}"
    Bots = @(
{bots}
    )
  }}"""


def _powershell_bot(bot: dict) -> str:
    return f"""      [pscustomobject]@{{
        ProfileId = "{_escape(bot['profile_id'])}"
        BotDisplayName = "{_escape(bot['bot_display_name'])}"
        HermesCommand = "{_escape(bot['hermes_command'])}"
      }}"""


def _constant_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return re.sub(r"_+", "_", cleaned).upper()


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
