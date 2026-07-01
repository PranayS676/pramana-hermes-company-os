import json

from hermes_company_os.gateway_operations import (
    gateway_operations_json,
    gateway_operations_markdown,
    gateway_operations_payload,
    gateway_operations_powershell,
)
from hermes_company_os.secret_guard import secret_violations

AGENTS = [
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
        "slack_channel": "#founder-command",
        "telegram_policy": "Urgent founder alerts",
    },
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "hermes_command": "engineering-manager",
        "slack_channel": "#engineering",
        "telegram_policy": "Chief escalation only",
    },
]

MESSAGING_CHECKS = [
    {
        "id": "chief-of-staff-slack-gateway",
        "owner_agent_id": "chief-of-staff",
        "platform": "slack",
        "label": "Chief of Staff Slack gateway running",
        "status": "needed",
        "evidence": "Do not export this raw evidence.",
    },
    {
        "id": "chief-of-staff-telegram-urgent",
        "owner_agent_id": "chief-of-staff",
        "platform": "telegram",
        "label": "Chief of Staff Telegram urgent alert",
        "status": "deferred",
        "evidence": "",
    },
]

SECRET_REQUIREMENTS = [
    {
        "id": "chief-of-staff-slack-bot-token",
        "owner_agent_id": "chief-of-staff",
        "category": "slack",
        "label": "Chief of Staff Slack bot token",
        "environment_key": "SLACK_BOT_TOKEN",
        "status": "loaded",
    },
    {
        "id": "chief-of-staff-telegram-bot-token",
        "owner_agent_id": "chief-of-staff",
        "category": "telegram",
        "label": "Chief of Staff Telegram bot token",
        "environment_key": "TELEGRAM_BOT_TOKEN",
        "status": "needed",
    },
]

INTEGRATIONS = [
    {"id": "slack-chief-of-staff", "category": "slack", "status": "needs_input"},
    {"id": "telegram-founder-alerts", "category": "telegram", "status": "needs_input"},
]


def test_gateway_operations_payload_maps_profiles_commands_and_statuses():
    payload = gateway_operations_payload(
        agents=AGENTS,
        messaging_checks=MESSAGING_CHECKS,
        integrations=INTEGRATIONS,
        secret_requirements=SECRET_REQUIREMENTS,
    )

    assert payload["title"] == "Hermes Gateway Operations"
    assert payload["profiles"][0]["commands"]["setup"] == (
        "chief-of-staff gateway setup"
    )
    assert payload["profiles"][0]["secret_status"] == {"loaded": 1, "needed": 1}
    assert payload["profiles"][0]["messaging_status"] == {"needed": 1, "deferred": 1}
    assert payload["profiles"][1]["secret_status"] == {}
    assert payload["entry_points"]["messaging_verification"] == (
        "/setup/messaging#messaging-verification"
    )


def test_gateway_operations_exports_no_secret_runbook_and_script():
    markdown = gateway_operations_markdown(
        agents=AGENTS,
        messaging_checks=MESSAGING_CHECKS,
        integrations=INTEGRATIONS,
        secret_requirements=SECRET_REQUIREMENTS,
    )
    payload = json.loads(
        gateway_operations_json(
            agents=AGENTS,
            messaging_checks=MESSAGING_CHECKS,
            integrations=INTEGRATIONS,
            secret_requirements=SECRET_REQUIREMENTS,
        )
    )
    script = gateway_operations_powershell(AGENTS)
    raw = json.dumps(payload) + markdown + script

    assert "Hermes Gateway Operations" in markdown
    assert ".\\gateway-operations.ps1 -CheckCommands" in markdown
    assert "-PostDashboardStatus" in markdown
    assert "Invoke-GatewayAction" in script
    assert "PostDashboardStatus" in script
    assert "Post-MessagingGatewayStatus" in script
    assert "/setup/messaging-checks/$checkId" in script
    assert "status = \"loaded\"" in script
    assert "DASHBOARD loaded $checkId" in script
    assert "DASHBOARD skipped ${checkId}:" in script
    assert "DASHBOARD skipped $checkId:" not in script
    assert "$InstallService" in script
    assert 'Invoke-GatewayAction $profile "install"' in script
    assert "Do not export this raw evidence" not in raw
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []
