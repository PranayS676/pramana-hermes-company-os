from __future__ import annotations

import json
import re
from collections import defaultdict


def delegation_playbook_payload(
    *,
    agents: list[dict],
    relationships: list[dict],
    workflow_templates: list[dict],
    schedules: list[dict],
) -> dict:
    agents_by_id = {agent["id"]: agent for agent in agents}
    manager_groups = _manager_groups(agents_by_id, relationships, workflow_templates)
    handoffs = [_workflow_handoff(template, agents_by_id) for template in workflow_templates]
    return {
        "title": "Hermes Delegation Playbook",
        "credential_boundary": (
            "This playbook contains operating rules, routing, profile commands, "
            "channels, schedule names, and workflow ownership only. It does not "
            "include Slack tokens, Telegram bot tokens, provider API keys, OAuth "
            "values, Kanban credentials, or verification evidence."
        ),
        "operating_loop": [
            {
                "step": 1,
                "owner": "founder",
                "action": (
                    "State the objective, constraints, and decision rights in "
                    "`#founder-command`."
                ),
            },
            {
                "step": 2,
                "owner": "chief-of-staff",
                "action": (
                    "Decompose the request into local workflow tasks, assign owners, "
                    "and keep the founder-facing thread concise."
                ),
            },
            {
                "step": 3,
                "owner": "manager-profiles",
                "action": (
                    "Route work to specialist profiles when a manager has direct "
                    "members; otherwise own the work directly."
                ),
            },
            {
                "step": 4,
                "owner": "specialist-profiles",
                "action": (
                    "Produce research notes, plans, implementation artifacts, tests, "
                    "or launch drafts inside the assigned task boundary."
                ),
            },
            {
                "step": 5,
                "owner": "chief-of-staff",
                "action": (
                    "Summarize progress in Slack standups and escalate only founder-"
                    "blocking or urgent production issues to Telegram."
                ),
            },
        ],
        "delegation_rules": [
            "Slack is the primary workspace for normal daily communication.",
            "Telegram is urgent-only and should route through Chief of Staff policy.",
            "Every task must have one owner profile and one Kanban idempotency key.",
            "Managers can delegate execution, but keep architecture and quality gates visible.",
            "LLM credentials and profile smoke checks are verified after Slack, "
            "Telegram, and Kanban wiring.",
        ],
        "manager_groups": manager_groups,
        "workflow_handoffs": handoffs,
        "channel_policy": _channel_policy(agents),
        "standups": [_standup(schedule) for schedule in schedules],
        "telegram_escalations": [
            {
                "case": "Founder decision blocked",
                "source": "Chief of Staff",
                "destination": "Telegram urgent policy",
                "example": (
                    "A task is blocked on budget, scope, legal risk, or strategic "
                    "direction."
                ),
            },
            {
                "case": "Production or integration risk",
                "source": "Engineering Manager",
                "destination": "Chief of Staff, then Telegram if founder action is needed",
                "example": "A live workflow breaks, data is at risk, or a release cannot proceed.",
            },
            {
                "case": "Credential or provider failure",
                "source": "Responsible profile",
                "destination": "Setup dashboard status, then Chief of Staff summary",
                "example": "A token, OAuth grant, Kanban auth, or LLM provider check fails.",
            },
        ],
        "activation_drill": [
            "Review `/setup/team-topology.md` to confirm managers and specialist profiles.",
            "Review `/setup/project-workflow.md` to confirm default task owners.",
            "Run Slack and Telegram messaging drills before creating the first real project.",
            "Run Kanban diagnostics, then push only reviewed local workflow tasks.",
            "Finalize LLM credentials last, then run profile smoke and acceptance checks.",
        ],
        "entry_points": {
            "team_topology": "/setup/team-topology.md",
            "project_workflow": "/setup/project-workflow.md",
            "kanban_runbook": "/setup/kanban-runbook.md",
            "messaging_drill": "/setup/messaging-drill.md",
            "standup_preview": "/setup/standup-preview.md",
            "telegram_policy": "/setup/telegram-policy.md",
            "llm_finalization": "/setup/llm-finalize.md",
            "profile_acceptance": "/setup/profile-acceptance.md",
        },
    }


