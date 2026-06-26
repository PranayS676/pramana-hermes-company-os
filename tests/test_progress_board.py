import json

from hermes_company_os.progress_board import (
    progress_board_json,
    progress_board_markdown,
    progress_board_payload,
)
from hermes_company_os.secret_guard import secret_violations


def test_progress_board_groups_setup_by_stage_without_secrets():
    kwargs = {
        "setup_inputs": [
            {
                "key": "founder_name",
                "group_name": "founder",
                "label": "Founder name",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
            }
        ],
        "runtime_checks": [
            {
                "id": "hermes-cli",
                "label": "Hermes CLI",
                "status": "missing",
                "detail": "`hermes` was not found on PATH.",
                "remediation": "Install Hermes.",
            }
        ],
        "secret_requirements": [
            {
                "id": "chief-of-staff-slack-bot-token",
                "category": "slack",
                "label": "Chief of Staff Slack bot token",
                "owner_agent_id": "chief-of-staff",
                "owner_name": "Chief of Staff",
                "destination": "chief-of-staff Hermes profile .env",
                "status": "needed",
            },
            {
                "id": "chief-of-staff-llm-provider-credential",
                "category": "llm",
                "label": "Chief of Staff LLM provider credential",
                "owner_agent_id": "chief-of-staff",
                "owner_name": "Chief of Staff",
                "destination": "chief-of-staff Hermes profile .env",
                "status": "deferred",
            },
        ],
        "messaging_checks": [{"id": "slack-dm", "label": "Slack DM", "status": "needed"}],
        "schedule_checks": [
            {"id": "standup", "label": "Standup", "status": "needed"}
        ],
        "kanban_checks": [
            {"id": "kanban-init", "label": "Kanban init", "status": "needed"}
        ],
        "model_preferences": [
            {
                "agent_id": "chief-of-staff",
                "agent_name": "Chief of Staff",
                "provider": "openai-codex",
                "model": "gpt-5-codex",
                "status": "planned",
            }
        ],
        "profile_installation_checks": [
            {"id": "profile-install", "label": "Profile install", "status": "needed"}
        ],
        "profile_acceptance_checks": [
            {"id": "acceptance", "label": "Acceptance", "status": "needed"}
        ],
        "founder_decisions": [
            {
                "id": "decision-first",
                "title": "Approve first idea",
                "status": "needed",
                "urgency": "urgent",
                "owner_agent_id": "chief-of-staff",
            }
        ],
    }

    payload = progress_board_payload(**kwargs)
    markdown = progress_board_markdown(**kwargs)
    exported = json.loads(progress_board_json(**kwargs))
    raw = json.dumps(payload) + markdown + json.dumps(exported)

    assert payload["title"] == "Founder Setup Progress Board"
    assert payload["ready"] is False
    assert [column["id"] for column in payload["columns"]] == [
        "do-now",
        "after-hermes-install",
        "after-credentials",
        "final-verification",
    ]
    assert payload["entry_points"]["markdown"] == "/setup/progress-board.md"
    assert payload["entry_points"]["first_run"] == "/setup/first-run.ps1"
    assert "Do now" in markdown
    assert "Do after Hermes install" in markdown
    assert "Do after credentials" in markdown
    assert "Final verification" in markdown
    assert "/setup/progress-board.json" in markdown
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert "TELEGRAM_BOT_TOKEN" not in raw
    assert secret_violations({"raw": raw}) == []
