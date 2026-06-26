from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES


def progress_board_payload(
    *,
    setup_inputs: list[dict],
    runtime_checks: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    profile_installation_checks: list[dict],
    profile_acceptance_checks: list[dict],
    founder_decisions: list[dict] | None = None,
) -> dict:
    required_inputs = [
        item
        for item in setup_inputs
        if item["required"]
        and item["secret_policy"] == "non_secret"
        and not item["value"].strip()
    ]
    local_runtime_checks = [
        item for item in runtime_checks if not item["id"].startswith("integration-")
    ]
    runtime_open = [
        item for item in local_runtime_checks if item["status"] != "ready"
    ]
    messaging_secret_requirements = [
        item for item in secret_requirements if item["category"] in {"slack", "telegram"}
    ]
    llm_secret_requirements = [
        item for item in secret_requirements if item["category"] == "llm"
    ]
    decisions = founder_decisions or []
    open_decisions = [
        item for item in decisions if item["status"] not in RESOLVED_DECISION_STATUSES
    ]
    columns = [
        _column(
            column_id="do-now",
            title="Do now",
            description="Safe inputs and local Hermes runtime gates.",
            items=[
                _task(
                    "required-dashboard-inputs",
                    "Capture required safe dashboard inputs",
                    "ready" if not required_inputs else "needs_input",
                    len(required_inputs),
                    len(required_inputs),
                    "/setup/first-run.ps1",
                    "Use `/setup/first-run.ps1` or `/setup/founder-inputs.ps1`.",
                    [_input_stub(item) for item in required_inputs[:8]],
                ),
                _task(
                    "local-hermes-runtime",
                    "Install/connect Hermes and run preflight",
                    "ready" if local_runtime_checks and not runtime_open else "needs_setup",
                    len(runtime_open),
                    len(local_runtime_checks),
                    "/setup/hermes-runtime.md",
                    "Use `/setup/hermes-install.ps1`, then `/setup/runtime-preflight.ps1`.",
                    [_check_stub(item) for item in runtime_open[:8]],
                ),
            ],
        ),
        _column(
            column_id="after-hermes-install",
            title="Do after Hermes install",
            description="Profile assets, local Kanban setup, and no-secret checks.",
            items=[
                _verification_task(
                    "profile-installation",
                    "Verify starter profile installation",
                    profile_installation_checks,
                    "/setup/profile-installation.md",
                    "Run `/setup/profile-installation.ps1` and import no-secret audit output.",
                ),
                _verification_task(
                    "kanban-setup",
                    "Initialize and verify Hermes Kanban",
                    kanban_checks,
                    "/setup/kanban-runbook.md",
                    "Run Kanban initialization, diagnostics, and one dashboard task push.",
                ),
            ],
        ),
        _column(
            column_id="after-credentials",
            title="Do after credentials",
            description="Slack and Telegram credential-loaded communication checks.",
            items=[
                _task(
                    "messaging-credentials",
                    "Load Slack and Telegram credentials externally",
                    (
                        "ready"
                        if messaging_secret_requirements
                        and _all_status(messaging_secret_requirements, {"loaded", "verified"})
                        else "needs_secret_status"
                    ),
                    _open_count(messaging_secret_requirements, {"loaded", "verified"}),
                    len(messaging_secret_requirements),
                    "/setup/credential-loading.md",
                    "Load real credentials into Hermes profiles, then import status only.",
                    [_secret_stub(item) for item in messaging_secret_requirements[:8]],
                ),
                _verification_task(
                    "messaging-verification",
                    "Verify Slack and Telegram messaging",
                    messaging_checks,
                    "/setup#messaging-verification",
                    "Verify DMs, channel posts, mentions, and urgent Telegram alerts.",
                ),
                _verification_task(
                    "standup-verification",
                    "Verify standups and schedule delivery",
                    schedule_checks,
                    "/setup#schedule-verification",
                    "Run manual standups and cron/list checks after messaging works.",
                ),
            ],
        ),
        _column(
            column_id="final-verification",
            title="Final verification",
            description="LLM-last smoke checks, role acceptance, and founder go/no-go.",
            items=[
                _task(
                    "llm-credentials-last",
                    "Load LLM credentials last",
                    (
                        "ready"
                        if llm_secret_requirements
                        and _all_status(llm_secret_requirements, {"loaded", "verified"})
                        else "deferred"
                    ),
                    _open_count(llm_secret_requirements, {"loaded", "verified"}),
                    len(llm_secret_requirements),
                    "/setup/llm-finalize.md",
                    "Load provider credentials externally and run the LLM finalization audit.",
                    [_secret_stub(item) for item in llm_secret_requirements[:8]],
                ),
                _model_task(
                    "llm-profile-smoke",
                    "Run profile LLM smoke checks",
                    model_preferences,
                    "/setup#profile-smoke",
                    "Run each profile smoke prompt after LLM credentials are loaded.",
                ),
                _verification_task(
                    "profile-acceptance",
                    "Run role acceptance prompts",
                    profile_acceptance_checks,
                    "/setup/profile-acceptance.md",
                    "Verify each role behaves according to its founder-approved profile.",
                ),
                _task(
                    "founder-go-no-go",
                    "Resolve founder go/no-go decisions",
                    "ready" if not open_decisions else "needs_decision",
                    len(open_decisions),
                    len(decisions),
                    "/setup/founder-decisions.md",
                    "Resolve urgent decisions before first real idea intake.",
                    [_decision_stub(item) for item in open_decisions[:8]],
                ),
            ],
        ),
    ]
    return {
        "title": "Founder Setup Progress Board",
        "credential_boundary": (
            "This board stores and displays only non-secret counts, statuses, labels, "
            "and dashboard links. It does not include Slack tokens, Telegram bot "
            "tokens, provider API keys, OAuth payloads, profile .env values, raw "
            "logs, or private verification evidence."
        ),
        "ready": all(column["ready"] for column in columns),
        "columns": columns,
        "entry_points": {
            "markdown": "/setup/progress-board.md",
            "json": "/setup/progress-board.json",
            "first_run": "/setup/first-run.ps1",
            "founder_next_actions": "/setup/founder-next-actions.md",
            "company_launch_drill": "/setup/company-launch-drill.md",
            "live_verification": "/setup/live-verification.md",
        },
    }


