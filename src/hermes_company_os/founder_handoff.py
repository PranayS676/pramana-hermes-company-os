from __future__ import annotations

import json
from collections import defaultdict

from hermes_company_os.focused_setup_imports import (
    focused_setup_entry_points,
    focused_setup_imports,
    focused_setup_markdown_lines,
)


def founder_handoff_payload(
    *,
    setup_inputs: list[dict],
    secret_requirements: list[dict],
    model_preferences: list[dict],
) -> dict:
    safe_inputs = [
        _safe_input(item) for item in setup_inputs if item["secret_policy"] == "non_secret"
    ]
    deferred_preferences = [
        _deferred_preference(item)
        for item in setup_inputs
        if item["secret_policy"] != "non_secret"
    ]
    secrets = [_secret_requirement(item) for item in secret_requirements]
    focused_imports = focused_setup_imports()
    return {
        "title": "Founder Return Packet",
        "credential_boundary": (
            "This packet is for collecting non-secret dashboard values and "
            "status-only external credential updates. Do not paste Slack tokens, "
            "Telegram bot tokens, provider API keys, OAuth payloads, request "
            "headers, private endpoints, raw logs, or profile outputs into the "
            "dashboard."
        ),
        "safe_dashboard_reply_template": [
            _reply_line(item) for item in safe_inputs
        ],
        "safe_dashboard_inputs": safe_inputs,
        "deferred_preferences": deferred_preferences,
        "external_credentials_to_load": _grouped_secrets(secrets),
        "credential_status_reply_template": [
            f"{item['id']}={item['status']} | status note only" for item in secrets
        ],
        "focused_setup_imports": focused_imports,
        "llm_profiles": [
            {
                "agent_id": preference["agent_id"],
                "agent_name": preference.get("agent_name", preference["agent_id"]),
                "provider": preference["provider"],
                "model": preference["model"],
                "status": preference["status"],
                "llm_env": f"/setup/profile-llm-env/{preference['agent_id']}.env",
                "config": f"/setup/profile-config/{preference['agent_id']}.yaml",
            }
            for preference in model_preferences
        ],
        "return_steps": [
            "Paste safe dashboard values into `/setup#input-import`.",
            "Use the focused setup reply templates for Slack channel IDs, Slack bot "
            "user IDs, Telegram recipient IDs, schedule settings, verification, and "
            "profile personalization.",
            "Load Slack and Telegram credentials into the real Hermes profile env files.",
            "Run `/setup/secret-audit.ps1 -PostDashboardStatus`.",
            "Run `/setup/gateway-operations.ps1 -CheckCommands`, then setup/start gateways.",
            "Complete `/setup#messaging-verification` with short non-secret evidence.",
            "Run Kanban diagnostics and complete `/setup#kanban-verification`.",
            "Verify standups and complete `/setup#schedule-verification`.",
            "Review `/setup/llm-provisioning.md`, load LLM provider credentials last, "
            "then run `/setup/llm-finalize.md`.",
            "Review `/setup/verification-evidence.md` and `/setup/live-verification.md`.",
        ],
        "entry_points": {
            "input_import": "/setup#input-import",
            "credential_loading": "/setup/credential-loading.md",
            "credential_status_import": "/setup#credential-status-import",
            "gateway_operations": "/setup/gateway-operations.md",
            "secret_audit": "/setup/secret-audit.md",
            "messaging_verification": "/setup#messaging-verification",
            "kanban_verification": "/setup#kanban-verification",
            "schedule_verification": "/setup#schedule-verification",
            "llm_provisioning": "/setup/llm-provisioning.md",
            "llm_finalization": "/setup/llm-finalize.md",
            "verification_evidence": "/setup/verification-evidence.md",
            "live_verification": "/setup/live-verification.md",
            **focused_setup_entry_points(),
        },
    }


def founder_handoff_json(**kwargs) -> str:
    return json.dumps(founder_handoff_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def founder_handoff_markdown(**kwargs) -> str:
    payload = founder_handoff_payload(**kwargs)
    lines = [
        "# Founder Return Packet",
        "",
        "Use this when you come back with workspace IDs, external credential status, "
        "and live verification updates.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Safe Dashboard Reply Template",
        "",
        "```text",
        *payload["safe_dashboard_reply_template"],
        "```",
        "",
        "## External Credentials To Load Outside This Dashboard",
        "",
    ]
    for category, items in payload["external_credentials_to_load"].items():
        lines.extend([f"### {category.title()}", ""])
        for item in items:
            lines.extend(
                [
                    f"- `{item['id']}`: {item['label']}",
                    f"  Owner: {item['owner']}",
                    f"  Destination: {item['destination']}",
                    f"  Env key label: `{item['environment_key']}`",
                    f"  Current status: `{item['status']}`",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Credential Status Reply Template",
            "",
            "```text",
            *payload["credential_status_reply_template"],
            "```",
            "",
            "## Focused Setup Reply Templates",
            "",
            *focused_setup_markdown_lines(payload["focused_setup_imports"]),
            "",
            "## LLM Profiles To Configure Last",
            "",
        ]
    )
    for profile in payload["llm_profiles"]:
        lines.append(
            f"- {profile['agent_name']} (`{profile['agent_id']}`): "
            f"`{profile['provider']}` / `{profile['model']}`; "
            f"env `{profile['llm_env']}`; config `{profile['config']}`"
        )
    lines.extend(["", "## Return Steps", ""])
    for index, step in enumerate(payload["return_steps"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Entry Points", ""])
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def _safe_input(item: dict) -> dict:
    value = item["value"].strip()
    return {
        "key": item["key"],
        "group": item["group_name"],
        "label": item["label"],
        "required": bool(item["required"]),
        "status": "captured" if value else "missing",
        "value": value,
        "help_text": item["help_text"],
    }


def _deferred_preference(item: dict) -> dict:
    return {
        "key": item["key"],
        "group": item["group_name"],
        "label": item["label"],
        "status": "captured" if item["value"].strip() else "deferred",
        "help_text": item["help_text"],
    }


def _secret_requirement(item: dict) -> dict:
    return {
        "id": item["id"],
        "category": item["category"],
        "label": item["label"],
        "owner": item.get("owner_name") or item.get("owner_agent_id") or "unassigned",
        "destination": item["destination"],
        "environment_key": item["environment_key"],
        "status": item["status"],
    }


def _grouped_secrets(secrets: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in secrets:
        grouped[item["category"]].append(item)
    return dict(sorted(grouped.items()))


def _reply_line(item: dict) -> str:
    requirement = "required" if item["required"] else "optional"
    return f"{item['key']}={item['value']}  # {item['label']} ({requirement})"
