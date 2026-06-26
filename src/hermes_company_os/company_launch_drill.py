from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.activation_report import activation_summary
from hermes_company_os.activation_sequence import next_best_action
from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.profile_acceptance import profile_acceptance_suite


def company_launch_drill_payload(
    *,
    agents: list[dict],
    relationships: list[dict],
    schedules: list[dict],
    workflow_templates: list[dict],
    activation_checks: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    setup_inputs: list[dict] | None = None,
    runtime_checks: list[dict] | None = None,
    profile_acceptance_checks: list[dict] | None = None,
    profile_installation_checks: list[dict] | None = None,
    founder_decisions: list[dict] | None = None,
) -> dict:
    acceptance_suite = profile_acceptance_suite(agents)
    required_acceptance_cases = len(acceptance_suite["cases"])
    decisions = founder_decisions or []
    phases = [
        _inputs_phase(setup_inputs or []),
        _runtime_phase(runtime_checks or []),
        _profile_phase(agents, relationships),
        _installation_phase(profile_installation_checks or []),
        _messaging_phase(secret_requirements, messaging_checks),
        _kanban_phase(kanban_checks),
        _schedule_phase(schedules, schedule_checks),
        _llm_phase(secret_requirements, model_preferences, integrations),
        _workflow_phase(workflow_templates),
        _acceptance_phase(agents, profile_acceptance_checks or []),
        _founder_decision_phase(decisions),
    ]
    tracked_phases = [phase for phase in phases if phase["tracked_gate"]]
    tracked_gates_ready = all(phase["status"] == "ready" for phase in tracked_phases)
    summary = activation_summary(activation_checks)
    return {
        "title": "Company Launch Drill",
        "purpose": (
            "Rehearse the founder company operating system before the first real "
            "startup idea enters the workflow."
        ),
        "credential_boundary": (
            "This drill references setup status, commands, routes, and evidence "
            "presence only. It does not include Slack tokens, Telegram bot tokens, "
            "provider keys, OAuth values, request headers, raw logs, or secret values."
        ),
        "activation_summary": summary,
        "tracked_gates_ready": tracked_gates_ready,
        "first_idea_mode": (
            "ready_for_manual_founder_go"
            if tracked_gates_ready
            else "setup_rehearsal_only"
        ),
        "manual_profile_installation_required": not _profile_installation_ready(
            profile_installation_checks or []
        ),
        "manual_acceptance_required": not _acceptance_ready(
            profile_acceptance_checks or [],
            required_acceptance_cases,
        ),
        "manual_founder_decision_required": not _founder_decisions_ready(decisions),
        "next_best_action": next_best_action(
            activation_checks,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            model_preferences,
            integrations,
        ),
        "phases": phases,
        "rehearsal_order": [
            {
                "step": 1,
                "name": "Capture founder and workspace IDs",
                "entry_point": "/setup/founder-inputs.ps1",
            },
            {
                "step": 2,
                "name": "Install or connect the local Hermes runtime",
                "entry_point": "/setup/hermes-runtime.md",
            },
            {
                "step": 3,
                "name": "Review current state",
                "entry_point": "/setup/company-manifest.md",
            },
            {
                "step": 4,
                "name": "Confirm profile topology and verify installed profile identity files",
                "entry_point": "/setup/profile-installation.md",
            },
            {
                "step": 5,
                "name": "Run Slack and Telegram gateway drills",
                "entry_point": "/setup/messaging-drill.md",
            },
            {
                "step": 6,
                "name": "Verify Kanban as the source of truth",
                "entry_point": "/setup/kanban-runbook.md",
            },
            {
                "step": 7,
                "name": "Verify 9 AM and 3 PM standup delivery",
                "entry_point": "/setup/schedule-provisioning.md",
            },
            {
                "step": 8,
                "name": "Load LLM credentials last and run profile smoke checks",
                "entry_point": "/setup/llm-finalize.md",
            },
            {
                "step": 9,
                "name": "Run role acceptance prompts",
                "entry_point": "/setup/profile-acceptance.md",
            },
            {
                "step": 10,
                "name": "Record founder operating and first-idea decisions",
                "entry_point": "/setup/founder-decisions.md",
            },
            {
                "step": 11,
                "name": "Use idea intake to start the first project workflow",
                "entry_point": "/setup/idea-intake.md",
            },
        ],
        "entry_points": {
            "manifest": "/setup/company-manifest.md",
            "activation_sequence": "/setup/activation-sequence.md",
            "founder_next_actions": "/setup/founder-next-actions.md",
            "first_run": "/setup/first-run.md",
            "first_run_runner": "/setup/first-run.ps1",
            "progress_board": "/setup/progress-board.md",
            "progress_board_json": "/setup/progress-board.json",
            "safe_inputs": "/setup/founder-input-request.md",
            "input_collector": "/setup/founder-inputs.ps1",
            "hermes_runtime": "/setup/hermes-runtime.md",
            "hermes_install_runner": "/setup/hermes-install.ps1",
            "runtime_preflight": "/setup/runtime-preflight.md",
            "founder_decisions": "/setup/founder-decisions.md",
            "profile_installation": "/setup/profile-installation.md",
            "profile_acceptance": "/setup/profile-acceptance.md",
            "messaging_drill": "/setup/messaging-drill.md",
            "kanban_runbook": "/setup/kanban-runbook.md",
            "schedule_provisioning": "/setup/schedule-provisioning.md",
            "llm_finalization": "/setup/llm-finalize.md",
            "idea_intake": "/setup/idea-intake.md",
        },
    }


