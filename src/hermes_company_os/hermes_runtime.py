from __future__ import annotations

import json

OFFICIAL_DOCS_URL = (
    "https://github.com/NousResearch/hermes-agent/blob/main/"
    "website/docs/getting-started/installation.md"
)
OFFICIAL_QUICKSTART_URL = (
    "https://hermes-agent.nousresearch.com/docs/getting-started/quickstart"
)
UPSTREAM_REPO_URL = "https://github.com/NousResearch/hermes-agent"
WINDOWS_INSTALL_COMMAND = "iex (irm https://hermes-agent.nousresearch.com/install.ps1)"
UNIX_INSTALL_COMMAND = "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"


def hermes_runtime_payload() -> dict:
    return {
        "title": "Hermes Runtime Connect",
        "credential_boundary": (
            "This packet only explains how to install or connect the Hermes runtime. "
            "It does not request, store, print, or transmit Slack tokens, Telegram "
            "tokens, provider API keys, OAuth payloads, profile logs, or live .env "
            "contents."
        ),
        "source": {
            "upstream_repo": UPSTREAM_REPO_URL,
            "official_install_docs": OFFICIAL_DOCS_URL,
            "official_quickstart": OFFICIAL_QUICKSTART_URL,
        },
        "decision": {
            "normal_operation": (
                "Install Hermes as the runtime dependency, then connect this dashboard "
                "to the resulting `hermes` command and profile aliases."
            ),
            "clone_repo_only_when": [
                "You want to modify Hermes core behavior.",
                "You want to debug Hermes itself from source.",
                "You want to contribute a Hermes upstream pull request.",
                "You need repo-local Hermes tooling for a plugin or distribution.",
            ],
            "do_not_vendor_into_dashboard": True,
        },
        "install_options": [
            {
                "id": "windows-desktop",
                "label": "Windows desktop installer",
                "recommended_for": "Native Windows 10/11 with desktop UI.",
                "command": "Download and run the Hermes Desktop installer.",
                "verify": "hermes doctor",
            },
            {
                "id": "windows-cli",
                "label": "Windows command-line install",
                "recommended_for": "Native Windows PowerShell CLI setup.",
                "command": WINDOWS_INSTALL_COMMAND,
                "verify": "hermes doctor",
            },
            {
                "id": "wsl-linux-cli",
                "label": "WSL2/Linux/macOS command-line install",
                "recommended_for": "WSL2, Linux, macOS, or service-user CLI setup.",
                "command": UNIX_INSTALL_COMMAND,
                "verify": "hermes doctor",
            },
        ],
        "post_install_sequence": [
            "Download `/setup/hermes-install.ps1` and run it first without flags.",
            "If the printed command is correct, rerun it with `-RunInstall`.",
            "Open a new shell so PATH changes are visible.",
            "Run `hermes doctor` and resolve any reported runtime issues.",
            "Run `/setup/runtime-preflight.ps1` from this dashboard.",
            "Run `/setup/bootstrap.ps1` or per-profile apply scripts.",
            "Run `/setup/profile-installation.ps1` and import the no-secret audit output.",
            "Continue Slack, Telegram, Kanban, scheduling, then final LLM verification.",
        ],
        "entry_points": {
            "installer_runner": "/setup/hermes-install.ps1",
            "runtime_preflight": "/setup/runtime-preflight.md",
            "runtime_preflight_runner": "/setup/runtime-preflight.ps1",
            "bootstrap": "/setup/bootstrap.ps1",
            "profile_installation": "/setup/profile-installation.md",
            "profile_installation_runner": "/setup/profile-installation.ps1",
            "activation_runner": "/setup/activation-runner.ps1",
        },
    }


def hermes_runtime_json() -> str:
    return json.dumps(hermes_runtime_payload(), indent=2, sort_keys=True) + "\n"


