from __future__ import annotations

import json
import re
from collections import Counter


def project_workflow_payload(
    *,
    workflow_templates: list[dict],
    kanban_checks: list[dict],
    tasks: list[dict],
) -> dict:
    linked_tasks = [task for task in tasks if task.get("kanban_task_id")]
    waiting_tasks = [task for task in tasks if not task.get("kanban_task_id")]
    return {
        "title": "Project Workflow And Kanban Handoff",
        "credential_boundary": (
            "This handoff contains workflow templates, local task linkage, and Kanban "
            "command mapping only. It does not include Slack tokens, Telegram bot tokens, "
            "provider API keys, or private founder credentials."
        ),
        "operating_boundary": {
            "project_creation": "Creates local SQLite tasks and draft documents first.",
            "kanban_push": "Explicit founder action pushes unlinked local tasks to Hermes Kanban.",
            "idempotency": "The local task ID is the Kanban idempotency key.",
            "assignee": "The workflow template owner_agent_id becomes the Kanban assignee.",
        },
        "kanban_readiness": {
            "ready": bool(kanban_checks)
            and all(check["status"] == "verified" for check in kanban_checks),
            "status": _status_counts(kanban_checks),
            "checks": [_check(check) for check in kanban_checks],
        },
        "templates": [_template(template) for template in workflow_templates],
        "current_local_tasks": {
            "total": len(tasks),
            "linked_to_kanban": len(linked_tasks),
            "waiting_for_push": len(waiting_tasks),
            "waiting": [_task(task) for task in waiting_tasks[:20]],
        },
        "kanban_create_shape": {
            "command": "hermes kanban create <task title> --assignee <owner_agent_id> "
            "--idempotency-key <local_task_id> --json",
            "body_source": "local task summary generated from workflow prompt_template",
            "remote_id_storage": "tasks.kanban_task_id",
        },
        "drill": [
            {
                "step": 1,
                "action": "Create a project from `/projects` with a placeholder idea.",
                "expected": "Local workflow tasks and draft documents are created.",
            },
            {
                "step": 2,
                "action": "Review the generated tasks and owner agents.",
                "expected": (
                    "Research, product, engineering, QA, marketing, and "
                    "founder-decision work exist."
                ),
            },
            {
                "step": 3,
                "action": "Run Kanban diagnostics before pushing.",
                "expected": "`/setup/verification#kanban-verification` "
                "records diagnostics as verified.",
            },
            {
                "step": 4,
                "action": "Push the project workflow to Kanban.",
                "expected": "Every unlinked local task receives a remote Hermes Kanban task ID.",
            },
        ],
        "entry_points": {
            "projects": "/projects",
            "kanban_runbook": "/setup/kanban-runbook.md",
            "kanban_diagnostics": "/setup/kanban-diagnostics.ps1",
            "kickoff_readiness": "/setup/kickoff-readiness.md",
        },
    }


def project_workflow_json(**kwargs) -> str:
    return json.dumps(project_workflow_payload(**kwargs), indent=2, sort_keys=True)


def project_workflow_markdown(**kwargs) -> str:
    payload = project_workflow_payload(**kwargs)
    task_counts = payload["current_local_tasks"]
    lines = [
        "# Project Workflow And Kanban Handoff",
        "",
        "Use this before the first real founder idea to inspect the workflow that "
        "will be created locally and then pushed to Hermes Kanban.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Operating Boundary",
        "",
    ]
    for label, detail in payload["operating_boundary"].items():
        lines.append(f"- {label}: {detail}")
    lines.extend(
        [
            "",
            "## Kanban Readiness",
            "",
            f"- Ready: {'yes' if payload['kanban_readiness']['ready'] else 'no'}",
            f"- Status: {_format_counts(payload['kanban_readiness']['status'])}",
            "",
            "## Workflow Templates",
            "",
        ]
    )
    for template in payload["templates"]:
        lines.extend(
            [
                f"### {template['name']}",
                "",
                f"- Phase: `{template['phase']}`",
                f"- Owner: {template['owner_name']} (`{template['owner_agent_id']}`)",
                f"- Priority: `{template['priority']}`",
                f"- Document type: `{template['doc_type']}`",
                f"- Title template: {template['title_template']}",
                "- Kanban mapping: title -> task title, prompt -> body, "
                "owner_agent_id -> assignee, local task ID -> idempotency key",
                "",
            ]
        )
    lines.extend(
        [
            "## Current Local Task Linkage",
            "",
            f"- Total local tasks: {task_counts['total']}",
            f"- Linked to Hermes Kanban: {task_counts['linked_to_kanban']}",
            f"- Waiting for push: {task_counts['waiting_for_push']}",
            "",
        ]
    )
    if task_counts["waiting"]:
        lines.extend(["### Waiting For Push", ""])
        for task in task_counts["waiting"]:
            lines.append(
                f"- `{task['id']}`: {task['title']} -> {task['owner_name']} "
                f"({task['priority']})"
            )
        lines.append("")
    lines.extend(
        [
            "## Kanban Create Shape",
            "",
            f"- Command: `{payload['kanban_create_shape']['command']}`",
            f"- Body source: {payload['kanban_create_shape']['body_source']}",
            f"- Remote ID storage: `{payload['kanban_create_shape']['remote_id_storage']}`",
            "",
            "## Drill",
            "",
        ]
    )
    for item in payload["drill"]:
        lines.append(f"{item['step']}. {item['action']} Expected: {item['expected']}")
    lines.append("")
    return "\n".join(lines)


def _template(template: dict) -> dict:
    return {
        "id": template["id"],
        "name": template["name"],
        "phase": template["phase"],
        "owner_agent_id": template["owner_agent_id"],
        "owner_name": template.get("owner_name", template["owner_agent_id"]),
        "sort_order": template["sort_order"],
        "doc_type": template["doc_type"],
        "priority": template["priority"],
        "title_template": _safe_text(template["title_template"]),
        "prompt_template": _safe_text(template["prompt_template"]),
    }


def _task(task: dict) -> dict:
    return {
        "id": _safe_text(task["id"]),
        "title": _safe_text(task["title"]),
        "owner_agent_id": task["owner_agent_id"],
        "owner_name": task.get("owner_name", task["owner_agent_id"]),
        "status": task["status"],
        "priority": task["priority"],
        "kanban_task_id_present": bool(task.get("kanban_task_id")),
    }


def _check(check: dict) -> dict:
    return {
        "id": check["id"],
        "label": check["label"],
        "check_type": check["check_type"],
        "status": check["status"],
        "has_evidence": bool(check.get("evidence", "").strip()),
    }


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _safe_text(value: str) -> str:
    cleaned = re.sub(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{16,}", "sk_REDACTED", value)
    cleaned = re.sub(r"xoxb-[A-Za-z0-9-]{12,}", "xoxb_REDACTED", cleaned)
    return re.sub(r"xapp-[A-Za-z0-9-]{12,}", "xapp_REDACTED", cleaned)
