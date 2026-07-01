from __future__ import annotations

import json
from collections import Counter

BOARD_LANES = [
    {
        "id": "intake",
        "name": "Intake",
        "purpose": "Founder requests and newly created workflow items before routing.",
        "default_status": "planned",
    },
    {
        "id": "research",
        "name": "Research",
        "purpose": "Market, competitor, customer, and technical evidence gathering.",
        "default_status": "in_progress",
    },
    {
        "id": "product",
        "name": "Product",
        "purpose": "PRDs, scope choices, user workflows, and less-is-more decisions.",
        "default_status": "in_progress",
    },
    {
        "id": "engineering",
        "name": "Engineering",
        "purpose": "Architecture, backend, frontend, cloud, AWS, and testing work.",
        "default_status": "in_progress",
    },
    {
        "id": "qa-review",
        "name": "QA Review",
        "purpose": "Risk review, contradiction checks, and missing-test review.",
        "default_status": "review",
    },
    {
        "id": "marketing",
        "name": "Marketing",
        "purpose": "Positioning, messaging, launch plans, and campaign tasks.",
        "default_status": "in_progress",
    },
    {
        "id": "founder-decision",
        "name": "Founder Decision",
        "purpose": "Explicit founder approvals, tradeoffs, and blocked decisions.",
        "default_status": "blocked",
    },
    {
        "id": "done",
        "name": "Done",
        "purpose": "Completed and accepted project work.",
        "default_status": "done",
    },
    {
        "id": "blocked",
        "name": "Blocked",
        "purpose": "Tasks blocked by external accounts, credentials, or founder input.",
        "default_status": "blocked",
    },
]

PHASE_LANE_MAP = {
    "research": "research",
    "product": "product",
    "engineering": "engineering",
    "quality": "qa-review",
    "marketing": "marketing",
    "founder": "founder-decision",
}


def kanban_provisioning_payload(
    *,
    workflow_templates: list[dict],
    kanban_checks: list[dict],
    tasks: list[dict],
) -> dict:
    linked_tasks = [task for task in tasks if task.get("kanban_task_id")]
    waiting_tasks = [task for task in tasks if not task.get("kanban_task_id")]
    return {
        "title": "Kanban Provisioning Pack",
        "credential_boundary": (
            "This pack contains board lanes, workflow mappings, local task counts, "
            "and Hermes Kanban command shapes only. It does not include Slack tokens, "
            "Telegram bot tokens, provider API keys, private founder credentials, "
            "or raw run logs."
        ),
        "board": {
            "name": "Hermes Company OS",
            "lanes": BOARD_LANES,
            "source_of_truth": "Hermes Kanban after activation; SQLite before activation.",
        },
        "workflow_mapping": [
            _workflow_mapping(template) for template in workflow_templates
        ],
        "current_local_tasks": {
            "total": len(tasks),
            "linked_to_kanban": len(linked_tasks),
            "waiting_for_push": len(waiting_tasks),
            "status": dict(Counter(task["status"] for task in tasks)),
            "waiting": [_task(task) for task in waiting_tasks[:20]],
        },
        "verification": {
            "ready": bool(kanban_checks)
            and all(check["status"] == "verified" for check in kanban_checks),
            "status": dict(Counter(check["status"] for check in kanban_checks)),
            "checks": [_check(check) for check in kanban_checks],
        },
        "runner": {
            "route": "/setup/kanban-provisioning.ps1",
            "default_mode": "dry_run",
            "commands": {
                "init": "hermes kanban init",
                "diagnostics": "hermes kanban diagnostics --json",
                "post_dashboard_status": (
                    "post verified status to "
                    "/setup/kanban-checks/kanban-board-initialized"
                ),
            },
        },
        "entry_points": {
            "kanban_runbook": "/setup/kanban-runbook.md",
            "kanban_diagnostics": "/setup/kanban-diagnostics.ps1",
            "project_workflow": "/setup/project-workflow.md",
            "project_workflow_json": "/setup/project-workflow.json",
            "kanban_verification": "/setup/verification#kanban-verification",
            "projects": "/projects",
        },
    }