def hermes_runtime_markdown() -> str:
    payload = hermes_runtime_payload()
    lines = [
        "# Hermes Runtime Connect",
        "",
        "Use this packet to resolve the current `Hermes CLI` runtime gate before "
        "profile installation, Slack, Telegram, Kanban, scheduling, or final LLM "
        "verification.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Why We Do Not Clone By Default",
        "",
        payload["decision"]["normal_operation"],
        "",
        "Clone `NousResearch/hermes-agent` only when:",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["decision"]["clone_repo_only_when"])
    lines.extend(
        [
            "",
            "For normal company operation, keep Hermes installed as the runtime "
            "dependency and keep this dashboard as the founder operating layer.",
            "",
            "## Official Sources",
            "",
            f"- Upstream repo: {payload['source']['upstream_repo']}",
            f"- Install docs: {payload['source']['official_install_docs']}",
            f"- Quickstart: {payload['source']['official_quickstart']}",
            "",
            "## Guarded Installer Helper",
            "",
            "Download `/setup/hermes-install.ps1` when you want the dashboard to "
            "hand you the official install command. It prints the command by "
            "default and only runs it when `-RunInstall` is passed.",
            "",
            "```powershell",
            "Invoke-WebRequest -UseBasicParsing "
            "http://127.0.0.1:8002/setup/hermes-install.ps1 "
            "-OutFile .\\hermes-install.ps1",
            ".\\hermes-install.ps1",
            ".\\hermes-install.ps1 -RunInstall",
            "```",
            "",
            "## Install Options",
            "",
        ]
    )
    for option in payload["install_options"]:
        lines.extend(
            [
                f"### {option['label']}",
                "",
                f"- Recommended for: {option['recommended_for']}",
                f"- Command: `{option['command']}`",
                f"- Verify: `{option['verify']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Post-Install Sequence",
            "",
        ]
    )
    for index, step in enumerate(payload["post_install_sequence"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(
        [
            "",
            "## Dashboard Entry Points",
            "",
        ]
    )
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def hermes_install_powershell() -> str:
    return f"""# Hermes runtime installer helper
# Generated by Hermes Company OS. Dry-run by default; no credentials are read or stored.

param(
  [ValidateSet("NativeWindows", "WslLinux")]
  [string]$Mode = "NativeWindows",
  [switch]$RunInstall
)

$ErrorActionPreference = "Stop"

$WindowsCommand = '{WINDOWS_INSTALL_COMMAND}'
$UnixCommand = '{UNIX_INSTALL_COMMAND}'

Write-Host "Hermes runtime installer helper"
Write-Host "Mode: $Mode"
Write-Host "RunInstall: $RunInstall"
Write-Host ""
Write-Host "Credential boundary: this script does not ask for tokens, API keys,"
Write-Host "OAuth payloads, or profile .env values."
Write-Host ""

if ($Mode -eq "NativeWindows") {{
  Write-Host "Official Windows PowerShell install command:"
  Write-Host $WindowsCommand
  if ($RunInstall) {{
    Write-Host ""
    Write-Host "Running official Windows installer..."
    Invoke-Expression $WindowsCommand
  }} else {{
    Write-Host ""
    Write-Host "Dry run only. Rerun with -RunInstall when you are ready."
  }}
}} else {{
  Write-Host "Official WSL/Linux/macOS install command:"
  Write-Host $UnixCommand
  if ($RunInstall) {{
    $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
    if (-not $wsl) {{
      throw "wsl.exe was not found. Use -Mode NativeWindows or install manually."
    }}
    Write-Host ""
    Write-Host "Running official installer through WSL..."
    wsl.exe bash -lc $UnixCommand
  }} else {{
    Write-Host ""
    Write-Host "Dry run only. Rerun with -Mode WslLinux -RunInstall when you are ready."
  }}
}}

Write-Host ""
Write-Host "After install:"
Write-Host "1. Open a new shell so PATH changes are visible."
Write-Host "2. Run: hermes doctor"
Write-Host "3. Run: .\\runtime-preflight.ps1"
"""
