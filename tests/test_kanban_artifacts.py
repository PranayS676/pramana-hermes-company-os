from hermes_company_os.kanban_artifacts import (
    kanban_diagnostics_powershell,
    kanban_runbook_markdown,
)


def test_kanban_runbook_lists_checks_templates_and_task_linkage():
    runbook = kanban_runbook_markdown(
        [
            {
                "id": "kanban-diagnostics-pass",
                "label": "Hermes Kanban diagnostics pass",
                "status": "needed",
                "evidence": "",
            }
        ],
        [
            {
                "id": "architecture-plan",
                "name": "Architecture plan",
                "owner_agent_name": "Engineering Manager",
            }
        ],
        [
            {
                "id": "work-item-1",
                "title": "Draft architecture",
                "owner_name": "Engineering Manager",
                "kanban_task_id": "",
            },
            {
                "id": "task-2",
                "title": "Research market",
                "owner_name": "Research Agent",
                "kanban_task_id": "kb_123",
            },
        ],
    )

    assert "Hermes Kanban Setup Runbook" in runbook
    assert "hermes kanban init" in runbook
    assert "`kanban-diagnostics-pass`" in runbook
    assert "`architecture-plan`: Architecture plan -> Engineering Manager" in runbook
    assert "Linked to Hermes Kanban: 1" in runbook
    assert "Waiting for Kanban push: 1" in runbook
    assert "`work-item-1`: Draft architecture -> Engineering Manager" in runbook
    assert "SLACK_BOT_TOKEN" not in runbook
    assert "TELEGRAM_BOT_TOKEN" not in runbook
    assert "sk-" not in runbook


def test_kanban_diagnostics_powershell_is_no_secret():
    script = kanban_diagnostics_powershell()

    assert "Hermes Company OS Kanban diagnostics" in script
    assert "hermes kanban init" in script
    assert "hermes kanban diagnostics --json" in script
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
