from __future__ import annotations

import json
from collections import defaultdict

from hermes_company_os.focused_setup_imports import (
    focused_setup_entry_points,
    focused_setup_imports,
    focused_setup_markdown_lines,
)


def founder_input_request_markdown(
    setup_inputs: list[dict],
    secret_requirements: list[dict],
) -> str:
    safe_inputs = [
        item for item in setup_inputs if item["secret_policy"] == "non_secret"
    ]
    deferred_inputs = [
        item for item in setup_inputs if item["secret_policy"] != "non_secret"
    ]
    focused_imports = focused_setup_imports()
    lines = [
        "# Founder Input Request",
        "",
        "Use this packet to collect only values that are safe to store in the "
        "Hermes Company OS dashboard. Do not paste bot tokens, API keys, OAuth "
        "payloads, private endpoint credentials, or full logs here.",
        "",
        "## Reply Template",
        "",
        "```text",
    ]
    for item in safe_inputs:
        required = "required" if item["required"] else "optional"
        value = item["value"].strip() or ""
        lines.append(f"{item['key']}={value}  # {item['label']} ({required})")
    lines.extend(
        [
            "```",
            "",
            "## Safe Dashboard Inputs",
            "",
        ]
    )
    grouped = _group_by(safe_inputs, "group_name")
    for group_name in sorted(grouped):
        lines.extend([f"### {group_name.title()}", ""])
        for item in grouped[group_name]:
            status = "captured" if item["value"].strip() else "missing"
            required = "required" if item["required"] else "optional"
            lines.extend(
                [
                    f"- `{item['key']}`: {item['label']}",
                    f"  Status: `{status}`",
                    f"  Requirement: `{required}`",
                    f"  Guidance: {item['help_text']}",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Deferred Non-Secret Preferences",
            "",
        ]
    )
    if deferred_inputs:
        for item in deferred_inputs:
            lines.append(f"- `{item['key']}`: {item['label']}. {item['help_text']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## External Secrets To Load Later",
            "",
        ]
    )
    lines.extend(_external_secret_lines(secret_requirements))
    lines.extend(
        [
            "",
            "## Where To Enter Values",
            "",
            "- Paste completed reply template: `/setup/inputs#input-import`",
            "- Safe dashboard inputs: `/setup/inputs#inputs`",
            "- External credential status only: `/setup/messaging#secret-status`",
            "- Final verification after credentials are loaded: `/setup/live-verification.md`",
            "",
            "## Focused Setup Reply Templates",
            "",
            *focused_setup_markdown_lines(focused_imports),
            "",
        ]
    )
    return "\n".join(lines)