def delegation_playbook_json(**kwargs) -> str:
    return json.dumps(delegation_playbook_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def delegation_playbook_markdown(**kwargs) -> str:
    payload = delegation_playbook_payload(**kwargs)
    lines = [
        "# Hermes Delegation Playbook",
        "",
        "Use this as the no-secret operating map for turning a founder idea into "
        "assigned Hermes agent work.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Operating Loop",
        "",
    ]
    for item in payload["operating_loop"]:
        lines.append(f"{item['step']}. `{item['owner']}`: {item['action']}")
    lines.extend(["", "## Delegation Rules", ""])
    for rule in payload["delegation_rules"]:
        lines.append(f"- {rule}")
    lines.extend(["", "## Manager Delegation", ""])
    if payload["manager_groups"]:
        for group in payload["manager_groups"]:
            manager = group["manager"]
            lines.extend(
                [
                    f"### {manager['name']}",
                    "",
                    f"- Command: `{manager['hermes_command']}`",
                    f"- Slack channel: `{manager['slack_channel']}`",
                    "- Direct specialist profiles:",
                ]
            )
            for member in group["members"]:
                lines.append(
                    f"  - {member['name']} (`{member['hermes_command']}`): "
                    f"{member['responsibility']}"
                )
            lines.extend(["- Workflow ownership visible to this manager:"])
            for handoff in group["workflow_handoffs"]:
                lines.append(
                    f"  - {handoff['name']} -> {handoff['owner_name']} "
                    f"(`{handoff['owner_agent_id']}`)"
                )
            lines.append("")
    else:
        lines.extend(["- No manager/member relationships configured.", ""])
    lines.extend(["## Workflow Handoff Map", ""])
    for handoff in payload["workflow_handoffs"]:
        lines.append(
            f"- `{handoff['phase']}` / {handoff['name']}: {handoff['owner_name']} "
            f"(`{handoff['owner_agent_id']}`), channel `{handoff['slack_channel']}`, "
            f"priority `{handoff['priority']}`, doc `{handoff['doc_type']}`"
        )
    lines.extend(["", "## Slack Channel Policy", ""])
    for channel in payload["channel_policy"]:
        lines.append(
            f"- `{channel['channel']}`: {', '.join(channel['profile_names'])}"
        )
    lines.extend(["", "## Standups And Escalation", ""])
    for standup in payload["standups"]:
        lines.append(
            f"- {standup['name']}: {standup['time']} {standup['timezone']} in "
            f"`{standup['slack_channel']}`; Telegram policy `{standup['telegram_policy']}`"
        )
    lines.extend(["", "### Telegram Escalations", ""])
    for item in payload["telegram_escalations"]:
        lines.append(
            f"- {item['case']}: {item['source']} -> {item['destination']}. "
            f"{item['example']}"
        )
    lines.extend(["", "## Activation Drill", ""])
    for item in payload["activation_drill"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _manager_groups(
    agents_by_id: dict[str, dict],
    relationships: list[dict],
    workflow_templates: list[dict],
) -> list[dict]:
    templates_by_owner = defaultdict(list)
    for template in workflow_templates:
        templates_by_owner[template["owner_agent_id"]].append(template)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for relationship in relationships:
        grouped[relationship["manager_agent_id"]].append(relationship)
    groups = []
    for manager_id, member_relationships in grouped.items():
        manager = agents_by_id.get(manager_id)
        if manager is None:
            continue
        member_ids = [relationship["member_agent_id"] for relationship in member_relationships]
        visible_templates = templates_by_owner[manager_id][:]
        for member_id in member_ids:
            visible_templates.extend(templates_by_owner[member_id])
        groups.append(
            {
                "manager": _agent_summary(manager),
                "members": [
                    _member_summary(relationship, agents_by_id)
                    for relationship in member_relationships
                    if relationship["member_agent_id"] in agents_by_id
                ],
                "workflow_handoffs": [
                    _workflow_handoff(template, agents_by_id)
                    for template in sorted(
                        visible_templates,
                        key=lambda item: (item["sort_order"], item["id"]),
                    )
                ],
            }
        )
    return groups


def _workflow_handoff(template: dict, agents_by_id: dict[str, dict]) -> dict:
    owner = agents_by_id.get(template["owner_agent_id"], {})
    return {
        "id": template["id"],
        "name": _safe_text(template["name"]),
        "phase": template["phase"],
        "owner_agent_id": template["owner_agent_id"],
        "owner_name": template.get("owner_name") or owner.get("name", template["owner_agent_id"]),
        "owner_command": owner.get("hermes_command", template["owner_agent_id"]),
        "slack_channel": owner.get("slack_channel", "unassigned"),
        "priority": template["priority"],
        "doc_type": template["doc_type"],
        "sort_order": template["sort_order"],
    }


def _channel_policy(agents: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for agent in agents:
        grouped[agent["slack_channel"]].append(agent)
    return [
        {
            "channel": channel,
            "profile_ids": [agent["id"] for agent in members],
            "profile_names": [agent["name"] for agent in members],
        }
        for channel, members in sorted(grouped.items())
    ]


def _standup(schedule: dict) -> dict:
    return {
        "id": schedule["id"],
        "name": schedule["name"],
        "time": f"{int(schedule['hour']):02d}:{int(schedule['minute']):02d}",
        "timezone": schedule["timezone"],
        "slack_channel": schedule["slack_channel"],
        "telegram_policy": schedule["telegram_policy"],
        "active": bool(schedule["active"]),
    }


def _member_summary(relationship: dict, agents_by_id: dict[str, dict]) -> dict:
    member = agents_by_id[relationship["member_agent_id"]]
    return {
        **_agent_summary(member),
        "relationship_type": relationship["relationship_type"],
        "responsibility": _safe_text(relationship["responsibility"]),
    }


def _agent_summary(agent: dict) -> dict:
    return {
        "id": agent["id"],
        "name": agent["name"],
        "role": agent["role"],
        "hermes_command": agent["hermes_command"],
        "slack_channel": agent["slack_channel"],
        "telegram_policy": agent["telegram_policy"],
    }


def _safe_text(value: str) -> str:
    cleaned = re.sub(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{16,}", "sk_REDACTED", value)
    cleaned = re.sub(r"xoxb-[A-Za-z0-9-]{12,}", "xoxb_REDACTED", cleaned)
    return re.sub(r"xapp-[A-Za-z0-9-]{12,}", "xapp_REDACTED", cleaned)
