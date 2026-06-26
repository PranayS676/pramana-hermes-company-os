import json

from hermes_company_os.founder_decisions import (
    founder_decisions_json,
    founder_decisions_markdown,
    founder_decisions_payload,
)
from hermes_company_os.secret_guard import secret_violations

DECISIONS = [
    {
        "id": "decision-first-idea-start",
        "title": "Approve first idea intake start",
        "status": "needed",
        "urgency": "urgent",
        "source": "setup",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "owner_command": "chief-of-staff",
        "slack_channel": "#founder-command",
        "telegram_policy": "Escalate to Telegram when all setup gates are ready",
        "context": "Approve before starting the first project workflow.",
        "decision": "",
        "updated_at": "2026-06-23T15:00:00+00:00",
    },
    {
        "id": "decision-operating-model",
        "title": "Approve operating model",
        "status": "approved",
        "urgency": "routine",
        "source": "setup",
        "owner_agent_id": "chief-of-staff",
        "owner_name": "Chief of Staff",
        "owner_command": "chief-of-staff",
        "slack_channel": "#decisions",
        "telegram_policy": "Slack first.",
        "context": "Confirm Slack, Telegram, standups, Kanban, and LLM-last setup.",
        "decision": "Approved as the starter company operating model.",
        "updated_at": "2026-06-23T14:00:00+00:00",
    },
]


def test_founder_decisions_payload_summarizes_open_urgent_items():
    payload = founder_decisions_payload(DECISIONS)

    assert payload["title"] == "Founder Decision Queue"
    assert payload["summary"]["open"] == 1
    assert payload["summary"]["urgent_open"] == 1
    assert payload["summary"]["status_counts"] == {"needed": 1, "approved": 1}
    assert payload["open_decisions"][0]["id"] == "decision-first-idea-start"
    assert payload["entry_points"]["dashboard"] == "/#founder-decisions"


def test_founder_decisions_exports_non_secret_decision_log():
    markdown = founder_decisions_markdown(DECISIONS)
    payload = json.loads(founder_decisions_json(DECISIONS))

    assert "Founder Decision Queue" in markdown
    assert "Approve first idea intake start" in markdown
    assert payload["decisions"][1]["has_decision"] is True
    raw = json.dumps(payload) + markdown
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