def company_launch_drill_json(**kwargs) -> str:
    return json.dumps(company_launch_drill_payload(**kwargs), indent=2, sort_keys=True) + "\n"


def company_launch_drill_markdown(**kwargs) -> str:
    payload = company_launch_drill_payload(**kwargs)
    summary = payload["activation_summary"]
    lines = [
        "# Company Launch Drill",
        "",
        payload["purpose"],
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Current Gate",
        "",
        f"- Tracked gates ready: {'yes' if payload['tracked_gates_ready'] else 'no'}",
        f"- First idea mode: `{payload['first_idea_mode']}`",
        (
            "- Manual profile installation required: "
            f"{'yes' if payload['manual_profile_installation_required'] else 'no'}"
        ),
        (
            "- Manual profile acceptance required: "
            f"{'yes' if payload['manual_acceptance_required'] else 'no'}"
        ),
        (
            "- Manual founder decision required: "
            f"{'yes' if payload['manual_founder_decision_required'] else 'no'}"
        ),
        f"- Activation ready flag: {'yes' if summary['ready'] else 'no'}",
        f"- Blocking checks: {summary['blocking']}",
        f"- Needs setup checks: {summary['needs_setup']}",
        f"- Deferred checks: {summary['deferred']}",
        f"- Ready checks: {summary['ready_checks']} of {summary['total']}",
        f"- Next best action: {payload['next_best_action']}",
        "",
        "## Drill Phases",
        "",
    ]
    for phase in payload["phases"]:
        lines.extend(
            [
                f"### {phase['name']}",
                "",
                f"- Status: `{phase['status']}`",
                f"- Tracked gate: {'yes' if phase['tracked_gate'] else 'no'}",
                f"- Detail: {phase['detail']}",
                f"- Entry point: `{phase['entry_point']}`",
                "",
            ]
        )
    lines.extend(["## Rehearsal Order", ""])
    for item in payload["rehearsal_order"]:
        lines.append(f"{item['step']}. {item['name']}: `{item['entry_point']}`")
    lines.extend(
        [
            "",
            "## Founder Go / No-Go Rule",
            "",
            "- Do not start the first real company idea until tracked gates are ready.",
            "- Run profile acceptance prompts after LLM smoke checks pass.",
            "- Treat any failed acceptance answer as a profile personalization task.",
            "- Resolve `/setup/founder-decisions.md` before first idea intake.",
            "- Use `/setup/idea-intake.md` only after the founder accepts the profile behavior.",
            "",
            "## Exports",
            "",
            "- JSON drill: `/setup/company-launch-drill.json`",
            "- Activation sequence: `/setup/activation-sequence.md`",
            "",
        ]
    )
    return "\n".join(lines)


