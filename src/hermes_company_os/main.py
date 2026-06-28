from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, replace
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from hermes_company_os.activation import (
    activation_commands,
    cron_commands,
    missing_required_inputs,
)
from hermes_company_os.activation_report import (
    activation_checks,
    activation_report_markdown,
    activation_summary,
)
from hermes_company_os.activation_runner import (
    activation_runner_markdown,
    activation_runner_powershell,
)
from hermes_company_os.activation_sequence import activation_sequence_markdown
from hermes_company_os.agent_work_queue import (
    QUEUE_PRIORITIES,
    QUEUE_PRIORITY_LABELS,
    QUEUE_STATE_LABELS,
    QUEUE_STATES,
)
from hermes_company_os.bootstrap import powershell_bootstrap, profile_setup_commands
from hermes_company_os.codex_execution import (
    CODEX_EXECUTION_DECISION_SOURCE,
    CODEX_EXECUTION_DECISION_TYPE,
    CODEX_EXECUTION_STAGE_ID,
    codex_execution_markdown,
    codex_execution_package,
    queue_codex_execution_run,
    start_codex_execution_git_worktree,
)
from hermes_company_os.company_launch_drill import (
    company_launch_drill_json,
    company_launch_drill_markdown,
)
from hermes_company_os.company_manifest import (
    company_manifest_json,
    company_manifest_markdown,
)
from hermes_company_os.config_templates import (
    profile_config_template,
    profile_live_config_template,
)
from hermes_company_os.credential_loading_sequence import (
    credential_loading_json,
    credential_loading_markdown,
)
from hermes_company_os.credential_status_import import (
    credential_status_import_redirect,
    credential_status_template_json,
    credential_status_template_markdown,
    parse_credential_status_reply,
)
from hermes_company_os.database import initialize_database
from hermes_company_os.delegation_playbook import (
    delegation_playbook_json,
    delegation_playbook_markdown,
)
from hermes_company_os.env_templates import profile_env_template
from hermes_company_os.external_dispatch import HermesExternalDispatchCommandAdapter
from hermes_company_os.first_run import (
    first_run_json,
    first_run_markdown,
    first_run_powershell,
)
from hermes_company_os.founder_control import project_founder_control_summary
from hermes_company_os.founder_decisions import (
    DECISION_TYPE_LABELS,
    RESOLVED_DECISION_STATUSES,
    founder_decisions_json,
    founder_decisions_markdown,
    founder_decisions_payload,
)
from hermes_company_os.founder_handoff import (
    founder_handoff_json,
    founder_handoff_markdown,
)
from hermes_company_os.founder_input_import import (
    founder_input_import_redirect,
    parse_founder_input_reply,
)
from hermes_company_os.founder_inputs import (
    founder_input_collector_powershell,
    founder_input_request_json,
    founder_input_request_markdown,
)
from hermes_company_os.founder_next_actions import (
    founder_next_actions_json,
    founder_next_actions_markdown,
    founder_next_actions_payload,
)
from hermes_company_os.gateway_operations import (
    gateway_operations_json,
    gateway_operations_markdown,
    gateway_operations_powershell,
)
from hermes_company_os.generation_service import (
    LIVE_HERMES_GENERATION_MODE,
    LOCAL_DEMO_GENERATION_MODE,
    GenerationMode,
    LiveHermesCommandAdapter,
    LiveHermesGenerationService,
    LocalDemoGenerationService,
    StageGenerationRequest,
    live_hermes_operator_preview,
    normalize_generation_mode,
)
from hermes_company_os.hermes_client import HermesClient
from hermes_company_os.hermes_runtime import (
    hermes_install_powershell,
    hermes_runtime_json,
    hermes_runtime_markdown,
)
from hermes_company_os.idea_intake import idea_intake_json, idea_intake_markdown
from hermes_company_os.input_ledger import input_ledger_json, input_ledger_markdown
from hermes_company_os.kanban_artifacts import (
    kanban_diagnostics_powershell,
    kanban_runbook_markdown,
)
from hermes_company_os.kanban_client import KanbanClient
from hermes_company_os.kanban_provisioning import (
    kanban_provisioning_json,
    kanban_provisioning_markdown,
    kanban_provisioning_powershell,
)
from hermes_company_os.kanban_verification_import import (
    kanban_verification_import_redirect,
    kanban_verification_template_json,
    kanban_verification_template_markdown,
    parse_kanban_verification_reply,
)
from hermes_company_os.kickoff_readiness import (
    kickoff_readiness_json,
    kickoff_readiness_markdown,
    kickoff_readiness_payload,
)
from hermes_company_os.live_hermes_readiness import (
    LIVE_HERMES_DECISION_SOURCE,
    LIVE_HERMES_DECISION_TYPE,
    LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
    LIVE_HERMES_RUN_CONFIRMATION_TYPE,
    evaluate_live_hermes_readiness,
    evaluate_live_hermes_run_confirmation,
)
from hermes_company_os.live_verification import live_verification_markdown
from hermes_company_os.llm_artifacts import (
    llm_credentials_plan_markdown,
    profile_llm_env_template,
)
from hermes_company_os.llm_finalization import (
    llm_finalization_markdown,
    llm_finalization_powershell,
)
from hermes_company_os.llm_preference_import import (
    llm_preference_import_redirect,
    llm_preference_template_json,
    llm_preference_template_markdown,
    parse_llm_preference_reply,
)
from hermes_company_os.llm_provider_presets import (
    llm_preset_preferences,
    llm_provider_presets_json,
    llm_provider_presets_markdown,
    llm_provider_presets_payload,
)
from hermes_company_os.llm_provisioning import (
    llm_provisioning_json,
    llm_provisioning_markdown,
    llm_provisioning_powershell,
)
from hermes_company_os.llm_smoke_artifacts import (
    llm_smoke_json,
    llm_smoke_markdown,
)
from hermes_company_os.messaging_drill_artifacts import (
    messaging_drill_json,
    messaging_drill_markdown,
)
from hermes_company_os.messaging_verification_import import (
    messaging_verification_import_redirect,
    messaging_verification_template_json,
    messaging_verification_template_markdown,
    parse_messaging_verification_reply,
)
from hermes_company_os.multi_agent_review import (
    generate_multi_agent_review,
    multi_agent_review_markdown,
    multi_agent_review_package,
)
from hermes_company_os.product_wizard import (
    FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
    ProductWizardIntake,
)
from hermes_company_os.profile_acceptance import (
    profile_acceptance_json,
    profile_acceptance_markdown,
)
from hermes_company_os.profile_acceptance_import import (
    parse_profile_acceptance_reply,
    profile_acceptance_import_redirect,
    profile_acceptance_template_json,
    profile_acceptance_template_markdown,
)
from hermes_company_os.profile_artifacts import (
    profile_apply_powershell,
    profile_artifacts_markdown,
    profile_manifest_json,
    profile_soul_markdown,
)
from hermes_company_os.profile_handoff_contracts import (
    profile_handoff_contract,
    profile_handoff_contract_markdown,
)
from hermes_company_os.profile_installation import (
    profile_installation_json,
    profile_installation_markdown,
    profile_installation_powershell,
)
from hermes_company_os.profile_installation_import import (
    parse_profile_installation_audit,
    profile_installation_import_redirect,
)
from hermes_company_os.profile_live_assets import (
    profile_live_assets_json,
    profile_live_assets_markdown,
    profile_live_assets_powershell,
    profile_live_context_markdown,
    profile_live_prompts_markdown,
    profile_live_rules_markdown,
)
from hermes_company_os.profile_personalization_import import (
    parse_profile_personalization_reply,
    profile_personalization_import_redirect,
    profile_personalization_template_json,
    profile_personalization_template_markdown,
)
from hermes_company_os.progress_board import (
    progress_board_json,
    progress_board_markdown,
)
from hermes_company_os.project_memory import (
    memory_category_options,
    memory_confidence_options,
    memory_reuse_policy_summary,
    product_wizard_memory_context,
    project_memory_markdown,
    project_memory_package,
)
from hermes_company_os.project_operating_loop import (
    consume_external_dispatch_preview_approval,
    project_external_dispatch_preview_package,
    project_operating_loop_package,
    request_external_dispatch_approval,
    run_external_dispatch_runner,
)
from hermes_company_os.project_workflow_artifacts import (
    project_workflow_json,
    project_workflow_markdown,
)
from hermes_company_os.prompts import build_agent_prompt, build_standup_prompt
from hermes_company_os.readiness import ReadinessService
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.runtime_preflight import (
    runtime_preflight_checks,
    runtime_preflight_json,
    runtime_preflight_markdown,
    runtime_preflight_powershell,
)
from hermes_company_os.schedule_config_import import (
    parse_schedule_config_reply,
    schedule_config_import_redirect,
    schedule_config_template_json,
    schedule_config_template_markdown,
)
from hermes_company_os.schedule_provisioning import (
    schedule_provisioning_json,
    schedule_provisioning_markdown,
    schedule_provisioning_powershell,
)
from hermes_company_os.schedule_verification_import import (
    parse_schedule_verification_reply,
    schedule_verification_import_redirect,
    schedule_verification_template_json,
    schedule_verification_template_markdown,
)
from hermes_company_os.secret_audit import (
    secret_audit_markdown,
    secret_audit_powershell,
    secret_audit_requirements,
)
from hermes_company_os.secret_guard import assert_no_secret_values
from hermes_company_os.settings import Settings
from hermes_company_os.setup_artifacts import (
    activation_checklist_markdown,
    inputs_needed_markdown,
    llm_setup_plan_markdown,
    slack_setup_plan_markdown,
    telegram_setup_plan_markdown,
)
from hermes_company_os.slack_bot_user_import import (
    parse_slack_bot_user_reply,
    slack_bot_user_import_redirect,
    slack_bot_user_template_json,
    slack_bot_user_template_markdown,
)
from hermes_company_os.slack_channel_import import (
    parse_slack_channel_reply,
    slack_channel_import_redirect,
    slack_channel_template_json,
    slack_channel_template_markdown,
)
from hermes_company_os.slack_manifest import (
    slack_app_manifest_json,
    slack_app_manifests_bundle_json,
)
from hermes_company_os.slack_provisioning import (
    slack_bot_user_map_template_json,
    slack_provisioning_json,
    slack_provisioning_markdown,
    slack_provisioning_powershell,
)
from hermes_company_os.slack_workspace import (
    slack_invite_matrix_csv,
    slack_invite_matrix_json,
    slack_workspace_markdown,
)
from hermes_company_os.smoke_checks import append_smoke_note, profile_smoke_prompt
from hermes_company_os.standup_artifacts import (
    standup_cron_powershell,
    standup_runbook_markdown,
)
from hermes_company_os.standup_preview import (
    standup_preview_json,
    standup_preview_markdown,
)
from hermes_company_os.team_topology import team_topology_json, team_topology_markdown
from hermes_company_os.telegram_artifacts import telegram_botfather_setup_markdown
from hermes_company_os.telegram_policy import (
    telegram_policy_json,
    telegram_policy_markdown,
)
from hermes_company_os.telegram_provisioning import (
    telegram_provisioning_json,
    telegram_provisioning_markdown,
    telegram_provisioning_powershell,
)
from hermes_company_os.telegram_recipient_import import (
    parse_telegram_recipient_reply,
    telegram_recipient_import_redirect,
    telegram_recipient_template_json,
    telegram_recipient_template_markdown,
)
from hermes_company_os.verification_evidence import (
    verification_evidence_json,
    verification_evidence_markdown,
)

PACKAGE_ROOT = Path(__file__).parent
LIVE_HERMES_PILOT_CONFIRMATION_PHRASE = "RUN LIVE HERMES"
LIVE_HERMES_PILOT_CONFIRMATION_ERROR = (
    "Live Hermes manual pilot blocked: type RUN LIVE HERMES before real execution."
)
DECISION_STATUS_OPTIONS = ("needed", "blocked", "approved", "rejected", "deferred")
REVISION_REASON_LABELS = {
    "evidence_gap": "Evidence gap",
    "scope_issue": "Scope issue",
    "risk_concern": "Risk concern",
    "test_gap": "Test gap",
    "owner_mismatch": "Owner mismatch",
    "acceptance_concern": "Acceptance concern",
}


