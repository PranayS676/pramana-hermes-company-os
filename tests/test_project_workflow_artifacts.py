import json

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.project_workflow_artifacts import (
    project_workflow_json,
    project_workflow_markdown,
)
from hermes_company_os.settings import Settings


def test_project_workflow_routes_export_templates_and_kanban_mapping(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    markdown = client.get("/setup/project-workflow.md")
    response = client.get("/setup/project-workflow.json")

    assert markdown.status_code == 200
    assert "Project Workflow And Kanban Handoff" in markdown.text
    assert "Architecture plan" in markdown.text
    assert "Kanban Create Shape" in markdown.text
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Project Workflow And Kanban Handoff"
    assert payload["operating_boundary"]["project_creation"].startswith("Creates local")
    assert payload["kanban_create_shape"]["remote_id_storage"] == "tasks.kanban_task_id"
    assert payload["entry_points"]["kanban_runbook"] == "/setup/kanban-runbook.md"
    assert any(template["id"] == "architecture-plan" for template in payload["templates"])

    raw = json.dumps(payload) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw


def test_project_workflow_helpers_include_waiting_tasks_without_summaries():
    payload = json.loads(
        project_workflow_json(
            workflow_templates=[
                {
                    "id": "architecture-plan",
                    "name": "Architecture plan",
                    "phase": "engineering",
                    "owner_agent_id": "engineering-manager",
                    "owner_name": "Engineering Manager",
                    "sort_order": 10,
                    "doc_type": "architecture",
                    "priority": "high",
                    "title_template": "Architecture plan for {project_name}",
                    "prompt_template": "Plan {idea}",
                }
            ],
            kanban_checks=[
                {
                    "id": "kanban-diagnostics-pass",
                    "label": "Hermes Kanban diagnostics pass",
                    "check_type": "diagnostics",
                    "status": "verified",
                    "evidence": "Private external evidence.",
                }
            ],
            tasks=[
                {
                    "id": "task-1",
                    "title": "Draft architecture",
                    "owner_agent_id": "engineering-manager",
                    "owner_name": "Engineering Manager",
                    "status": "planned",
                    "priority": "high",
                    "summary": "Do not export full task body here.",
                    "kanban_task_id": "",
                },
                {
                    "id": "task-2",
                    "title": "Research market",
                    "owner_agent_id": "research-agent",
                    "owner_name": "Research Agent",
                    "status": "planned",
                    "priority": "medium",
                    "summary": "Already pushed.",
                    "kanban_task_id": "kb_123",
                },
            ],
        )
    )
    markdown = project_workflow_markdown(
        workflow_templates=[
            {
                "id": "architecture-plan",
                "name": "Architecture plan",
                "phase": "engineering",
                "owner_agent_id": "engineering-manager",
                "owner_name": "Engineering Manager",
                "sort_order": 10,
                "doc_type": "architecture",
                "priority": "high",
                "title_template": "Architecture plan for {project_name}",
                "prompt_template": "Plan {idea}",
            }
        ],
        kanban_checks=[],
        tasks=[],
    )

    waiting = payload["current_local_tasks"]["waiting"]
    assert payload["current_local_tasks"]["linked_to_kanban"] == 1
    assert payload["current_local_tasks"]["waiting_for_push"] == 1
    assert waiting[0]["id"] == "task-1"
    assert "summary" not in waiting[0]
    assert payload["kanban_readiness"]["ready"] is True
    assert "local task ID -> idempotency key" in markdown
    assert "Private external evidence." not in json.dumps(payload)
