from __future__ import annotations

import re

TELEGRAM_COMMANDS = [
    ("start", "Identify the urgent-only Hermes founder alert bot"),
    ("help", "Show the urgent alert policy and allowed founder commands"),
    ("status", "Request the latest company operating status"),
    ("approve", "Record a founder approval for a named decision"),
    ("blocker", "Escalate a founder-blocking issue to Chief of Staff"),
]


def telegram_botfather_setup_markdown(setup_values: dict[str, str]) -> str:
    founder_user = setup_values.get("founder_telegram_user_id") or "REPLACE_WITH_USER_ID"
    home_channel = setup_values.get("telegram_home_channel") or founder_user
    username = suggested_bot_username(setup_values)
    command_lines = [f"{command} - {description}" for command, description in TELEGRAM_COMMANDS]
    return "\n".join(
        [
            "# Telegram BotFather Setup Sheet",
            "",
            "Telegram is urgent-only. Configure one bot for the Chief of Staff profile; "
            "routine agent updates stay in Slack.",
            "",
            "## Bot Identity",
            "",
            "- Display name: `Hermes Chief of Staff`",
            f"- Suggested username: `{username}`",
            "- Owner profile: `chief-of-staff`",
            "- Purpose: founder approval requests, blockers, failed scheduled operations",
            "",
            "## BotFather Conversation",
            "",
            "1. Open `@BotFather` in Telegram.",
            "2. Send `/newbot`.",
            "3. Use `Hermes Chief of Staff` as the display name.",
            f"4. Use `{username}` as the username, or any available username ending in `bot`.",
            "5. Store the returned token only in the Chief of Staff Hermes profile `.env`.",
            "6. Do not paste the token into this dashboard.",
            "7. Run `/mybots`, select the bot, then set description, about text, "
            "and commands using the sections below.",
            "",
            "## Description",
            "",
            "Urgent founder alert bot for Hermes Company OS. Used by the Chief of Staff "
            "profile only for approvals, blockers, failed runs, and schedule failures.",
            "",
            "## About Text",
            "",
            "Hermes Chief of Staff urgent founder alerts.",
            "",
            "## Commands To Register",
            "",
            "```text",
            *command_lines,
            "```",
            "",
            "## Chief Of Staff `.env` Values",
            "",
            "```text",
            "TELEGRAM_BOT_TOKEN=REPLACE_WITH_BOTFATHER_TOKEN",
            f"TELEGRAM_ALLOWED_USERS={founder_user}",
            f"TELEGRAM_HOME_CHANNEL={home_channel}",
            "```",
            "",
            "## Manual Smoke Prompts",
            "",
            "### Should Trigger Telegram",
            "",
            "```text",
            "Send an urgent Telegram alert to the founder: the company standup cron failed "
            "and needs founder approval before retrying. Keep the message short and mark "
            "it as urgent.",
            "```",
            "",
            "Expected result: the Chief of Staff profile sends one Telegram alert to the "
            "configured founder/home chat and records non-secret evidence in "
            "`/setup#messaging-verification`.",
            "",
            "### Should Stay In Slack Only",
            "",
            "```text",
            "Post a routine progress update for today's research and engineering work. "
            "No founder action is needed.",
            "```",
            "",
            "Expected result: no Telegram message is sent; the update stays in Slack.",
            "",
            "## Verification",
            "",
            "- Founder Telegram user ID is recorded in `/setup` as a non-secret value.",
            "- Token is loaded only in the Chief of Staff Hermes profile `.env`.",
            "- Chief of Staff gateway starts without exposing the token in logs.",
            "- Urgent smoke prompt sends exactly one founder alert.",
            "- Routine smoke prompt sends no Telegram message.",
            "- `/setup#messaging-verification` has the Chief of Staff Telegram check marked "
            "`verified` with non-secret evidence.",
            "",
        ]
    )


def suggested_bot_username(setup_values: dict[str, str]) -> str:
    workspace = setup_values.get("slack_workspace_name", "")
    slug = re.sub(r"[^a-z0-9_]+", "_", workspace.lower()).strip("_")
    if slug:
        slug = slug[:12].strip("_")
        return f"hermes_{slug}_chief_bot"
    return "hermes_chief_of_staff_bot"