def _inputs_phase(setup_inputs: list[dict]) -> dict:
    safe_required = [
        item
        for item in setup_inputs
        if item.get("required") and item.get("secret_policy") == "non_secret"
    ]
    missing = [item for item in safe_required if not item.get("value", "").strip()]
    status = "ready" if safe_required and not missing else "needs_setup"
    return _phase(
        phase_id="safe-founder-inputs",
        name="Founder and workspace inputs",
        status=status,
        tracked_gate=True,
        detail=(
            f"{len(safe_required) - len(missing)} captured, "
            f"{len(missing)} required safe input(s) missing."
        ),
        entry_point="/setup/founder-inputs.ps1",
    )


def _runtime_phase(runtime_checks: list[dict]) -> dict:
    local_checks = [
        item for item in runtime_checks if not item["id"].startswith("integration-")
    ]
    open_checks = [item for item in local_checks if item["status"] != "ready"]
    status = "ready" if local_checks and not open_checks else "needs_setup"
    hermes_cli = next((item for item in local_checks if item["id"] == "hermes-cli"), None)
    entry_point = (
        "/setup/hermes-runtime.md"
        if hermes_cli is None or hermes_cli["status"] != "ready"
        else "/setup/runtime-preflight.md"
    )
    return _phase(
        phase_id="local-hermes-runtime",
        name="Local Hermes runtime",
        status=status,
        tracked_gate=True,
        detail=(
            f"Runtime checks {_format_counts(_status_counts(local_checks))}; "
            f"{len(open_checks)} open."
        ),
        entry_point=entry_point,
    )


def _profile_phase(agents: list[dict], relationships: list[dict]) -> dict:
    status = "ready" if agents and relationships else "needs_setup"
    return _phase(
        phase_id="profile-topology",
        name="Profile topology",
        status=status,
        tracked_gate=True,
        detail=(
            f"{len(agents)} profiles and {len(relationships)} manager/member "
            "relationship(s) are defined."
        ),
        entry_point="/setup/team-topology.md",
    )


def _installation_phase(profile_installation_checks: list[dict]) -> dict:
    status = (
        "ready"
        if _profile_installation_ready(profile_installation_checks)
        else "needs_setup"
    )
    return _phase(
        phase_id="profile-installation",
        name="Hermes profile installation",
        status=status,
        tracked_gate=True,
        detail=(
            "Profile installation checks "
            f"{_format_counts(_status_counts(profile_installation_checks))}."
        ),
        entry_point="/setup/profile-installation.md",
    )


def _profile_installation_ready(profile_installation_checks: list[dict]) -> bool:
    return bool(profile_installation_checks) and all(
        item["status"] == "verified" for item in profile_installation_checks
    )


def _messaging_phase(
    secret_requirements: list[dict],
    messaging_checks: list[dict],
) -> dict:
    messaging_secrets = [
        item for item in secret_requirements if item["category"] in {"slack", "telegram"}
    ]
    open_secrets = [
        item for item in messaging_secrets if item["status"] not in {"loaded", "verified"}
    ]
    open_checks = [item for item in messaging_checks if item["status"] != "verified"]
    status = (
        "ready"
        if messaging_secrets and not open_secrets and not open_checks
        else "needs_setup"
    )
    return _phase(
        phase_id="slack-telegram-gateways",
        name="Slack workspace and Telegram urgent path",
        status=status,
        tracked_gate=True,
        detail=(
            f"Messaging secret status {_format_counts(_status_counts(messaging_secrets))}; "
            f"messaging checks {_format_counts(_status_counts(messaging_checks))}."
        ),
        entry_point="/setup/messaging-drill.md",
    )


def _kanban_phase(kanban_checks: list[dict]) -> dict:
    status = (
        "ready"
        if kanban_checks and all(item["status"] == "verified" for item in kanban_checks)
        else "needs_setup"
    )
    return _phase(
        phase_id="kanban-source-of-truth",
        name="Kanban source of truth",
        status=status,
        tracked_gate=True,
        detail=f"Kanban checks {_format_counts(_status_counts(kanban_checks))}.",
        entry_point="/setup/kanban-runbook.md",
    )


