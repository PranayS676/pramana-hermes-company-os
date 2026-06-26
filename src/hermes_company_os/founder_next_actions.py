from __future__ import annotations

import json
from collections import Counter, defaultdict

from hermes_company_os.activation_report import activation_summary
from hermes_company_os.activation_sequence import next_best_action
from hermes_company_os.focused_setup_imports import (
    focused_setup_entry_points,
    focused_setup_imports,
    focused_setup_markdown_lines,
)
from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES


def founder_next_actions_payload(
    *,
    activation_checks: list[dict],
    setup_inputs: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    runtime_checks: list[dict] | None = None,
    profile_acceptance_checks: list[dict] | None = None,
    profile_installation_checks: list[dict] | None = None,
    founder_decisions: list[dict] | None = None,
) -> dict:
    summary = activation_summary(activation_checks)
    decisions = founder_decisions or []
    return {
        "title": "Founder Next Actions",
        "credential_boundary": (
            "This packet requests only non-secret setup values and status updates. "
            "Do not paste Slack tokens, Telegram bot tokens, provider API keys, OAuth "
            "payloads, private endpoint credentials, or raw logs into the dashboard."
        ),
        "activation_summary": summary,
        "next_best_action": next_best_action(
            activation_checks,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            model_preferences,
            integrations,
        ),
        "missing_dashboard_inputs": [
            _setup_input(item)
            for item in setup_inputs
            if item["required"]
            and item["secret_policy"] == "non_secret"
            and not item["value"].strip()
        ],
        "optional_dashboard_inputs": [
            _setup_input(item)
            for item in setup_inputs
            if not item["required"]
            and item["secret_policy"] == "non_secret"
            and not item["value"].strip()
        ],
        "external_secret_status": _external_secret_status(secret_requirements),
        "verification_work": {
            "messaging": _verification_summary(messaging_checks),
            "schedule": _verification_summary(schedule_checks),
            "kanban": _verification_summary(kanban_checks),
            "llm_profiles": _model_summary(model_preferences),
            "profile_installation": _verification_summary(
                profile_installation_checks or []
            ),
            "profile_acceptance": _verification_summary(
                profile_acceptance_checks or []
            ),
        },
        "local_runtime": _local_runtime_summary(runtime_checks or []),
        "founder_decisions": _decision_summary(decisions),
        "integration_status": _status_counts(integrations),
        "focused_setup_imports": focused_setup_imports(),
        "entry_points": {
            "founder_decisions": "/setup/founder-decisions.md",
            "first_run": "/setup/first-run.md",
            "first_run_runner": "/setup/first-run.ps1",
            "progress_board": "/setup/progress-board.md",
            "progress_board_json": "/setup/progress-board.json",
            "input_ledger": "/setup/input-ledger.md",
            "hermes_runtime": "/setup/hermes-runtime.md",
            "hermes_install_runner": "/setup/hermes-install.ps1",
            "runtime_preflight": "/setup/runtime-preflight.md",
            "runtime_preflight_runner": "/setup/runtime-preflight.ps1",
            "safe_inputs": "/setup#inputs",
            "secret_status_only": "/setup#secret-status",
            "messaging_verification": "/setup#messaging-verification",
            "schedule_verification": "/setup#schedule-verification",
            "kanban_verification": "/setup#kanban-verification",
            "profile_installation": "/setup#profile-installation-tracking",
            "profile_smoke": "/setup#profile-smoke",
            "activation_sequence": "/setup/activation-sequence.md",
            "live_verification": "/setup/live-verification.md",
            **focused_setup_entry_points(),
        },
    }


def founder_next_actions_json(**kwargs) -> str:
    return json.dumps(founder_next_actions_payload(**kwargs), indent=2, sort_keys=True)


def founder_next_actions_markdown(**kwargs) -> str:
    payload = founder_next_actions_payload(**kwargs)
    summary = payload["activation_summary"]
    lines = [
        "# Founder Next Actions",
        "",
        "Use this as the compact action packet before live Hermes activation.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Current Gate",
        "",
        f"- Ready for live activation: {'yes' if summary['ready'] else 'no'}",
        f"- Blocking checks: {summary['blocking']}",
        f"- Needs setup checks: {summary['needs_setup']}",
        f"- Deferred checks: {summary['deferred']}",
        f"- Ready checks: {summary['ready_checks']} of {summary['total']}",
        f"- Next best action: {payload['next_best_action']}",
        "",
        "## Non-Secret Dashboard Inputs Needed",
        "",
    ]
    if payload["missing_dashboard_inputs"]:
        for item in payload["missing_dashboard_inputs"]:
            lines.append(f"- `{item['key']}`: {item['label']}. {item['help_text']}")
    else:
        lines.append("- None. Required non-secret dashboard inputs are captured.")
    lines.extend(
        [
            "",
            "## External Secret Status To Update",
            "",
        ]
    )
    for category, items in payload["external_secret_status"]["by_category"].items():
        open_items = [item for item in items if item["status"] not in {"loaded", "verified"}]
        lines.extend([f"### {category.title()}", ""])
        if open_items:
            for item in open_items:
                lines.append(
                    f"- `{item['status']}` {item['label']} -> {item['destination']}"
                )
        else:
            lines.append("- No open items.")
        lines.append("")
    lines.extend(
        [
            "## Verification Work Remaining",
            "",
            _verification_line("Messaging", payload["verification_work"]["messaging"]),
            _verification_line("Schedule", payload["verification_work"]["schedule"]),
            _verification_line("Kanban", payload["verification_work"]["kanban"]),
            _verification_line("LLM profiles", payload["verification_work"]["llm_profiles"]),
            _verification_line(
                "Profile installation",
                payload["verification_work"]["profile_installation"],
            ),
            _verification_line(
                "Profile acceptance",
                payload["verification_work"]["profile_acceptance"],
            ),
            "",
            "## Local Runtime",
            "",
            f"- Ready: {'yes' if payload['local_runtime']['ready'] else 'no'}",
            f"- Open local checks: {payload['local_runtime']['open']}",
            f"- Next runtime action: {payload['local_runtime']['next_action']}",
            "",
            "## Founder Decisions",
            "",
            (
                "- Open decisions: "
                f"{payload['founder_decisions']['open']} "
                f"({payload['founder_decisions']['urgent_open']} urgent)."
            ),
            (
                "- Decision queue: "
                f"`{payload['entry_points']['founder_decisions']}`"
            ),
            "",
            "## Focused Setup Reply Templates",
            "",
            *focused_setup_markdown_lines(payload["focused_setup_imports"]),
            "",
            "## Where To Act",
            "",
        ]
    )
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def _setup_input(item: dict) -> dict:
    return {
        "key": item["key"],
        "group": item["group_name"],
        "label": item["label"],
        "required": bool(item["required"]),
        "help_text": item["help_text"],
    }


