from __future__ import annotations

CHANNEL_INPUT_BY_AGENT = {
    "chief-of-staff": "slack_channel_founder_command",
    "product-manager": "slack_channel_product",
    "research-agent": "slack_channel_research",
    "engineering-manager": "slack_channel_engineering",
    "backend-engineer": "slack_channel_engineering",
    "frontend-engineer": "slack_channel_engineering",
    "cloud-infra-agent": "slack_channel_engineering",
    "test-automation-agent": "slack_channel_engineering",
    "marketing-agent": "slack_channel_marketing",
    "qa-critic": "slack_channel_qa_review",
}

PROFILE_ROOT_LABEL = "$env:HERMES_HOME\\profiles"


def activation_commands(agents: list[dict], setup_values: dict[str, str]) -> list[dict]:
    commands = []
    for agent in agents:
        commands.append(
            {
                "agent": agent["name"],
                "profile_id": agent["id"],
                "env": _env_commands(agent, setup_values),
                "model": f"{agent['hermes_command']} model",
                "config_template": f"/setup/profile-config/{agent['id']}.yaml",
                "setup": f"{agent['hermes_command']} gateway setup",
                "start": f"{agent['hermes_command']} gateway start",
                "install": f"{agent['hermes_command']} gateway install",
            }
        )
    return commands


def cron_commands(
    setup_values: dict[str, str],
    schedules: list[dict] | None = None,
) -> list[str]:
    cadence = setup_values.get("standup_cadence", "every day").strip() or "every day"
    if cadence.lower() in {"weekday", "weekdays", "business days"}:
        schedule_prefix = "every weekday"
    else:
        schedule_prefix = "every day"
    active_schedules = [
        schedule for schedule in _default_schedules(schedules) if schedule.get("active", 1)
    ]
    return [_cron_command(schedule_prefix, schedule) for schedule in active_schedules]


def missing_required_inputs(setup_inputs: list[dict]) -> list[dict]:
    return [
        item
        for item in setup_inputs
        if item["required"]
        and item["secret_policy"] == "non_secret"
        and not item["value"].strip()
    ]


def _env_commands(agent: dict, setup_values: dict[str, str]) -> list[str]:
    profile_path = f"{PROFILE_ROOT_LABEL}\\{agent['id']}\\.env"
    channel_key = CHANNEL_INPUT_BY_AGENT[agent["id"]]
    channel_id = setup_values.get(channel_key, "")
    allowed_users = setup_values.get("founder_slack_member_id", "")
    commands = [
        f"# Edit {profile_path}",
        f"SLACK_ALLOWED_USERS={allowed_users or 'U_REPLACE_WITH_FOUNDER_MEMBER_ID'}",
        f"SLACK_HOME_CHANNEL={channel_id or 'C_REPLACE_WITH_CHANNEL_ID'}",
        f"SLACK_HOME_CHANNEL_NAME={agent['slack_channel'].lstrip('#')}",
        "SLACK_BOT_TOKEN=TODO",
        "SLACK_APP_TOKEN=TODO",
    ]
    if agent["id"] == "chief-of-staff":
        telegram_user = setup_values.get("founder_telegram_user_id", "")
        telegram_home = setup_values.get("telegram_home_channel", "") or telegram_user
        telegram_allowed_users = telegram_user or "REPLACE_WITH_FOUNDER_TELEGRAM_USER_ID"
        commands.extend(
            [
                "TELEGRAM_BOT_TOKEN=TODO",
                f"TELEGRAM_ALLOWED_USERS={telegram_allowed_users}",
                f"TELEGRAM_HOME_CHANNEL={telegram_home or 'REPLACE_WITH_HOME_CHAT_ID'}",
            ]
        )
    return commands


def _default_schedules(schedules: list[dict] | None) -> list[dict]:
    if schedules is not None:
        return schedules
    return [
        {
            "name": "morning company standup",
            "hour": 9,
            "minute": 0,
            "slack_channel": "#agent-standup",
            "telegram_policy": "founder approvals, blockers, failed runs, or urgent decisions",
            "active": 1,
        },
        {
            "name": "afternoon company standup",
            "hour": 15,
            "minute": 0,
            "slack_channel": "#agent-standup",
            "telegram_policy": "urgent founder alerts",
            "active": 1,
        },
    ]


def _cron_command(schedule_prefix: str, schedule: dict) -> str:
    schedule_time = _schedule_time(int(schedule["hour"]), int(schedule["minute"]))
    name = str(schedule["name"]).strip()
    slack_channel = str(schedule["slack_channel"]).strip()
    telegram_policy = str(schedule["telegram_policy"]).strip()
    prompt = (
        f"Run the {name}. Post the full summary to Slack {slack_channel}. "
        f"Send Telegram only for {telegram_policy}."
    )
    return f'chief-of-staff cron create "{schedule_prefix} at {schedule_time}" "{prompt}"'


def _schedule_time(hour: int, minute: int) -> str:
    suffix = "am" if hour < 12 else "pm"
    hour_12 = hour % 12 or 12
    if minute:
        return f"{hour_12}:{minute:02d}{suffix}"
    return f"{hour_12}{suffix}"
