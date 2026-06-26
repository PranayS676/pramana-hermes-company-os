import csv
import io
import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.slack_workspace import (
    slack_invite_matrix_csv,
    slack_invite_matrix_json,
    slack_workspace_markdown,
    slack_workspace_matrix,
)

AGENTS = [
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
    },
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "hermes_command": "engineering-manager",
    },
    {
        "id": "qa-critic",
        "name": "QA / Critic",
        "hermes_command": "qa-critic",
    },
]


def test_slack_workspace_matrix_maps_channels_to_profile_bots():
    matrix = slack_workspace_matrix(
        AGENTS,
        {
            "slack_workspace_name": "Founder Lab",
            "founder_slack_member_id": "U123",
            "slack_channel_engineering": "CENG",
        },
    )

    by_channel = {row["channel_name"]: row for row in matrix}
    assert by_channel["#engineering"]["channel_id"] == "CENG"
    assert by_channel["#engineering"]["required"] is True
    assert by_channel["#engineering"]["invite_commands"] == [
        "/invite @Hermes Chief of Staff",
        "/invite @Hermes Engineering Manager",
    ]
    standup_bots = {
        bot["profile_id"] for bot in by_channel["#agent-standup"]["bots"]
    }
    assert standup_bots == {"chief-of-staff", "engineering-manager", "qa-critic"}


def test_slack_workspace_exports_json_csv_and_markdown_without_secrets():
    setup_values = {
        "slack_workspace_name": "Founder Lab",
        "founder_slack_member_id": "U123",
        "slack_channel_agent_standup": "CSTANDUP",
    }

    markdown = slack_workspace_markdown(AGENTS, setup_values)
    payload = json.loads(slack_invite_matrix_json(AGENTS, setup_values))
    rows = list(csv.DictReader(io.StringIO(slack_invite_matrix_csv(AGENTS, setup_values))))

    assert "Slack Workspace Matrix" in markdown
    assert "/setup/slack-invite-matrix.csv" in markdown
    assert payload["title"] == "Slack Workspace Matrix"
    assert any(row["channel_name"] == "#agent-standup" for row in rows)
    assert any(row["bot_display_name"] == "Hermes QA Critic" for row in rows)
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
    assert secret_violations(
        {
            "markdown": markdown,
            "json": json.dumps(payload),
            "csv": "\n".join(str(row) for row in rows),
        }
    ) == []
