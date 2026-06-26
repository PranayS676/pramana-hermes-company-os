import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.slack_provisioning import (
    slack_bot_user_map_template,
    slack_bot_user_map_template_json,
    slack_provisioning_json,
    slack_provisioning_markdown,
    slack_provisioning_payload,
    slack_provisioning_powershell,
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


def test_slack_provisioning_payload_maps_channels_runner_and_bot_user_template():
    payload = slack_provisioning_payload(
        agents=AGENTS,
        setup_values={
            "slack_workspace_name": "Founder Lab",
            "founder_slack_member_id": "U123",
            "slack_channel_engineering": "CENG",
            "slack_bot_user_id_qa_critic": "UQA123456",
        },
    )

    by_channel = {channel["channel_name"]: channel for channel in payload["channels"]}
    assert payload["title"] == "Slack Provisioning Pack"
    assert payload["workspace"] == "Founder Lab"
    assert payload["founder_member_id_captured"] is True
    assert payload["runner"]["default_mode"] == "dry_run"
    assert payload["runner"]["post_dashboard_inputs"].startswith(
        "post created Slack channel IDs"
    )
    assert payload["entry_points"]["bot_user_map"] == "/setup/slack-bot-user-map.json"
    assert by_channel["#engineering"]["api_name"] == "engineering"
    assert by_channel["#engineering"]["channel_id"] == "CENG"
    assert by_channel["#engineering"]["create_method"] == "conversations.create"
    assert by_channel["#engineering"]["invite_method"] == "conversations.invite"
    assert "/invite @Hermes Engineering Manager" in (
        by_channel["#engineering"]["manual_invite_commands"]
    )
    assert payload["bot_user_map_template"]["qa-critic"] == "UQA123456"


def test_slack_bot_user_map_template_json_is_profile_keyed():
    template = slack_bot_user_map_template(
        AGENTS,
        {"slack_bot_user_id_chief_of_staff": "UCHIEF1234"},
    )
    payload = json.loads(
        slack_bot_user_map_template_json(
            AGENTS,
            {"slack_bot_user_id_chief_of_staff": "UCHIEF1234"},
        )
    )

    assert template["chief-of-staff"] == "UCHIEF1234"
    assert payload["engineering-manager"] == (
        "U_REPLACE_WITH_ENGINEERING_MANAGER_BOT_USER_ID"
    )


def test_slack_provisioning_exports_no_secret_markdown_json_and_runner():
    markdown = slack_provisioning_markdown(
        agents=AGENTS,
        setup_values={"slack_channel_engineering": "CENG"},
    )
    payload = json.loads(
        slack_provisioning_json(
            agents=AGENTS,
            setup_values={"slack_channel_engineering": "CENG"},
        )
    )
    script = slack_provisioning_powershell(
        agents=AGENTS,
        setup_values={"slack_channel_engineering": "CENG"},
    )
    raw = json.dumps(payload) + markdown + script

    assert "Slack Provisioning Pack" in markdown
    assert "/setup/slack-bot-user-map.json" in markdown
    assert "conversations.create" in markdown
    assert payload["title"] == "Slack Provisioning Pack"
    assert "Hermes Company OS Slack provisioning runner" in script
    assert "Dry run only" in script
    assert "Invoke-SlackApi" in script
    assert "conversations.invite" in script
    assert "PostDashboardInputs" in script
    assert "Post-DashboardInput" in script
    assert "/setup/inputs" in script
    assert "DASHBOARD input $Key=$Value" in script
    assert "DASHBOARD skipped input ${Key}:" in script
    assert "DASHBOARD skipped input $Key:" not in script
    assert "InputKey" in script
    assert "-PostDashboardInputs" in markdown
    assert "Token values were not printed" in script
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