def founder_input_request_json(
    setup_inputs: list[dict],
    secret_requirements: list[dict],
) -> str:
    payload = {
        "safe_dashboard_inputs": [
            {
                "key": item["key"],
                "group": item["group_name"],
                "label": item["label"],
                "value": item["value"],
                "required": bool(item["required"]),
                "status": "captured" if item["value"].strip() else "missing",
                "help_text": item["help_text"],
            }
            for item in setup_inputs
            if item["secret_policy"] == "non_secret"
        ],
        "deferred_preferences": [
            {
                "key": item["key"],
                "group": item["group_name"],
                "label": item["label"],
                "status": "captured" if item["value"].strip() else "deferred",
                "help_text": item["help_text"],
            }
            for item in setup_inputs
            if item["secret_policy"] != "non_secret"
        ],
        "external_secret_status": [
            {
                "category": item["category"],
                "label": item["label"],
                "owner": item.get("owner_name") or item.get("owner_agent_id") or "",
                "destination": item["destination"],
                "status": item["status"],
            }
            for item in secret_requirements
        ],
        "focused_setup_imports": focused_setup_imports(),
        "entry_points": {
            "reply_import": "/setup/inputs#input-import",
            "collector_script": "/setup/founder-inputs.ps1",
            "safe_inputs": "/setup/inputs#inputs",
            "secret_status_only": "/setup/messaging#secret-status",
            "live_verification": "/setup/live-verification.md",
            **focused_setup_entry_points(),
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def founder_input_collector_powershell(setup_inputs: list[dict]) -> str:
    safe_inputs = [
        item for item in setup_inputs if item["secret_policy"] == "non_secret"
    ]
    input_block = "\n".join(_powershell_input(item) for item in safe_inputs)
    return f"""# Hermes Company OS founder input collector
# Generated by the dashboard. Prompts only for safe, non-secret setup values.

param(
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$IncludeOptional,
  [switch]$PostDashboardInputs
)

$ErrorActionPreference = "Stop"

$Inputs = @(
{input_block}
)

function Assert-SafeValue {{
  param(
    [string]$Key,
    [string]$Value
  )
  if ([string]::IsNullOrWhiteSpace($Value)) {{
    return
  }}
  if ($Value -match "(?i)(token|secret|password|credential)\\s*=") {{
    throw "Refusing to collect secret-looking assignment for $Key."
  }}
  if ($Value -match "(?i)(api[_-]?key|oauth|bearer)") {{
    throw "Refusing to collect secret-looking value for $Key."
  }}
}}

$Lines = @()

foreach ($inputItem in $Inputs) {{
  if (-not $inputItem.Required -and -not $IncludeOptional) {{
    continue
  }}

  $current = if ($inputItem.Current) {{ " [$($inputItem.Current)]" }} else {{ "" }}
  Write-Host ""
  Write-Host "$($inputItem.Label)$current"
  Write-Host "$($inputItem.HelpText)"
  $value = Read-Host $inputItem.Key
  if ([string]::IsNullOrWhiteSpace($value)) {{
    $value = $inputItem.Current
  }}
  Assert-SafeValue -Key $inputItem.Key -Value $value
  if (-not [string]::IsNullOrWhiteSpace($value)) {{
    $Lines += "$($inputItem.Key)=$value"
  }}
}}

$ReplyText = $Lines -join "`n"
Write-Host ""
Write-Host "Safe founder input reply:"
Write-Host '```text'
Write-Host $ReplyText
Write-Host '```'

if ($PostDashboardInputs) {{
  if ([string]::IsNullOrWhiteSpace($ReplyText)) {{
    Write-Host "No values captured; nothing to post."
  }} else {{
    $body = @{{ reply_text = $ReplyText }}
    Invoke-WebRequest `
      -UseBasicParsing `
      -Method Post `
      -Uri "$DashboardBaseUrl/setup/founder-input-reply" `
      -Body $body | Out-Null
    Write-Host "Posted safe inputs to $DashboardBaseUrl/setup/founder-input-reply"
  }}
}}
"""


def _external_secret_lines(secret_requirements: list[dict]) -> list[str]:
    if not secret_requirements:
        return ["- None tracked."]
    grouped = _group_by(secret_requirements, "category")
    lines: list[str] = []
    for category in sorted(grouped):
        lines.extend([f"### {category.title()}", ""])
        for item in grouped[category]:
            owner = item.get("owner_name") or item.get("owner_agent_id") or "unassigned"
            lines.append(
                f"- `{item['status']}` {item['label']} for {owner}: "
                f"load externally into {item['destination']}"
            )
        lines.append("")
    return lines


def _group_by(items: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[str(item[key])].append(item)
    return grouped


def _powershell_input(item: dict) -> str:
    required = "$true" if item["required"] else "$false"
    return f"""  [pscustomobject]@{{
    Key = "{_escape_powershell(item['key'])}"
    Label = "{_escape_powershell(item['label'])}"
    Group = "{_escape_powershell(item['group_name'])}"
    Required = {required}
    Current = "{_escape_powershell(item['value'])}"
    HelpText = "{_escape_powershell(item['help_text'])}"
  }}"""


def _escape_powershell(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
