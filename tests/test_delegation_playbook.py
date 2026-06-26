import json

from hermes_company_os.delegation_playbook import (
    delegation_playbook_json,
    delegation_playbook_markdown,
    delegation_playbook_payload,
)

AGENTS = [
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "role": "Engineering",
        "hermes_command": "engineering-manager",
        "slack_channel": "#engineering",
        "telegram_policy": "Chief escalation only",
    },
    {
        "id": "backend-engineer",
        "name": "Backend Engineer",
        "role": "Engineering",
        "hermes_command": "backend-engineer",
        "slack_channel": "#engineering",
        "telegram_policy": "Manager escalation only",
    },
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "role": "Orchestrator",
        "hermes_command": "chief-of-staff",
        "slack_channel": "#founder-command",
        "telegram_policy": "Urgent founder alerts",
    },
]

RELATIONSHIPS = [
    {
        "id": "engineering-manager-backend-engineer",
        "manager_agent_id": "engineering-manager",
        "member_agent_id": "backend-engineer",
        "relationship_type": "reports_to",
        "responsibility": "Own backend services and integration tests.",
    }
]

WORKFLOW_TEMPLATES = [
    {
        "id": "architecture-plan",
        "name": "Architecture plan",
        "phase": "engineering",
        "owner_agent_id": "engineering-manager",
        "owner_name": "Engineering Manager",
        "sort_order": 10,
        "doc_type": "architecture",
        "priority": "high",
    },
    {
        "id": "backend-implementation-plan",
        "name": "Backend implementation plan",
        "phase": "engineering",
        "owner_agent_id": "backend-engineer",
        "owner_name": "Backend Engineer",
        "sort_order": 20,
        "doc_type": "implementation",
        "priority": "high",
    },
]

SCHEDULES = [
    {
        "id": "morning-standup",
        "name": "Morning Standup",
        "hour": 9,
        "minute": 0,
        "timezone": "America/New_York",
        "slack_channel": "#agent-standup",
        "telegram_policy": "urgent only",
        "active": 1,
    }
]


def test_delegation_playbook_payload_maps_manager_specialists_and_workflow():
    payload = delegation_playbook_payload(
        agents=AGENTS,
        relationships=RELATIONSHIPS,
        workflow_templates=WORKFLOW_TEMPLATES,
        schedules=SCHEDULES,
    )

    assert payload["title"] == "Hermes Delegation Playbook"
    assert payload["manager_groups"][0]["manager"]["id"] == "engineering-manager"
    assert payload["manager_groups"][0]["members"][0]["id"] == "backend-engineer"
    assert [
        handoff["id"] for handoff in payload["manager_groups"][0]["workflow_handoffs"]
    ] == ["architecture-plan", "backend-implementation-plan"]
    assert payload["workflow_handoffs"][1]["slack_channel"] == "#engineering"
    assert payload["standups"][0]["time"] == "09:00"
    assert payload["entry_points"]["project_workflow"] == "/setup/project-workflow.md"


def test_delegation_playbook_markdown_and_json_are_no_secret_artifacts():
    markdown = delegation_playbook_markdown(
        agents=AGENTS,
        relationships=RELATIONSHIPS,
        workflow_templates=WORKFLOW_TEMPLATES,
        schedules=SCHEDULES,
    )
    payload = json.loads(
        delegation_playbook_json(
            agents=AGENTS,
            relationships=RELATIONSHIPS,
            workflow_templates=WORKFLOW_TEMPLATES,
            schedules=SCHEDULES,
        )
    )

    assert "Hermes Delegation Playbook" in markdown
    assert "Engineering Manager" in markdown
    assert "Backend implementation plan" in markdown
    assert payload["telegram_escalations"]
    raw = json.dumps(payload) + markdown
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