def reject_secret_values(values: dict[str, str]) -> None:
    try:
        assert_no_secret_values(values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def safe_return_path(return_to: str, fallback: str) -> str:
    if return_to.startswith("/") and not return_to.startswith("//"):
        return return_to
    return fallback


def form_checkbox_checked(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on", "confirmed"}


def kanban_project_push_blocker(repository: CompanyRepository) -> str:
    if repository.kanban_verification_ready():
        return ""
    open_checks = [
        item for item in repository.list_kanban_checks() if item["status"] != "verified"
    ]
    if not open_checks:
        return "Kanban verification checks are not available."
    labels = ", ".join(item["label"] for item in open_checks[:3])
    suffix = "" if len(open_checks) <= 3 else f", plus {len(open_checks) - 3} more"
    return (
        "Complete Kanban verification before pushing a full project workflow. "
        f"Open checks: {labels}{suffix}."
    )


def project_task_stage_approved(repository: CompanyRepository, project_id: str) -> bool:
    stages = repository.list_project_wizard_stages(project_id)
    if not stages:
        return True
    task_stage = next((stage for stage in stages if stage["stage_id"] == "tasks"), None)
    return bool(task_stage and task_stage["status"] == "approved")


def project_wizard_kanban_blocker(
    repository: CompanyRepository,
    project_id: str,
) -> str:
    if not project_task_stage_approved(repository, project_id):
        return (
            "Complete product wizard tasks approval before pushing this project to "
            "Kanban."
        )
    return kanban_project_push_blocker(repository)


def kanban_task_push_blocker(repository: CompanyRepository) -> str:
    prerequisite_checks = [
        item
        for item in repository.list_kanban_checks()
        if item["check_type"] != "task_create"
    ]
    open_checks = [item for item in prerequisite_checks if item["status"] != "verified"]
    if not open_checks:
        return ""
    labels = ", ".join(item["label"] for item in open_checks)
    return (
        "Complete Kanban initialization and diagnostics before running the task-create "
        f"drill. Open checks: {labels}."
    )


def product_wizard_intake_from_form(
    *,
    name: str,
    founder_idea: str,
    target_audience: str = "",
    problem_statement: str = "",
    current_alternative: str = "",
    product_category: str = "",
    launch_tier: str = "",
    deadline_pressure: str = "",
    desired_outcome: str = "",
    constraints: str = "",
    non_goals: str = "",
    success_metrics: str = "",
) -> dict[str, str]:
    return {
        "project_name": name.strip(),
        "founder_idea": founder_idea.strip(),
        "target_customer": target_audience.strip(),
        "problem": problem_statement.strip(),
        "current_alternatives": current_alternative.strip(),
        "desired_outcome": desired_outcome.strip(),
        "constraints": "\n".join(
            item
            for item in [
                f"Product category: {product_category.strip()}" if product_category.strip() else "",
                f"Launch tier: {launch_tier.strip()}" if launch_tier.strip() else "",
                (
                    f"Deadline pressure: {deadline_pressure.strip()}"
                    if deadline_pressure.strip()
                    else ""
                ),
                constraints.strip(),
                f"Non-goals: {non_goals.strip()}" if non_goals.strip() else "",
            ]
            if item
        ),
        "success_metric": success_metrics.strip(),
    }


def product_wizard_intake_from_project(project: dict) -> ProductWizardIntake:
    intake = dict(project.get("intake") or {})
    intake.setdefault("project_name", project["name"])
    intake.setdefault("founder_idea", project["founder_idea"])
    return ProductWizardIntake.from_mapping(intake)


def stage_icon(stage_id: str) -> str:
    return {
        "research": "search",
        "prd": "file-text",
        "architecture": "network",
        "tasks": "list-checks",
        "code_plan": "code-2",
        "acceptance": "badge-check",
    }.get(stage_id, "circle")


def stage_view(stage: dict) -> dict:
    return {
        **stage,
        "id": stage["stage_id"],
        "label": stage["name"],
        "icon": stage_icon(stage["stage_id"]),
        "summary": stage["description"],
    }


def markdown_review_sections(markdown_content: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_title = "Summary"
    current_lines: list[str] = []

    def flush_section() -> None:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append({"title": current_title, "body": body})

    for line in markdown_content.splitlines():
        if line.startswith("## "):
            flush_section()
            current_title = line.removeprefix("## ").strip()
            current_lines = []
            continue
        if line.startswith("# ") and not sections and not current_lines:
            current_title = line.removeprefix("# ").strip()
            continue
        current_lines.append(line)
    flush_section()
    if not sections and markdown_content.strip():
        sections.append({"title": "Summary", "body": markdown_content.strip()})
    return sections


def artifact_view(artifact: dict | None) -> dict | None:
    if artifact is None:
        return None
    metadata = artifact.get("json", {})
    title = metadata.get("title") or artifact["stage_id"].replace("_", " ").title()
    checks = metadata.get("checks") if isinstance(metadata.get("checks"), list) else []
    source_artifact_ids = metadata.get("source_artifact_ids")
    memory_ids = metadata.get("memory_ids")
    supporting_agent_ids = metadata.get("supporting_agent_ids")
    return {
        **artifact,
        "title": title,
        "body": artifact["markdown_content"],
        "summary": artifact["markdown_content"],
        "metadata": metadata,
        "generation_mode": metadata.get("generation_mode", ""),
        "next_decision": metadata.get("next_decision", ""),
        "source_artifact_ids": (
            source_artifact_ids if isinstance(source_artifact_ids, list) else []
        ),
        "memory_ids": memory_ids if isinstance(memory_ids, list) else [],
        "supporting_agent_ids": (
            supporting_agent_ids if isinstance(supporting_agent_ids, list) else []
        ),
        "quality_checks": checks,
        "sections": markdown_review_sections(artifact["markdown_content"]),
        "selected": False,
    }


def stage_artifacts_view(
    repository: CompanyRepository,
    project_id: str,
    stages: list[dict],
) -> dict[str, list[dict]]:
    return {
        stage["stage_id"]: [
            artifact_view(artifact)
            for artifact in repository.list_project_stage_artifacts(
                project_id,
                stage["stage_id"],
            )
        ]
        for stage in stages
    }


def approved_source_artifacts(
    repository: CompanyRepository,
    project_id: str,
) -> list[dict]:
    sources = []
    for stage in repository.list_project_wizard_stages(project_id):
        artifact = repository.latest_project_stage_artifact(project_id, stage["stage_id"])
        if not artifact or artifact["status"] != "approved":
            continue
        sources.append(
            {
                "id": artifact["id"],
                "stage": artifact["stage_id"],
                "title": artifact.get("json", {}).get("title") or stage["name"],
                "content": artifact["markdown_content"],
                "status": "approved",
            }
        )
    return sources


def generation_run_view(run: dict | None) -> dict | None:
    if run is None:
        return None
    source_artifact_ids = run.get("source_artifact_ids")
    memory_ids = run.get("memory_ids")
    return {
        **run,
        "source_artifact_ids": (
            source_artifact_ids if isinstance(source_artifact_ids, list) else []
        ),
        "memory_ids": memory_ids if isinstance(memory_ids, list) else [],
    }


def project_activity_package(
    repository: CompanyRepository,
    project: dict,
    *,
    limit: int = 50,
) -> dict:
    events = []
    for event in repository.list_audit_events(project_id=project["id"], limit=limit):
        event_payload = dict(event)
        event_payload.pop("payload_json", None)
        events.append(event_payload)
    payload = {
        "schema": "project_activity_package_v1",
        "project": {
            "id": project["id"],
            "name": project["name"],
            "status": project["status"],
        },
        "aggregate": {
            "event_count": len(events),
            "latest_event_type": events[0]["event_type"] if events else "",
        },
        "events": events,
    }
    assert_no_secret_values({"project_activity_package": json.dumps(payload, sort_keys=True)})
    return payload


def live_hermes_operator_console(
    *,
    settings: Settings,
    repository: CompanyRepository,
    project: dict,
    stage_id: str,
    live_readiness: dict | None,
    run_confirmation: dict | None,
    latest_artifact: dict | None,
) -> dict:
    memory_context = product_wizard_memory_context(repository, project["id"])
    preview = live_hermes_operator_preview(
        stage_id,
        product_wizard_intake_from_project(project),
        approved_source_artifacts(repository, project["id"]),
        memory_context=memory_context,
        memory_policy=FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
        timeout_seconds=settings.hermes_timeout_seconds,
        live_execution_enabled=settings.hermes_live_execution_enabled,
    )
    generation_metadata = {}
    if latest_artifact:
        artifact_metadata = latest_artifact.get("metadata") or latest_artifact.get("json", {})
        raw_generation_metadata = artifact_metadata.get("generation_metadata")
        if isinstance(raw_generation_metadata, dict):
            generation_metadata = raw_generation_metadata

    live_ready = bool(live_readiness and live_readiness.get("ready"))
    founder_approved = bool(live_readiness and live_readiness.get("founder_approved"))
    run_confirmed = bool(run_confirmation and run_confirmation.get("fresh"))
    run_request_open = bool(run_confirmation and run_confirmation.get("request_open"))
    run_request_allowed = bool(
        settings.hermes_live_execution_enabled
        and live_ready
        and run_confirmation
        and run_confirmation.get("request_allowed")
    )
    last_adapter = str(generation_metadata.get("adapter", ""))
    last_status = str(generation_metadata.get("status", ""))
    last_external_execution = str(generation_metadata.get("external_execution", ""))
    last_command_preview = generation_metadata.get("command_preview")
    if not isinstance(last_command_preview, list):
        last_command_preview = []
    stdout_capture = generation_metadata.get("stdout_capture")
    stderr_capture = generation_metadata.get("stderr_capture")
    if not isinstance(stdout_capture, dict):
        stdout_capture = {}
    if not isinstance(stderr_capture, dict):
        stderr_capture = {}
    runner = generation_metadata.get("runner")
    if not isinstance(runner, dict):
        runner = {}
    operator_preflight = generation_metadata.get("operator_preflight")
    if not isinstance(operator_preflight, dict):
        operator_preflight = {}
    execution_audit = generation_metadata.get("execution_audit")
    if not isinstance(execution_audit, dict):
        execution_audit = {}
    live_run_possible = (
        settings.hermes_live_execution_enabled and live_ready and run_confirmed
    )

    return {
        "execution_enabled": settings.hermes_live_execution_enabled,
        "execution_status": (
            "enabled" if settings.hermes_live_execution_enabled else "disabled"
        ),
        "env_var": "HERMES_LIVE_EXECUTION_ENABLED",
        "timeout_seconds": settings.hermes_timeout_seconds,
        "command_preview": preview,
        "live_run_possible": live_run_possible,
        "pilot_confirmation_phrase": LIVE_HERMES_PILOT_CONFIRMATION_PHRASE,
        "pilot_status": "ready" if live_run_possible else "blocked",
        "pilot_detail": (
            "Type the confirmation phrase to consume the one-run token and start the pilot."
            if live_run_possible
            else "Complete execution flag, readiness, and one-run confirmation first."
        ),
        "run_confirmation": run_confirmation or {},
        "run_confirmation_ready": run_confirmed,
        "run_confirmation_request_open": run_request_open,
        "run_confirmation_request_allowed": run_request_allowed,
        "warning": (
            "Real Hermes command execution is enabled for this process."
            if settings.hermes_live_execution_enabled
            else (
                "Real Hermes command execution is disabled for this process; "
                "live mode will stay on the dry-run runner boundary."
            )
        ),
        "checklist": [
            {
                "id": "execution_flag",
                "label": "Execution flag",
                "status": (
                    "ready" if settings.hermes_live_execution_enabled else "manual"
                ),
                "detail": (
                    "HERMES_LIVE_EXECUTION_ENABLED is true."
                    if settings.hermes_live_execution_enabled
                    else "Set HERMES_LIVE_EXECUTION_ENABLED=true outside the dashboard."
                ),
            },
            {
                "id": "readiness_gates",
                "label": "Readiness gates",
                "status": "ready" if live_ready else "blocked",
                "detail": (
                    "Founder and runtime readiness gates are satisfied."
                    if live_ready
                    else "Complete live Hermes readiness before a real runner attempt."
                ),
            },
            {
                "id": "founder_approval",
                "label": "Founder approval",
                "status": "ready" if founder_approved else "needed",
                "detail": (
                    "Founder approval is recorded for this stage."
                    if founder_approved
                    else "Founder approval is required before live Hermes execution."
                ),
            },
            {
                "id": "run_confirmation",
                "label": "One-run confirmation",
                "status": (
                    "ready"
                    if run_confirmed
                    else ("manual" if not settings.hermes_live_execution_enabled else "needed")
                ),
                "detail": (
                    "Founder-confirmed one-run approval is fresh for this stage."
                    if run_confirmed
                    else (
                        "Dry-run mode does not require one-run confirmation."
                        if not settings.hermes_live_execution_enabled
                        else "Request and approve a one-run token before real execution."
                    )
                ),
            },
            {
                "id": "dry_run_evidence",
                "label": "Dry-run evidence",
                "status": "ready" if last_adapter else "needed",
                "detail": (
                    f"Last adapter evidence: {last_adapter} / {last_status}."
                    if last_adapter
                    else "Run the dry-run adapter and review the generated artifact first."
                ),
            },
            {
                "id": "capture_boundary",
                "label": "Capture boundary",
                "status": "ready",
                "detail": (
                    "Runner output stores hashes and byte counts; "
                    "secret-shaped errors are redacted."
                ),
            },
            {
                "id": "manual_pilot_confirmation",
                "label": "Manual pilot confirmation",
                "status": "ready" if live_run_possible else "needed",
                "detail": (
                    "Founder can type the pilot phrase in the stage action panel."
                    if live_run_possible
                    else "The pilot phrase is accepted only after all live gates pass."
                ),
            },
        ],
        "last_run": {
            "available": bool(generation_metadata),
            "adapter": last_adapter,
            "status": last_status,
            "external_execution": last_external_execution,
            "duration_ms": generation_metadata.get("duration_ms", ""),
            "command_preview": last_command_preview,
            "command_preview_text": " ".join(str(part) for part in last_command_preview),
            "prompt_handoff": generation_metadata.get("prompt_handoff", {}),
            "output_parser": generation_metadata.get("output_parser", {}),
            "stdout_capture": stdout_capture,
            "stderr_capture": stderr_capture,
            "runner": runner,
            "operator_preflight": operator_preflight,
            "execution_audit": execution_audit,
        },
    }


def live_hermes_gate_for(
    live_readiness,
    run_confirmation,
):
    gate = live_readiness.gate
    if run_confirmation:
        gate = gate.with_run_confirmation(run_confirmation.fresh)
    return gate


def validate_live_hermes_pilot_confirmation(
    *,
    settings: Settings,
    mode: GenerationMode,
    confirmation: str,
) -> None:
    if mode != LIVE_HERMES_GENERATION_MODE:
        return
    if not settings.hermes_live_execution_enabled:
        return
    if confirmation.strip() != LIVE_HERMES_PILOT_CONFIRMATION_PHRASE:
        raise ValueError(LIVE_HERMES_PILOT_CONFIRMATION_ERROR)


def artifact_with_live_hermes_pilot_evidence(
    *,
    artifact,
    settings: Settings,
    mode: GenerationMode,
    confirmation: str,
    run_confirmation,
    generation_run_id: str,
):
    if mode != LIVE_HERMES_GENERATION_MODE:
        return artifact
    if not settings.hermes_live_execution_enabled:
        return artifact
    generation_metadata = dict(artifact.generation_metadata)
    generation_metadata["operator_preflight"] = {
        "manual_pilot_confirmation": "verified",
        "confirmation_phrase_sha256": hashlib.sha256(
            confirmation.strip().encode("utf-8")
        ).hexdigest(),
        "run_confirmation_decision_id": (
            run_confirmation.decision_id if run_confirmation else ""
        ),
        "run_confirmation_fresh": bool(run_confirmation and run_confirmation.fresh),
        "env_var": "HERMES_LIVE_EXECUTION_ENABLED",
        "external_execution_enabled": True,
    }
    generation_metadata["execution_audit"] = live_hermes_execution_audit(
        generation_metadata,
        run_confirmation=run_confirmation,
        generation_run_id=generation_run_id,
    )
    return replace(artifact, generation_metadata=generation_metadata)


def live_hermes_execution_audit(
    generation_metadata: dict,
    *,
    run_confirmation,
    generation_run_id: str,
) -> dict:
    command_preview = [
        str(part) for part in generation_metadata.get("command_preview", [])
    ]
    source_artifact_ids = [
        str(source_id) for source_id in generation_metadata.get("source_artifact_ids", [])
    ]
    memory_ids = [
        str(memory_id) for memory_id in generation_metadata.get("memory_ids", [])
    ]
    prompt_handoff = generation_metadata.get("prompt_handoff")
    if not isinstance(prompt_handoff, dict):
        prompt_handoff = {}
    stdout_capture = generation_metadata.get("stdout_capture")
    if not isinstance(stdout_capture, dict):
        stdout_capture = {}
    stderr_capture = generation_metadata.get("stderr_capture")
    if not isinstance(stderr_capture, dict):
        stderr_capture = {}
    decision_id = run_confirmation.decision_id if run_confirmation else ""
    return {
        "schema": "live_hermes_execution_audit_v1",
        "immutable": True,
        "generation_run_id": generation_run_id,
        "command_fingerprint": {
            "sha256": hashlib.sha256(
                "\n".join(command_preview).encode("utf-8")
            ).hexdigest(),
            "command_preview": command_preview,
        },
        "prompt_fingerprint": {
            "sha256": str(prompt_handoff.get("sha256", "")),
            "contract": str(
                prompt_handoff.get("contract", "product_wizard_prompt_contract_v1")
            ),
            "source_artifact_ids": source_artifact_ids,
            "memory_ids": memory_ids,
        },
        "approval_consumption": {
            "decision_id": decision_id,
            "consumed_by_generation_run_id": generation_run_id,
            "status": "consumed" if decision_id else "not_recorded",
        },
        "output_fingerprints": {
            "stdout_sha256": str(stdout_capture.get("sha256", "")),
            "stderr_sha256": str(stderr_capture.get("sha256", "")),
            "stdout_bytes": int(stdout_capture.get("bytes", 0) or 0),
            "stderr_bytes": int(stderr_capture.get("bytes", 0) or 0),
        },
        "post_run_review": {
            "status": "awaiting_founder_review",
            "next_action": "Review the live Hermes artifact before stage approval.",
        },
    }


def product_wizard_generation_service(
    request: Request,
    mode: GenerationMode,
    live_gate=None,
):
    if mode == LOCAL_DEMO_GENERATION_MODE:
        return request.app.state.generation_service
    if mode == LIVE_HERMES_GENERATION_MODE:
        settings: Settings = request.app.state.settings
        injected_runner = getattr(request.app.state, "live_hermes_command_runner", None)
        adapter = None
        if injected_runner is not None:
            adapter = LiveHermesCommandAdapter(
                live_execution_enabled=settings.hermes_live_execution_enabled,
                runner=injected_runner,
                runner_label=getattr(
                    request.app.state,
                    "live_hermes_runner_label",
                    "injected_runner",
                ),
            )
        return LiveHermesGenerationService(
            live_gate,
            adapter=adapter,
            timeout_seconds=settings.hermes_timeout_seconds,
            live_execution_enabled=settings.hermes_live_execution_enabled,
        )
    raise ValueError(f"Unsupported Product Wizard generation mode: {mode}")


def wizard_review_decision_type(stage_id: str) -> str:
    return "final_artifact_approval" if stage_id == "acceptance" else "artifact_approval"


def create_project_stage_review_decision(
    repository: CompanyRepository,
    project: dict,
    stage_id: str,
    artifact_id: str,
    artifact,
) -> str:
    decision_type = wizard_review_decision_type(stage_id)
    stage = repository.get_project_wizard_stage(project["id"], stage_id)
    stage_label = stage["name"] if stage else stage_id.replace("_", " ").title()
    is_final = decision_type == "final_artifact_approval"
    return repository.create_founder_decision(
        title=f"Approve {stage_label} artifact for {project['name']}",
        urgency="urgent" if is_final else "routine",
        decision_type=decision_type,
        source="product_wizard",
        owner_agent_id=artifact.owner_agent_id,
        project_id=project["id"],
        stage_id=stage_id,
        artifact_id=artifact_id,
        slack_channel="#founder-command" if is_final else "#decisions",
        telegram_policy=(
            "Telegram only if this final artifact approval blocks launch."
            if is_final
            else "Slack first; Telegram only if this blocks founder progress."
        ),
        context=(
            f"Review the generated {stage_label} artifact before it becomes approved "
            f"source input for {project['name']}."
        ),
        evidence=(
            f"Artifact {artifact_id} was generated in {artifact.generation_mode}. "
            f"Next decision: {artifact.next_decision}"
        ),
        requires_founder_approval=is_final,
    )


def resolve_stage_id(repository: CompanyRepository, project_id: str, stage_id: str) -> str:
    if stage_id != "current":
        return stage_id
    stage = repository.next_actionable_stage(project_id)
    if stage is None:
        raise HTTPException(status_code=409, detail="No actionable product wizard stage.")
    return stage["stage_id"]


def profile_live_run_blocker(repository: CompanyRepository, agent_id: str) -> str:
    preference = repository.get_model_preference(agent_id)
    if preference is None:
        return "Create a model preference before running this Hermes profile."
    if preference["status"] != "verified":
        return (
            f"Run the profile smoke check for {preference['agent_name']} after loading "
            f"LLM credentials. Current model status: {preference['status']}."
        )
    llm_secret = next(
        (
            item
            for item in repository.list_secret_requirements()
            if item["owner_agent_id"] == agent_id and item["category"] == "llm"
        ),
        None,
    )
    if llm_secret is not None and llm_secret["status"] != "verified":
        return (
            f"Mark {llm_secret['label']} verified after loading provider credentials "
            "outside this dashboard."
        )
    return ""


def messaging_check_credential_blocker(
    repository: CompanyRepository,
    check: dict,
) -> str:
    requirements = [
        item
        for item in repository.list_secret_requirements()
        if item["owner_agent_id"] == check["owner_agent_id"]
        and item["category"] == check["platform"]
    ]
    open_requirements = [
        item for item in requirements if item["status"] not in {"loaded", "verified"}
    ]
    if not open_requirements:
        return ""
    labels = ", ".join(item["label"] for item in open_requirements)
    return (
        f"Mark external {check['platform']} credential status loaded before verifying "
        f"`{check['label']}`. Open credentials: {labels}."
    )


def refresh_messaging_integration_status(
    repository: CompanyRepository,
    platform: str,
) -> None:
    if not repository.messaging_platform_verified(platform):
        return
    for integration in repository.list_integrations():
        if integration["category"] == platform:
            repository.update_integration_status(integration["id"], "configured")


def schedule_check_prerequisite_blocker(
    repository: CompanyRepository,
    check: dict,
) -> str:
    if check["check_type"] == "manual_run":
        live_run_blocker = profile_live_run_blocker(repository, "chief-of-staff")
        if live_run_blocker:
            return (
                "Complete Chief of Staff LLM verification before marking a manual "
                f"standup run verified. {live_run_blocker}"
            )
        if not repository.messaging_platform_verified("slack"):
            return "Complete Slack messaging verification before marking manual standups verified."
        if not repository.messaging_platform_verified("telegram"):
            return (
                "Complete Telegram urgent-alert verification before marking manual "
                "standups verified."
            )
    if check["check_type"] == "cron_installed":
        manual_check = repository.get_schedule_check(f"{check['schedule_id']}-manual-run")
        if manual_check is not None and manual_check["status"] != "verified":
            return (
                f"Verify the manual dashboard run for {check['schedule_name']} before "
                "marking cron installed."
            )
    return ""


def staged_schedule_check_prerequisite_blocker(
    repository: CompanyRepository,
    check: dict,
    updates: dict[str, dict],
) -> str:
    if check["check_type"] != "cron_installed":
        return schedule_check_prerequisite_blocker(repository, check)
    manual_check_id = f"{check['schedule_id']}-manual-run"
    manual_check = repository.get_schedule_check(manual_check_id)
    manual_update = updates.get(manual_check_id, {})
    manual_will_be_verified = manual_update.get("status") == "verified"
    if (
        manual_check is not None
        and manual_check["status"] != "verified"
        and not manual_will_be_verified
    ):
        return (
            f"Verify the manual dashboard run for {check['schedule_name']} before "
            "marking cron installed."
        )
    return ""


def profile_acceptance_prerequisite_blocker(
    repository: CompanyRepository,
    check: dict,
) -> str:
    preference = repository.get_model_preference(check["agent_id"])
    if preference is None or preference["status"] != "verified":
        return (
            "Run the matching profile smoke check successfully before marking "
            "role acceptance verified."
        )
    return ""


def profile_installation_prerequisite_blocker(
    repository: CompanyRepository,
    agent_id: str,
) -> str:
    if not repository.agent_profile_installation_verified(agent_id):
        return (
            "Verify this Hermes profile installation before running its profile "
            "smoke check."
        )
    return ""


def reject_manual_llm_verified_status(category: str, status: str) -> None:
    if category == "llm" and status == "verified":
        raise HTTPException(
            status_code=409,
            detail=(
                "LLM credentials are marked verified only by a successful profile "
                "smoke check. Use loaded or ready_for_verification before smoke checks."
            ),
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    database_path = resolved_settings.resolved_database_path()
    initialize_database(database_path)

    app = FastAPI(title="Hermes Company OS")
    app.state.settings = resolved_settings
    app.state.repository = CompanyRepository(database_path)
    app.state.hermes_client = HermesClient(resolved_settings)
    app.state.kanban_client = KanbanClient()
    app.state.generation_service = LocalDemoGenerationService()
    app.state.live_generation_service = LiveHermesGenerationService(
        timeout_seconds=resolved_settings.hermes_timeout_seconds,
        live_execution_enabled=resolved_settings.hermes_live_execution_enabled,
    )
    app.state.live_hermes_command_runner = None
    app.state.live_hermes_runner_label = "subprocess"
    app.state.external_dispatch_runner = None
    app.state.external_dispatch_runner_label = "not_configured"
    app.state.readiness_service = ReadinessService(database_path)

    templates = Jinja2Templates(directory=str(PACKAGE_ROOT / "templates"))
    app.mount("/static", StaticFiles(directory=str(PACKAGE_ROOT / "static")), name="static")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/")
    def dashboard(request: Request):
        repository: CompanyRepository = request.app.state.repository
        agents = repository.list_agents()
        schedules = repository.list_schedules()
        integrations = repository.list_integrations()
        setup_inputs = repository.list_setup_inputs()
        model_preferences = repository.list_model_preferences()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        agent_work_items = repository.list_agent_work_items(limit=6, include_done=False)
        agent_work_summary = repository.agent_work_queue_summary()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                agents,
                integrations,
            )
        ]
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "agents": agents,
                "schedules": schedules,
                "tasks": repository.list_tasks(),
                "documents": repository.list_documents(),
                "runs": repository.list_runs(),
                "projects": repository.list_projects(),
                "founder_decisions": founder_decisions,
                "agent_work_items": agent_work_items,
                "agent_work_summary": agent_work_summary,
                "founder_actions": founder_next_actions_payload(
                    activation_checks=checks,
                    setup_inputs=setup_inputs,
                    secret_requirements=secret_requirements,
                    messaging_checks=messaging_checks,
                    schedule_checks=schedule_checks,
                    kanban_checks=kanban_checks,
                    model_preferences=model_preferences,
                    integrations=integrations,
                    runtime_checks=runtime_checks,
                    profile_acceptance_checks=profile_acceptance_checks,
                    profile_installation_checks=profile_installation_checks,
                    founder_decisions=founder_decisions,
                ),
                "standup_run_blocker": profile_live_run_blocker(
                    repository,
                    "chief-of-staff",
                ),
                "kanban_task_push_blocker": kanban_task_push_blocker(repository),
                "settings": request.app.state.settings,
            },
        )

    @app.get("/setup")
    def setup(request: Request):
        repository: CompanyRepository = request.app.state.repository
        agents = repository.list_agents()
        integrations = repository.list_integrations()
        setup_inputs = repository.list_setup_inputs()
        setup_values = repository.setup_input_map()
        model_preferences = repository.list_model_preferences()
        messaging_checks = repository.list_messaging_checks()
        schedules = repository.list_schedules()
        secret_requirements = repository.list_secret_requirements()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        readiness_service: ReadinessService = request.app.state.readiness_service
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "agents": agents,
                "integrations": integrations,
                "setup_steps": repository.list_setup_steps(),
                "setup_inputs": setup_inputs,
                "schedules": schedules,
                "model_preferences": model_preferences,
                "llm_presets": llm_provider_presets_payload(
                    agents=agents,
                    model_preferences=model_preferences,
                )["presets"],
                "secret_requirements": secret_requirements,
                "messaging_checks": messaging_checks,
                "messaging_credential_blockers": {
                    check["id"]: messaging_check_credential_blocker(repository, check)
                    for check in messaging_checks
                },
                "schedule_checks": schedule_checks,
                "schedule_prerequisite_blockers": {
                    check["id"]: schedule_check_prerequisite_blocker(repository, check)
                    for check in schedule_checks
                },
                "kanban_checks": kanban_checks,
                "profile_installation_checks": profile_installation_checks,
                "profile_acceptance_checks": profile_acceptance_checks,
                "profile_acceptance_blockers": {
                    check["id"]: profile_acceptance_prerequisite_blocker(
                        repository,
                        check,
                    )
                    for check in profile_acceptance_checks
                },
                "profile_smoke_blockers": {
                    preference["agent_id"]: profile_installation_prerequisite_blocker(
                        repository,
                        preference["agent_id"],
                    )
                    for preference in model_preferences
                },
                "profile_smoke_runs": repository.latest_runs_by_type("profile-smoke"),
                "activation_summary": activation_summary(checks),
                "input_completion": repository.setup_input_completion(),
                "missing_inputs": missing_required_inputs(setup_inputs),
                "readiness": readiness_service.check(agents, integrations),
                "hermes_version": readiness_service.hermes_version(),
                "profile_commands": profile_setup_commands(agents),
                "activation_commands": activation_commands(agents, setup_values),
                "cron_commands": cron_commands(setup_values, schedules),
                "input_import_summary": {
                    "imported": request.query_params.get("input_imported"),
                    "unknown": request.query_params.get("input_unknown"),
                    "deferred": request.query_params.get("input_deferred"),
                    "ignored": request.query_params.get("input_ignored"),
                },
                "credential_import_summary": {
                    "imported": request.query_params.get("credential_imported"),
                    "unknown": request.query_params.get("credential_unknown"),
                    "invalid": request.query_params.get("credential_invalid"),
                    "ignored": request.query_params.get("credential_ignored"),
                },
                "messaging_import_summary": {
                    "imported": request.query_params.get("messaging_imported"),
                    "unknown": request.query_params.get("messaging_unknown"),
                    "invalid": request.query_params.get("messaging_invalid"),
                    "ignored": request.query_params.get("messaging_ignored"),
                },
                "slack_channel_import_summary": {
                    "imported": request.query_params.get("slack_channel_imported"),
                    "unknown": request.query_params.get("slack_channel_unknown"),
                    "invalid": request.query_params.get("slack_channel_invalid"),
                    "ignored": request.query_params.get("slack_channel_ignored"),
                },
                "slack_bot_user_import_summary": {
                    "imported": request.query_params.get("slack_bot_user_imported"),
                    "unknown": request.query_params.get("slack_bot_user_unknown"),
                    "invalid": request.query_params.get("slack_bot_user_invalid"),
                    "ignored": request.query_params.get("slack_bot_user_ignored"),
                },
                "telegram_recipient_import_summary": {
                    "imported": request.query_params.get(
                        "telegram_recipient_imported"
                    ),
                    "unknown": request.query_params.get("telegram_recipient_unknown"),
                    "invalid": request.query_params.get("telegram_recipient_invalid"),
                    "ignored": request.query_params.get("telegram_recipient_ignored"),
                },
                "schedule_config_import_summary": {
                    "imported": request.query_params.get("schedule_config_imported"),
                    "unknown": request.query_params.get("schedule_config_unknown"),
                    "invalid": request.query_params.get("schedule_config_invalid"),
                    "ignored": request.query_params.get("schedule_config_ignored"),
                },
                "schedule_import_summary": {
                    "imported": request.query_params.get("schedule_imported"),
                    "unknown": request.query_params.get("schedule_unknown"),
                    "invalid": request.query_params.get("schedule_invalid"),
                    "ignored": request.query_params.get("schedule_ignored"),
                },
                "kanban_import_summary": {
                    "imported": request.query_params.get("kanban_imported"),
                    "unknown": request.query_params.get("kanban_unknown"),
                    "invalid": request.query_params.get("kanban_invalid"),
                    "ignored": request.query_params.get("kanban_ignored"),
                },
                "profile_acceptance_import_summary": {
                    "imported": request.query_params.get(
                        "profile_acceptance_imported"
                    ),
                    "unknown": request.query_params.get("profile_acceptance_unknown"),
                    "invalid": request.query_params.get("profile_acceptance_invalid"),
                    "ignored": request.query_params.get("profile_acceptance_ignored"),
                },
                "profile_installation_import_summary": {
                    "imported": request.query_params.get("profile_installation_imported"),
                    "unknown": request.query_params.get("profile_installation_unknown"),
                    "incomplete": request.query_params.get(
                        "profile_installation_incomplete"
                    ),
                    "ignored": request.query_params.get("profile_installation_ignored"),
                },
                "profile_personalization_import_summary": {
                    "imported": request.query_params.get(
                        "profile_personalization_imported"
                    ),
                    "unknown": request.query_params.get(
                        "profile_personalization_unknown"
                    ),
                    "invalid": request.query_params.get(
                        "profile_personalization_invalid"
                    ),
                    "ignored": request.query_params.get(
                        "profile_personalization_ignored"
                    ),
                },
                "llm_preference_import_summary": {
                    "imported": request.query_params.get("llm_preference_imported"),
                    "unknown": request.query_params.get("llm_preference_unknown"),
                    "invalid": request.query_params.get("llm_preference_invalid"),
                    "ignored": request.query_params.get("llm_preference_ignored"),
                },
                "settings": request.app.state.settings,
            },
        )

    @app.get("/setup/bootstrap.ps1")
    def bootstrap_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            powershell_bootstrap(
                repository.list_agents(),
                repository.setup_input_map(),
                repository.list_schedules(),
                repository.model_preference_map(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/profile-env/{agent_id}.env")
    def profile_env(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_env_template(agent, repository.setup_input_map()),
            media_type="text/plain",
        )

    @app.get("/setup/profile-config/{agent_id}.yaml")
    def profile_config(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_config_template(
                agent,
                repository.setup_input_map(),
                repository.get_model_preference(agent_id),
            ),
            media_type="text/yaml",
        )

    @app.get("/setup/profile-live-config/{agent_id}.yaml")
    def profile_live_config(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_live_config_template(
                agent,
                repository.setup_input_map(),
                repository.get_model_preference(agent_id),
            ),
            media_type="text/yaml",
        )

    @app.get("/setup/profile-llm-env/{agent_id}.env")
    def profile_llm_env(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_llm_env_template(agent, repository.get_model_preference(agent_id)),
            media_type="text/plain",
        )

    @app.get("/setup/profile-artifacts.md")
    def profile_artifacts(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_artifacts_markdown(repository.list_agents()),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-personalization-template.md")
    def profile_personalization_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_personalization_template_markdown(repository.list_agents()),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-personalization-template.json")
    def profile_personalization_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_personalization_template_json(repository.list_agents()),
            media_type="application/json",
        )

    @app.get("/setup/profile-installation.md")
    def profile_installation_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_installation_markdown(
                agents=repository.list_agents(),
                profile_installation_checks=repository.list_profile_installation_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-installation.json")
    def profile_installation_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_installation_json(
                agents=repository.list_agents(),
                profile_installation_checks=repository.list_profile_installation_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/profile-installation.ps1")
    def profile_installation_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_installation_powershell(repository.list_agents()),
            media_type="text/plain",
        )

    @app.get("/setup/profile-live-assets.md")
    def profile_live_assets_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_live_assets_markdown(
                agents=repository.list_agents(),
                model_preferences=repository.list_model_preferences(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-live-assets.json")
    def profile_live_assets_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_live_assets_json(
                agents=repository.list_agents(),
                model_preferences=repository.list_model_preferences(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/profile-live-assets.ps1")
    def profile_live_assets_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_live_assets_powershell(repository.list_agents()),
            media_type="text/plain",
        )

    @app.get("/setup/profile-live-context/{agent_id}.md")
    def profile_live_context(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_live_context_markdown(
                agent=agent,
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
                schedules=repository.list_schedules(),
                setup_values=repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-live-prompts/{agent_id}.md")
    def profile_live_prompts(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_live_prompts_markdown(
                agent,
                repository.get_model_preference(agent_id),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-live-rules/{agent_id}.md")
    def profile_live_rules(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_live_rules_markdown(agent),
            media_type="text/markdown",
        )

    @app.get("/setup/team-topology.md")
    def team_topology_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            team_topology_markdown(
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/team-topology.json")
    def team_topology_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            team_topology_json(
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/delegation-playbook.md")
    def delegation_playbook_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            delegation_playbook_markdown(
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
                workflow_templates=repository.list_workflow_templates(),
                schedules=repository.list_schedules(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/delegation-playbook.json")
    def delegation_playbook_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            delegation_playbook_json(
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
                workflow_templates=repository.list_workflow_templates(),
                schedules=repository.list_schedules(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/profile-acceptance.md")
    def profile_acceptance_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_acceptance_markdown(
                repository.list_agents(),
                repository.list_profile_acceptance_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-acceptance.json")
    def profile_acceptance_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_acceptance_json(
                repository.list_agents(),
                repository.list_profile_acceptance_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/profile-acceptance-template.md")
    def profile_acceptance_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_acceptance_template_markdown(
                repository.list_profile_acceptance_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-acceptance-template.json")
    def profile_acceptance_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            profile_acceptance_template_json(
                repository.list_profile_acceptance_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/profile-soul/{agent_id}.md")
    def profile_soul(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_soul_markdown(agent),
            media_type="text/markdown",
        )

    @app.get("/setup/profile-manifest/{agent_id}.json")
    def profile_manifest(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_manifest_json(agent),
            media_type="application/json",
        )

    @app.get("/setup/profile-apply/{agent_id}.ps1")
    def profile_apply_script(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            profile_apply_powershell(agent),
            media_type="text/plain",
        )

    @app.get("/setup/inputs-needed.md")
    def inputs_needed(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            inputs_needed_markdown(
                repository.list_setup_inputs(),
                repository.list_agents(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/first-run.md")
    def first_run_report() -> PlainTextResponse:
        return PlainTextResponse(
            first_run_markdown(),
            media_type="text/markdown",
        )

    @app.get("/setup/first-run.json")
    def first_run_export() -> PlainTextResponse:
        return PlainTextResponse(
            first_run_json(),
            media_type="application/json",
        )

    @app.get("/setup/first-run.ps1")
    def first_run_script() -> PlainTextResponse:
        return PlainTextResponse(
            first_run_powershell(),
            media_type="text/plain",
        )

    @app.get("/setup/progress-board.md")
    def progress_board_report(request: Request) -> PlainTextResponse:
        repository: CompanyRepository = request.app.state.repository
        integrations = repository.list_integrations()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                repository.list_agents(),
                integrations,
            )
        ]
        return PlainTextResponse(
            progress_board_markdown(
                setup_inputs=repository.list_setup_inputs(),
                runtime_checks=runtime_checks,
                secret_requirements=repository.list_secret_requirements(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
                model_preferences=repository.list_model_preferences(),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
                founder_decisions=repository.list_founder_decisions(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/progress-board.json")
    def progress_board_export(request: Request) -> PlainTextResponse:
        repository: CompanyRepository = request.app.state.repository
        integrations = repository.list_integrations()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                repository.list_agents(),
                integrations,
            )
        ]
        return PlainTextResponse(
            progress_board_json(
                setup_inputs=repository.list_setup_inputs(),
                runtime_checks=runtime_checks,
                secret_requirements=repository.list_secret_requirements(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
                model_preferences=repository.list_model_preferences(),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
                founder_decisions=repository.list_founder_decisions(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/founder-input-request.md")
    def founder_input_request(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_input_request_markdown(
                repository.list_setup_inputs(),
                repository.list_secret_requirements(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/founder-input-request.json")
    def founder_input_request_schema(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_input_request_json(
                repository.list_setup_inputs(),
                repository.list_secret_requirements(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/founder-inputs.ps1")
    def founder_input_collector(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_input_collector_powershell(repository.list_setup_inputs()),
            media_type="text/plain",
        )

    @app.get("/setup/input-ledger.md")
    def input_ledger(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            input_ledger_markdown(
                setup_inputs=repository.list_setup_inputs(),
                secret_requirements=repository.list_secret_requirements(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
                model_preferences=repository.list_model_preferences(),
                integrations=repository.list_integrations(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/input-ledger.json")
    def input_ledger_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            input_ledger_json(
                setup_inputs=repository.list_setup_inputs(),
                secret_requirements=repository.list_secret_requirements(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
                model_preferences=repository.list_model_preferences(),
                integrations=repository.list_integrations(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/founder-handoff.md")
    def founder_handoff_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_handoff_markdown(
                setup_inputs=repository.list_setup_inputs(),
                secret_requirements=repository.list_secret_requirements(),
                model_preferences=repository.list_model_preferences(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/founder-handoff.json")
    def founder_handoff_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_handoff_json(
                setup_inputs=repository.list_setup_inputs(),
                secret_requirements=repository.list_secret_requirements(),
                model_preferences=repository.list_model_preferences(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/founder-decisions.md")
    def founder_decisions_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_decisions_markdown(repository.list_founder_decisions()),
            media_type="text/markdown",
        )

    @app.get("/setup/founder-decisions.json")
    def founder_decisions_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            founder_decisions_json(repository.list_founder_decisions()),
            media_type="application/json",
        )

    @app.get("/setup/credential-loading.md")
    def credential_loading_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            credential_loading_markdown(
                secret_requirements=repository.list_secret_requirements(),
                model_preferences=repository.list_model_preferences(),
                integrations=repository.list_integrations(),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/credential-loading.json")
    def credential_loading_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            credential_loading_json(
                secret_requirements=repository.list_secret_requirements(),
                model_preferences=repository.list_model_preferences(),
                integrations=repository.list_integrations(),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/credential-status-template.md")
    def credential_status_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            credential_status_template_markdown(repository.list_secret_requirements()),
            media_type="text/markdown",
        )

    @app.get("/setup/credential-status-template.json")
    def credential_status_schema(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            credential_status_template_json(repository.list_secret_requirements()),
            media_type="application/json",
        )

    @app.get("/setup/founder-next-actions.md")
    def founder_next_actions_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                repository.list_agents(),
                integrations,
            )
        ]
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return PlainTextResponse(
            founder_next_actions_markdown(
                activation_checks=checks,
                setup_inputs=setup_inputs,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                model_preferences=model_preferences,
                integrations=integrations,
                runtime_checks=runtime_checks,
                profile_acceptance_checks=profile_acceptance_checks,
                profile_installation_checks=profile_installation_checks,
                founder_decisions=founder_decisions,
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/founder-next-actions.json")
    def founder_next_actions_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                repository.list_agents(),
                integrations,
            )
        ]
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return PlainTextResponse(
            founder_next_actions_json(
                activation_checks=checks,
                setup_inputs=setup_inputs,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                model_preferences=model_preferences,
                integrations=integrations,
                runtime_checks=runtime_checks,
                profile_acceptance_checks=profile_acceptance_checks,
                profile_installation_checks=profile_installation_checks,
                founder_decisions=founder_decisions,
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-plan.md")
    def slack_setup_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_setup_plan_markdown(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/slack-manifest/{agent_id}.json")
    def slack_app_manifest(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return PlainTextResponse(
            slack_app_manifest_json(agent, repository.setup_input_map()),
            media_type="application/json",
        )

    @app.get("/setup/slack-manifests.json")
    def slack_app_manifests(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_app_manifests_bundle_json(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-provisioning.md")
    def slack_provisioning_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_provisioning_markdown(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/slack-provisioning.json")
    def slack_provisioning_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_provisioning_json(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-provisioning.ps1")
    def slack_provisioning_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_provisioning_powershell(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/slack-channel-template.md")
    def slack_channel_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_channel_template_markdown(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/slack-channel-template.json")
    def slack_channel_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_channel_template_json(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-bot-user-map.json")
    def slack_bot_user_map(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_bot_user_map_template_json(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-bot-user-map-template.md")
    def slack_bot_user_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_bot_user_template_markdown(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/slack-bot-user-map-template.json")
    def slack_bot_user_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_bot_user_template_json(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-workspace.md")
    def slack_workspace(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_workspace_markdown(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/slack-invite-matrix.json")
    def slack_invite_matrix(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_invite_matrix_json(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/slack-invite-matrix.csv")
    def slack_invite_matrix_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            slack_invite_matrix_csv(
                repository.list_agents(),
                repository.setup_input_map(),
            ),
            media_type="text/csv",
        )

    @app.get("/setup/telegram-plan.md")
    def telegram_setup_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_setup_plan_markdown(repository.setup_input_map()),
            media_type="text/markdown",
        )

    @app.get("/setup/telegram-botfather.md")
    def telegram_botfather_setup(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_botfather_setup_markdown(repository.setup_input_map()),
            media_type="text/markdown",
        )

    @app.get("/setup/telegram-recipient-template.md")
    def telegram_recipient_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_recipient_template_markdown(repository.setup_input_map()),
            media_type="text/markdown",
        )

    @app.get("/setup/telegram-recipient-template.json")
    def telegram_recipient_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_recipient_template_json(repository.setup_input_map()),
            media_type="application/json",
        )

    @app.get("/setup/telegram-provisioning.md")
    def telegram_provisioning_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_provisioning_markdown(
                setup_values=repository.setup_input_map(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/telegram-provisioning.json")
    def telegram_provisioning_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_provisioning_json(
                setup_values=repository.setup_input_map(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/telegram-provisioning.ps1")
    def telegram_provisioning_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_provisioning_powershell(
                setup_values=repository.setup_input_map(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/telegram-policy.md")
    def telegram_policy(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_policy_markdown(
                repository.setup_input_map(),
                repository.list_schedules(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/telegram-policy.json")
    def telegram_policy_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            telegram_policy_json(
                repository.setup_input_map(),
                repository.list_schedules(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/messaging-drill.md")
    def messaging_drill_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            messaging_drill_markdown(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
                messaging_checks=repository.list_messaging_checks(),
                secret_requirements=repository.list_secret_requirements(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/messaging-drill.json")
    def messaging_drill_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            messaging_drill_json(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
                messaging_checks=repository.list_messaging_checks(),
                secret_requirements=repository.list_secret_requirements(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/messaging-verification-template.md")
    def messaging_verification_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            messaging_verification_template_markdown(
                repository.list_messaging_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/messaging-verification-template.json")
    def messaging_verification_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            messaging_verification_template_json(
                repository.list_messaging_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/gateway-operations.md")
    def gateway_operations_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            gateway_operations_markdown(
                agents=repository.list_agents(),
                messaging_checks=repository.list_messaging_checks(),
                integrations=repository.list_integrations(),
                secret_requirements=repository.list_secret_requirements(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/gateway-operations.json")
    def gateway_operations_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            gateway_operations_json(
                agents=repository.list_agents(),
                messaging_checks=repository.list_messaging_checks(),
                integrations=repository.list_integrations(),
                secret_requirements=repository.list_secret_requirements(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/gateway-operations.ps1")
    def gateway_operations_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            gateway_operations_powershell(repository.list_agents()),
            media_type="text/plain",
        )

    @app.get("/setup/llm-plan.md")
    def llm_setup_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_setup_plan_markdown(repository.list_model_preferences()),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-credentials.md")
    def llm_credentials_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_credentials_plan_markdown(repository.list_model_preferences()),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-provisioning.md")
    def llm_provisioning_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_provisioning_markdown(
                model_preferences=repository.list_model_preferences(),
                secret_requirements=repository.list_secret_requirements(),
                integrations=repository.list_integrations(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-provisioning.json")
    def llm_provisioning_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_provisioning_json(
                model_preferences=repository.list_model_preferences(),
                secret_requirements=repository.list_secret_requirements(),
                integrations=repository.list_integrations(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/llm-provisioning.ps1")
    def llm_provisioning_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_provisioning_powershell(repository.list_model_preferences()),
            media_type="text/plain",
        )

    @app.get("/setup/llm-provider-presets.md")
    def llm_provider_presets_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_provider_presets_markdown(
                agents=repository.list_agents(),
                model_preferences=repository.list_model_preferences(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-provider-presets.json")
    def llm_provider_presets_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_provider_presets_json(
                agents=repository.list_agents(),
                model_preferences=repository.list_model_preferences(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/llm-preference-template.md")
    def llm_preference_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_preference_template_markdown(repository.list_model_preferences()),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-preference-template.json")
    def llm_preference_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_preference_template_json(repository.list_model_preferences()),
            media_type="application/json",
        )

    @app.get("/setup/llm-finalize.md")
    def llm_finalization_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_finalization_markdown(repository.list_model_preferences()),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-finalize.ps1")
    def llm_finalization_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_finalization_powershell(repository.list_model_preferences()),
            media_type="text/plain",
        )

    @app.get("/setup/llm-smoke.md")
    def llm_smoke_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_smoke_markdown(
                agents=repository.list_agents(),
                model_preferences=repository.list_model_preferences(),
                secret_requirements=repository.list_secret_requirements(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/llm-smoke.json")
    def llm_smoke_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            llm_smoke_json(
                agents=repository.list_agents(),
                model_preferences=repository.list_model_preferences(),
                secret_requirements=repository.list_secret_requirements(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/secret-audit.md")
    def secret_audit_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        requirements = secret_audit_requirements(
            repository.list_secret_requirements(),
            repository.list_model_preferences(),
        )
        return PlainTextResponse(
            secret_audit_markdown(requirements),
            media_type="text/markdown",
        )

    @app.get("/setup/secret-audit.ps1")
    def secret_audit_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        requirements = secret_audit_requirements(
            repository.list_secret_requirements(),
            repository.list_model_preferences(),
        )
        return PlainTextResponse(
            secret_audit_powershell(requirements),
            media_type="text/plain",
        )

    @app.get("/setup/readiness-report.md")
    def activation_readiness_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        checks = activation_checks(
            repository.list_setup_inputs(),
            repository.list_schedules(),
            repository.list_model_preferences(),
            repository.list_integrations(),
            repository.list_secret_requirements(),
            repository.list_messaging_checks(),
            repository.list_schedule_checks(),
            repository.list_kanban_checks(),
            repository.list_profile_acceptance_checks(),
            repository.list_profile_installation_checks(),
        )
        return PlainTextResponse(
            activation_report_markdown(checks),
            media_type="text/markdown",
        )

    @app.get("/setup/company-manifest.md")
    def company_manifest_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return PlainTextResponse(
            company_manifest_markdown(
                agents=repository.list_agents(),
                setup_inputs=setup_inputs,
                schedules=schedules,
                model_preferences=model_preferences,
                integrations=integrations,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                workflow_templates=repository.list_workflow_templates(),
                activation_checks=checks,
                profile_acceptance_checks=profile_acceptance_checks,
                profile_installation_checks=profile_installation_checks,
                founder_decisions=founder_decisions,
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/company-manifest.json")
    def company_manifest_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return PlainTextResponse(
            company_manifest_json(
                agents=repository.list_agents(),
                setup_inputs=setup_inputs,
                schedules=schedules,
                model_preferences=model_preferences,
                integrations=integrations,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                workflow_templates=repository.list_workflow_templates(),
                activation_checks=checks,
                profile_acceptance_checks=profile_acceptance_checks,
                profile_installation_checks=profile_installation_checks,
                founder_decisions=founder_decisions,
            ),
            media_type="application/json",
        )

    @app.get("/setup/company-launch-drill.md")
    def company_launch_drill_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                repository.list_agents(),
                integrations,
            )
        ]
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return PlainTextResponse(
            company_launch_drill_markdown(
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
                schedules=schedules,
                workflow_templates=repository.list_workflow_templates(),
                activation_checks=checks,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                model_preferences=model_preferences,
                integrations=integrations,
                setup_inputs=setup_inputs,
                runtime_checks=runtime_checks,
                profile_acceptance_checks=profile_acceptance_checks,
                profile_installation_checks=profile_installation_checks,
                founder_decisions=founder_decisions,
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/company-launch-drill.json")
    def company_launch_drill_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        founder_decisions = repository.list_founder_decisions()
        runtime_checks = [
            asdict(check)
            for check in runtime_preflight_checks(
                request.app.state.settings,
                repository.list_agents(),
                integrations,
            )
        ]
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        return PlainTextResponse(
            company_launch_drill_json(
                agents=repository.list_agents(),
                relationships=repository.list_agent_relationships(),
                schedules=schedules,
                workflow_templates=repository.list_workflow_templates(),
                activation_checks=checks,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                model_preferences=model_preferences,
                integrations=integrations,
                setup_inputs=setup_inputs,
                runtime_checks=runtime_checks,
                profile_acceptance_checks=profile_acceptance_checks,
                profile_installation_checks=profile_installation_checks,
                founder_decisions=founder_decisions,
            ),
            media_type="application/json",
        )

    @app.get("/setup/kickoff-readiness.md")
    def kickoff_readiness_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        agents = repository.list_agents()
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        runtime_checks = runtime_preflight_checks(
            request.app.state.settings,
            agents,
            integrations,
        )
        return PlainTextResponse(
            kickoff_readiness_markdown(
                agents=agents,
                workflow_templates=repository.list_workflow_templates(),
                activation_checks=checks,
                runtime_checks=runtime_checks,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                model_preferences=model_preferences,
                integrations=integrations,
                profile_installation_checks=profile_installation_checks,
                profile_acceptance_checks=profile_acceptance_checks,
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/kickoff-readiness.json")
    def kickoff_readiness_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        agents = repository.list_agents()
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        runtime_checks = runtime_preflight_checks(
            request.app.state.settings,
            agents,
            integrations,
        )
        return PlainTextResponse(
            kickoff_readiness_json(
                agents=agents,
                workflow_templates=repository.list_workflow_templates(),
                activation_checks=checks,
                runtime_checks=runtime_checks,
                secret_requirements=secret_requirements,
                messaging_checks=messaging_checks,
                schedule_checks=schedule_checks,
                kanban_checks=kanban_checks,
                model_preferences=model_preferences,
                integrations=integrations,
                profile_installation_checks=profile_installation_checks,
                profile_acceptance_checks=profile_acceptance_checks,
            ),
            media_type="application/json",
        )

    @app.get("/setup/activation-checklist.md")
    def activation_checklist(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            activation_checklist_markdown(
                repository.list_agents(),
                repository.setup_input_map(),
                repository.list_schedules(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/activation-sequence.md")
    def activation_sequence(request: Request):
        repository: CompanyRepository = request.app.state.repository
        checks = activation_checks(
            repository.list_setup_inputs(),
            repository.list_schedules(),
            repository.list_model_preferences(),
            repository.list_integrations(),
            repository.list_secret_requirements(),
            repository.list_messaging_checks(),
            repository.list_schedule_checks(),
            repository.list_kanban_checks(),
            repository.list_profile_acceptance_checks(),
            repository.list_profile_installation_checks(),
        )
        return PlainTextResponse(
            activation_sequence_markdown(
                checks,
                repository.list_setup_inputs(),
                repository.list_secret_requirements(),
                repository.list_messaging_checks(),
                repository.list_schedule_checks(),
                repository.list_kanban_checks(),
                repository.list_model_preferences(),
                repository.list_integrations(),
                repository.list_profile_installation_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/activation-runner.md")
    def activation_runner(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            activation_runner_markdown(
                repository.list_agents(),
                repository.setup_input_map(),
                repository.list_schedules(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/activation-runner.ps1")
    def activation_runner_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            activation_runner_powershell(
                repository.list_agents(),
                repository.setup_input_map(),
                repository.list_schedules(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/live-verification.md")
    def live_verification(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            live_verification_markdown(
                repository.list_secret_requirements(),
                repository.list_messaging_checks(),
                repository.list_schedule_checks(),
                repository.list_kanban_checks(),
                repository.list_model_preferences(),
                repository.list_integrations(),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/verification-evidence.md")
    def verification_evidence_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            verification_evidence_markdown(
                agents=repository.list_agents(),
                secret_requirements=repository.list_secret_requirements(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
                model_preferences=repository.list_model_preferences(),
                profile_smoke_runs=repository.latest_runs_by_type("profile-smoke"),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
                founder_decisions=repository.list_founder_decisions(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/verification-evidence.json")
    def verification_evidence_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            verification_evidence_json(
                agents=repository.list_agents(),
                secret_requirements=repository.list_secret_requirements(),
                messaging_checks=repository.list_messaging_checks(),
                schedule_checks=repository.list_schedule_checks(),
                kanban_checks=repository.list_kanban_checks(),
                model_preferences=repository.list_model_preferences(),
                profile_smoke_runs=repository.latest_runs_by_type("profile-smoke"),
                profile_installation_checks=repository.list_profile_installation_checks(),
                profile_acceptance_checks=repository.list_profile_acceptance_checks(),
                founder_decisions=repository.list_founder_decisions(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/runtime-preflight.md")
    def runtime_preflight_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        checks = runtime_preflight_checks(
            request.app.state.settings,
            repository.list_agents(),
            repository.list_integrations(),
        )
        return PlainTextResponse(
            runtime_preflight_markdown(checks),
            media_type="text/markdown",
        )

    @app.get("/setup/runtime-preflight.json")
    def runtime_preflight_report_json(request: Request):
        repository: CompanyRepository = request.app.state.repository
        checks = runtime_preflight_checks(
            request.app.state.settings,
            repository.list_agents(),
            repository.list_integrations(),
        )
        return PlainTextResponse(
            runtime_preflight_json(checks),
            media_type="application/json",
        )

    @app.get("/setup/runtime-preflight.ps1")
    def runtime_preflight_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            runtime_preflight_powershell(repository.list_agents()),
            media_type="text/plain",
        )

    @app.get("/setup/hermes-runtime.md")
    def hermes_runtime_report() -> PlainTextResponse:
        return PlainTextResponse(
            hermes_runtime_markdown(),
            media_type="text/markdown",
        )

    @app.get("/setup/hermes-runtime.json")
    def hermes_runtime_export() -> PlainTextResponse:
        return PlainTextResponse(
            hermes_runtime_json(),
            media_type="application/json",
        )

    @app.get("/setup/hermes-install.ps1")
    def hermes_install_script() -> PlainTextResponse:
        return PlainTextResponse(
            hermes_install_powershell(),
            media_type="text/plain",
        )

    @app.get("/setup/schedule-provisioning.md")
    def schedule_provisioning_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_provisioning_markdown(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
                schedules=repository.list_schedules(),
                schedule_checks=repository.list_schedule_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/schedule-provisioning.json")
    def schedule_provisioning_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_provisioning_json(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
                schedules=repository.list_schedules(),
                schedule_checks=repository.list_schedule_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/schedule-provisioning.ps1")
    def schedule_provisioning_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_provisioning_powershell(
                agents=repository.list_agents(),
                setup_values=repository.setup_input_map(),
                schedules=repository.list_schedules(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/schedule-config-template.md")
    def schedule_config_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_config_template_markdown(repository.list_schedules()),
            media_type="text/markdown",
        )

    @app.get("/setup/schedule-config-template.json")
    def schedule_config_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_config_template_json(repository.list_schedules()),
            media_type="application/json",
        )

    @app.get("/setup/schedule-verification-template.md")
    def schedule_verification_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_verification_template_markdown(
                repository.list_schedule_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/schedule-verification-template.json")
    def schedule_verification_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            schedule_verification_template_json(
                repository.list_schedule_checks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/standup-runbook.md")
    def standup_runbook(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            standup_runbook_markdown(
                repository.setup_input_map(),
                repository.list_schedules(),
                repository.list_schedule_checks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/standup-preview.md")
    def standup_preview_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        settings: Settings = request.app.state.settings
        return PlainTextResponse(
            standup_preview_markdown(
                schedules=repository.list_schedules(),
                agents=repository.list_agents(),
                tasks=repository.list_tasks(),
                documents=repository.list_documents(),
                slack_founder_command=settings.slack_founder_command,
                slack_alerts=settings.slack_alerts,
                telegram_urgent_label=settings.telegram_urgent_label,
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/standup-preview.json")
    def standup_preview_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        settings: Settings = request.app.state.settings
        return PlainTextResponse(
            standup_preview_json(
                schedules=repository.list_schedules(),
                agents=repository.list_agents(),
                tasks=repository.list_tasks(),
                documents=repository.list_documents(),
                slack_founder_command=settings.slack_founder_command,
                slack_alerts=settings.slack_alerts,
                telegram_urgent_label=settings.telegram_urgent_label,
            ),
            media_type="application/json",
        )

    @app.get("/setup/standup-cron.ps1")
    def standup_cron_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            standup_cron_powershell(
                repository.setup_input_map(),
                repository.list_schedules(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/kanban-runbook.md")
    def kanban_runbook(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            kanban_runbook_markdown(
                repository.list_kanban_checks(),
                repository.list_workflow_templates(),
                repository.list_tasks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/kanban-provisioning.md")
    def kanban_provisioning_plan(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            kanban_provisioning_markdown(
                workflow_templates=repository.list_workflow_templates(),
                kanban_checks=repository.list_kanban_checks(),
                tasks=repository.list_tasks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/kanban-provisioning.json")
    def kanban_provisioning_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            kanban_provisioning_json(
                workflow_templates=repository.list_workflow_templates(),
                kanban_checks=repository.list_kanban_checks(),
                tasks=repository.list_tasks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/kanban-provisioning.ps1")
    def kanban_provisioning_script(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            kanban_provisioning_powershell(
                workflow_templates=repository.list_workflow_templates(),
            ),
            media_type="text/plain",
        )

    @app.get("/setup/kanban-verification-template.md")
    def kanban_verification_template(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            kanban_verification_template_markdown(repository.list_kanban_checks()),
            media_type="text/markdown",
        )

    @app.get("/setup/kanban-verification-template.json")
    def kanban_verification_template_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            kanban_verification_template_json(repository.list_kanban_checks()),
            media_type="application/json",
        )

    @app.get("/setup/project-workflow.md")
    def project_workflow_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            project_workflow_markdown(
                workflow_templates=repository.list_workflow_templates(),
                kanban_checks=repository.list_kanban_checks(),
                tasks=repository.list_tasks(),
            ),
            media_type="text/markdown",
        )

    @app.get("/setup/project-workflow.json")
    def project_workflow_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            project_workflow_json(
                workflow_templates=repository.list_workflow_templates(),
                kanban_checks=repository.list_kanban_checks(),
                tasks=repository.list_tasks(),
            ),
            media_type="application/json",
        )

    @app.get("/setup/idea-intake.md")
    def idea_intake_report(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            idea_intake_markdown(repository.list_workflow_templates()),
            media_type="text/markdown",
        )

    @app.get("/setup/idea-intake.json")
    def idea_intake_export(request: Request):
        repository: CompanyRepository = request.app.state.repository
        return PlainTextResponse(
            idea_intake_json(repository.list_workflow_templates()),
            media_type="application/json",
        )

    @app.get("/setup/kanban-diagnostics.ps1")
    def kanban_diagnostics_script():
        return PlainTextResponse(
            kanban_diagnostics_powershell(),
            media_type="text/plain",
        )

    @app.post("/setup/inputs")
    async def update_setup_inputs(request: Request):
        repository: CompanyRepository = request.app.state.repository
        form = await request.form()
        values = {key: str(value) for key, value in form.items()}
        reject_secret_values(values)
        repository.update_setup_inputs(values)
        return RedirectResponse("/setup", status_code=303)

    @app.post("/setup/founder-input-reply")
    def import_founder_input_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_founder_input_reply(reply_text, repository.list_setup_inputs())
        if summary["values"]:
            repository.update_setup_inputs(summary["values"])
        return RedirectResponse(founder_input_import_redirect(summary), status_code=303)

    @app.post("/setup/slack-channel-reply")
    def import_slack_channel_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_slack_channel_reply(reply_text)
        if summary["parse_error"]:
            raise HTTPException(status_code=400, detail=summary["parse_error"])
        if summary["invalid_channel_ids"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid Slack channel IDs for: "
                + ", ".join(summary["invalid_channel_ids"]),
            )
        if summary["values"]:
            repository.update_setup_inputs(summary["values"])
        return RedirectResponse(slack_channel_import_redirect(summary), status_code=303)

    @app.post("/setup/slack-bot-user-map-reply")
    def import_slack_bot_user_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_slack_bot_user_reply(reply_text, repository.list_agents())
        if summary["parse_error"]:
            raise HTTPException(status_code=400, detail=summary["parse_error"])
        if summary["invalid_user_ids"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid Slack bot user IDs for: "
                + ", ".join(summary["invalid_user_ids"]),
            )
        if summary["values"]:
            repository.update_setup_inputs(summary["values"])
        return RedirectResponse(slack_bot_user_import_redirect(summary), status_code=303)

    @app.post("/setup/telegram-recipient-reply")
    def import_telegram_recipient_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_telegram_recipient_reply(reply_text)
        if summary["parse_error"]:
            raise HTTPException(status_code=400, detail=summary["parse_error"])
        if summary["invalid_keys"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid Telegram recipient IDs for: "
                + ", ".join(summary["invalid_keys"]),
            )
        if summary["values"]:
            repository.update_setup_inputs(summary["values"])
        return RedirectResponse(
            telegram_recipient_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/schedule-config-reply")
    def import_schedule_config_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_schedule_config_reply(reply_text, repository.list_schedules())
        if summary["parse_error"]:
            raise HTTPException(status_code=400, detail=summary["parse_error"])
        if summary["invalid_fields"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid schedule configuration fields: "
                + ", ".join(summary["invalid_fields"]),
            )
        for schedule_id, update in summary["updates"].items():
            repository.update_schedule(
                schedule_id=schedule_id,
                name=update["name"],
                hour=update["hour"],
                minute=update["minute"],
                timezone=update["timezone"],
                slack_channel=update["slack_channel"],
                telegram_policy=update["telegram_policy"],
                active=update["active"],
            )
        return RedirectResponse(
            schedule_config_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/profile-personalization-reply")
    def import_profile_personalization_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_profile_personalization_reply(
            reply_text,
            repository.list_agents(),
        )
        if summary["parse_error"]:
            raise HTTPException(status_code=400, detail=summary["parse_error"])
        if summary["invalid_profiles"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid profile personalization for: "
                + ", ".join(summary["invalid_profiles"]),
            )

        merged_updates = []
        for agent_id, update in summary["updates"].items():
            current = repository.get_agent(agent_id)
            if current is None:
                continue
            merged = {
                "agent_id": agent_id,
                "description": update.get("description", current["description"]),
                "soul": update.get("soul", current["soul"]),
                "capabilities": update.get("capabilities", current["capabilities"]),
                "slack_channel": update.get("slack_channel", current["slack_channel"]),
                "telegram_policy": update.get(
                    "telegram_policy",
                    current["telegram_policy"],
                ),
                "hermes_command": update.get(
                    "hermes_command",
                    current["hermes_command"],
                ),
            }
            if (
                not merged["description"].strip()
                or not merged["soul"].strip()
                or not merged["capabilities"]
                or not merged["slack_channel"].strip()
                or not merged["telegram_policy"].strip()
                or not merged["hermes_command"].strip()
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Incomplete profile personalization for: {agent_id}",
                )
            reject_secret_values(
                {
                    "description": merged["description"],
                    "soul": merged["soul"],
                    "capabilities": "\n".join(merged["capabilities"]),
                    "slack_channel": merged["slack_channel"],
                    "telegram_policy": merged["telegram_policy"],
                    "hermes_command": merged["hermes_command"],
                }
            )
            merged_updates.append(merged)

        for merged in merged_updates:
            repository.update_agent_profile(
                agent_id=merged["agent_id"],
                description=merged["description"],
                soul=merged["soul"],
                capabilities=merged["capabilities"],
            )
            repository.update_agent_routing(
                agent_id=merged["agent_id"],
                slack_channel=merged["slack_channel"],
                telegram_policy=merged["telegram_policy"],
                hermes_command=merged["hermes_command"],
            )

        return RedirectResponse(
            profile_personalization_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/llm-preference-reply")
    def import_llm_preference_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_llm_preference_reply(
            reply_text,
            repository.list_model_preferences(),
        )
        if summary["parse_error"]:
            raise HTTPException(status_code=400, detail=summary["parse_error"])
        if summary["invalid_preferences"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid LLM preference for: "
                + ", ".join(summary["invalid_preferences"]),
            )

        merged_updates = []
        for agent_id, update in summary["updates"].items():
            current = repository.get_model_preference(agent_id)
            if current is None:
                continue
            merged = {
                "agent_id": agent_id,
                "provider": update.get("provider", current["provider"]),
                "model": update.get("model", current["model"]),
                "fallback_provider": update.get(
                    "fallback_provider",
                    current["fallback_provider"],
                ),
                "fallback_model": update.get(
                    "fallback_model",
                    current["fallback_model"],
                ),
                "auth_method": update.get("auth_method", current["auth_method"]),
                "status": update.get(
                    "status",
                    (
                        "ready_for_verification"
                        if current["status"] == "verified"
                        else current["status"]
                    ),
                ),
                "notes": update.get("notes", current["notes"]),
            }
            if (
                not merged["provider"].strip()
                or not merged["model"].strip()
                or not merged["auth_method"].strip()
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Incomplete LLM preference for: {agent_id}",
                )
            reject_secret_values(
                {
                    "provider": merged["provider"],
                    "model": merged["model"],
                    "fallback_provider": merged["fallback_provider"],
                    "fallback_model": merged["fallback_model"],
                    "auth_method": merged["auth_method"],
                    "notes": merged["notes"],
                }
            )
            merged_updates.append(merged)

        for merged in merged_updates:
            repository.update_model_preference(
                agent_id=merged["agent_id"],
                provider=merged["provider"],
                model=merged["model"],
                fallback_provider=merged["fallback_provider"],
                fallback_model=merged["fallback_model"],
                auth_method=merged["auth_method"],
                status=merged["status"],
                notes=merged["notes"],
            )

        return RedirectResponse(
            llm_preference_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/credential-status-reply")
    def import_credential_status_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_credential_status_reply(
            reply_text,
            repository.list_secret_requirements(),
        )
        if summary["invalid_statuses"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid credential status for: "
                + ", ".join(summary["invalid_statuses"]),
            )
        for requirement_id, update in summary["updates"].items():
            current = repository.get_secret_requirement(requirement_id)
            if current is None:
                continue
            reject_manual_llm_verified_status(current["category"], update["status"])
            repository.update_secret_requirement(
                requirement_id=requirement_id,
                status=update["status"],
                notes=update["notes"] or current["notes"],
            )
        return RedirectResponse(
            credential_status_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/messaging-verification-reply")
    def import_messaging_verification_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_messaging_verification_reply(
            reply_text,
            repository.list_messaging_checks(),
        )
        if summary["invalid_statuses"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid messaging status for: "
                + ", ".join(summary["invalid_statuses"]),
            )
        for check_id, update in summary["updates"].items():
            check = repository.get_messaging_check(check_id)
            if check is None:
                continue
            if update["status"] == "verified":
                credential_blocker = messaging_check_credential_blocker(
                    repository,
                    check,
                )
                if credential_blocker:
                    raise HTTPException(status_code=409, detail=credential_blocker)
        touched_platforms = set()
        for check_id, update in summary["updates"].items():
            check = repository.get_messaging_check(check_id)
            if check is None:
                continue
            reject_secret_values({"evidence": update["evidence"]})
            repository.update_messaging_check(
                check_id=check_id,
                status=update["status"],
                evidence=update["evidence"] or check["evidence"],
            )
            touched_platforms.add(check["platform"])
        for platform in touched_platforms:
            refresh_messaging_integration_status(repository, platform)
        return RedirectResponse(
            messaging_verification_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/profile-acceptance-reply")
    def import_profile_acceptance_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_profile_acceptance_reply(
            reply_text,
            repository.list_profile_acceptance_checks(),
        )
        if summary["invalid_statuses"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid profile acceptance status for: "
                + ", ".join(summary["invalid_statuses"]),
            )
        for check_id, update in summary["updates"].items():
            check = repository.get_profile_acceptance_check(check_id)
            if check is None:
                continue
            if update["status"] == "verified":
                prerequisite_blocker = profile_acceptance_prerequisite_blocker(
                    repository,
                    check,
                )
                if prerequisite_blocker:
                    raise HTTPException(status_code=409, detail=prerequisite_blocker)
        for check_id, update in summary["updates"].items():
            check = repository.get_profile_acceptance_check(check_id)
            if check is None:
                continue
            reject_secret_values({"evidence": update["evidence"]})
            repository.update_profile_acceptance_check(
                check_id=check_id,
                status=update["status"],
                evidence=update["evidence"] or check["evidence"],
            )
        return RedirectResponse(
            profile_acceptance_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/schedule-verification-reply")
    def import_schedule_verification_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_schedule_verification_reply(
            reply_text,
            repository.list_schedule_checks(),
        )
        if summary["invalid_statuses"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid schedule verification status for: "
                + ", ".join(summary["invalid_statuses"]),
            )
        for check_id, update in summary["updates"].items():
            check = repository.get_schedule_check(check_id)
            if check is None:
                continue
            if update["status"] == "verified":
                prerequisite_blocker = staged_schedule_check_prerequisite_blocker(
                    repository,
                    check,
                    summary["updates"],
                )
                if prerequisite_blocker:
                    raise HTTPException(status_code=409, detail=prerequisite_blocker)
        for check_id, update in summary["updates"].items():
            check = repository.get_schedule_check(check_id)
            if check is None:
                continue
            reject_secret_values({"evidence": update["evidence"]})
            repository.update_schedule_check(
                check_id=check_id,
                status=update["status"],
                evidence=update["evidence"] or check["evidence"],
            )
        if repository.active_schedule_verification_ready():
            repository.update_integration_status("standup-cron", "configured")
        return RedirectResponse(
            schedule_verification_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/kanban-verification-reply")
    def import_kanban_verification_reply(
        request: Request,
        reply_text: str = Form(...),
    ):
        reject_secret_values({"reply_text": reply_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_kanban_verification_reply(
            reply_text,
            repository.list_kanban_checks(),
        )
        if summary["invalid_statuses"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid Kanban verification status for: "
                + ", ".join(summary["invalid_statuses"]),
            )
        for check_id, update in summary["updates"].items():
            check = repository.get_kanban_check(check_id)
            if check is None:
                continue
            reject_secret_values({"evidence": update["evidence"]})
            repository.update_kanban_check(
                check_id=check_id,
                status=update["status"],
                evidence=update["evidence"] or check["evidence"],
            )
        if repository.kanban_verification_ready():
            repository.update_integration_status("hermes-kanban", "configured")
        return RedirectResponse(
            kanban_verification_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/profile-installation-audit")
    def import_profile_installation_audit(
        request: Request,
        audit_text: str = Form(...),
    ):
        reject_secret_values({"audit_text": audit_text})
        repository: CompanyRepository = request.app.state.repository
        summary = parse_profile_installation_audit(
            audit_text,
            repository.list_profile_installation_checks(),
        )
        for check_id, update in summary["updates"].items():
            repository.update_profile_installation_check(
                check_id=check_id,
                status=update["status"],
                evidence=update["evidence"],
            )
        return RedirectResponse(
            profile_installation_import_redirect(summary),
            status_code=303,
        )

    @app.post("/setup/integrations/{integration_id}")
    def update_integration(
        request: Request,
        integration_id: str,
        status: str = Form(...),
    ):
        repository: CompanyRepository = request.app.state.repository
        allowed = {"needs_input", "needs_setup", "ready", "configured", "deferred"}
        if status not in allowed:
            raise HTTPException(status_code=400, detail="Invalid integration status")
        repository.update_integration_status(integration_id, status)
        return RedirectResponse("/setup", status_code=303)

    @app.post("/setup/schedules/{schedule_id}")
    def update_schedule(
        request: Request,
        schedule_id: str,
        name: str = Form(...),
        hour: int = Form(...),
        minute: int = Form(...),
        timezone: str = Form(...),
        slack_channel: str = Form(...),
        telegram_policy: str = Form(...),
        active: str | None = Form(None),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_schedule(schedule_id) is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise HTTPException(status_code=400, detail="Invalid schedule time")
        if not name.strip() or not timezone.strip() or not slack_channel.strip():
            raise HTTPException(
                status_code=400,
                detail="Name, timezone, and Slack channel required",
            )
        reject_secret_values(
            {
                "name": name,
                "timezone": timezone,
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
            }
        )
        repository.update_schedule(
            schedule_id=schedule_id,
            name=name,
            hour=hour,
            minute=minute,
            timezone=timezone,
            slack_channel=slack_channel,
            telegram_policy=telegram_policy,
            active=active == "on",
        )
        return RedirectResponse("/setup", status_code=303)

    @app.post("/setup/model-preferences/{agent_id}")
    def update_model_preference(
        request: Request,
        agent_id: str,
        provider: str = Form(...),
        model: str = Form(...),
        fallback_provider: str = Form(""),
        fallback_model: str = Form(""),
        auth_method: str = Form("deferred_profile_secret"),
        status: str = Form("planned"),
        notes: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_agent(agent_id) is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        allowed_statuses = {"planned", "needs_secret", "ready_for_verification", "verified"}
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid model preference status")
        if status == "verified":
            raise HTTPException(
                status_code=409,
                detail=(
                    "LLM profile status is marked verified only by a successful "
                    "profile smoke check."
                ),
            )
        if not provider.strip() or not model.strip():
            raise HTTPException(status_code=400, detail="Provider and model are required")
        reject_secret_values(
            {
                "provider": provider,
                "model": model,
                "fallback_provider": fallback_provider,
                "fallback_model": fallback_model,
                "auth_method": auth_method,
                "notes": notes,
            }
        )
        repository.update_model_preference(
            agent_id=agent_id,
            provider=provider,
            model=model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            auth_method=auth_method,
            status=status,
            notes=notes,
        )
        return RedirectResponse("/setup", status_code=303)

    @app.post("/setup/llm-provider-presets/{preset_id}")
    def apply_llm_provider_preset(request: Request, preset_id: str):
        repository: CompanyRepository = request.app.state.repository
        try:
            preferences = llm_preset_preferences(preset_id, repository.list_agents())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="LLM provider preset not found") from exc
        for preference in preferences:
            reject_secret_values(
                {
                    "provider": preference["provider"],
                    "model": preference["model"],
                    "fallback_provider": preference["fallback_provider"],
                    "fallback_model": preference["fallback_model"],
                    "auth_method": preference["auth_method"],
                    "notes": preference["notes"],
                }
            )
            repository.update_model_preference(
                agent_id=preference["agent_id"],
                provider=preference["provider"],
                model=preference["model"],
                fallback_provider=preference["fallback_provider"],
                fallback_model=preference["fallback_model"],
                auth_method=preference["auth_method"],
                status=preference["status"],
                notes=preference["notes"],
            )
        return RedirectResponse("/setup#models", status_code=303)

    @app.post("/setup/secret-requirements/{requirement_id}")
    def update_secret_requirement(
        request: Request,
        requirement_id: str,
        status: str = Form(...),
        notes: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        requirement = repository.get_secret_requirement(requirement_id)
        if requirement is None:
            raise HTTPException(status_code=404, detail="Secret requirement not found")
        allowed_statuses = {"needed", "loaded", "verified", "deferred"}
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid secret status")
        reject_manual_llm_verified_status(requirement["category"], status)
        reject_secret_values({"notes": notes})
        repository.update_secret_requirement(
            requirement_id=requirement_id,
            status=status,
            notes=notes,
        )
        return RedirectResponse("/setup", status_code=303)

    @app.post("/setup/messaging-checks/{check_id}")
    def update_messaging_check(
        request: Request,
        check_id: str,
        status: str = Form(...),
        evidence: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        check = repository.get_messaging_check(check_id)
        if check is None:
            raise HTTPException(status_code=404, detail="Messaging check not found")
        allowed_statuses = {"needed", "loaded", "verified", "blocked", "deferred"}
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid messaging check status")
        reject_secret_values({"evidence": evidence})
        if status == "verified":
            credential_blocker = messaging_check_credential_blocker(repository, check)
            if credential_blocker:
                raise HTTPException(status_code=409, detail=credential_blocker)
        repository.update_messaging_check(
            check_id=check_id,
            status=status,
            evidence=evidence,
        )
        refresh_messaging_integration_status(repository, check["platform"])
        return RedirectResponse("/setup#messaging-verification", status_code=303)

    @app.post("/setup/schedule-checks/{check_id}")
    def update_schedule_check(
        request: Request,
        check_id: str,
        status: str = Form(...),
        evidence: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_schedule_check(check_id) is None:
            raise HTTPException(status_code=404, detail="Schedule check not found")
        allowed_statuses = {"needed", "verified", "blocked", "deferred"}
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid schedule check status")
        reject_secret_values({"evidence": evidence})
        check = repository.get_schedule_check(check_id)
        if status == "verified" and check is not None:
            prerequisite_blocker = schedule_check_prerequisite_blocker(repository, check)
            if prerequisite_blocker:
                raise HTTPException(status_code=409, detail=prerequisite_blocker)
        repository.update_schedule_check(
            check_id=check_id,
            status=status,
            evidence=evidence,
        )
        if repository.active_schedule_verification_ready():
            repository.update_integration_status("standup-cron", "configured")
        return RedirectResponse("/setup#schedule-verification", status_code=303)

    @app.post("/setup/kanban-checks/{check_id}")
    def update_kanban_check(
        request: Request,
        check_id: str,
        status: str = Form(...),
        evidence: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_kanban_check(check_id) is None:
            raise HTTPException(status_code=404, detail="Kanban check not found")
        allowed_statuses = {"needed", "verified", "blocked", "deferred"}
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid Kanban check status")
        reject_secret_values({"evidence": evidence})
        repository.update_kanban_check(
            check_id=check_id,
            status=status,
            evidence=evidence,
        )
        if repository.kanban_verification_ready():
            repository.update_integration_status("hermes-kanban", "configured")
        return RedirectResponse("/setup#kanban-verification", status_code=303)

    @app.post("/setup/profile-installation-checks/{check_id}")
    def update_profile_installation_check(
        request: Request,
        check_id: str,
        status: str = Form(...),
        evidence: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_profile_installation_check(check_id) is None:
            raise HTTPException(
                status_code=404,
                detail="Profile installation check not found",
            )
        allowed_statuses = {"needed", "verified", "blocked", "deferred"}
        if status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid profile installation status",
            )
        reject_secret_values({"evidence": evidence})
        repository.update_profile_installation_check(
            check_id=check_id,
            status=status,
            evidence=evidence,
        )
        return RedirectResponse(
            "/setup#profile-installation-tracking",
            status_code=303,
        )

    @app.post("/setup/profile-acceptance-checks/{check_id}")
    def update_profile_acceptance_check(
        request: Request,
        check_id: str,
        status: str = Form(...),
        evidence: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        check = repository.get_profile_acceptance_check(check_id)
        if check is None:
            raise HTTPException(status_code=404, detail="Profile acceptance check not found")
        allowed_statuses = {"needed", "verified", "failed", "blocked", "deferred"}
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid profile acceptance status")
        reject_secret_values({"evidence": evidence})
        if status == "verified":
            prerequisite_blocker = profile_acceptance_prerequisite_blocker(
                repository,
                check,
            )
            if prerequisite_blocker:
                raise HTTPException(status_code=409, detail=prerequisite_blocker)
        repository.update_profile_acceptance_check(
            check_id=check_id,
            status=status,
            evidence=evidence,
        )
        return RedirectResponse("/setup#profile-acceptance-tracking", status_code=303)

    @app.post("/setup/kanban/diagnostics")
    def kanban_diagnostics(request: Request):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent("chief-of-staff")
        if agent is None:
            raise HTTPException(status_code=500, detail="Chief of Staff profile is missing")
        run_id = repository.create_run(
            agent_id=agent["id"],
            run_type="kanban-diagnostics",
            prompt="hermes kanban diagnostics --json",
        )
        result = request.app.state.kanban_client.diagnostics()
        repository.complete_run(run_id, output=result.output, error=result.error)
        if result.ok:
            repository.update_kanban_check(
                check_id="kanban-diagnostics-pass",
                status="verified",
                evidence="Dashboard Kanban diagnostics passed.",
            )
            if repository.kanban_verification_ready():
                repository.update_integration_status("hermes-kanban", "configured")
        return RedirectResponse("/setup", status_code=303)

    @app.post("/setup/profile-smoke/{agent_id}")
    def profile_smoke_check(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        blocker = profile_installation_prerequisite_blocker(repository, agent_id)
        if blocker:
            raise HTTPException(status_code=409, detail=blocker)
        preference = repository.get_model_preference(agent_id)
        prompt = profile_smoke_prompt(agent, preference)
        run_id = repository.create_run(
            agent_id=agent["id"],
            run_type="profile-smoke",
            prompt=prompt,
        )
        result = request.app.state.hermes_client.run_prompt(agent, prompt)
        repository.complete_run(run_id, output=result.output, error=result.error)
        if result.ok and preference is not None:
            repository.update_model_preference(
                agent_id=agent_id,
                provider=preference["provider"],
                model=preference["model"],
                fallback_provider=preference["fallback_provider"],
                fallback_model=preference["fallback_model"],
                auth_method=preference["auth_method"],
                status="verified",
                notes=append_smoke_note(preference["notes"], "passed"),
            )
            llm_secret = next(
                (
                    item
                    for item in repository.list_secret_requirements()
                    if item["owner_agent_id"] == agent_id and item["category"] == "llm"
                ),
                None,
            )
            if llm_secret is not None:
                repository.update_agent_secret_requirements(
                    agent_id=agent_id,
                    category="llm",
                    status="verified",
                    notes=append_smoke_note(llm_secret["notes"], "passed"),
                )
            if all(
                item["status"] == "verified"
                for item in repository.list_model_preferences()
            ):
                repository.update_integration_status("llm-provider", "configured")
        return RedirectResponse("/setup#profile-smoke", status_code=303)

    @app.get("/queue")
    def agent_work_queue(
        request: Request,
        status: str = "",
        project_id: str = "",
        owner_agent_id: str = "",
    ):
        repository: CompanyRepository = request.app.state.repository
        try:
            items = repository.list_agent_work_items(
                project_id=project_id,
                owner_agent_id=owner_agent_id,
                status=status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return templates.TemplateResponse(
            request,
            "queue.html",
            {
                "items": items,
                "summary": repository.agent_work_queue_summary(),
                "agents": repository.list_agents(),
                "projects": repository.list_projects(),
                "states": QUEUE_STATES,
                "state_labels": QUEUE_STATE_LABELS,
                "priorities": QUEUE_PRIORITIES,
                "priority_labels": QUEUE_PRIORITY_LABELS,
                "filters": {
                    "status": status,
                    "project_id": project_id,
                    "owner_agent_id": owner_agent_id,
                },
            },
        )

    @app.post("/queue")
    def create_agent_work_item(
        request: Request,
        title: str = Form(...),
        owner_agent_id: str = Form("chief-of-staff"),
        status: str = Form("planned"),
        priority: str = Form("medium"),
        project_id: str = Form(""),
        summary: str = Form(""),
        blocked_reason: str = Form(""),
        blocked_owner: str = Form(""),
        founder_action_required: str = Form(""),
        return_to: str = Form("/queue"),
    ):
        repository: CompanyRepository = request.app.state.repository
        reject_secret_values(
            {
                "title": title,
                "owner_agent_id": owner_agent_id,
                "status": status,
                "priority": priority,
                "project_id": project_id,
                "summary": summary,
                "blocked_reason": blocked_reason,
                "blocked_owner": blocked_owner,
            }
        )
        try:
            repository.create_agent_work_item(
                title=title,
                owner_agent_id=owner_agent_id,
                summary=summary,
                status=status,
                priority=priority,
                project_id=project_id or None,
                blocked_reason=blocked_reason,
                blocked_owner=blocked_owner,
                founder_action_required=form_checkbox_checked(founder_action_required),
                source="manual",
                external_handoff_status="dashboard_source_of_truth",
                slack_channel="#decisions",
                telegram_policy="Telegram only if this blocks founder progress.",
            )
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(safe_return_path(return_to, "/queue"), status_code=303)

    @app.post("/queue/{work_item_id}")
    def update_agent_work_item(
        request: Request,
        work_item_id: str,
        status: str = Form(...),
        priority: str = Form(""),
        owner_agent_id: str = Form(""),
        blocked_reason: str = Form(""),
        blocked_owner: str = Form(""),
        founder_action_required: str = Form(""),
        founder_confirmed: str = Form(""),
        return_to: str = Form("/queue"),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_agent_work_item(work_item_id) is None:
            raise HTTPException(status_code=404, detail="Agent work item not found")
        reject_secret_values(
            {
                "status": status,
                "priority": priority,
                "owner_agent_id": owner_agent_id,
                "blocked_reason": blocked_reason,
                "blocked_owner": blocked_owner,
            }
        )
        try:
            repository.update_agent_work_item(
                work_item_id,
                status=status,
                priority=priority or None,
                owner_agent_id=owner_agent_id or None,
                blocked_reason=blocked_reason,
                blocked_owner=blocked_owner,
                founder_action_required=form_checkbox_checked(founder_action_required),
                founder_confirmed=form_checkbox_checked(founder_confirmed),
            )
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(safe_return_path(return_to, "/queue"), status_code=303)

    @app.get("/queue/{work_item_id}/handoff.json")
    def agent_work_item_handoff_json(request: Request, work_item_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        work_item = repository.get_agent_work_item(work_item_id)
        if work_item is None:
            raise HTTPException(status_code=404, detail="Agent work item not found")
        return profile_handoff_contract(repository, work_item)

    @app.get("/queue/{work_item_id}/handoff.md")
    def agent_work_item_handoff_markdown(request: Request, work_item_id: str):
        repository: CompanyRepository = request.app.state.repository
        work_item = repository.get_agent_work_item(work_item_id)
        if work_item is None:
            raise HTTPException(status_code=404, detail="Agent work item not found")
        contract = profile_handoff_contract(repository, work_item)
        return PlainTextResponse(profile_handoff_contract_markdown(contract))

    @app.get("/decisions")
    def founder_decision_inbox(
        request: Request,
        status: str = "",
        urgency: str = "",
        decision_type: str = "",
        project_id: str = "",
        stage_id: str = "",
        owner_agent_id: str = "",
    ):
        repository: CompanyRepository = request.app.state.repository
        try:
            decisions = repository.list_founder_decisions(
                status=status,
                urgency=urgency,
                decision_type=decision_type,
                project_id=project_id,
                stage_id=stage_id,
                owner_agent_id=owner_agent_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        all_decisions = repository.list_founder_decisions()
        return templates.TemplateResponse(
            request,
            "decisions.html",
            {
                "decisions": decisions,
                "selected_decision": decisions[0] if len(decisions) == 1 else None,
                "summary": founder_decisions_payload(all_decisions)["summary"],
                "agents": repository.list_agents(),
                "projects": repository.list_projects(),
                "decision_types": DECISION_TYPE_LABELS,
                "statuses": DECISION_STATUS_OPTIONS,
                "filters": {
                    "status": status,
                    "urgency": urgency,
                    "decision_type": decision_type,
                    "project_id": project_id,
                    "stage_id": stage_id,
                    "owner_agent_id": owner_agent_id,
                },
            },
        )

    @app.get("/decisions/{decision_id}")
    def founder_decision_detail(request: Request, decision_id: str):
        repository: CompanyRepository = request.app.state.repository
        selected_decision = repository.get_founder_decision(decision_id)
        if selected_decision is None:
            raise HTTPException(status_code=404, detail="Founder decision not found")
        all_decisions = repository.list_founder_decisions()
        return templates.TemplateResponse(
            request,
            "decisions.html",
            {
                "decisions": [selected_decision],
                "selected_decision": selected_decision,
                "summary": founder_decisions_payload(all_decisions)["summary"],
                "agents": repository.list_agents(),
                "projects": repository.list_projects(),
                "decision_types": DECISION_TYPE_LABELS,
                "statuses": DECISION_STATUS_OPTIONS,
                "filters": {
                    "status": "",
                    "urgency": "",
                    "decision_type": "",
                    "project_id": selected_decision.get("project_id") or "",
                    "stage_id": selected_decision.get("stage_id") or "",
                    "owner_agent_id": selected_decision.get("owner_agent_id") or "",
                },
            },
        )

    @app.post("/decisions")
    def create_founder_decision(
        request: Request,
        title: str = Form(...),
        urgency: str = Form("routine"),
        decision_type: str = Form("operating_decision"),
        source: str = Form("manual"),
        owner_agent_id: str = Form("chief-of-staff"),
        project_id: str = Form(""),
        stage_id: str = Form(""),
        artifact_id: str = Form(""),
        slack_channel: str = Form("#decisions"),
        telegram_policy: str = Form("Telegram only if this blocks founder progress."),
        context: str = Form(""),
        evidence: str = Form(""),
        requires_founder_approval: str = Form(""),
        return_to: str = Form("/decisions"),
    ):
        repository: CompanyRepository = request.app.state.repository
        allowed_urgencies = {"routine", "urgent"}
        if urgency not in allowed_urgencies:
            raise HTTPException(status_code=400, detail="Invalid decision urgency")
        if repository.get_agent(owner_agent_id) is None:
            raise HTTPException(status_code=404, detail="Decision owner profile not found")
        if not title.strip() or not context.strip() or not slack_channel.strip():
            raise HTTPException(
                status_code=400,
                detail="Title, context, and Slack channel are required",
            )
        reject_secret_values(
            {
                "title": title,
                "urgency": urgency,
                "decision_type": decision_type,
                "source": source,
                "owner_agent_id": owner_agent_id,
                "project_id": project_id,
                "stage_id": stage_id,
                "artifact_id": artifact_id,
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
                "context": context,
                "evidence": evidence,
            }
        )
        try:
            repository.create_founder_decision(
                title=title,
                urgency=urgency,
                decision_type=decision_type,
                source=source,
                owner_agent_id=owner_agent_id,
                project_id=project_id or None,
                stage_id=stage_id or None,
                artifact_id=artifact_id or None,
                slack_channel=slack_channel,
                telegram_policy=telegram_policy,
                context=context,
                evidence=evidence,
                requires_founder_approval=(
                    True if form_checkbox_checked(requires_founder_approval) else None
                ),
            )
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(
            safe_return_path(return_to, "/decisions"),
            status_code=303,
        )

    @app.post("/decisions/{decision_id}")
    def update_founder_decision(
        request: Request,
        decision_id: str,
        status: str = Form(...),
        decision: str = Form(""),
        founder_confirmed: str = Form(""),
        return_to: str = Form("/decisions"),
    ):
        repository: CompanyRepository = request.app.state.repository
        current = repository.get_founder_decision(decision_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Founder decision not found")
        allowed_statuses = set(DECISION_STATUS_OPTIONS)
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid founder decision status")
        if status in RESOLVED_DECISION_STATUSES and not decision.strip():
            raise HTTPException(
                status_code=400,
                detail="A decision note is required before resolving a founder decision",
            )
        reject_secret_values({"status": status, "decision": decision})
        try:
            repository.update_founder_decision(
                decision_id=decision_id,
                status=status,
                decision=decision,
                founder_confirmed=form_checkbox_checked(founder_confirmed),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(
            safe_return_path(return_to, "/decisions"),
            status_code=303,
        )

    @app.get("/projects")
    def projects(request: Request):
        repository: CompanyRepository = request.app.state.repository
        agents = repository.list_agents()
        setup_inputs = repository.list_setup_inputs()
        schedules = repository.list_schedules()
        model_preferences = repository.list_model_preferences()
        integrations = repository.list_integrations()
        secret_requirements = repository.list_secret_requirements()
        messaging_checks = repository.list_messaging_checks()
        schedule_checks = repository.list_schedule_checks()
        kanban_checks = repository.list_kanban_checks()
        profile_acceptance_checks = repository.list_profile_acceptance_checks()
        profile_installation_checks = repository.list_profile_installation_checks()
        checks = activation_checks(
            setup_inputs,
            schedules,
            model_preferences,
            integrations,
            secret_requirements,
            messaging_checks,
            schedule_checks,
            kanban_checks,
            profile_acceptance_checks,
            profile_installation_checks,
        )
        runtime_checks = runtime_preflight_checks(
            request.app.state.settings,
            agents,
            integrations,
        )
        return templates.TemplateResponse(
            request,
            "projects.html",
            {
                "projects": repository.list_projects(),
                "templates": repository.list_workflow_templates(),
                "kickoff_readiness": kickoff_readiness_payload(
                    agents=agents,
                    workflow_templates=repository.list_workflow_templates(),
                    activation_checks=checks,
                    runtime_checks=runtime_checks,
                    secret_requirements=secret_requirements,
                    messaging_checks=messaging_checks,
                    schedule_checks=schedule_checks,
                    kanban_checks=kanban_checks,
                    model_preferences=model_preferences,
                    integrations=integrations,
                ),
            },
        )

    @app.get("/projects/new")
    def new_project(request: Request):
        return templates.TemplateResponse(request, "project_new.html", {})

    @app.post("/projects")
    def create_project(
        request: Request,
        name: str = Form(...),
        founder_idea: str = Form(...),
        wizard_version: str = Form(""),
        product_category: str = Form(""),
        target_audience: str = Form(""),
        current_alternative: str = Form(""),
        problem_statement: str = Form(""),
        desired_outcome: str = Form(""),
        launch_tier: str = Form(""),
        deadline_pressure: str = Form(""),
        constraints: str = Form(""),
        non_goals: str = Form(""),
        success_metrics: str = Form(""),
    ):
        intake = product_wizard_intake_from_form(
            name=name,
            founder_idea=founder_idea,
            product_category=product_category,
            target_audience=target_audience,
            current_alternative=current_alternative,
            problem_statement=problem_statement,
            desired_outcome=desired_outcome,
            launch_tier=launch_tier,
            deadline_pressure=deadline_pressure,
            constraints=constraints,
            non_goals=non_goals,
            success_metrics=success_metrics,
        )
        reject_secret_values(intake)
        repository: CompanyRepository = request.app.state.repository
        if wizard_version == "product-wizard-v1":
            project_id = repository.create_structured_project(
                name=name.strip(),
                founder_idea=founder_idea.strip(),
                intake=intake,
            )
        else:
            project_id = repository.create_project_with_workflow(
                name=name.strip(),
                founder_idea=founder_idea.strip(),
            )
        repository.sync_project_wizard_work_items(project_id)
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    @app.get("/projects/{project_id}")
    def project_detail(
        request: Request,
        project_id: str,
        artifact_id: str = "",
    ):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        workflow_items = repository.list_project_workflow_items(project_id)
        wizard_stages = repository.list_project_wizard_stages(project_id)
        selected_artifact = None
        selected_stage = None
        if artifact_id:
            selected_artifact = repository.get_project_wizard_artifact(
                project_id,
                artifact_id,
            )
            if selected_artifact is None:
                raise HTTPException(status_code=404, detail="Artifact not found")
            selected_stage = repository.get_project_wizard_stage(
                project_id,
                selected_artifact["stage_id"],
            )
        current_stage = repository.next_actionable_stage(project_id)
        if current_stage is None and wizard_stages:
            current_stage = wizard_stages[-1]
        review_stage = selected_stage or current_stage
        latest_artifact = (
            artifact_view(
                selected_artifact
                or repository.latest_project_stage_artifact(
                    project_id,
                    review_stage["stage_id"],
                )
            )
            if review_stage
            else None
        )
        latest_generation_run = (
            generation_run_view(
                repository.latest_generation_run(
                    project_id=project_id,
                    stage_id=review_stage["stage_id"],
                    artifact_id=selected_artifact["id"] if selected_artifact else None,
                )
            )
            if review_stage
            else None
        )
        live_hermes_readiness = (
            evaluate_live_hermes_readiness(
                repository,
                project_id,
                review_stage["stage_id"],
            ).to_dict()
            if review_stage
            else None
        )
        live_hermes_run_confirmation = (
            evaluate_live_hermes_run_confirmation(
                repository,
                project_id,
                review_stage["stage_id"],
            ).to_dict()
            if review_stage
            else None
        )
        live_hermes_operator = (
            live_hermes_operator_console(
                settings=request.app.state.settings,
                repository=repository,
                project=project,
                stage_id=review_stage["stage_id"],
                live_readiness=live_hermes_readiness,
                run_confirmation=live_hermes_run_confirmation,
                latest_artifact=latest_artifact,
            )
            if review_stage
            else None
        )
        if latest_artifact:
            latest_artifact["selected"] = bool(selected_artifact)
            latest_artifact["generation_run"] = latest_generation_run
        task_stage_approved = project_task_stage_approved(repository, project_id)
        kanban_blocker = project_wizard_kanban_blocker(repository, project_id)
        codex_execution = codex_execution_package(repository, project_id)
        multi_agent_review = multi_agent_review_package(repository, project_id)
        project_memory = project_memory_package(repository, project_id)
        operating_loop = project_operating_loop_package(repository, project_id)
        external_dispatch_preview = project_external_dispatch_preview_package(
            repository,
            project_id,
            external_dispatch_enabled=request.app.state.settings.external_dispatch_enabled,
        )
        project_activity_events = repository.list_audit_events(
            project_id=project_id,
            limit=12,
        )
        founder_decisions = repository.list_founder_decisions(
            project_id=project_id,
            limit=6,
        )
        agent_work_items = repository.list_agent_work_items(
            project_id=project_id,
            limit=8,
        )
        founder_control_summary = project_founder_control_summary(
            project=project,
            active_stage=stage_view(review_stage) if review_stage else None,
            latest_artifact=latest_artifact,
            founder_decisions=founder_decisions,
            agent_work_items=agent_work_items,
            task_stage_approved=task_stage_approved,
            kanban_ready=not kanban_blocker,
            codex_execution=codex_execution,
            multi_agent_review=multi_agent_review,
        )
        memory_owner_options = repository.list_agents()
        return templates.TemplateResponse(
            request,
            "project.html",
            {
                "project": project,
                "workflow_items": workflow_items,
                "kanban_linked_count": sum(1 for item in workflow_items if item["kanban_task_id"]),
                "kanban_ready": not kanban_blocker,
                "kanban_blocker": kanban_blocker,
                "codex_execution": codex_execution,
                "multi_agent_review": multi_agent_review,
                "project_memory": project_memory,
                "operating_loop": operating_loop,
                "external_dispatch_preview": external_dispatch_preview,
                "project_activity_events": project_activity_events,
                "memory_reuse_policy": memory_reuse_policy_summary(
                    FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY
                ),
                "memory_category_options": memory_category_options(),
                "memory_confidence_options": memory_confidence_options(),
                "memory_owner_options": memory_owner_options,
                "founder_control_summary": founder_control_summary,
                "wizard_stages": [stage_view(stage) for stage in wizard_stages],
                "current_stage": stage_view(review_stage) if review_stage else None,
                "actionable_stage": stage_view(current_stage) if current_stage else None,
                "latest_artifact": latest_artifact,
                "latest_generation_run": latest_generation_run,
                "live_hermes_readiness": live_hermes_readiness,
                "live_hermes_run_confirmation": live_hermes_run_confirmation,
                "live_hermes_operator": live_hermes_operator,
                "stage_artifacts": stage_artifacts_view(
                    repository,
                    project_id,
                    wizard_stages,
                ),
                "selected_artifact_id": artifact_id,
                "revision_reasons": REVISION_REASON_LABELS,
                "task_stage_approved": task_stage_approved,
                "founder_decisions": founder_decisions,
                "agent_work_items": agent_work_items,
            },
        )

    @app.get("/projects/{project_id}/activity.json")
    def project_activity_json(request: Request, project_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_activity_package(repository, project)

    @app.get("/projects/{project_id}/operating-loop.json")
    def project_operating_loop_json(request: Request, project_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_operating_loop_package(repository, project_id)

    @app.get("/projects/{project_id}/external-dispatch-preview.json")
    def project_external_dispatch_preview_json(request: Request, project_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_external_dispatch_preview_package(
            repository,
            project_id,
            external_dispatch_enabled=request.app.state.settings.external_dispatch_enabled,
        )

    @app.post("/projects/{project_id}/external-dispatch-approval")
    def request_project_external_dispatch_approval(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            request_external_dispatch_approval(repository, project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#external-dispatch-preview",
            status_code=303,
        )

    @app.post("/projects/{project_id}/external-dispatch-audit")
    def consume_project_external_dispatch_audit(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            consume_external_dispatch_preview_approval(repository, project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#external-dispatch-preview",
            status_code=303,
        )

    @app.post("/projects/{project_id}/external-dispatch-run")
    def run_project_external_dispatch(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        settings: Settings = request.app.state.settings
        runner = getattr(request.app.state, "external_dispatch_runner", None)
        runner_label = getattr(
            request.app.state,
            "external_dispatch_runner_label",
            "external_dispatch_runner",
        )
        if runner is None and settings.external_dispatch_enabled:
            runner = HermesExternalDispatchCommandAdapter(
                enabled=True,
                runner_label="subprocess",
            )
            runner_label = runner.runner_label
        try:
            run_external_dispatch_runner(
                repository,
                project_id,
                enabled=settings.external_dispatch_enabled,
                runner=runner,
                runner_label=runner_label,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#external-dispatch-preview",
            status_code=303,
        )

    @app.get("/projects/{project_id}/codex-execution.json")
    def project_codex_execution_json(request: Request, project_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return codex_execution_package(repository, project_id)

    @app.get("/projects/{project_id}/multi-agent-review.json")
    def project_multi_agent_review_json(request: Request, project_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return multi_agent_review_package(repository, project_id)

    @app.get("/projects/{project_id}/multi-agent-review.md")
    def project_multi_agent_review_markdown(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = multi_agent_review_package(repository, project_id)
        return PlainTextResponse(multi_agent_review_markdown(package))

    @app.post("/projects/{project_id}/multi-agent-review")
    def generate_project_multi_agent_review(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            package = generate_multi_agent_review(repository, project_id)
        except ValueError as exc:
            repository.create_audit_event(
                project_id=project_id,
                event_type="multi_agent_review_blocked",
                status="blocked",
                actor_agent_id="qa-critic",
                source_table="company_projects",
                source_id=project_id,
                summary=f"Multi-agent review blocked: {exc}",
                payload={"blocker": str(exc)},
            )
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        repository.create_audit_event(
            project_id=project_id,
            event_type="multi_agent_review_completed",
            status=package["aggregate"]["status"],
            actor_agent_id="qa-critic",
            source_table="project_review_records",
            source_id=package["review_batch_id"],
            summary=(
                "Multi-agent review completed with "
                f"{package['aggregate']['reviewer_count']} reviewer records."
            ),
            payload={
                "review_batch_id": package["review_batch_id"],
                "reviewer_count": package["aggregate"]["reviewer_count"],
                "required_reviewer_count": package["aggregate"]["required_reviewer_count"],
                "status": package["aggregate"]["status"],
            },
        )
        return RedirectResponse(
            f"/projects/{project_id}#multi-agent-review",
            status_code=303,
        )

    @app.get("/projects/{project_id}/memory.json")
    def project_memory_json(request: Request, project_id: str) -> dict:
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_memory_package(repository, project_id)

    @app.get("/projects/{project_id}/memory.md")
    def project_memory_markdown_route(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = project_memory_package(repository, project_id)
        return PlainTextResponse(project_memory_markdown(package))

    @app.post("/projects/{project_id}/memory")
    def create_project_memory(
        request: Request,
        project_id: str,
        category: str = Form(...),
        memory_type: str = Form("context"),
        owner_agent_id: str = Form("chief-of-staff"),
        source: str = Form("founder-memory-form"),
        title: str = Form(...),
        summary: str = Form(...),
        body: str = Form(...),
        confidence: str = Form("medium"),
        pinned: str | None = Form(None),
        review_after: str = Form(""),
        expires_at: str = Form(""),
        source_artifact_id: str = Form(""),
        source_decision_id: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            repository.create_project_memory_entry(
                project_id=project_id,
                category=category,
                memory_type=memory_type,
                owner_agent_id=owner_agent_id,
                source=source,
                title=title,
                summary=summary,
                body=body,
                confidence=confidence,
                status="active",
                pinned=bool(pinned),
                review_after=review_after,
                expires_at=expires_at,
                source_artifact_id=source_artifact_id,
                source_decision_id=source_decision_id,
            )
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}#project-memory", status_code=303)

    @app.post("/projects/{project_id}/memory/{memory_id}")
    def update_project_memory(
        request: Request,
        project_id: str,
        memory_id: str,
        memory_action: str = Form("pin"),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        entry = repository.get_project_memory_entry(memory_id)
        if entry is None or (entry["project_id"] and entry["project_id"] != project_id):
            raise HTTPException(status_code=404, detail="Project memory entry not found")
        try:
            if memory_action == "retire":
                repository.update_project_memory_entry(memory_id, status="retired")
            elif memory_action == "pin":
                repository.update_project_memory_entry(memory_id, pinned=True)
            elif memory_action == "unpin":
                repository.update_project_memory_entry(memory_id, pinned=False)
            elif memory_action == "reactivate":
                repository.update_project_memory_entry(memory_id, status="active")
            else:
                raise ValueError(f"Unsupported memory action: {memory_action}")
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}#project-memory", status_code=303)

    @app.get("/projects/{project_id}/codex-execution.md")
    def project_codex_execution_markdown(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = codex_execution_package(repository, project_id)
        return PlainTextResponse(codex_execution_markdown(package))

    @app.post("/projects/{project_id}/codex-execution-approval")
    def request_project_codex_execution_approval(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = codex_execution_package(repository, project_id)
        if package["execution"]["approval_request_allowed"]:
            source_artifacts = ", ".join(
                f"{artifact['stage_id']}={artifact['id']}@v{artifact['version']}"
                for artifact in package["source_artifacts"]
            )
            command_preview = "; ".join(
                command["command"] for command in package["command_preview"]
            )
            acceptance_artifact = next(
                (
                    artifact
                    for artifact in package["source_artifacts"]
                    if artifact["stage_id"] == CODEX_EXECUTION_STAGE_ID
                ),
                {},
            )
            repository.create_founder_decision(
                title=f"Approve Codex execution for {project['name']}",
                urgency="urgent",
                decision_type=CODEX_EXECUTION_DECISION_TYPE,
                source=CODEX_EXECUTION_DECISION_SOURCE,
                owner_agent_id="chief-of-staff",
                project_id=project_id,
                stage_id=CODEX_EXECUTION_STAGE_ID,
                artifact_id=acceptance_artifact.get("id") or None,
                slack_channel="#founder-command",
                telegram_policy="Telegram only if Codex execution blocks launch.",
                context=(
                    f"Approve Codex implementation start for {project['name']}. "
                    "This dashboard action does not create branches, create "
                    "worktrees, spawn chats, or run commands."
                ),
                evidence=(
                    f"Source artifacts: {source_artifacts}. Branch preview: "
                    f"{package['branch_plan']['branch_name']}. Commands previewed: "
                    f"{command_preview}."
                ),
                requires_founder_approval=True,
            )
        return RedirectResponse(
            f"/projects/{project_id}#codex-execution",
            status_code=303,
        )

    @app.post("/projects/{project_id}/codex-execution-run")
    def queue_project_codex_execution_run(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            queue_codex_execution_run(repository, project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#codex-execution",
            status_code=303,
        )

    @app.post("/projects/{project_id}/codex-execution-real-run")
    def start_project_codex_execution_real_run(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        settings: Settings = request.app.state.settings
        try:
            start_codex_execution_git_worktree(
                repository,
                project_id,
                enabled=settings.codex_execution_enabled,
                workspace_root=settings.codex_workspace_root,
                worktree_root=settings.codex_worktree_root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#codex-execution",
            status_code=303,
        )

    @app.post("/projects/{project_id}/stages/{stage_id}/generate")
    def generate_project_stage(
        request: Request,
        project_id: str,
        stage_id: str,
        generation_mode: str = Form(LOCAL_DEMO_GENERATION_MODE),
        live_pilot_confirmation: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = resolve_stage_id(repository, project_id, stage_id)
        try:
            resolved_generation_mode = normalize_generation_mode(generation_mode)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        source_artifacts = approved_source_artifacts(repository, project_id)
        memory_context = product_wizard_memory_context(repository, project_id)
        generation_request = StageGenerationRequest(
            stage_id=resolved_stage_id,
            intake=product_wizard_intake_from_project(project),
            approved_sources=source_artifacts,
            memory_context=memory_context,
            memory_policy=FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
            mode=resolved_generation_mode,
        )
        live_hermes_readiness = (
            evaluate_live_hermes_readiness(
                repository,
                project_id,
                resolved_stage_id,
            )
            if resolved_generation_mode == LIVE_HERMES_GENERATION_MODE
            else None
        )
        live_hermes_run_confirmation = (
            evaluate_live_hermes_run_confirmation(
                repository,
                project_id,
                resolved_stage_id,
            )
            if resolved_generation_mode == LIVE_HERMES_GENERATION_MODE
            else None
        )
        generation_run_id = repository.create_generation_run(
            project_id=project_id,
            stage_id=resolved_stage_id,
            generation_mode=generation_request.mode,
            source_artifact_ids=[source["id"] for source in source_artifacts],
            memory_ids=[memory["id"] for memory in memory_context],
        )
        generation_service = product_wizard_generation_service(
            request,
            resolved_generation_mode,
            (
                live_hermes_gate_for(
                    live_hermes_readiness,
                    live_hermes_run_confirmation,
                )
                if live_hermes_readiness
                else None
            ),
        )
        try:
            if live_hermes_readiness and not live_hermes_readiness.ready:
                raise ValueError(live_hermes_readiness.blocker)
            if (
                request.app.state.settings.hermes_live_execution_enabled
                and live_hermes_run_confirmation
                and not live_hermes_run_confirmation.fresh
            ):
                raise ValueError(live_hermes_run_confirmation.blocker)
            validate_live_hermes_pilot_confirmation(
                settings=request.app.state.settings,
                mode=resolved_generation_mode,
                confirmation=live_pilot_confirmation,
            )
            artifact = generation_service.generate_stage(generation_request)
            artifact = artifact_with_live_hermes_pilot_evidence(
                artifact=artifact,
                settings=request.app.state.settings,
                mode=resolved_generation_mode,
                confirmation=live_pilot_confirmation,
                run_confirmation=live_hermes_run_confirmation,
                generation_run_id=generation_run_id,
            )
            repository.resolve_project_stage_decisions(
                project_id=project_id,
                stage_id=resolved_stage_id,
                status="deferred",
                decision="Superseded by a newly generated artifact draft.",
                decision_types={"artifact_approval", "final_artifact_approval"},
            )
            artifact_id = repository.save_stage_artifact_draft(
                project_id=project_id,
                stage_id=resolved_stage_id,
                markdown_content=artifact.markdown,
                json_content=artifact.metadata,
                owner_agent_id=artifact.owner_agent_id,
            )
            repository.complete_generation_run(
                generation_run_id,
                artifact_id,
                source_artifact_ids=list(artifact.source_artifact_ids),
                memory_ids=list(artifact.memory_ids),
            )
            create_project_stage_review_decision(
                repository=repository,
                project=project,
                stage_id=resolved_stage_id,
                artifact_id=artifact_id,
                artifact=artifact,
            )
            repository.sync_project_wizard_work_items(project_id)
        except ValueError as exc:
            repository.fail_generation_run(generation_run_id, str(exc))
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    @app.post("/projects/{project_id}/stages/{stage_id}/regenerate")
    def regenerate_project_stage(
        request: Request,
        project_id: str,
        stage_id: str,
        generation_mode: str = Form(LOCAL_DEMO_GENERATION_MODE),
        live_pilot_confirmation: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = resolve_stage_id(repository, project_id, stage_id)
        try:
            resolved_generation_mode = normalize_generation_mode(generation_mode)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        latest_artifact = repository.latest_project_stage_artifact(
            project_id,
            resolved_stage_id,
        )
        source_artifacts = approved_source_artifacts(repository, project_id)
        memory_context = product_wizard_memory_context(repository, project_id)
        generation_request = StageGenerationRequest(
            stage_id=resolved_stage_id,
            intake=product_wizard_intake_from_project(project),
            approved_sources=source_artifacts,
            memory_context=memory_context,
            memory_policy=FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
            mode=resolved_generation_mode,
        )
        live_hermes_readiness = (
            evaluate_live_hermes_readiness(
                repository,
                project_id,
                resolved_stage_id,
            )
            if resolved_generation_mode == LIVE_HERMES_GENERATION_MODE
            else None
        )
        live_hermes_run_confirmation = (
            evaluate_live_hermes_run_confirmation(
                repository,
                project_id,
                resolved_stage_id,
            )
            if resolved_generation_mode == LIVE_HERMES_GENERATION_MODE
            else None
        )
        generation_run_id = repository.create_generation_run(
            project_id=project_id,
            stage_id=resolved_stage_id,
            generation_mode=generation_request.mode,
            source_artifact_ids=[source["id"] for source in source_artifacts],
            memory_ids=[memory["id"] for memory in memory_context],
        )
        generation_service = product_wizard_generation_service(
            request,
            resolved_generation_mode,
            (
                live_hermes_gate_for(
                    live_hermes_readiness,
                    live_hermes_run_confirmation,
                )
                if live_hermes_readiness
                else None
            ),
        )
        try:
            if live_hermes_readiness and not live_hermes_readiness.ready:
                raise ValueError(live_hermes_readiness.blocker)
            if (
                request.app.state.settings.hermes_live_execution_enabled
                and live_hermes_run_confirmation
                and not live_hermes_run_confirmation.fresh
            ):
                raise ValueError(live_hermes_run_confirmation.blocker)
            validate_live_hermes_pilot_confirmation(
                settings=request.app.state.settings,
                mode=resolved_generation_mode,
                confirmation=live_pilot_confirmation,
            )
            artifact = generation_service.generate_stage(generation_request)
            artifact = artifact_with_live_hermes_pilot_evidence(
                artifact=artifact,
                settings=request.app.state.settings,
                mode=resolved_generation_mode,
                confirmation=live_pilot_confirmation,
                run_confirmation=live_hermes_run_confirmation,
                generation_run_id=generation_run_id,
            )
            if latest_artifact and latest_artifact["status"] == "approved":
                repository.request_stage_revision(
                    project_id=project_id,
                    stage_id=resolved_stage_id,
                    notes="Regeneration requested from the product wizard.",
                )
            repository.resolve_project_stage_decisions(
                project_id=project_id,
                stage_id=resolved_stage_id,
                status="deferred",
                decision="Superseded by a regenerated artifact draft.",
                decision_types={"artifact_approval", "final_artifact_approval"},
            )
            artifact_id = repository.save_stage_artifact_draft(
                project_id=project_id,
                stage_id=resolved_stage_id,
                markdown_content=artifact.markdown,
                json_content=artifact.metadata,
                owner_agent_id=artifact.owner_agent_id,
            )
            repository.complete_generation_run(
                generation_run_id,
                artifact_id,
                source_artifact_ids=list(artifact.source_artifact_ids),
                memory_ids=list(artifact.memory_ids),
            )
            create_project_stage_review_decision(
                repository=repository,
                project=project,
                stage_id=resolved_stage_id,
                artifact_id=artifact_id,
                artifact=artifact,
            )
            repository.sync_project_wizard_work_items(project_id)
        except ValueError as exc:
            repository.fail_generation_run(generation_run_id, str(exc))
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    @app.post("/projects/{project_id}/stages/{stage_id}/live-hermes-approval")
    def request_live_hermes_approval(
        request: Request,
        project_id: str,
        stage_id: str,
    ):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = resolve_stage_id(repository, project_id, stage_id)
        stage = repository.get_project_wizard_stage(project_id, resolved_stage_id)
        if stage is None:
            raise HTTPException(status_code=404, detail="Project stage not found")
        readiness = evaluate_live_hermes_readiness(
            repository,
            project_id,
            resolved_stage_id,
        )
        if readiness.approval_request_allowed:
            context = (
                f"Approve live Hermes generation for {stage['name']} in "
                f"{project['name']}. Live execution remains blocked until profile "
                "installation, profile smoke, profile acceptance, and prior artifact "
                "readiness checks pass."
            )
            evidence = (
                "Current live Hermes readiness: "
                + "; ".join(
                    f"{check['label']}={check['status']}"
                    for check in readiness.checks
                )
                + "."
            )
            repository.create_founder_decision(
                title=f"Approve live Hermes generation for {stage['name']}",
                urgency="urgent",
                decision_type=LIVE_HERMES_DECISION_TYPE,
                source=LIVE_HERMES_DECISION_SOURCE,
                owner_agent_id="chief-of-staff",
                project_id=project_id,
                stage_id=resolved_stage_id,
                slack_channel="#founder-command",
                telegram_policy="Telegram only if live Hermes execution blocks launch.",
                context=context,
                evidence=evidence,
                requires_founder_approval=True,
            )
        return RedirectResponse(
            f"/projects/{project_id}#live-hermes-readiness",
            status_code=303,
        )

    @app.post("/projects/{project_id}/stages/{stage_id}/live-hermes-run-confirmation")
    def request_live_hermes_run_confirmation(
        request: Request,
        project_id: str,
        stage_id: str,
    ):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = resolve_stage_id(repository, project_id, stage_id)
        stage = repository.get_project_wizard_stage(project_id, resolved_stage_id)
        if stage is None:
            raise HTTPException(status_code=404, detail="Project stage not found")
        readiness = evaluate_live_hermes_readiness(
            repository,
            project_id,
            resolved_stage_id,
        )
        run_confirmation = evaluate_live_hermes_run_confirmation(
            repository,
            project_id,
            resolved_stage_id,
        )
        settings: Settings = request.app.state.settings
        if (
            settings.hermes_live_execution_enabled
            and readiness.ready
            and run_confirmation.request_allowed
        ):
            preview = live_hermes_operator_preview(
                resolved_stage_id,
                product_wizard_intake_from_project(project),
                approved_source_artifacts(repository, project_id),
                memory_context=product_wizard_memory_context(repository, project_id),
                memory_policy=FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
                timeout_seconds=settings.hermes_timeout_seconds,
                live_execution_enabled=True,
            )
            context = (
                f"Confirm exactly one live Hermes command runner attempt for "
                f"{stage['name']} in {project['name']}. This confirmation is consumed "
                "by the next live_hermes generation run for this stage."
            )
            evidence = (
                "Command preview: "
                + preview["command_preview_text"]
                + f". Prompt SHA256: {preview['prompt_handoff']['sha256']}."
            )
            repository.create_founder_decision(
                title=f"Confirm one live Hermes run for {stage['name']}",
                urgency="urgent",
                decision_type=LIVE_HERMES_RUN_CONFIRMATION_TYPE,
                source=LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
                owner_agent_id="chief-of-staff",
                project_id=project_id,
                stage_id=resolved_stage_id,
                slack_channel="#founder-command",
                telegram_policy="Telegram only if live Hermes execution blocks launch.",
                context=context,
                evidence=evidence,
                requires_founder_approval=True,
            )
        return RedirectResponse(
            f"/projects/{project_id}#live-hermes-operator",
            status_code=303,
        )

    @app.post("/projects/{project_id}/stages/{stage_id}/approve")
    def approve_project_stage(request: Request, project_id: str, stage_id: str):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = resolve_stage_id(repository, project_id, stage_id)
        try:
            repository.approve_stage(project_id, resolved_stage_id)
            repository.resolve_project_stage_decisions(
                project_id=project_id,
                stage_id=resolved_stage_id,
                status="approved",
                decision=(
                    f"Founder approved the {resolved_stage_id} artifact from the "
                    "project review workspace."
                ),
                decision_types={"artifact_approval", "final_artifact_approval"},
            )
            if resolved_stage_id == "tasks":
                repository.ensure_project_workflow_items(project_id)
            repository.sync_project_wizard_work_items(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    @app.post("/projects/{project_id}/stages/{stage_id}/revision")
    def request_project_stage_revision(
        request: Request,
        project_id: str,
        stage_id: str,
        revision_reason: str = Form("acceptance_concern"),
        revision_request: str = Form(""),
    ):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = resolve_stage_id(repository, project_id, stage_id)
        if revision_reason not in REVISION_REASON_LABELS:
            raise HTTPException(status_code=400, detail="Invalid revision reason")
        reject_secret_values(
            {
                "revision_reason": revision_reason,
                "revision_request": revision_request,
            }
        )
        try:
            latest_artifact = repository.latest_project_stage_artifact(
                project_id,
                resolved_stage_id,
            )
            revision_reason_label = REVISION_REASON_LABELS[revision_reason]
            revision_note = (
                f"{revision_reason_label}: {revision_request.strip()}"
                if revision_request.strip()
                else (
                    f"{revision_reason_label}: Founder requested a revision before "
                    "approving this stage."
                )
            )
            repository.request_stage_revision(
                project_id=project_id,
                stage_id=resolved_stage_id,
                notes=revision_note,
                reason=revision_reason,
            )
            repository.resolve_project_stage_decisions(
                project_id=project_id,
                stage_id=resolved_stage_id,
                status="rejected",
                decision=revision_note,
                decision_types={"artifact_approval", "final_artifact_approval"},
            )
            revision_decision_id = repository.create_founder_decision(
                title=f"Revision requested for {resolved_stage_id} in {project['name']}",
                urgency="routine",
                decision_type="revision_request",
                source="product_wizard",
                owner_agent_id="product-manager",
                project_id=project_id,
                stage_id=resolved_stage_id,
                artifact_id=latest_artifact["id"] if latest_artifact else None,
                slack_channel="#decisions",
                telegram_policy="Slack first; Telegram only if this blocks launch.",
                context=(
                    "Founder requested a revision in the project review workspace."
                ),
                evidence=revision_note,
            )
            repository.update_founder_decision(
                revision_decision_id,
                status="approved",
                decision=revision_note,
                founder_confirmed=True,
            )
            repository.sync_project_wizard_work_items(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    @app.post("/projects/{project_id}/kanban")
    def push_project_workflow_to_kanban(request: Request, project_id: str):
        repository: CompanyRepository = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        kanban_blocker = project_wizard_kanban_blocker(repository, project_id)
        if kanban_blocker:
            repository.create_audit_event(
                project_id=project_id,
                event_type="kanban_push_blocked",
                status="blocked",
                actor_agent_id="chief-of-staff",
                source_table="company_projects",
                source_id=project_id,
                summary=f"Kanban push blocked: {kanban_blocker}",
                payload={"blocker": kanban_blocker},
            )
            raise HTTPException(status_code=409, detail=kanban_blocker)
        workflow_items = repository.list_project_workflow_items(project_id)
        pending_items = [
            item
            for item in workflow_items
            if not item["kanban_task_id"] and item["task_id"]
        ]
        repository.create_audit_event(
            project_id=project_id,
            event_type="kanban_push_started",
            status="running",
            actor_agent_id="chief-of-staff",
            source_table="company_projects",
            source_id=project_id,
            summary=f"Kanban push started for {len(pending_items)} project tasks.",
            payload={"pending_task_count": len(pending_items)},
        )
        for item in workflow_items:
            if item["kanban_task_id"] or not item["task_id"]:
                continue
            task = repository.get_task(item["task_id"])
            if task is None:
                continue
            run_id = repository.create_run(
                agent_id=task["owner_agent_id"],
                run_type="project-kanban-create",
                prompt=f"Push project workflow task to Hermes Kanban: {task['title']}",
            )
            result = request.app.state.kanban_client.create_task(task)
            repository.complete_run(run_id, output=result.output, error=result.error)
            if result.ok and result.task_id:
                repository.attach_kanban_task(task["id"], result.task_id)
                repository.create_audit_event(
                    project_id=project_id,
                    event_type="kanban_task_linked",
                    status="succeeded",
                    actor_agent_id=task["owner_agent_id"],
                    source_table="tasks",
                    source_id=task["id"],
                    summary=f"Kanban task linked: {task['title']}.",
                    payload={
                        "run_id": run_id,
                        "kanban_task_id": result.task_id,
                        "workflow_item_id": item["id"],
                        "owner_agent_id": task["owner_agent_id"],
                    },
                )
                repository.update_kanban_check(
                    check_id="kanban-task-create",
                    status="verified",
                    evidence=f"Dashboard task created Hermes Kanban task {result.task_id}.",
                )
                if repository.kanban_verification_ready():
                    repository.update_integration_status("hermes-kanban", "configured")
        return RedirectResponse(f"/projects/{project_id}", status_code=303)

    @app.get("/agents/{agent_id}")
    def agent_detail(request: Request, agent_id: str):
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        return templates.TemplateResponse(
            request,
            "agent.html",
            {
                "agent": agent,
                "live_run_blocker": profile_live_run_blocker(repository, agent_id),
                "agent_work_items": repository.list_agent_work_items(
                    owner_agent_id=agent_id,
                    limit=8,
                    include_done=False,
                ),
                "settings": request.app.state.settings,
            },
        )

    @app.post("/agents/{agent_id}/profile")
    def update_agent_profile(
        request: Request,
        agent_id: str,
        description: str = Form(...),
        soul: str = Form(...),
        capabilities: str = Form(...),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_agent(agent_id) is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        parsed_capabilities = [
            line.strip()
            for line in capabilities.replace(",", "\n").splitlines()
            if line.strip()
        ]
        if not description.strip() or not soul.strip() or not parsed_capabilities:
            raise HTTPException(
                status_code=400,
                detail="Description, soul, and at least one capability are required",
            )
        reject_secret_values(
            {
                "description": description,
                "soul": soul,
                "capabilities": "\n".join(parsed_capabilities),
            }
        )
        repository.update_agent_profile(
            agent_id=agent_id,
            description=description,
            soul=soul,
            capabilities=parsed_capabilities,
        )
        return RedirectResponse(f"/agents/{agent_id}", status_code=303)

    @app.post("/agents/{agent_id}/routing")
    def update_agent_routing(
        request: Request,
        agent_id: str,
        slack_channel: str = Form(...),
        telegram_policy: str = Form(...),
        hermes_command: str = Form(...),
    ):
        repository: CompanyRepository = request.app.state.repository
        if repository.get_agent(agent_id) is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        if not slack_channel.strip() or not telegram_policy.strip() or not hermes_command.strip():
            raise HTTPException(
                status_code=400,
                detail="Slack channel, Telegram policy, and Hermes command are required",
            )
        reject_secret_values(
            {
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
                "hermes_command": hermes_command,
            }
        )
        repository.update_agent_routing(
            agent_id=agent_id,
            slack_channel=slack_channel,
            telegram_policy=telegram_policy,
            hermes_command=hermes_command,
        )
        return RedirectResponse(f"/agents/{agent_id}", status_code=303)

    @app.post("/tasks")
    def create_task(
        request: Request,
        title: str = Form(...),
        owner_agent_id: str = Form(...),
        priority: str = Form("medium"),
        summary: str = Form(""),
    ):
        reject_secret_values({"title": title, "priority": priority, "summary": summary})
        repository: CompanyRepository = request.app.state.repository
        repository.assert_agent_exists(owner_agent_id)
        repository.create_task(
            title=title.strip(),
            owner_agent_id=owner_agent_id,
            priority=priority,
            summary=summary.strip(),
        )
        return RedirectResponse("/", status_code=303)

    @app.post("/tasks/{task_id}/kanban")
    def push_task_to_kanban(request: Request, task_id: str):
        repository: CompanyRepository = request.app.state.repository
        task = repository.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        agent = repository.get_agent(task["owner_agent_id"])
        if agent is None:
            raise HTTPException(status_code=500, detail="Task owner profile is missing")
        kanban_blocker = kanban_task_push_blocker(repository)
        if kanban_blocker:
            raise HTTPException(status_code=409, detail=kanban_blocker)
        run_id = repository.create_run(
            agent_id=agent["id"],
            run_type="kanban-create",
            prompt=f"Create Hermes Kanban task for {task['id']}: {task['title']}",
        )
        result = request.app.state.kanban_client.create_task(task)
        repository.complete_run(run_id, output=result.output, error=result.error)
        if result.ok and result.task_id:
            repository.attach_kanban_task(task_id, result.task_id)
            repository.update_kanban_check(
                check_id="kanban-task-create",
                status="verified",
                evidence=f"Dashboard task created Hermes Kanban task {result.task_id}.",
            )
            if repository.kanban_verification_ready():
                repository.update_integration_status("hermes-kanban", "configured")
        return RedirectResponse("/", status_code=303)

    @app.post("/documents")
    def create_document(
        request: Request,
        title: str = Form(...),
        doc_type: str = Form("brief"),
        owner_agent_id: str = Form(...),
        body: str = Form(""),
    ):
        reject_secret_values({"title": title, "doc_type": doc_type, "body": body})
        repository: CompanyRepository = request.app.state.repository
        repository.assert_agent_exists(owner_agent_id)
        repository.create_document(
            title=title.strip(),
            doc_type=doc_type,
            owner_agent_id=owner_agent_id,
            body=body.strip(),
        )
        return RedirectResponse("/", status_code=303)

    @app.post("/agents/{agent_id}/run")
    def run_agent(request: Request, agent_id: str, founder_request: str = Form(...)):
        reject_secret_values({"founder_request": founder_request})
        repository: CompanyRepository = request.app.state.repository
        agent = repository.get_agent(agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        live_run_blocker = profile_live_run_blocker(repository, agent_id)
        if live_run_blocker:
            raise HTTPException(status_code=409, detail=live_run_blocker)
        prompt = build_agent_prompt(agent, founder_request.strip())
        run_id = repository.create_run(agent_id=agent_id, run_type="agent", prompt=prompt)
        result = request.app.state.hermes_client.run_prompt(agent, prompt)
        repository.complete_run(run_id, output=result.output, error=result.error)
        return RedirectResponse("/", status_code=303)

    @app.post("/standups/{schedule_id}/run")
    def run_standup(request: Request, schedule_id: str):
        repository: CompanyRepository = request.app.state.repository
        schedule = repository.get_schedule(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        agent = repository.get_agent("chief-of-staff")
        if agent is None:
            raise HTTPException(status_code=500, detail="Chief of Staff profile is missing")
        live_run_blocker = profile_live_run_blocker(repository, agent["id"])
        if live_run_blocker:
            raise HTTPException(status_code=409, detail=live_run_blocker)
        settings: Settings = request.app.state.settings
        prompt = build_standup_prompt(
            schedule=schedule,
            agents=repository.list_agents(),
            tasks=repository.list_tasks(),
            documents=repository.list_documents(),
            slack_founder_command=settings.slack_founder_command,
            slack_alerts=settings.slack_alerts,
            telegram_urgent_label=settings.telegram_urgent_label,
        )
        run_id = repository.create_run(agent_id=agent["id"], run_type="standup", prompt=prompt)
        result = request.app.state.hermes_client.run_prompt(agent, prompt)
        repository.complete_run(run_id, output=result.output, error=result.error)
        return RedirectResponse("/", status_code=303)

    return app


app = create_app()
