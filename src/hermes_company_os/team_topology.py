from __future__ import annotations

import json
from collections import defaultdict


def team_topology_payload(
    *,
    agents: list[dict],
    relationships: list[dict],
) -> dict:
    agents_by_id = {agent["id"]: agent for agent in agents}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for relationship in relationships:
        grouped[relationship["manager_agent_id"]].append(_member(relationship))
    return {
        "title": "Hermes Team Topology",
        "credential_boundary": (
            "This topology contains profile names, roles, commands, channels, and "
            "responsibilities only. It does not include Slack tokens, Telegram bot "
            "tokens, provider API keys, OAuth values, or verification evidence."
        ),
        "summary": {
            "profiles": len(agents),
            "managers": len(grouped),
            "relationships": len(relationships),
        },
        "managers": [
            {
                "manager": _manager(agents_by_id[manager_id]),
                "members": members,
            }
            for manager_id, members in grouped.items()
            if manager_id in agents_by_id
        ],
        "unmanaged_profiles": [
            _manager(agent)
            for agent in agents
            if agent["id"] not in grouped
            and not any(item["member_agent_id"] == agent["id"] for item in relationships)
        ],
        "entry_points": {
            "profile_artifacts": "/setup/profile-artifacts.md",
            "slack_workspace": "/setup/slack-workspace.md",
            "company_manifest": "/setup/company-manifest.md",
            "setup_dashboard": "/setup#profiles",
        },
    }


def team_topology_json(**kwargs) -> str:
    return json.dumps(team_topology_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def team_topology_markdown(**kwargs) -> str:
    payload = team_topology_payload(**kwargs)
    summary = payload["summary"]
    lines = [
        "# Hermes Team Topology",
        "",
        "Use this as the no-secret org map for the founder-led Hermes company.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Summary",
        "",
        f"- Profiles: {summary['profiles']}",
        f"- Managers with members: {summary['managers']}",
        f"- Manager/member relationships: {summary['relationships']}",
        "",
        "## Manager Groups",
        "",
    ]
    if payload["managers"]:
        for group in payload["managers"]:
            manager = group["manager"]
            lines.extend(
                [
                    f"### {manager['name']}",
                    "",
                    f"- Profile command: `{manager['hermes_command']}`",
                    f"- Role: {manager['role']}",
                    f"- Slack channel: `{manager['slack_channel']}`",
                    "- Members:",
                ]
            )
            for member in group["members"]:
                lines.append(
                    f"  - {member['member_name']} (`{member['member_command']}`): "
                    f"{member['responsibility']}"
                )
            lines.append("")
    else:
        lines.extend(["- No manager/member relationships configured.", ""])
    lines.extend(["## Unmanaged Core Profiles", ""])
    if payload["unmanaged_profiles"]:
        for profile in payload["unmanaged_profiles"]:
            lines.append(
                f"- {profile['name']} (`{profile['hermes_command']}`): {profile['role']}"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Activation Notes",
            "",
            "- Every listed profile is a real starter Hermes profile in this dashboard.",
            "- Engineering specialist profiles use the shared `#engineering` channel by default.",
            "- Slack, Telegram, Kanban, and LLM verification remain tracked by the setup gates.",
            "",
        ]
    )
    return "\n".join(lines)


def _manager(agent: dict) -> dict:
    return {
        "id": agent["id"],
        "name": agent["name"],
        "role": agent["role"],
        "hermes_command": agent["hermes_command"],
        "slack_channel": agent["slack_channel"],
    }


def _member(relationship: dict) -> dict:
    return {
        "id": relationship["id"],
        "member_agent_id": relationship["member_agent_id"],
        "member_name": relationship["member_name"],
        "member_role": relationship["member_role"],
        "member_command": relationship["member_command"],
        "member_slack_channel": relationship["member_slack_channel"],
        "relationship_type": relationship["relationship_type"],
        "responsibility": relationship["responsibility"],
    }
