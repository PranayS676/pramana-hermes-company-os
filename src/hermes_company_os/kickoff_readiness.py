from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict

from hermes_company_os.activation_sequence import next_best_action
from hermes_company_os.runtime_preflight import RuntimePreflightCheck

READY_STATUSES = {"ready", "configured", "verified"}
INPUT_CHECK_IDS = {
    "required-inputs",
    "slack-member-id",
    "slack-channel-ids",
    "telegram-ids",
    "standup-schedules",
}


def kickoff_readiness_payload(
    *,
    agents: list[dict],
    workflow_templates: list[dict],
    activation_checks: list[dict],
    runtime_checks: list[RuntimePreflightCheck],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    profile_installation_checks: list[dict] | None = None,
    profile_acceptance_checks: list[dict] | None = None,
) -> dict:
    gates = [
        _runtime_gate(runtime_checks),
        _input_gate(activation_checks),
        _profile_gate(agents),
        _profile_installation_gate(profile_installation_checks or []),
        _messaging_gate(messaging_checks, integrations),
        _kanban_gate(kanban_checks, integrations),
        _schedule_gate(schedule_checks, integrations),
        _llm_gate(model_preferences, secret_requirements, integrations),
        _profile_acceptance_gate(profile_acceptance_checks or []),
        _workflow_gate(workflow_templates),
    ]
    live_ready = all(gate["status"] == "ready" for gate in gates)
    next_action = _next_action(gates, activation_checks, secret_requirements, messaging_checks,
                               schedule_checks, kanban_checks, model_preferences, integrations)
    return {
        "title": "First Project Kickoff Readiness",
        "credential_boundary": (
            "No Slack tokens, Telegram bot tokens, provider API keys, or raw verification "
            "evidence are included in this artifact."
        ),
        "draft_workflow_allowed": True,
        "live_kickoff_ready": live_ready,
        "mode": "live_ready" if live_ready else "draft_only",
        "next_best_action": next_action,
        "gates": gates,
        "runtime_checks": [asdict(check) for check in runtime_checks],
        "entry_points": {
            "projects": "/projects",
            "setup": "/setup",
            "activation_sequence": "/setup/activation-sequence.md",
            "live_verification": "/setup/live-verification.md",
            "company_manifest": "/setup/company-manifest.json",
        },
    }


def kickoff_readiness_json(**kwargs) -> str:
    return json.dumps(kickoff_readiness_payload(**kwargs), indent=2, sort_keys=True)


def kickoff_readiness_markdown(**kwargs) -> str:
    payload = kickoff_readiness_payload(**kwargs)
    lines = [
        "# First Project Kickoff Readiness",
        "",
        "Use this before bringing the first founder idea into live Hermes execution.",
        "",
        "## Summary",
        "",
        (
            "- Draft workflow creation allowed: "
            f"{'yes' if payload['draft_workflow_allowed'] else 'no'}"
        ),
        f"- Live kickoff ready: {'yes' if payload['live_kickoff_ready'] else 'no'}",
        f"- Mode: `{payload['mode']}`",
        f"- Next best action: {payload['next_best_action']}",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Gates",
        "",
    ]
    for gate in payload["gates"]:
        lines.extend(
            [
                f"### {gate['label']}",
                "",
                f"- Status: `{gate['status']}`",
                f"- Detail: {gate['detail']}",
                f"- Next step: {gate['next_step']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Operating Rule",
            "",
            "- Draft workflows can be created locally before all gates are green.",
            "- Treat live agent execution, scheduled standups, and Kanban handoff as blocked "
            "until every live kickoff gate is `ready`.",
            "",
        ]
    )
    return "\n".join(lines)


def _next_action(
    gates: list[dict],
    activation_checks: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
) -> str:
    first_open_gate = next((gate for gate in gates if gate["status"] != "ready"), None)
    if first_open_gate and first_open_gate["id"] == "runtime":
        return f"Resolve runtime readiness: {first_open_gate['next_step']}"
    if first_open_gate and first_open_gate["id"] == "profiles":
        return first_open_gate["next_step"]
    return next_best_action(
        activation_checks,
        secret_requirements,
        messaging_checks,
        schedule_checks,
        kanban_checks,
        model_preferences,
        integrations,
    )


