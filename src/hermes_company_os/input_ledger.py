from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.focused_setup_imports import (
    focused_setup_entry_points,
    focused_setup_imports,
    focused_setup_markdown_lines,
)

READY_SECRET_STATUSES = {"loaded", "verified"}


def input_ledger_payload(
    *,
    setup_inputs: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
) -> dict:
    safe_inputs = [
        _safe_input(item) for item in setup_inputs if item["secret_policy"] == "non_secret"
    ]
    deferred_preferences = [
        _deferred_preference(item)
        for item in setup_inputs
        if item["secret_policy"] != "non_secret"
    ]
    external_credentials = [_external_credential(item) for item in secret_requirements]
    focused_imports = focused_setup_imports()
    return {
        "title": "Founder Input Ledger",
        "credential_boundary": (
            "This ledger asks for safe dashboard values and status-only external "
            "credential updates. Do not paste Slack tokens, Telegram bot tokens, "
            "provider API keys, OAuth payloads, request headers, private endpoints, "
            "raw logs, or profile outputs into this dashboard."
        ),
        "verification_last": True,
        "summary": {
            "safe_inputs": _status_summary(safe_inputs),
            "external_credentials": _status_summary(external_credentials),
            "messaging_checks": _status_summary(messaging_checks),
            "schedule_checks": _status_summary(
                [check for check in schedule_checks if check.get("schedule_active", 1)]
            ),
            "kanban_checks": _status_summary(kanban_checks),
            "model_preferences": _status_summary(model_preferences),
            "integrations": _status_summary(integrations),
        },
        "safe_dashboard_inputs": safe_inputs,
        "deferred_external_preferences": deferred_preferences,
        "external_credentials_status_only": external_credentials,
        "founder_questions": _founder_questions(
            safe_inputs,
            deferred_preferences,
            external_credentials,
        ),
        "phase_unlocks": _phase_unlocks(
            safe_inputs=safe_inputs,
            external_credentials=external_credentials,
            messaging_checks=messaging_checks,
            schedule_checks=schedule_checks,
            kanban_checks=kanban_checks,
            model_preferences=model_preferences,
            integrations=integrations,
        ),
        "reply_templates": {
            "safe_inputs": _safe_input_reply_lines(safe_inputs),
            "credential_status": _credential_status_reply_lines(external_credentials),
        },
        "focused_setup_imports": focused_imports,
        "entry_points": {
            "input_import": "/setup/inputs#input-import",
            "safe_inputs": "/setup/inputs#inputs",
            "credential_status_import": "/setup/messaging#credential-status-import",
            "founder_input_request": "/setup/founder-input-request.md",
            "founder_handoff": "/setup/founder-handoff.md",
            "credential_loading": "/setup/credential-loading.md",
            "activation_sequence": "/setup/activation-sequence.md",
            "live_verification": "/setup/live-verification.md",
            **focused_setup_entry_points(),
        },
    }