def kanban_provisioning_json(**kwargs) -> str:
    return json.dumps(kanban_provisioning_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def kanban_provisioning_markdown(**kwargs) -> str:
    payload = kanban_provisioning_payload(**kwargs)
    task_counts = payload["current_local_tasks"]
    lines = [
        "# Kanban Provisioning Pack",
        "",
        "Use this before the first real founder idea to prepare the Hermes Kanban "
        "board shape and verify the local handoff contract.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Runner",
        "",
        "```powershell",
        "Invoke-WebRequest -UseBasicParsing "
        "http://127.0.0.1:8002/setup/kanban-provisioning.ps1 "
        "-OutFile .\\kanban-provisioning.ps1",
        ".\\kanban-provisioning.ps1",
        "```",
        "",
        "Default mode prints the board and workflow plan. Use `-Execute` only after "
        "Hermes is installed and you want to run local Kanban init or diagnostics.",
        "",
        "```powershell",
        ".\\kanban-provisioning.ps1 -InitBoard -Execute",
        ".\\kanban-provisioning.ps1 -InitBoard -Execute -PostDashboardStatus",
        ".\\kanban-provisioning.ps1 -RunDiagnostics -Execute",
        ".\\kanban-provisioning.ps1 -PrintWorkflow",
        "```",
        "",
        "Add `-PostDashboardStatus` after a successful board init to mark "
        "`kanban-board-initialized` verified with no-secret evidence.",
        "",
        "## Board Lanes",
        "",
    ]
    for lane in payload["board"]["lanes"]:
        lines.extend(
            [
                f"### {lane['name']}",
                "",
                f"- Lane ID: `{lane['id']}`",
                f"- Default status: `{lane['default_status']}`",
                f"- Purpose: {lane['purpose']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Workflow Mapping",
            "",
        ]
    )
    for item in payload["workflow_mapping"]:
        lines.append(
            f"- `{item['template_id']}` -> `{item['lane_id']}`: "
            f"{item['template_name']} owned by {item['owner_agent_name']}"
        )
    lines.extend(
        [
            "",
            "## Current Local Task Linkage",
            "",
            f"- Total local tasks: {task_counts['total']}",
            f"- Linked to Hermes Kanban: {task_counts['linked_to_kanban']}",
            f"- Waiting for push: {task_counts['waiting_for_push']}",
            "",
            "## Completion Criteria",
            "",
            "- `hermes kanban init` runs successfully.",
            "- `hermes kanban diagnostics --json` passes.",
            "- The first project workflow creates local tasks and documents.",
            "- One dashboard task push receives a remote Hermes Kanban task ID.",
            "- `/setup/verification#kanban-verification` checks are all `verified`.",
            "",
        ]
    )
    return "\n".join(lines)


def kanban_provisioning_powershell(
    *,
    workflow_templates: list[dict],
) -> str:
    workflow_block = "\n".join(
        _powershell_workflow_item(_workflow_mapping(template))
        for template in workflow_templates
    )
    lane_block = "\n".join(_powershell_lane(lane) for lane in BOARD_LANES)
    return f"""# Hermes Company OS Kanban provisioning runner
# Generated by the dashboard. Review before running.
# Default mode is dry run. This script contains no tokens or provider credentials.

param(
  [switch]$InitBoard,
  [switch]$RunDiagnostics,
  [switch]$PrintWorkflow,
  [switch]$Execute,
  [string]$DashboardBaseUrl = "http://127.0.0.1:8002",
  [switch]$PostDashboardStatus
)

$ErrorActionPreference = "Stop"

$BoardLanes = @(
{lane_block}
)

$WorkflowMapping = @(
{workflow_block}
)

Write-Host "Kanban provisioning runner started."
if (-not $Execute) {{
  Write-Host "Dry run only. Add -Execute to run Hermes Kanban commands."
}}
if ($PostDashboardStatus -and -not $Execute) {{
  Write-Host "Dashboard status posting is skipped in dry-run mode."
}}

function Post-KanbanBoardInitializedStatus {{
  $uri = "$DashboardBaseUrl/setup/kanban-checks/kanban-board-initialized"
  $body = @{{
    status = "verified"
    evidence = "Kanban provisioning runner confirmed hermes kanban init."
  }}
  try {{
    Invoke-WebRequest `
      -UseBasicParsing `
      -Method Post `
      -Uri $uri `
      -ContentType "application/x-www-form-urlencoded" `
      -Body $body | Out-Null
    Write-Host "DASHBOARD verified kanban-board-initialized"
  }} catch {{
    Write-Host "DASHBOARD skipped kanban-board-initialized: $($_.Exception.Message)"
  }}
}}

Write-Host ""
Write-Host "Board lanes:"
foreach ($lane in $BoardLanes) {{
  Write-Host "$($lane.Id) -> $($lane.Name) [$($lane.DefaultStatus)]"
}}

if ($PrintWorkflow -or (-not ($InitBoard -or $RunDiagnostics))) {{
  Write-Host ""
  Write-Host "Workflow mapping:"
  foreach ($item in $WorkflowMapping) {{
    Write-Host "$($item.TemplateId) -> $($item.LaneId) owner=$($item.OwnerAgentId)"
  }}
}}

if ($InitBoard) {{
  if ($Execute) {{
    hermes kanban init
    if ($PostDashboardStatus) {{
      Post-KanbanBoardInitializedStatus
    }}
  }} else {{
    Write-Host "INIT    hermes kanban init"
  }}
}}

if ($RunDiagnostics) {{
  if ($Execute) {{
    hermes kanban diagnostics --json
  }} else {{
    Write-Host "CHECK   hermes kanban diagnostics --json"
  }}
}}

Write-Host "Kanban provisioning runner finished."
"""


def _workflow_mapping(template: dict) -> dict:
    phase = template["phase"]
    lane_id = PHASE_LANE_MAP.get(phase, "intake")
    return {
        "template_id": template["id"],
        "template_name": template["name"],
        "phase": phase,
        "lane_id": lane_id,
        "owner_agent_id": template["owner_agent_id"],
        "owner_agent_name": template.get("owner_name", template["owner_agent_id"]),
        "priority": template["priority"],
        "doc_type": template["doc_type"],
    }


def _task(task: dict) -> dict:
    return {
        "id": task["id"],
        "title": task["title"],
        "owner_agent_id": task["owner_agent_id"],
        "owner_name": task.get("owner_name", task["owner_agent_id"]),
        "status": task["status"],
        "priority": task["priority"],
    }


def _check(check: dict) -> dict:
    return {
        "id": check["id"],
        "label": check["label"],
        "check_type": check["check_type"],
        "status": check["status"],
        "has_evidence": bool(check.get("evidence", "").strip()),
    }


def _powershell_lane(lane: dict) -> str:
    return f"""  [pscustomobject]@{{
    Id = "{_escape(lane['id'])}"
    Name = "{_escape(lane['name'])}"
    DefaultStatus = "{_escape(lane['default_status'])}"
  }}"""


def _powershell_workflow_item(item: dict) -> str:
    return f"""  [pscustomobject]@{{
    TemplateId = "{_escape(item['template_id'])}"
    LaneId = "{_escape(item['lane_id'])}"
    OwnerAgentId = "{_escape(item['owner_agent_id'])}"
    Priority = "{_escape(item['priority'])}"
  }}"""


def _escape(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')
