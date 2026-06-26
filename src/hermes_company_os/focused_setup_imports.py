from __future__ import annotations

FOCUSED_SETUP_IMPORTS = [
    {
        "id": "safe_input",
        "label": "Safe dashboard values",
        "phase": "foundation",
        "collects": "Founder name, workspace names, member IDs, and other non-secret setup values.",
        "template": "/setup/founder-input-request.md",
        "json_template": "/setup/founder-input-request.json",
        "collector_script": "/setup/founder-inputs.ps1",
        "dashboard_anchor": "/setup#input-import",
        "reply_post": "/setup/founder-input-reply",
    },
    {
        "id": "slack_channel",
        "label": "Slack channel IDs",
        "phase": "slack",
        "collects": (
            "Channel IDs for founder command, standup, product, research, "
            "engineering, marketing, QA, decisions, and alerts."
        ),
        "template": "/setup/slack-channel-template.md",
        "json_template": "/setup/slack-channel-template.json",
        "dashboard_anchor": "/setup#slack-channel-import",
        "reply_post": "/setup/slack-channel-reply",
    },
    {
        "id": "slack_bot_user",
        "label": "Slack bot user IDs",
        "phase": "slack",
        "collects": (
            "Installed bot user IDs for each Hermes profile after the Slack apps "
            "are installed."
        ),
        "template": "/setup/slack-bot-user-map-template.md",
        "json_template": "/setup/slack-bot-user-map-template.json",
        "dashboard_anchor": "/setup#slack-bot-user-import",
        "reply_post": "/setup/slack-bot-user-map-reply",
    },
    {
        "id": "telegram_recipient",
        "label": "Telegram recipient IDs",
        "phase": "telegram",
        "collects": (
            "Founder Telegram user and urgent alert chat IDs for Chief of Staff "
            "notifications."
        ),
        "template": "/setup/telegram-recipient-template.md",
        "json_template": "/setup/telegram-recipient-template.json",
        "dashboard_anchor": "/setup#telegram-recipient-import",
        "reply_post": "/setup/telegram-recipient-reply",
    },
    {
        "id": "schedule_config",
        "label": "Standup schedule configuration",
        "phase": "schedule",
        "collects": (
            "9 AM and 3 PM ET standup settings, active flags, delivery targets, "
            "and non-secret schedule preferences."
        ),
        "template": "/setup/schedule-config-template.md",
        "json_template": "/setup/schedule-config-template.json",
        "dashboard_anchor": "/setup#schedule-config-import",
        "reply_post": "/setup/schedule-config-reply",
    },
    {
        "id": "profile_personalization",
        "label": "Profile personalization",
        "phase": "profiles",
        "collects": (
            "No-secret role preferences for each Hermes profile, such as operating "
            "style and quality bars."
        ),
        "template": "/setup/profile-personalization-template.md",
        "json_template": "/setup/profile-personalization-template.json",
        "dashboard_anchor": "/setup#profile-personalization-import",
        "reply_post": "/setup/profile-personalization-reply",
    },
    {
        "id": "credential_status",
        "label": "External credential status",
        "phase": "credentials",
        "collects": "Status-only updates after credentials are loaded outside the dashboard.",
        "template": "/setup/credential-status-template.md",
        "json_template": "/setup/credential-status-template.json",
        "dashboard_anchor": "/setup#credential-status-import",
        "reply_post": "/setup/credential-status-reply",
    },
    {
        "id": "messaging_verification",
        "label": "Slack and Telegram verification",
        "phase": "messaging",
        "collects": (
            "Short no-secret evidence that profile messaging gateways work after "
            "external credentials are loaded."
        ),
        "template": "/setup/messaging-verification-template.md",
        "json_template": "/setup/messaging-verification-template.json",
        "dashboard_anchor": "/setup#messaging-verification",
        "reply_post": "/setup/messaging-verification-reply",
    },
    {
        "id": "kanban_verification",
        "label": "Kanban verification",
        "phase": "kanban",
        "collects": "Status and no-secret notes from Kanban board/list/card diagnostics.",
        "template": "/setup/kanban-verification-template.md",
        "json_template": "/setup/kanban-verification-template.json",
        "dashboard_anchor": "/setup#kanban-verification",
        "reply_post": "/setup/kanban-verification-reply",
    },
    {
        "id": "schedule_verification",
        "label": "Schedule verification",
        "phase": "schedule",
        "collects": "Status and no-secret notes after standup jobs are provisioned and tested.",
        "template": "/setup/schedule-verification-template.md",
        "json_template": "/setup/schedule-verification-template.json",
        "dashboard_anchor": "/setup#schedule-verification",
        "reply_post": "/setup/schedule-verification-reply",
    },
    {
        "id": "llm_preference",
        "label": "LLM provider and model preferences",
        "phase": "llm",
        "collects": (
            "No-secret provider and model selections; real provider access stays "
            "outside the dashboard and happens last."
        ),
        "template": "/setup/llm-preference-template.md",
        "json_template": "/setup/llm-preference-template.json",
        "dashboard_anchor": "/setup#llm-preference-import",
        "reply_post": "/setup/llm-preference-reply",
    },
    {
        "id": "profile_acceptance",
        "label": "Profile acceptance results",
        "phase": "acceptance",
        "collects": (
            "Pass, fail, or blocked outcomes from role-specific acceptance prompts "
            "after live profile smoke checks."
        ),
        "template": "/setup/profile-acceptance-template.md",
        "json_template": "/setup/profile-acceptance-template.json",
        "dashboard_anchor": "/setup#profile-acceptance-tracking",
        "reply_post": "/setup/profile-acceptance-reply",
    },
]


def focused_setup_imports() -> list[dict[str, str]]:
    return [dict(item) for item in FOCUSED_SETUP_IMPORTS]


def focused_setup_entry_points() -> dict[str, str]:
    routes: dict[str, str] = {}
    for item in FOCUSED_SETUP_IMPORTS:
        routes[f"{item['id']}_template"] = item["template"]
        routes[f"{item['id']}_json"] = item["json_template"]
        routes[f"{item['id']}_dashboard"] = item["dashboard_anchor"]
        if "collector_script" in item:
            routes[f"{item['id']}_collector"] = item["collector_script"]
    return routes


def focused_setup_markdown_lines(imports: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for item in imports:
        lines.extend(
            [
                f"- {item['label']} (`{item['phase']}`): {item['collects']}",
                f"  Template: `{item['template']}`",
                f"  Dashboard: `{item['dashboard_anchor']}`",
            ]
        )
        if "collector_script" in item:
            lines.append(f"  Collector: `{item['collector_script']}`")
    return lines
