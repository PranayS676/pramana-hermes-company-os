from __future__ import annotations

import json
import re

from hermes_company_os.setup_artifacts import (
    CHANNEL_INPUT_BY_AGENT,
    SLACK_EVENTS,
    SLACK_SCOPES,
)

ACCENT_BY_ROLE = {
    "Engineering": "#2563EB",
    "Marketing": "#DB2777",
    "Orchestrator": "#059669",
    "Product": "#7C3AED",
    "Research": "#0891B2",
    "Review": "#EA580C",
}


def slack_app_manifest(agent: dict, setup_values: dict[str, str]) -> dict:
    home_channel_id = setup_values.get(CHANNEL_INPUT_BY_AGENT.get(agent["id"], ""), "")
    home_channel = home_channel_id or agent["slack_channel"]
    app_name = f"Hermes {_clean_name(agent['name'])}"
    role = agent["role"]
    description = (
        f"{agent['name']} Hermes profile bot for {role.lower()} work in Hermes Company OS."
    )
    long_description = (
        f"{app_name} is the Slack bot facade for the {agent['name']} Hermes profile. "
        "It receives founder and team messages, routes work to the matching Hermes "
        "profile command, posts concise progress updates, and keeps secrets outside "
        "the dashboard. Use this app with Socket Mode, a per-profile bot token, and "
        f"the profile home channel {home_channel}."
    )
    return {
        "_metadata": {"major_version": 2, "minor_version": 1},
        "display_information": {
            "name": app_name,
            "description": description,
            "long_description": long_description,
            "background_color": ACCENT_BY_ROLE.get(role, "#334155"),
        },
        "features": {
            "bot_user": {
                "display_name": app_name,
                "always_online": True,
            },
        },
        "oauth_config": {
            "scopes": {
                "bot": SLACK_SCOPES,
            },
        },
        "settings": {
            "event_subscriptions": {
                "bot_events": SLACK_EVENTS,
            },
            "interactivity": {
                "is_enabled": True,
            },
            "org_deploy_enabled": False,
            "socket_mode_enabled": True,
            "token_rotation_enabled": False,
        },
    }


def slack_app_manifest_json(agent: dict, setup_values: dict[str, str]) -> str:
    return json.dumps(slack_app_manifest(agent, setup_values), indent=2) + "\n"


def slack_app_manifests_bundle_json(
    agents: list[dict],
    setup_values: dict[str, str],
) -> str:
    bundle = {
        agent["id"]: {
            "profile": {
                "id": agent["id"],
                "name": agent["name"],
                "hermes_command": agent["hermes_command"],
                "home_channel": agent["slack_channel"],
                "home_channel_id": setup_values.get(
                    CHANNEL_INPUT_BY_AGENT.get(agent["id"], ""),
                    "",
                ),
            },
            "manifest": slack_app_manifest(agent, setup_values),
        }
        for agent in agents
    }
    return json.dumps(bundle, indent=2) + "\n"


def _clean_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()
