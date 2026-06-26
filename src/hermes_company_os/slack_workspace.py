from __future__ import annotations

import csv
import io
import json
import re

CHANNEL_INPUTS = [
    {
        "name": "#founder-command",
        "input_key": "slack_channel_founder_command",
        "required": True,
        "purpose": "Founder approvals, Chief of Staff coordination, and command intake.",
        "agent_ids": ["chief-of-staff"],
    },
    {
        "name": "#agent-standup",
        "input_key": "slack_channel_agent_standup",
        "required": True,
        "purpose": "9 AM and 3 PM ET operating summaries and cross-profile status.",
        "agent_ids": "all",
    },
    {
        "name": "#product",
        "input_key": "slack_channel_product",
        "required": True,
        "purpose": "Product decisions, PRDs, workflow scope, and tradeoffs.",
        "agent_ids": ["chief-of-staff", "product-manager"],
    },
    {
        "name": "#research",
        "input_key": "slack_channel_research",
        "required": True,
        "purpose": "Market, customer, competitor, and technical research.",
        "agent_ids": ["chief-of-staff", "research-agent"],
    },
    {
        "name": "#engineering",
        "input_key": "slack_channel_engineering",
        "required": True,
        "purpose": "Architecture, AWS, distributed systems, implementation planning, and tests.",
        "agent_ids": [
            "chief-of-staff",
            "engineering-manager",
            "backend-engineer",
            "frontend-engineer",
            "cloud-infra-agent",
            "test-automation-agent",
        ],
    },
    {
        "name": "#marketing",
        "input_key": "slack_channel_marketing",
        "required": True,
        "purpose": "Positioning, messaging, launch planning, and campaign work.",
        "agent_ids": ["chief-of-staff", "marketing-agent"],
    },
    {
        "name": "#qa-review",
        "input_key": "slack_channel_qa_review",
        "required": True,
        "purpose": "Risk review, test gaps, contradictions, and assumption checks.",
        "agent_ids": ["chief-of-staff", "qa-critic"],
    },
    {
        "name": "#decisions",
        "input_key": "slack_channel_decisions",
        "required": False,
        "purpose": "Optional durable decision log and founder decision archive.",
        "agent_ids": ["chief-of-staff", "product-manager", "qa-critic"],
    },
    {
        "name": "#alerts",
        "input_key": "slack_channel_alerts",
        "required": False,
        "purpose": "Optional blockers, failed runs, and urgent operational notices.",
        "agent_ids": ["chief-of-staff"],
    },
]


def slack_workspace_matrix(agents: list[dict], setup_values: dict[str, str]) -> list[dict]:
    agents_by_id = {agent["id"]: agent for agent in agents}
    all_agent_ids = [agent["id"] for agent in agents]
    rows = []
    for channel in CHANNEL_INPUTS:
        agent_ids = all_agent_ids if channel["agent_ids"] == "all" else channel["agent_ids"]
        members = [
            _member_row(agents_by_id[agent_id])
            for agent_id in agent_ids
            if agent_id in agents_by_id
        ]
        rows.append(
            {
                "channel_name": channel["name"],
                "channel_id": setup_values.get(channel["input_key"], ""),
                "input_key": channel["input_key"],
                "required": channel["required"],
                "purpose": channel["purpose"],
                "bots": members,
                "invite_commands": [
                    f"/invite @{member['bot_display_name']}" for member in members
                ],
            }
        )
    return rows


def slack_workspace_markdown(agents: list[dict], setup_values: dict[str, str]) -> str:
    matrix = slack_workspace_matrix(agents, setup_values)
    required_missing = [
        row for row in matrix if row["required"] and not row["channel_id"].strip()
    ]
    lines = [
        "# Slack Workspace Matrix",
        "",
        "Use this after creating the Slack workspace channels and before gateway "
        "verification. It maps channels to Hermes profile bots and gives invite "
        "commands you can run in Slack. It contains no bot tokens or app tokens.",
        "",
        "## Current Input Status",
        "",
        f"- Required channels missing IDs: {len(required_missing)}",
        f"- Workspace: {setup_values.get('slack_workspace_name') or 'not captured'}",
        f"- Founder member ID: {setup_values.get('founder_slack_member_id') or 'not captured'}",
        "",
        "## Channel Membership Matrix",
        "",
    ]
    for row in matrix:
        channel_id = row["channel_id"] or "not captured"
        required = "required" if row["required"] else "optional"
        bot_names = ", ".join(member["bot_display_name"] for member in row["bots"])
        lines.extend(
            [
                f"### {row['channel_name']}",
                "",
                f"- Status: `{required}`",
                f"- Channel ID: `{channel_id}`",
                f"- Dashboard input: `{row['input_key']}`",
                f"- Purpose: {row['purpose']}",
                f"- Bots to invite: {bot_names or 'none'}",
                "",
                "```text",
                *row["invite_commands"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Exports",
            "",
            "- JSON matrix: `/setup/slack-invite-matrix.json`",
            "- CSV matrix: `/setup/slack-invite-matrix.csv`",
            "- Slack app manifests: `/setup/slack-manifests.json`",
            "",
            "## Verification",
            "",
            "- Every required channel exists in Slack.",
            "- Every required channel ID is captured in `/setup#inputs`.",
            "- Every profile bot is installed in the workspace.",
            "- Every listed invite command has been run in the target channel.",
            "- `/setup#messaging-verification` has Slack gateway, DM, and mention checks.",
            "",
        ]
    )
    return "\n".join(lines)


def slack_invite_matrix_json(agents: list[dict], setup_values: dict[str, str]) -> str:
    return json.dumps(
        {
            "title": "Slack Workspace Matrix",
            "channels": slack_workspace_matrix(agents, setup_values),
        },
        indent=2,
    )


def slack_invite_matrix_csv(agents: list[dict], setup_values: dict[str, str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "channel_name",
            "channel_id",
            "required",
            "bot_display_name",
            "profile_id",
            "hermes_command",
            "invite_command",
        ],
        lineterminator="\n",
    )
    writer.writeheader()
    for channel in slack_workspace_matrix(agents, setup_values):
        for bot in channel["bots"]:
            writer.writerow(
                {
                    "channel_name": channel["channel_name"],
                    "channel_id": channel["channel_id"],
                    "required": "yes" if channel["required"] else "no",
                    "bot_display_name": bot["bot_display_name"],
                    "profile_id": bot["profile_id"],
                    "hermes_command": bot["hermes_command"],
                    "invite_command": f"/invite @{bot['bot_display_name']}",
                }
            )
    return output.getvalue()


def _member_row(agent: dict) -> dict:
    return {
        "profile_id": agent["id"],
        "profile_name": agent["name"],
        "bot_display_name": f"Hermes {_clean_name(agent['name'])}",
        "hermes_command": agent["hermes_command"],
    }


def _clean_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()
