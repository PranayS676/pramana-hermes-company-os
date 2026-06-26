import json

from hermes_company_os.kanban_provisioning import (
    BOARD_LANES,
    kanban_provisioning_json,
    kanban_provisioning_markdown,
    kanban_provisioning_payload,
    kanban_provisioning_powershell,
)
from hermes_company_os.secret_guard import secret_violations

WORKFLOW_TEMPLATES = [
    {
        "id": "opportunity-research",
        "name": "Opportunity research",
        "phase": "research",
        "owner_agent_id": "research-agent",
        "owner_name": "Research Agent",
        "priority": "high",
        "doc_type": "research",
    },
    {
        "id": "architecture-plan",
        "name": "Architecture plan",
        "phase": "engineering",
        "owner_agent_id": "engineering-manager",
        "owner_name": "Engineering Manager",
        "priority": "high",
        "doc_type": "architecture",
    },
]

KANBAN_CHECKS = [
    {
        "id": "kanban-board-initialized",
        "label": "Kanban board initialized",
        "check_type": "manual",
        "status": "needed",
        "evidence": "",
    }
]

TASKS = [
    {
        "id": "work-item-1",
        "title": "Research opportunity",
        "owner_agent_id": "research-agent",
        "owner_name": "Research Agent",
        "status": "planned",
        "priority": "high",
        "kanban_task_id": "",
    },
    {
        "id": "work-item-2",
        "title": "Draft architecture",
        "owner_agent_id": "engineering-manager",
        "owner_name": "Engineering Manager",
        "status": "planned",
        "priority": "high",
        "kanban_task_id": "kb_123",
    },
]


def test_kanban_provisioning_payload_maps_board_lanes_and_workflows():
    payload = kanban_provisioning_payload(
        workflow_templates=WORKFLOW_TEMPLATES,
        kanban_checks=KANBAN_CHECKS,
        tasks=TASKS,
    )

    mapping = {item["template_id"]: item for item in payload["workflow_mapping"]}
    assert payload["title"] == "Kanban Provisioning Pack"
    assert payload["board"]["name"] == "Hermes Company OS"
    assert {lane["id"] for lane in payload["board"]["lanes"]} >= {
        "research",
        "engineering",
        "founder-decision",
        "blocked",
    }
    assert mapping["opportunity-research"]["lane_id"] == "research"
    assert mapping["architecture-plan"]["lane_id"] == "engineering"
    assert payload["current_local_tasks"]["total"] == 2
    assert payload["current_local_tasks"]["linked_to_kanban"] == 1
    assert payload["current_local_tasks"]["waiting_for_push"] == 1
    assert payload["verification"]["ready"] is False
    assert payload["runner"]["default_mode"] == "dry_run"
    assert payload["runner"]["commands"]["post_dashboard_status"].startswith(
        "post verified status"
    )


def test_kanban_provisioning_exports_no_secret_markdown_json_and_runner():
    markdown = kanban_provisioning_markdown(
        workflow_templates=WORKFLOW_TEMPLATES,
        kanban_checks=KANBAN_CHECKS,
        tasks=TASKS,
    )
    payload = json.loads(
        kanban_provisioning_json(
            workflow_templates=WORKFLOW_TEMPLATES,
            kanban_checks=KANBAN_CHECKS,
            tasks=TASKS,
        )
    )
    script = kanban_provisioning_powershell(workflow_templates=WORKFLOW_TEMPLATES)
    raw = json.dumps(payload) + markdown + script

    assert "Kanban Provisioning Pack" in markdown
    assert "Board Lanes" in markdown
    assert "`architecture-plan` -> `engineering`" in markdown
    assert payload["board"]["lanes"] == BOARD_LANES
    assert "Hermes Company OS Kanban provisioning runner" in script
    assert "Dry run only" in script
    assert "hermes kanban init" in script
    assert "PostDashboardStatus" in script
    assert "Post-KanbanBoardInitializedStatus" in script
    assert "/setup/kanban-checks/kanban-board-initialized" in script
    assert "DASHBOARD verified kanban-board-initialized" in script
    assert "hermes kanban diagnostics --json" in script
    assert "-PostDashboardStatus" in markdown
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
