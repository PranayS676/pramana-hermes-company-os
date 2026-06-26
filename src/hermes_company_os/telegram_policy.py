import json

TELEGRAM_ALERT_RULES = [
    {
        "id": "founder-approval-needed",
        "decision": "send_telegram",
        "severity": "urgent",
        "description": (
            "A decision is blocked until the founder approves, rejects, or chooses an option."
        ),
        "example": (
            "Architecture has two viable paths and work is blocked until the founder chooses."
        ),
    },
    {
        "id": "failed-scheduled-operation",
        "decision": "send_telegram",
        "severity": "urgent",
        "description": "A scheduled standup, cron run, or recurring company operation failed.",
        "example": "The morning standup cron failed and did not post to Slack.",
    },
    {
        "id": "security-or-cost-risk",
        "decision": "send_telegram",
        "severity": "urgent",
        "description": (
            "A security, billing, data-loss, or external account risk needs founder action."
        ),
        "example": "Provider spend has exceeded the configured founder review threshold.",
    },
    {
        "id": "routine-progress",
        "decision": "slack_only",
        "severity": "normal",
        "description": (
            "Routine work finished, normal status updates, or non-blocking research findings."
        ),
        "example": "Research Agent posted competitor notes and no founder action is needed.",
    },
    {
        "id": "agent-to-agent-coordination",
        "decision": "slack_only",
        "severity": "normal",
        "description": "Profiles need to coordinate, clarify ownership, or update Kanban state.",
        "example": "Engineering Manager asks Product Manager to narrow a requirement.",
    },
    {
        "id": "marketing-or-product-draft",
        "decision": "slack_only",
        "severity": "normal",
        "description": (
            "Draft copy, PRDs, research notes, or plans are ready for review but not blocked."
        ),
        "example": "Marketing Agent finished positioning options for the next founder review.",
    },
]


def telegram_policy_payload(
    setup_values: dict[str, str],
    schedules: list[dict],
) -> dict:
    founder_user = setup_values.get("founder_telegram_user_id", "")
    home_channel = setup_values.get("telegram_home_channel", "") or founder_user
    return {
        "title": "Telegram Urgent Policy",
        "owner_profile": "chief-of-staff",
        "allowed_sender_policy": "Only Chief of Staff should send Telegram alerts.",
        "founder_telegram_user_id": founder_user,
        "telegram_home_channel": home_channel,
        "token_destination": "chief-of-staff Hermes profile env file",
        "rules": TELEGRAM_ALERT_RULES,
        "standup_schedules": [
            {
                "id": schedule["id"],
                "name": schedule["name"],
                "active": bool(schedule.get("active", 1)),
                "time": f"{int(schedule['hour']):02d}:{int(schedule['minute']):02d}",
                "timezone": schedule["timezone"],
                "slack_channel": schedule["slack_channel"],
                "telegram_policy": schedule["telegram_policy"],
            }
            for schedule in schedules
        ],
        "verification": [
            "Founder Telegram user ID is captured as a non-secret setup input.",
            "Chief of Staff profile env file contains the Telegram token externally.",
            "Urgent smoke prompt sends exactly one Telegram message.",
            "Routine smoke prompt stays in Slack only.",
            "Messaging verification check is marked verified with non-secret evidence.",
        ],
    }


def telegram_policy_json(setup_values: dict[str, str], schedules: list[dict]) -> str:
    return json.dumps(telegram_policy_payload(setup_values, schedules), indent=2)


def telegram_policy_markdown(setup_values: dict[str, str], schedules: list[dict]) -> str:
    payload = telegram_policy_payload(setup_values, schedules)
    founder_user = payload["founder_telegram_user_id"] or "not captured"
    home_channel = payload["telegram_home_channel"] or "not captured"
    lines = [
        "# Telegram Urgent Policy",
        "",
        "Telegram is reserved for founder urgency. Routine company communication, "
        "agent coordination, and standup summaries stay in Slack unless a rule below "
        "requires founder action.",
        "",
        "## Ownership",
        "",
        "- Sending profile: `chief-of-staff` only",
        f"- Founder Telegram user ID: `{founder_user}`",
        f"- Telegram home channel/chat: `{home_channel}`",
        "- Token destination: Chief of Staff Hermes profile environment",
        "",
        "## Send Telegram",
        "",
    ]
    for rule in _rules(payload, "send_telegram"):
        lines.extend(_rule_lines(rule))
    lines.extend(["", "## Keep In Slack Only", ""])
    for rule in _rules(payload, "slack_only"):
        lines.extend(_rule_lines(rule))
    lines.extend(["", "## Standup Policies", ""])
    if payload["standup_schedules"]:
        for schedule in payload["standup_schedules"]:
            state = "active" if schedule["active"] else "paused"
            lines.extend(
                [
                    f"### {schedule['name']}",
                    "",
                    f"- State: `{state}`",
                    f"- Time: `{schedule['time']}` `{schedule['timezone']}`",
                    f"- Slack channel: `{schedule['slack_channel']}`",
                    f"- Telegram policy: {schedule['telegram_policy']}",
                    "",
                ]
            )
    else:
        lines.append("- No schedules are configured.")
    lines.extend(
        [
            "## Verification",
            "",
            *[f"- {item}" for item in payload["verification"]],
            "",
            "## Exports",
            "",
            "- JSON policy: `/setup/telegram-policy.json`",
            "- BotFather setup: `/setup/telegram-botfather.md`",
            "- Messaging verification: `/setup#messaging-verification`",
            "",
        ]
    )
    return "\n".join(lines)


def _rules(payload: dict, decision: str) -> list[dict]:
    return [rule for rule in payload["rules"] if rule["decision"] == decision]


def _rule_lines(rule: dict) -> list[str]:
    return [
        f"### {rule['id']}",
        "",
        f"- Severity: `{rule['severity']}`",
        f"- Rule: {rule['description']}",
        f"- Example: {rule['example']}",
        "",
    ]