def input_ledger_json(**kwargs) -> str:
    return json.dumps(input_ledger_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def input_ledger_markdown(**kwargs) -> str:
    payload = input_ledger_payload(**kwargs)
    lines = [
        "# Founder Input Ledger",
        "",
        "Use this as the current list of what I need from you, what can wait, "
        "and what each input unlocks.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Summary",
        "",
        _summary_line("Safe dashboard inputs", payload["summary"]["safe_inputs"]),
        _summary_line(
            "External credential statuses",
            payload["summary"]["external_credentials"],
        ),
        _summary_line("Messaging checks", payload["summary"]["messaging_checks"]),
        _summary_line("Schedule checks", payload["summary"]["schedule_checks"]),
        _summary_line("Kanban checks", payload["summary"]["kanban_checks"]),
        _summary_line("LLM model preferences", payload["summary"]["model_preferences"]),
        "",
        "## Questions For You",
        "",
    ]
    if payload["founder_questions"]:
        for question in payload["founder_questions"]:
            lines.append(
                f"- `{question['priority']}` {question['question']} "
                f"Route: `{question['route']}`"
            )
    else:
        lines.append("- No open founder input questions right now.")
    lines.extend(
        [
            "",
            "## Safe Dashboard Inputs",
            "",
        ]
    )
    for item in payload["safe_dashboard_inputs"]:
        lines.append(
            f"- `{item['key']}` ({item['group']}): `{item['status']}`; "
            f"{item['label']}. {item['help_text']}"
        )
    lines.extend(
        [
            "",
            "## External Credential Status Only",
            "",
        ]
    )
    for item in payload["external_credentials_status_only"]:
        lines.append(
            f"- `{item['id']}` ({item['category']}): `{item['status']}`; "
            f"{item['label']} for {item['owner']}. Status updates only."
        )
    lines.extend(["", "## Phase Unlocks", ""])
    for phase in payload["phase_unlocks"]:
        lines.extend(
            [
                f"### {phase['name']}",
                "",
                f"- Status: `{phase['status']}`",
                f"- Can continue now: {'yes' if phase['can_continue_now'] else 'no'}",
                f"- Reason: {phase['reason']}",
                f"- Next route: `{phase['next_route']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Safe Reply Template",
            "",
            "```text",
            *payload["reply_templates"]["safe_inputs"],
            "```",
            "",
            "## Credential Status Reply Template",
            "",
            "```text",
            *payload["reply_templates"]["credential_status"],
            "```",
            "",
            "## Focused Setup Reply Templates",
            "",
            *focused_setup_markdown_lines(payload["focused_setup_imports"]),
            "",
            "## Entry Points",
            "",
        ]
    )
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def _safe_input(item: dict) -> dict:
    value = item["value"].strip()
    required = bool(item["required"])
    return {
        "key": item["key"],
        "group": item["group_name"],
        "label": item["label"],
        "required": required,
        "status": "captured" if value else "missing",
        "value": value,
        "help_text": item["help_text"],
        "route": "/setup/inputs#inputs",
        "can_continue_without": not required,
    }


def _deferred_preference(item: dict) -> dict:
    value = item["value"].strip()
    return {
        "key": item["key"],
        "group": item["group_name"],
        "label": item["label"],
        "status": "captured" if value else "deferred",
        "help_text": item["help_text"],
        "route": "/setup/inputs#inputs",
        "store_value_here": False,
    }


def _external_credential(item: dict) -> dict:
    owner = item.get("owner_name") or item.get("owner_agent_id") or "unassigned"
    return {
        "id": item["id"],
        "category": item["category"],
        "label": item["label"],
        "owner": owner,
        "destination": item["destination"],
        "status": item["status"],
        "route": "/setup/messaging#secret-status",
        "status_only": True,
    }


def _founder_questions(
    safe_inputs: list[dict],
    deferred_preferences: list[dict],
    external_credentials: list[dict],
) -> list[dict]:
    questions = []
    for item in safe_inputs:
        if item["status"] == "missing" and item["required"]:
            questions.append(
                {
                    "priority": "now",
                    "phase": item["group"],
                    "question": (
                        f"Please provide {item['label']} (`{item['key']}`). "
                        f"{item['help_text']}"
                    ),
                    "route": item["route"],
                }
            )
    for item in safe_inputs:
        if item["status"] == "missing" and not item["required"]:
            questions.append(
                {
                    "priority": "optional",
                    "phase": item["group"],
                    "question": (
                        f"Optional: provide {item['label']} (`{item['key']}`). "
                        f"{item['help_text']}"
                    ),
                    "route": item["route"],
                }
            )
    open_credentials = [
        item for item in external_credentials if item["status"] not in READY_SECRET_STATUSES
    ]
    for category in sorted({item["category"] for item in open_credentials}):
        questions.append(
            {
                "priority": "status-only",
                "phase": category,
                "question": (
                    f"After loading {category} credentials externally, tell me "
                    "`loaded` or `verified` status only. Do not send credential values."
                ),
                "route": "/setup/messaging#credential-status-import",
            }
        )
    if any(item["status"] == "deferred" for item in deferred_preferences):
        questions.append(
            {
                "priority": "later",
                "phase": "llm",
                "question": (
                    "LLM provider and API-key verification stay last; provider "
                    "preferences can be chosen after messaging, scheduling, and Kanban."
                ),
                "route": "/setup/llm-provisioning.md",
            }
        )
    return questions


def _phase_unlocks(
    *,
    safe_inputs: list[dict],
    external_credentials: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
) -> list[dict]:
    required_missing = [
        item for item in safe_inputs if item["required"] and item["status"] == "missing"
    ]
    slack_open = _open_credentials(external_credentials, "slack")
    telegram_open = _open_credentials(external_credentials, "telegram")
    llm_open = _open_credentials(external_credentials, "llm")
    active_schedule_checks = [
        check for check in schedule_checks if check.get("schedule_active", 1)
    ]
    return [
        _phase(
            "profiles",
            "Starter Hermes profiles",
            not required_missing,
            f"{len(required_missing)} required safe inputs missing.",
            "/setup/bootstrap.ps1",
        ),
        _phase(
            "slack",
            "Slack workspace and profile bots",
            not slack_open,
            f"{len(slack_open)} Slack credential statuses open.",
            "/setup/slack-provisioning.md",
        ),
        _phase(
            "telegram",
            "Chief of Staff Telegram urgent alerts",
            not telegram_open,
            f"{len(telegram_open)} Telegram credential statuses open.",
            "/setup/telegram-provisioning.md",
        ),
        _phase(
            "kanban",
            "Kanban coordination",
            _all_verified(kanban_checks),
            f"{_open_count(kanban_checks)} Kanban verification checks open.",
            "/setup/kanban-provisioning.md",
        ),
        _phase(
            "schedule",
            "Twice-daily standups",
            _all_verified(active_schedule_checks),
            f"{_open_count(active_schedule_checks)} active schedule checks open.",
            "/setup/schedule-provisioning.md",
        ),
        _phase(
            "llm",
            "LLM provider credentials and profile smoke",
            not llm_open and _all_status(model_preferences, {"verified"}),
            f"{len(llm_open)} LLM credential statuses open; "
            f"{_open_count(model_preferences, ready={'verified'})} profile smoke checks open.",
            "/setup/llm-provisioning.md",
        ),
        _phase(
            "acceptance",
            "Role acceptance prompts",
            _integration_ready(integrations, "runtime")
            and _all_status(model_preferences, {"verified"}),
            "Requires runtime integration ready and every profile smoke check verified.",
            "/setup/profile-acceptance.md",
        ),
    ]


def _phase(
    phase_id: str,
    name: str,
    can_continue_now: bool,
    reason: str,
    next_route: str,
) -> dict:
    return {
        "id": phase_id,
        "name": name,
        "status": "ready" if can_continue_now else "waiting",
        "can_continue_now": can_continue_now,
        "reason": reason,
        "next_route": next_route,
    }


def _status_summary(items: list[dict]) -> dict:
    return {
        "total": len(items),
        "status": dict(Counter(item["status"] for item in items)),
    }


def _summary_line(label: str, summary: dict) -> str:
    counts = summary["status"]
    if not counts:
        formatted = "none"
    else:
        formatted = ", ".join(
            f"{status}={count}" for status, count in sorted(counts.items())
        )
    return f"- {label}: total={summary['total']}, {formatted}"


def _open_credentials(credentials: list[dict], category: str) -> list[dict]:
    return [
        item
        for item in credentials
        if item["category"] == category and item["status"] not in READY_SECRET_STATUSES
    ]


def _all_verified(checks: list[dict]) -> bool:
    return bool(checks) and all(check["status"] == "verified" for check in checks)


def _all_status(items: list[dict], ready: set[str]) -> bool:
    return bool(items) and all(item["status"] in ready for item in items)


def _open_count(items: list[dict], ready: set[str] | None = None) -> int:
    ready_statuses = ready or {"verified"}
    return len([item for item in items if item["status"] not in ready_statuses])


def _integration_ready(integrations: list[dict], category: str) -> bool:
    relevant = [item for item in integrations if item["category"] == category]
    return bool(relevant) and all(
        item["status"] in {"configured", "ready"} for item in relevant
    )


def _safe_input_reply_lines(inputs: list[dict]) -> list[str]:
    lines = [
        f"{item['key']}={item['value']}  # {item['label']}"
        for item in inputs
    ]
    return lines or ["# No safe dashboard inputs tracked."]


def _credential_status_reply_lines(credentials: list[dict]) -> list[str]:
    lines = [
        f"{item['id']}={item['status']} | status note only"
        for item in credentials
    ]
    return lines or ["# No external credential statuses tracked."]
