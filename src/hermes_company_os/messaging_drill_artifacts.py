from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.slack_workspace import slack_workspace_matrix
from hermes_company_os.telegram_policy import TELEGRAM_ALERT_RULES


def messaging_drill_payload(
    *,
    agents: list[dict],
    setup_values: dict[str, str],
    messaging_checks: list[dict],
    secret_requirements: list[dict],
) -> dict:
    check_status = {check["id"]: check["status"] for check in messaging_checks}
    return {
        "title": "Messaging Drill Pack",
        "credential_boundary": (
            "This drill contains routing prompts, expected behavior, channel IDs, and "
            "status metadata only. It does not include Slack tokens, Telegram credentials, "
            "provider API keys, or raw verification evidence."
        ),
        "policy": {
            "primary_workspace": "slack",
            "slack_profile_bots": "separate bot per Hermes profile",
            "telegram_owner": "chief-of-staff",
            "telegram_scope": "urgent founder alerts only",
        },
        "status": {
            "messaging_checks": _status_counts(messaging_checks),
            "slack_credentials": _status_counts(
                [
                    item
                    for item in secret_requirements
                    if item["category"] == "slack"
                ]
            ),
            "telegram_credentials": _status_counts(
                [
                    item
                    for item in secret_requirements
                    if item["category"] == "telegram"
                ]
            ),
        },
        "slack_channels": _channel_rows(agents, setup_values),
        "slack_drills": [
            _slack_drill(agent, check_status)
            for agent in agents
        ],
        "telegram_drills": _telegram_drills(check_status),
        "entry_points": {
            "slack_plan": "/setup/slack-plan.md",
            "slack_workspace": "/setup/slack-workspace.md",
            "telegram_policy": "/setup/telegram-policy.md",
            "verification_template": "/setup/messaging-verification-template.md",
            "messaging_verification": "/setup/messaging#messaging-verification",
            "secret_status": "/setup/messaging#secret-status",
            "live_verification": "/setup/live-verification.md",
        },
    }


def messaging_drill_json(**kwargs) -> str:
    return json.dumps(messaging_drill_payload(**kwargs), indent=2, sort_keys=True)


def messaging_drill_markdown(**kwargs) -> str:
    payload = messaging_drill_payload(**kwargs)
    lines = [
        "# Messaging Drill Pack",
        "",
        "Use this after creating Slack apps and the Chief of Staff Telegram bot, "
        "but before treating company communication as live.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Policy",
        "",
        f"- Primary workspace: {payload['policy']['primary_workspace']}",
        f"- Slack bot model: {payload['policy']['slack_profile_bots']}",
        f"- Telegram owner: `{payload['policy']['telegram_owner']}`",
        f"- Telegram scope: {payload['policy']['telegram_scope']}",
        "",
        "## Status",
        "",
        f"- Messaging checks: {_format_counts(payload['status']['messaging_checks'])}",
        f"- Slack credentials: {_format_counts(payload['status']['slack_credentials'])}",
        f"- Telegram credentials: {_format_counts(payload['status']['telegram_credentials'])}",
        "",
        "## Slack Channel Invite Drill",
        "",
    ]
    for channel in payload["slack_channels"]:
        lines.extend(
            [
                f"### {channel['channel_name']}",
                "",
                f"- Channel ID: `{channel['channel_id'] or 'not captured'}`",
                f"- Required: {'yes' if channel['required'] else 'no'}",
                f"- Purpose: {channel['purpose']}",
                "- Invite commands:",
                "```text",
                *channel["invite_commands"],
                "```",
                "",
            ]
        )
    lines.extend(["## Slack Profile Drills", ""])
    for drill in payload["slack_drills"]:
        lines.extend(
            [
                f"### {drill['profile_name']}",
                "",
                f"- Gateway check: `{drill['gateway_status']}`",
                f"- DM check: `{drill['dm_status']}`",
                f"- Channel mention check: `{drill['channel_status']}`",
                f"- DM prompt: {drill['dm_prompt']}",
                f"- Channel prompt: {drill['channel_prompt']}",
                f"- Expected behavior: {drill['expected_behavior']}",
                "",
            ]
        )
    lines.extend(["## Telegram Urgency Drills", ""])
    for drill in payload["telegram_drills"]:
        lines.extend(
            [
                f"### {drill['label']}",
                "",
                f"- Decision: `{drill['decision']}`",
                f"- Severity: `{drill['severity']}`",
                f"- Prompt: {drill['prompt']}",
                f"- Expected behavior: {drill['expected_behavior']}",
                f"- Verification status: `{drill['verification_status']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Completion Criteria",
            "",
            "- Every Slack profile gateway check is verified.",
            "- Every Slack DM and channel mention drill is verified.",
            "- Chief of Staff Telegram sends only urgent founder alerts.",
            "- Routine updates stay in Slack.",
            "- `/setup/messaging#messaging-verification` stores non-secret evidence only.",
            "- Use `/setup/messaging-verification-template.md` for bulk status import.",
            "",
        ]
    )
    return "\n".join(lines)


def _channel_rows(agents: list[dict], setup_values: dict[str, str]) -> list[dict]:
    return [
        {
            "channel_name": row["channel_name"],
            "channel_id": row["channel_id"],
            "required": row["required"],
            "purpose": row["purpose"],
            "invite_commands": row["invite_commands"],
        }
        for row in slack_workspace_matrix(agents, setup_values)
    ]


def _slack_drill(agent: dict, check_status: dict[str, str]) -> dict:
    display_name = f"Hermes {agent['name'].replace('/', '').strip()}"
    display_name = " ".join(display_name.split())
    return {
        "profile_id": agent["id"],
        "profile_name": agent["name"],
        "home_channel": agent["slack_channel"],
        "hermes_command": agent["hermes_command"],
        "gateway_status": check_status.get(f"{agent['id']}-slack-gateway", "missing"),
        "dm_status": check_status.get(f"{agent['id']}-slack-dm", "missing"),
        "channel_status": check_status.get(f"{agent['id']}-slack-channel", "missing"),
        "dm_prompt": (
            f"DM @{display_name}: Reply with your profile name, role, and one setup "
            "check you still need."
        ),
        "channel_prompt": (
            f"In {agent['slack_channel']}, mention @{display_name}: Confirm that "
            "this channel is your home channel and do not send Telegram."
        ),
        "expected_behavior": (
            "The profile replies in Slack only. Telegram remains quiet unless Chief "
            "of Staff escalates an urgent founder alert."
        ),
    }


def _telegram_drills(check_status: dict[str, str]) -> list[dict]:
    verification_status = check_status.get(
        "chief-of-staff-telegram-urgent-alert",
        "missing",
    )
    drills = []
    for rule in TELEGRAM_ALERT_RULES:
        should_send = rule["decision"] == "send_telegram"
        drills.append(
            {
                "id": rule["id"],
                "label": rule["id"].replace("-", " ").title(),
                "decision": rule["decision"],
                "severity": rule["severity"],
                "prompt": rule["example"],
                "expected_behavior": (
                    "Chief of Staff sends one concise Telegram alert and posts context "
                    "in Slack."
                    if should_send
                    else "No Telegram message. Keep the update in Slack only."
                ),
                "verification_status": verification_status if should_send else "slack_only",
            }
        )
    return drills


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