def _runtime_gate(runtime_checks: list[RuntimePreflightCheck]) -> dict:
    local_checks = [
        check for check in runtime_checks if not check.id.startswith("integration-")
    ]
    counts = _status_counts([asdict(check) for check in local_checks])
    open_checks = [check for check in local_checks if check.status not in READY_STATUSES]
    if not open_checks:
        return _gate(
            "runtime",
            "Local Hermes runtime",
            "ready",
            _format_counts(counts),
            "Runtime preflight is ready.",
        )
    first = open_checks[0]
    status = "deferred" if all(check.status == "deferred" for check in open_checks) else "blocked"
    return _gate(
        "runtime",
        "Local Hermes runtime",
        status,
        _format_counts(counts),
        f"{first.label}: {first.remediation}",
    )


def _input_gate(activation_checks: list[dict]) -> dict:
    relevant = [item for item in activation_checks if item["id"] in INPUT_CHECK_IDS]
    open_checks = [item for item in relevant if item["status"] != "ready"]
    if not open_checks:
        return _gate(
            "inputs",
            "Founder and workspace inputs",
            "ready",
            "Required non-secret inputs are valid.",
            "Continue to external credential and live verification gates.",
        )
    first = open_checks[0]
    return _gate(
        "inputs",
        "Founder and workspace inputs",
        "blocked",
        first["detail"],
        f"Complete `/setup/inputs#inputs` for {first['label']}.",
    )


def _profile_gate(agents: list[dict]) -> dict:
    incomplete = [
        agent["name"]
        for agent in agents
        if not agent["description"].strip()
        or not agent["soul"].strip()
        or not agent["capabilities"]
        or not agent["hermes_command"].strip()
    ]
    if incomplete:
        return _gate(
            "profiles",
            "Hermes profile starter values",
            "blocked",
            "Incomplete profiles: " + ", ".join(incomplete),
            "Open each profile page and complete description, soul, capabilities, and command.",
        )
    return _gate(
        "profiles",
        "Hermes profile starter values",
        "ready",
        f"{len(agents)} profiles have starter values.",
        "Run `/setup/profile-acceptance.md` after LLM setup.",
    )


def _profile_installation_gate(profile_installation_checks: list[dict]) -> dict:
    open_checks = [
        item for item in profile_installation_checks if item["status"] != "verified"
    ]
    if profile_installation_checks and not open_checks:
        return _gate(
            "profile_installation",
            "Hermes profile installation",
            "ready",
            "All starter profile installation checks are verified.",
            "Continue to messaging, Kanban, schedule, and LLM verification.",
        )
    return _gate(
        "profile_installation",
        "Hermes profile installation",
        "blocked",
        f"{len(profile_installation_checks) - len(open_checks)} verified, "
        f"{len(open_checks)} open.",
        "Run `/setup/profile-installation.ps1` and import results at "
        "`/setup/profiles#profile-installation-tracking`.",
    )


def _messaging_gate(messaging_checks: list[dict], integrations: list[dict]) -> dict:
    open_checks = [item for item in messaging_checks if item["status"] != "verified"]
    integration_ready = _category_ready(integrations, "slack") and _category_ready(
        integrations, "telegram"
    )
    if not open_checks and integration_ready:
        return _gate(
            "messaging",
            "Slack and Telegram messaging",
            "ready",
            "All messaging checks are verified.",
            "Keep routine work in Slack and urgent founder alerts in Telegram.",
        )
    return _gate(
        "messaging",
        "Slack and Telegram messaging",
        "blocked",
        f"{len(messaging_checks) - len(open_checks)} verified, {len(open_checks)} open.",
        "Load external messaging credentials and complete "
        "`/setup/messaging#messaging-verification`.",
    )


