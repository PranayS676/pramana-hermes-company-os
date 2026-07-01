from __future__ import annotations


def kanban_runbook_markdown(
    checks: list[dict],
    workflow_templates: list[dict],
    tasks: list[dict],
) -> str:
    linked_tasks = [task for task in tasks if task.get("kanban_task_id")]
    unlinked_tasks = [task for task in tasks if not task.get("kanban_task_id")]
    lines = [
        "# Hermes Kanban Setup Runbook",
        "",
        "Hermes Kanban is the shared execution board for profile work. The dashboard "
        "keeps local task planning in SQLite, then pushes approved work to real Hermes "
        "Kanban with idempotency keys.",
        "",
        "## Setup Order",
        "",
        "1. Create Hermes profiles and starter profile artifacts.",
        "2. Run `/setup/kanban-diagnostics.ps1` locally.",
        "3. Use the dashboard `Kanban diagnostics` button in "
        "`/setup/verification#kanban-verification`.",
        "4. Create a dashboard task or project workflow.",
        "5. Push one task to Hermes Kanban and confirm a remote task ID appears.",
        "6. Mark remaining Kanban verification checks with non-secret evidence.",
        "",
        "## Local Commands",
        "",
        "```powershell",
        "hermes kanban init",
        "hermes kanban diagnostics --json",
        "```",
        "",
        "## Dashboard Verification Checks",
        "",
    ]
    if checks:
        for check in checks:
            lines.extend(
                [
                    f"- `{_safe_identifier(check['id'])}`: {check['label']}",
                    f"  Status: `{check['status']}`",
                    f"  Evidence: {check['evidence'] or 'not recorded'}",
                ]
            )
    else:
        lines.append("- No Kanban verification checks are configured.")
    lines.extend(
        [
            "",
            "## Workflow Templates That Push To Kanban",
            "",
        ]
    )
    for template in workflow_templates:
        owner = (
            template.get("owner_name")
            or template.get("owner_agent_name")
            or template["owner_agent_id"]
        )
        lines.append(
            f"- `{_safe_identifier(template['id'])}`: {template['name']} -> {owner}"
        )
    lines.extend(
        [
            "",
            "## Current Local Task Linkage",
            "",
            f"- Linked to Hermes Kanban: {len(linked_tasks)}",
            f"- Waiting for Kanban push: {len(unlinked_tasks)}",
            "",
        ]
    )
    if unlinked_tasks:
        lines.append("### Waiting For Push")
        lines.append("")
        for task in unlinked_tasks[:10]:
            lines.append(
                f"- `{_safe_identifier(task['id'])}`: {task['title']} -> {task['owner_name']}"
            )
        if len(unlinked_tasks) > 10:
            lines.append(f"- ...and {len(unlinked_tasks) - 10} more")
        lines.append("")
    lines.extend(
        [
            "## Completion Criteria",
            "",
            "- `hermes kanban init` has been run successfully.",
            "- `hermes kanban diagnostics --json` passes locally and from the dashboard.",
            "- At least one dashboard task has a remote Hermes Kanban task ID.",
            "- `/setup/verification#kanban-verification` checks are all `verified`.",
            "- `hermes-kanban` integration status is `configured`.",
            "",
            "## No-Secret Rule",
            "",
            "Kanban setup should not require Slack, Telegram, or LLM provider tokens. "
            "Do not paste provider keys or bot tokens into task titles, summaries, "
            "verification evidence, or project ideas.",
            "",
        ]
    )
    return "\n".join(lines)


def _safe_identifier(value: str) -> str:
    return value.replace("sk-", "sk_").replace("xoxb-", "xoxb_").replace("xapp-", "xapp_")


def kanban_diagnostics_powershell() -> str:
    return "\n".join(
        [
            "# Hermes Company OS Kanban diagnostics",
            "# Run locally after Hermes is installed and profiles are created.",
            "# This script contains no tokens or provider credentials.",
            "",
            "hermes kanban init",
            "hermes kanban diagnostics --json",
            "",
        ]
    )