def _external_secret_status(secret_requirements: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in secret_requirements:
        grouped[item["category"]].append(
            {
                "id": item["id"],
                "label": item["label"],
                "owner": item.get("owner_name") or item.get("owner_agent_id") or "",
                "destination": item["destination"],
                "status": item["status"],
            }
        )
    return {
        "status_counts": _status_counts(secret_requirements),
        "by_category": dict(sorted(grouped.items())),
    }


def _verification_summary(items: list[dict]) -> dict:
    verified = [item for item in items if item["status"] == "verified"]
    open_items = [item for item in items if item["status"] != "verified"]
    return {
        "verified": len(verified),
        "open": len(open_items),
        "status_counts": _status_counts(items),
    }


def _model_summary(model_preferences: list[dict]) -> dict:
    verified = [item for item in model_preferences if item["status"] == "verified"]
    open_items = [item for item in model_preferences if item["status"] != "verified"]
    return {
        "verified": len(verified),
        "open": len(open_items),
        "status_counts": _status_counts(model_preferences),
    }


def _local_runtime_summary(runtime_checks: list[dict]) -> dict:
    local_checks = [
        item for item in runtime_checks if not item["id"].startswith("integration-")
    ]
    open_items = [item for item in local_checks if item["status"] != "ready"]
    return {
        "available": bool(local_checks),
        "ready": bool(local_checks) and not open_items,
        "open": len(open_items),
        "status_counts": _status_counts(local_checks),
        "next_action": _local_runtime_next_action(local_checks, open_items),
        "open_checks": [
            {
                "id": item["id"],
                "label": item["label"],
                "status": item["status"],
                "detail": item["detail"],
                "remediation": item["remediation"],
            }
            for item in open_items[:8]
        ],
    }


def _local_runtime_next_action(
    local_checks: list[dict],
    open_items: list[dict],
) -> str:
    if not local_checks:
        return "Run `/setup/runtime-preflight.md` to inspect local Hermes runtime state."
    hermes_cli = next((item for item in local_checks if item["id"] == "hermes-cli"), None)
    if hermes_cli is not None and hermes_cli["status"] != "ready":
        return (
            "Install or connect Hermes with `/setup/hermes-runtime.md` and "
            "`/setup/hermes-install.ps1`, then rerun `/setup/runtime-preflight.ps1`."
        )
    profile_paths = [
        item
        for item in open_items
        if item["id"] == "hermes-profile-home"
        or item["id"].startswith("profile-path-")
    ]
    if profile_paths:
        return (
            "Run `/setup/bootstrap.ps1` or the relevant `/setup/profile-apply/*.ps1`, "
            "then import `/setup/profile-installation.ps1` output."
        )
    profile_commands = [
        item for item in open_items if item["id"].startswith("profile-command-")
    ]
    if profile_commands:
        return (
            "Expose Hermes profile aliases, then rerun `/setup/runtime-preflight.ps1`."
        )
    if open_items:
        first = open_items[0]
        return f"Resolve `{first['label']}`: {first['remediation']}"
    return "Local Hermes runtime checks are ready."


def _decision_summary(decisions: list[dict]) -> dict:
    open_items = [
        item for item in decisions if item["status"] not in RESOLVED_DECISION_STATUSES
    ]
    return {
        "open": len(open_items),
        "urgent_open": len(
            [item for item in open_items if item["urgency"] == "urgent"]
        ),
        "status_counts": _status_counts(decisions),
        "items": [
            {
                "id": item["id"],
                "title": item["title"],
                "status": item["status"],
                "urgency": item["urgency"],
                "owner_agent_id": item["owner_agent_id"],
                "slack_channel": item["slack_channel"],
            }
            for item in open_items
        ],
    }


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _verification_line(label: str, summary: dict) -> str:
    return f"- {label}: {summary['verified']} verified, {summary['open']} open."