def progress_board_json(**kwargs) -> str:
    return json.dumps(progress_board_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def progress_board_markdown(**kwargs) -> str:
    payload = progress_board_payload(**kwargs)
    lines = [
        "# Founder Setup Progress Board",
        "",
        "Use this as the stage-by-stage setup board before the first real company idea.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Summary",
        "",
        f"- Ready for live activation: {'yes' if payload['ready'] else 'no'}",
        f"- Board route: `{payload['entry_points']['markdown']}`",
        f"- First-run helper: `{payload['entry_points']['first_run']}`",
        "",
    ]
    for column in payload["columns"]:
        lines.extend(
            [
                f"## {column['title']}",
                "",
                f"- Ready: {'yes' if column['ready'] else 'no'}",
                f"- Open items: {column['open']}",
                f"- {column['description']}",
                "",
            ]
        )
        for item in column["items"]:
            lines.extend(
                [
                    f"### {item['label']}",
                    "",
                    f"- Status: `{item['status']}`",
                    f"- Open: {item['open']} of {item['total']}",
                    f"- Link: `{item['link']}`",
                    f"- Next: {item['next_action']}",
                    "",
                ]
            )
    lines.extend(["## Entry Points", ""])
    for label, route in payload["entry_points"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def _column(
    *,
    column_id: str,
    title: str,
    description: str,
    items: list[dict],
) -> dict:
    open_items = sum(item["open"] for item in items)
    return {
        "id": column_id,
        "title": title,
        "description": description,
        "ready": all(item["status"] == "ready" for item in items),
        "open": open_items,
        "items": items,
    }


def _task(
    task_id: str,
    label: str,
    status: str,
    open_count: int,
    total: int,
    link: str,
    next_action: str,
    examples: list[dict],
) -> dict:
    return {
        "id": task_id,
        "label": label,
        "status": status,
        "open": open_count,
        "total": total,
        "link": link,
        "next_action": next_action,
        "examples": examples,
    }


def _verification_task(
    task_id: str,
    label: str,
    checks: list[dict],
    link: str,
    next_action: str,
) -> dict:
    open_items = [item for item in checks if item["status"] != "verified"]
    return _task(
        task_id,
        label,
        "ready" if checks and not open_items else "needs_verification",
        len(open_items),
        len(checks),
        link,
        next_action,
        [_check_stub(item) for item in open_items[:8]],
    )


def _model_task(
    task_id: str,
    label: str,
    model_preferences: list[dict],
    link: str,
    next_action: str,
) -> dict:
    open_items = [
        item for item in model_preferences if item["status"] != "verified"
    ]
    return _task(
        task_id,
        label,
        "ready" if model_preferences and not open_items else "needs_verification",
        len(open_items),
        len(model_preferences),
        link,
        next_action,
        [_model_stub(item) for item in open_items[:8]],
    )


def _all_status(items: list[dict], ready_statuses: set[str]) -> bool:
    return all(item["status"] in ready_statuses for item in items)


def _open_count(items: list[dict], ready_statuses: set[str]) -> int:
    return len([item for item in items if item["status"] not in ready_statuses])


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _input_stub(item: dict) -> dict:
    return {
        "key": item["key"],
        "label": item["label"],
        "group": item["group_name"],
        "required": bool(item["required"]),
    }


def _check_stub(item: dict) -> dict:
    payload = {
        "id": item["id"],
        "label": item.get("label") or item.get("title") or item["id"],
        "status": item["status"],
    }
    if "platform" in item:
        payload["platform"] = item["platform"]
    if "check_type" in item:
        payload["check_type"] = item["check_type"]
    return payload


def _secret_stub(item: dict) -> dict:
    return {
        "id": item["id"],
        "label": item["label"],
        "category": item["category"],
        "owner": item.get("owner_name") or item.get("owner_agent_id") or "",
        "destination": item["destination"],
        "status": item["status"],
    }


def _model_stub(item: dict) -> dict:
    return {
        "agent_id": item["agent_id"],
        "agent_name": item["agent_name"],
        "provider": item["provider"],
        "model": item["model"],
        "status": item["status"],
    }


def _decision_stub(item: dict) -> dict:
    return {
        "id": item["id"],
        "title": item["title"],
        "status": item["status"],
        "urgency": item["urgency"],
        "owner_agent_id": item["owner_agent_id"],
    }
