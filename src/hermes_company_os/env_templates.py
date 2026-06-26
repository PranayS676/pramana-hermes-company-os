from __future__ import annotations


def profile_env_template(agent: dict, setup_values: dict[str, str] | None = None) -> str:
    values = setup_values or {}
    founder_slack_id = values.get("founder_slack_member_id") or "U_REPLACE_WITH_FOUNDER_MEMBER_ID"
    channel_id = _channel_id_for_agent(agent, values) or "C_REPLACE_WITH_CHANNEL_ID"
    lines = [
        f"# Hermes profile .env template for {agent['name']}",
        "# Store this in the profile's Hermes .env file, not in this dashboard repo.",
        "",
        "# LLM provider is configured last.",
        "# OPENAI_API_KEY=",
        "# OPENROUTER_API_KEY=",
        "# ANTHROPIC_API_KEY=",
        "",
        "# Slack Socket Mode",
        "SLACK_BOT_TOKEN=TODO",
        "SLACK_APP_TOKEN=TODO",
        f"SLACK_ALLOWED_USERS={founder_slack_id}",
        f"SLACK_HOME_CHANNEL_NAME={agent['slack_channel'].lstrip('#')}",
        f"SLACK_HOME_CHANNEL={channel_id}",
        "",
    ]
    if agent["id"] == "chief-of-staff":
        telegram_user = (
            values.get("founder_telegram_user_id")
            or "REPLACE_WITH_FOUNDER_TELEGRAM_USER_ID"
        )
        telegram_home = values.get("telegram_home_channel") or telegram_user
        lines.extend(
            [
                "# Telegram urgent founder alerts",
                "TELEGRAM_BOT_TOKEN=TODO",
                f"TELEGRAM_ALLOWED_USERS={telegram_user}",
                f"TELEGRAM_HOME_CHANNEL={telegram_home}",
                "",
            ]
        )
    return "\n".join(lines)


def _channel_id_for_agent(agent: dict, values: dict[str, str]) -> str:
    mapping = {
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
    return values.get(mapping[agent["id"]], "")