def _schedule_phase(schedules: list[dict], schedule_checks: list[dict]) -> dict:
    active_checks = [item for item in schedule_checks if item.get("schedule_active", 1)]
    active_schedules = [item for item in schedules if item.get("active", 1)]
    status = (
        "ready"
        if active_schedules
        and active_checks
        and all(item["status"] == "verified" for item in active_checks)
        else "needs_setup"
    )
    return _phase(
        phase_id="standup-loop",
        name="9 AM and 3 PM standup loop",
        status=status,
        tracked_gate=True,
        detail=(
            f"{len(active_schedules)} active schedule(s); active schedule checks "
            f"{_format_counts(_status_counts(active_checks))}."
        ),
        entry_point="/setup/schedule-provisioning.md",
    )


def _llm_phase(
    secret_requirements: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
) -> dict:
    llm_secrets = [item for item in secret_requirements if item["category"] == "llm"]
    runtime_integrations = [item for item in integrations if item["category"] == "runtime"]
    status = (
        "ready"
        if llm_secrets
        and model_preferences
        and all(item["status"] == "verified" for item in llm_secrets)
        and all(item["status"] == "verified" for item in model_preferences)
        and all(item["status"] in {"configured", "ready"} for item in runtime_integrations)
        else "needs_setup"
    )
    return _phase(
        phase_id="llm-final-smoke",
        name="LLM credentials and profile smoke checks",
        status=status,
        tracked_gate=True,
        detail=(
            f"LLM secrets {_format_counts(_status_counts(llm_secrets))}; "
            f"profile smoke {_format_counts(_status_counts(model_preferences))}; "
            f"runtime {_format_counts(_status_counts(runtime_integrations))}."
        ),
        entry_point="/setup/llm-finalize.md",
    )


def _workflow_phase(workflow_templates: list[dict]) -> dict:
    return _phase(
        phase_id="project-workflow",
        name="First-project workflow templates",
        status="ready" if workflow_templates else "needs_setup",
        tracked_gate=True,
        detail=f"{len(workflow_templates)} workflow template(s) are available.",
        entry_point="/setup/project-workflow.md",
    )


def _acceptance_phase(agents: list[dict], acceptance_checks: list[dict]) -> dict:
    suite = profile_acceptance_suite(agents)
    status = (
        "ready"
        if _acceptance_ready(acceptance_checks, len(suite["cases"]))
        else "needs_setup"
    )
    return _phase(
        phase_id="profile-acceptance",
        name="Role-quality acceptance prompts",
        status=status,
        tracked_gate=True,
        detail=(
            f"{len(suite['cases'])} role acceptance case(s); tracked status "
            f"{_format_counts(_status_counts(acceptance_checks))}."
        ),
        entry_point="/setup/profile-acceptance.md",
    )


def _acceptance_ready(acceptance_checks: list[dict], required_count: int) -> bool:
    return len(acceptance_checks) >= required_count and all(
        item["status"] == "verified" for item in acceptance_checks
    )


def _founder_decision_phase(founder_decisions: list[dict]) -> dict:
    open_decisions = [
        item
        for item in founder_decisions
        if item["status"] not in RESOLVED_DECISION_STATUSES
    ]
    urgent_open = [item for item in open_decisions if item["urgency"] == "urgent"]
    return _phase(
        phase_id="founder-decisions",
        name="Founder decision queue",
        status="ready" if _founder_decisions_ready(founder_decisions) else "needs_setup",
        tracked_gate=True,
        detail=(
            f"Decision status {_format_counts(_status_counts(founder_decisions))}; "
            f"open={len(open_decisions)}, urgent_open={len(urgent_open)}."
        ),
        entry_point="/setup/founder-decisions.md",
    )


def _founder_decisions_ready(founder_decisions: list[dict]) -> bool:
    return bool(founder_decisions) and all(
        item["status"] in RESOLVED_DECISION_STATUSES and item["decision"].strip()
        for item in founder_decisions
    )


def _phase(
    *,
    phase_id: str,
    name: str,
    status: str,
    tracked_gate: bool,
    detail: str,
    entry_point: str,
) -> dict:
    return {
        "id": phase_id,
        "name": name,
        "status": status,
        "tracked_gate": tracked_gate,
        "detail": detail,
        "entry_point": entry_point,
    }


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
