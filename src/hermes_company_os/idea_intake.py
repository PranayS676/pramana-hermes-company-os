from __future__ import annotations

import json
import re

IDEA_FIELDS = [
    {
        "key": "project_name",
        "label": "Project name",
        "required": True,
        "help_text": "Short working name for the company idea.",
    },
    {
        "key": "founder_idea",
        "label": "Founder idea",
        "required": True,
        "help_text": "Plain-English description of the product, customer, and outcome.",
    },
    {
        "key": "target_customer",
        "label": "Target customer",
        "required": False,
        "help_text": "Who should buy or use this first.",
    },
    {
        "key": "problem",
        "label": "Problem",
        "required": False,
        "help_text": "The painful workflow or missed opportunity this should solve.",
    },
    {
        "key": "current_alternatives",
        "label": "Current alternatives",
        "required": False,
        "help_text": "How customers solve this today, including manual workarounds.",
    },
    {
        "key": "why_now",
        "label": "Why now",
        "required": False,
        "help_text": "Timing, market, technical, or founder advantage.",
    },
    {
        "key": "desired_outcome",
        "label": "Desired outcome",
        "required": False,
        "help_text": "What should be true after the first useful version exists.",
    },
    {
        "key": "constraints",
        "label": "Constraints",
        "required": False,
        "help_text": "Budget, timeline, compliance, team, data, or integration limits.",
    },
    {
        "key": "technical_preferences",
        "label": "Technical preferences",
        "required": False,
        "help_text": "Architecture, AWS, data, deployment, or testing preferences.",
    },
    {
        "key": "go_to_market",
        "label": "Go-to-market hunch",
        "required": False,
        "help_text": "First channel, wedge, launch motion, or buyer conversation.",
    },
    {
        "key": "success_metric",
        "label": "Success metric",
        "required": False,
        "help_text": "The first measurable proof that the idea is working.",
    },
    {
        "key": "open_questions",
        "label": "Open questions",
        "required": False,
        "help_text": "Known uncertainties the agents should investigate.",
    },
]


def idea_intake_payload(workflow_templates: list[dict]) -> dict:
    templates = sorted(workflow_templates, key=lambda item: item["sort_order"])
    return {
        "title": "Founder Idea Intake Packet",
        "credential_boundary": (
            "Provide product and company context only. Do not include Slack tokens, "
            "Telegram bot tokens, provider credentials, OAuth payloads, private endpoint "
            "credentials, raw logs, or sensitive customer data."
        ),
        "draft_mode": {
            "available_now": True,
            "description": (
                "The dashboard can create local SQLite workflow tasks and draft documents "
                "before live Hermes credentials are ready."
            ),
        },
        "live_mode_requires": [
            "Hermes profiles installed and accepted",
            "Slack and Telegram credentials loaded externally and verified",
            "Kanban initialized, diagnostics passed, and task push verified",
            "Standup schedules manually verified and cron installed",
            "LLM provider credentials loaded last and profile smoke checks verified",
        ],
        "reply_template": _reply_template(),
        "fields": IDEA_FIELDS,
        "routing": [_routing_item(template) for template in templates],
        "creation_flow": [
            {
                "step": 1,
                "action": "Fill the safe idea fields in this packet.",
                "result": "You have enough context to create a local project workflow.",
            },
            {
                "step": 2,
                "action": "Open `/projects` and create the project with the name and idea.",
                "result": "The dashboard creates local tasks and draft documents.",
            },
            {
                "step": 3,
                "action": "Review the generated workflow owners and outputs.",
                "result": (
                    "Research, product, engineering, testing, marketing, and review "
                    "work are queued."
                ),
            },
            {
                "step": 4,
                "action": "Push to Hermes Kanban only after the Kanban readiness gate is verified.",
                "result": "Each local task receives a Hermes Kanban task ID.",
            },
        ],
        "entry_points": {
            "projects": "/projects",
            "kickoff_readiness": "/setup/kickoff-readiness.md",
            "project_workflow": "/setup/project-workflow.md",
            "delegation_playbook": "/setup/delegation-playbook.md",
            "kanban_verification": "/setup/verification#kanban-verification",
            "llm_finalization": "/setup/llm-finalize.md",
        },
    }


def idea_intake_json(workflow_templates: list[dict]) -> str:
    return json.dumps(idea_intake_payload(workflow_templates), indent=2, sort_keys=True)


def idea_intake_markdown(workflow_templates: list[dict]) -> str:
    payload = idea_intake_payload(workflow_templates)
    lines = [
        "# Founder Idea Intake Packet",
        "",
        "Use this when you are ready to bring the first company idea into the system.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Mode",
        "",
        (
            "- Draft workflow available now: "
            f"{'yes' if payload['draft_mode']['available_now'] else 'no'}"
        ),
        f"- Draft behavior: {payload['draft_mode']['description']}",
        "",
        "## Safe Reply Template",
        "",
        "```text",
        payload["reply_template"],
        "```",
        "",
        "## Fields",
        "",
    ]
    for field in payload["fields"]:
        required = "required" if field["required"] else "optional"
        lines.append(f"- `{field['key']}` ({required}): {field['help_text']}")
    lines.extend(["", "## Workflow Routing", ""])
    for item in payload["routing"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- Phase: `{item['phase']}`",
                f"- Owner: {item['owner_name']} (`{item['owner_agent_id']}`)",
                f"- Output: `{item['doc_type']}`",
                f"- Priority: `{item['priority']}`",
                f"- Title pattern: {item['title_template']}",
                "",
            ]
        )
    lines.extend(["## Live Mode Requires", ""])
    for item in payload["live_mode_requires"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Creation Flow", ""])
    for item in payload["creation_flow"]:
        lines.append(f"{item['step']}. {item['action']} Result: {item['result']}")
    lines.extend(["", "## Entry Points", ""])
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def _reply_template() -> str:
    return "\n".join(f"{field['key']}=" for field in IDEA_FIELDS)


def _routing_item(template: dict) -> dict:
    return {
        "id": template["id"],
        "name": template["name"],
        "phase": template["phase"],
        "owner_agent_id": template["owner_agent_id"],
        "owner_name": template.get("owner_name", template["owner_agent_id"]),
        "doc_type": template["doc_type"],
        "priority": template["priority"],
        "title_template": _safe_text(template["title_template"]),
    }


def _safe_text(value: str) -> str:
    cleaned = re.sub(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{16,}", "sk_REDACTED", value)
    cleaned = re.sub(r"xoxb-[A-Za-z0-9-]{12,}", "xoxb_REDACTED", cleaned)
    cleaned = re.sub(r"xapp-[A-Za-z0-9-]{12,}", "xapp_REDACTED", cleaned)
    return re.sub(
        r"TELEGRAM_BOT_TOKEN\s*=\s*[0-9]+:[A-Za-z0-9_-]{20,}",
        "TELEGRAM_TOKEN_REDACTED",
        cleaned,
    )
