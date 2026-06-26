import json

from hermes_company_os.team_topology import (
    team_topology_json,
    team_topology_markdown,
    team_topology_payload,
)

AGENTS = [
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "role": "Engineering",
        "hermes_command": "engineering-manager",
        "slack_channel": "#engineering",
    },
    {
        "id": "backend-engineer",
        "name": "Backend Engineer",
        "role": "Engineering",
        "hermes_command": "backend-engineer",
        "slack_channel": "#engineering",
    },
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "role": "Orchestrator",
        "hermes_command": "chief-of-staff",
        "slack_channel": "#founder-command",
    },
]


RELATIONSHIPS = [
    {
        "id": "engineering-manager-backend-engineer",
        "manager_agent_id": "engineering-manager",
        "member_agent_id": "backend-engineer",
        "manager_name": "Engineering Manager",
        "manager_role": "Engineering",
        "manager_command": "engineering-manager",
        "member_name": "Backend Engineer",
        "member_role": "Engineering",
        "member_command": "backend-engineer",
        "member_slack_channel": "#engineering",
        "relationship_type": "reports_to",
        "responsibility": "Own backend services and integration testing.",
    }
]


def test_team_topology_payload_groups_members_under_manager():
    payload = team_topology_payload(agents=AGENTS, relationships=RELATIONSHIPS)

    assert payload["title"] == "Hermes Team Topology"
    assert payload["summary"] == {
        "profiles": 3,
        "managers": 1,
        "relationships": 1,
    }
    assert payload["managers"][0]["manager"]["id"] == "engineering-manager"
    assert payload["managers"][0]["members"][0]["member_agent_id"] == "backend-engineer"
    assert payload["unmanaged_profiles"][0]["id"] == "chief-of-staff"


def test_team_topology_markdown_and_json_are_no_secret_artifacts():
    markdown = team_topology_markdown(agents=AGENTS, relationships=RELATIONSHIPS)
    payload = json.loads(team_topology_json(agents=AGENTS, relationships=RELATIONSHIPS))

    assert "Hermes Team Topology" in markdown
    assert "Backend Engineer (`backend-engineer`)" in markdown
    assert payload["managers"][0]["members"][0]["responsibility"] == (
        "Own backend services and integration testing."
    )
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