def _kanban_gate(kanban_checks: list[dict], integrations: list[dict]) -> dict:
    open_checks = [item for item in kanban_checks if item["status"] != "verified"]
    if not open_checks and _category_ready(integrations, "kanban"):
        return _gate(
            "kanban",
            "Hermes Kanban handoff",
            "ready",
            "Kanban initialization, diagnostics, and task creation are verified.",
            "Project workflows can be pushed to Hermes Kanban.",
        )
    return _gate(
        "kanban",
        "Hermes Kanban handoff",
        "blocked",
        f"{len(kanban_checks) - len(open_checks)} verified, {len(open_checks)} open.",
        "Run `/setup/kanban-runbook.md` and complete `/setup/verification#kanban-verification`.",
    )


def _schedule_gate(schedule_checks: list[dict], integrations: list[dict]) -> dict:
    active_checks = [item for item in schedule_checks if item.get("schedule_active", 1)]
    open_checks = [item for item in active_checks if item["status"] != "verified"]
    if active_checks and not open_checks and _category_ready(integrations, "schedule"):
        return _gate(
            "scheduling",
            "Standup scheduling",
            "ready",
            "Active standup checks are verified.",
            "Use Chief of Staff cron for 9 AM and 3 PM ET updates.",
        )
    return _gate(
        "scheduling",
        "Standup scheduling",
        "blocked",
        f"{len(active_checks) - len(open_checks)} verified, {len(open_checks)} open.",
        "Verify manual standups, install cron, and complete "
        "`/setup/verification#schedule-verification`.",
    )


def _llm_gate(
    model_preferences: list[dict],
    secret_requirements: list[dict],
    integrations: list[dict],
) -> dict:
    open_preferences = [item for item in model_preferences if item["status"] != "verified"]
    open_secrets = [
        item
        for item in secret_requirements
        if item["category"] == "llm" and item["status"] != "verified"
    ]
    if not open_preferences and not open_secrets and _category_ready(integrations, "runtime"):
        return _gate(
            "llm",
            "LLM provider verification",
            "ready",
            "Every profile smoke check and provider credential status is verified.",
            "Continue with role acceptance prompts before live project work.",
        )
    status = "deferred" if open_secrets else "blocked"
    return _gate(
        "llm",
        "LLM provider verification",
        status,
        f"{len(model_preferences) - len(open_preferences)} profiles verified, "
        f"{len(open_secrets)} LLM credentials open.",
        "Review `/setup/llm-provisioning.md`, load provider credentials last, "
        "then run `/setup/llm-finalize.md` and profile smoke checks.",
    )


def _profile_acceptance_gate(profile_acceptance_checks: list[dict]) -> dict:
    open_checks = [
        item for item in profile_acceptance_checks if item["status"] != "verified"
    ]
    if profile_acceptance_checks and not open_checks:
        return _gate(
            "profile_acceptance",
            "Hermes profile acceptance",
            "ready",
            "All role acceptance checks are verified.",
            "Live project work can use the accepted role behavior.",
        )
    return _gate(
        "profile_acceptance",
        "Hermes profile acceptance",
        "blocked",
        f"{len(profile_acceptance_checks) - len(open_checks)} verified, "
        f"{len(open_checks)} open.",
        "After profile smoke checks pass, run `/setup/profile-acceptance.md` and "
        "import outcomes at `/setup/profiles#profile-acceptance-tracking`.",
    )


def _workflow_gate(workflow_templates: list[dict]) -> dict:
    if workflow_templates:
        return _gate(
            "workflow",
            "First project workflow templates",
            "ready",
            f"{len(workflow_templates)} kickoff workflow templates are available.",
            "Draft project workflows can be created from `/projects`.",
        )
    return _gate(
        "workflow",
        "First project workflow templates",
        "blocked",
        "No kickoff workflow templates are available.",
        "Seed workflow templates before using the first project workflow.",
    )


def _category_ready(integrations: list[dict], category: str) -> bool:
    relevant = [item for item in integrations if item["category"] == category]
    return bool(relevant) and all(item["status"] in {"configured", "ready"} for item in relevant)


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _gate(
    gate_id: str,
    label: str,
    status: str,
    detail: str,
    next_step: str,
) -> dict:
    return {
        "id": gate_id,
        "label": label,
        "status": status,
        "detail": detail,
        "next_step": next_step,
    }
