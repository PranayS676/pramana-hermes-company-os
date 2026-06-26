from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime

from hermes_company_os.activation_report import activation_summary
from hermes_company_os.activation_sequence import next_best_action
from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES

ARTIFACT_ROUTES = {
    "bootstrap_script": "/setup/bootstrap.ps1",
    "company_launch_drill": "/setup/company-launch-drill.md",
    "company_launch_drill_json": "/setup/company-launch-drill.json",
    "company_manifest_markdown": "/setup/company-manifest.md",
    "company_manifest_json": "/setup/company-manifest.json",
    "founder_handoff": "/setup/founder-handoff.md",
    "founder_handoff_json": "/setup/founder-handoff.json",
    "founder_decisions": "/setup/founder-decisions.md",
    "founder_decisions_json": "/setup/founder-decisions.json",
    "founder_input_request": "/setup/founder-input-request.md",
    "founder_input_schema": "/setup/founder-input-request.json",
    "founder_input_collector": "/setup/founder-inputs.ps1",
    "first_run": "/setup/first-run.md",
    "first_run_json": "/setup/first-run.json",
    "first_run_runner": "/setup/first-run.ps1",
    "progress_board": "/setup/progress-board.md",
    "progress_board_json": "/setup/progress-board.json",
    "input_ledger": "/setup/input-ledger.md",
    "input_ledger_json": "/setup/input-ledger.json",
    "credential_loading": "/setup/credential-loading.md",
    "credential_loading_json": "/setup/credential-loading.json",
    "credential_status_template": "/setup/credential-status-template.md",
    "credential_status_json": "/setup/credential-status-template.json",
    "founder_next_actions": "/setup/founder-next-actions.md",
    "founder_next_actions_json": "/setup/founder-next-actions.json",
    "inputs_needed": "/setup/inputs-needed.md",
    "kickoff_readiness": "/setup/kickoff-readiness.md",
    "kickoff_readiness_json": "/setup/kickoff-readiness.json",
    "slack_plan": "/setup/slack-plan.md",
    "slack_manifests": "/setup/slack-manifests.json",
    "slack_provisioning": "/setup/slack-provisioning.md",
    "slack_provisioning_json": "/setup/slack-provisioning.json",
    "slack_provisioning_runner": "/setup/slack-provisioning.ps1",
    "slack_channel_template": "/setup/slack-channel-template.md",
    "slack_channel_template_json": "/setup/slack-channel-template.json",
    "slack_bot_user_map": "/setup/slack-bot-user-map.json",
    "slack_bot_user_template": "/setup/slack-bot-user-map-template.md",
    "slack_bot_user_template_json": "/setup/slack-bot-user-map-template.json",
    "slack_workspace": "/setup/slack-workspace.md",
    "slack_invite_json": "/setup/slack-invite-matrix.json",
    "slack_invite_csv": "/setup/slack-invite-matrix.csv",
    "telegram_plan": "/setup/telegram-plan.md",
    "telegram_botfather": "/setup/telegram-botfather.md",
    "telegram_recipient_template": "/setup/telegram-recipient-template.md",
    "telegram_recipient_template_json": "/setup/telegram-recipient-template.json",
    "telegram_provisioning": "/setup/telegram-provisioning.md",
    "telegram_provisioning_json": "/setup/telegram-provisioning.json",
    "telegram_provisioning_runner": "/setup/telegram-provisioning.ps1",
    "telegram_policy": "/setup/telegram-policy.md",
    "telegram_policy_json": "/setup/telegram-policy.json",
    "messaging_drill": "/setup/messaging-drill.md",
    "messaging_drill_json": "/setup/messaging-drill.json",
    "gateway_operations": "/setup/gateway-operations.md",
    "gateway_operations_json": "/setup/gateway-operations.json",
    "gateway_operations_runner": "/setup/gateway-operations.ps1",
    "llm_plan": "/setup/llm-plan.md",
    "llm_credentials": "/setup/llm-credentials.md",
    "llm_provisioning": "/setup/llm-provisioning.md",
    "llm_provisioning_json": "/setup/llm-provisioning.json",
    "llm_provisioning_runner": "/setup/llm-provisioning.ps1",
    "llm_provider_presets": "/setup/llm-provider-presets.md",
    "llm_provider_presets_json": "/setup/llm-provider-presets.json",
    "llm_preference_template": "/setup/llm-preference-template.md",
    "llm_preference_template_json": "/setup/llm-preference-template.json",
    "llm_finalization_plan": "/setup/llm-finalize.md",
    "llm_finalization_runner": "/setup/llm-finalize.ps1",
    "llm_smoke": "/setup/llm-smoke.md",
    "llm_smoke_json": "/setup/llm-smoke.json",
    "secret_audit_plan": "/setup/secret-audit.md",
    "secret_audit_runner": "/setup/secret-audit.ps1",
    "hermes_runtime": "/setup/hermes-runtime.md",
    "hermes_runtime_json": "/setup/hermes-runtime.json",
    "hermes_install_runner": "/setup/hermes-install.ps1",
    "runtime_preflight": "/setup/runtime-preflight.md",
    "runtime_preflight_json": "/setup/runtime-preflight.json",
    "schedule_provisioning": "/setup/schedule-provisioning.md",
    "schedule_provisioning_json": "/setup/schedule-provisioning.json",
    "schedule_provisioning_runner": "/setup/schedule-provisioning.ps1",
    "schedule_config_template": "/setup/schedule-config-template.md",
    "schedule_config_template_json": "/setup/schedule-config-template.json",
    "schedule_verification_template": "/setup/schedule-verification-template.md",
    "schedule_verification_template_json": "/setup/schedule-verification-template.json",
    "standup_preview": "/setup/standup-preview.md",
    "standup_preview_json": "/setup/standup-preview.json",
    "standup_runbook": "/setup/standup-runbook.md",
    "standup_cron": "/setup/standup-cron.ps1",
    "idea_intake": "/setup/idea-intake.md",
    "idea_intake_json": "/setup/idea-intake.json",
    "project_workflow": "/setup/project-workflow.md",
    "project_workflow_json": "/setup/project-workflow.json",
    "kanban_provisioning": "/setup/kanban-provisioning.md",
    "kanban_provisioning_json": "/setup/kanban-provisioning.json",
    "kanban_provisioning_runner": "/setup/kanban-provisioning.ps1",
    "kanban_verification_template": "/setup/kanban-verification-template.md",
    "kanban_verification_template_json": "/setup/kanban-verification-template.json",
    "kanban_runbook": "/setup/kanban-runbook.md",
    "kanban_diagnostics": "/setup/kanban-diagnostics.ps1",
    "activation_sequence": "/setup/activation-sequence.md",
    "activation_runner_plan": "/setup/activation-runner.md",
    "activation_runner": "/setup/activation-runner.ps1",
    "live_verification": "/setup/live-verification.md",
    "verification_evidence": "/setup/verification-evidence.md",
    "verification_evidence_json": "/setup/verification-evidence.json",
    "activation_checklist": "/setup/activation-checklist.md",
    "profile_personalization_template": "/setup/profile-personalization-template.md",
    "profile_personalization_template_json": "/setup/profile-personalization-template.json",
    "profile_artifacts": "/setup/profile-artifacts.md",
    "profile_installation": "/setup/profile-installation.md",
    "profile_installation_json": "/setup/profile-installation.json",
    "profile_installation_runner": "/setup/profile-installation.ps1",
    "team_topology": "/setup/team-topology.md",
    "team_topology_json": "/setup/team-topology.json",
    "delegation_playbook": "/setup/delegation-playbook.md",
    "delegation_playbook_json": "/setup/delegation-playbook.json",
    "profile_acceptance": "/setup/profile-acceptance.md",
    "profile_acceptance_json": "/setup/profile-acceptance.json",
    "profile_acceptance_template": "/setup/profile-acceptance-template.md",
    "profile_acceptance_template_json": "/setup/profile-acceptance-template.json",
    "readiness_report": "/setup/readiness-report.md",
}


def company_manifest_payload(
    *,
    agents: list[dict],
    setup_inputs: list[dict],
    schedules: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    workflow_templates: list[dict],
    activation_checks: list[dict],
    profile_acceptance_checks: list[dict] | None = None,
    profile_installation_checks: list[dict] | None = None,
    founder_decisions: list[dict] | None = None,
) -> dict:
    summary = activation_summary(activation_checks)
    decisions = founder_decisions or []
    return {
        "title": "Hermes Company OS Setup Manifest",
        "generated_at": datetime.now(UTC).isoformat(),
        "credential_boundary": (
            "This manifest is no-secret. It may name required environment keys, "
            "but it does not include Slack tokens, Telegram bot tokens, provider API keys, "
            "or verification evidence text."
        ),
        "activation": {
            "summary": summary,
            "next_best_action": next_best_action(
                activation_checks,
                secret_requirements,
                messaging_checks,
                schedule_checks,
                kanban_checks,
                model_preferences,
                integrations,
            ),
            "checks": [
                {
                    "id": item["id"],
                    "label": item["label"],
                    "status": item["status"],
                    "detail": item["detail"],
                }
                for item in activation_checks
            ],
        },
        "setup_inputs": {
            "safe_dashboard_inputs": [_setup_input(item) for item in setup_inputs],
            "required_missing": [
                item["key"]
                for item in setup_inputs
                if item["required"]
                and item["secret_policy"] == "non_secret"
                and not item["value"].strip()
            ],
        },
        "profiles": [_profile(agent) for agent in agents],
        "schedules": [_schedule(schedule) for schedule in schedules],
        "messaging": {
            "slack_is_main_workspace": True,
            "telegram_is_urgent_only": True,
            "verification": _verification_summary(messaging_checks),
        },
        "kanban": {
            "status": _status_counts(kanban_checks),
            "checks": [_check_stub(item) for item in kanban_checks],
        },
        "llm": {
            "verification_last": True,
            "profiles": [_model_preference(item) for item in model_preferences],
            "status": _status_counts(model_preferences),
        },
        "profile_installation": {
            "status": _status_counts(profile_installation_checks or []),
            "checks": [
                _profile_installation_check(item)
                for item in profile_installation_checks or []
            ],
        },
        "profile_acceptance": {
            "status": _status_counts(profile_acceptance_checks or []),
            "checks": [
                _profile_acceptance_check(item)
                for item in profile_acceptance_checks or []
            ],
        },
        "founder_decisions": {
            "status": _status_counts(decisions),
            "open": [
                _founder_decision_stub(item)
                for item in decisions
                if item["status"] not in RESOLVED_DECISION_STATUSES
            ],
            "urgent_open": len(
                [
                    item
                    for item in decisions
                    if item["status"] not in RESOLVED_DECISION_STATUSES
                    and item["urgency"] == "urgent"
                ]
            ),
        },
        "external_secrets": {
            "status": _status_counts(secret_requirements),
            "requirements": [_secret_requirement(item) for item in secret_requirements],
        },
        "integrations": [_integration(item) for item in integrations],
        "workflow": {
            "templates": [_workflow_template(item) for item in workflow_templates],
            "kanban_handoff": "Project workflow tasks can be pushed to Hermes Kanban.",
        },
        "artifacts": ARTIFACT_ROUTES,
    }


def company_manifest_json(**kwargs) -> str:
    return json.dumps(company_manifest_payload(**kwargs), indent=2, sort_keys=True)


def company_manifest_markdown(**kwargs) -> str:
    manifest = company_manifest_payload(**kwargs)
    activation = manifest["activation"]
    summary = activation["summary"]
    lines = [
        "# Hermes Company OS Setup Manifest",
        "",
        "This is the single no-secret handoff for the company bootstrap state. "
        "Use the JSON export when another tool or Hermes profile needs structured context.",
        "",
        "## Credential Boundary",
        "",
        manifest["credential_boundary"],
        "",
        "## Activation Summary",
        "",
        f"- Ready for live activation: {'yes' if summary['ready'] else 'no'}",
        f"- Blocking checks: {summary['blocking']}",
        f"- Needs setup checks: {summary['needs_setup']}",
        f"- Deferred checks: {summary['deferred']}",
        f"- Ready checks: {summary['ready_checks']} of {summary['total']}",
        f"- Next best action: {activation['next_best_action']}",
        "",
        "## Profiles",
        "",
    ]
    for profile in manifest["profiles"]:
        lines.append(
            f"- {profile['name']} (`{profile['id']}`): {profile['role']} via "
            f"`{profile['hermes_command']}`"
        )
    lines.extend(
        [
            "",
            "## Open Work",
            "",
            (
                "- Missing required dashboard inputs: "
                f"{len(manifest['setup_inputs']['required_missing'])}"
            ),
            (
                "- External secret statuses: "
                f"{_format_counts(manifest['external_secrets']['status'])}"
            ),
            (
                "- Messaging verification: "
                f"{_format_counts(manifest['messaging']['verification']['status'])}"
            ),
            f"- Kanban verification: {_format_counts(manifest['kanban']['status'])}",
            f"- LLM profile status: {_format_counts(manifest['llm']['status'])}",
            (
                "- Profile installation: "
                f"{_format_counts(manifest['profile_installation']['status'])}"
            ),
            (
                "- Profile acceptance: "
                f"{_format_counts(manifest['profile_acceptance']['status'])}"
            ),
            (
                "- Founder decisions: "
                f"{_format_counts(manifest['founder_decisions']['status'])}; "
                f"{manifest['founder_decisions']['urgent_open']} urgent open"
            ),
            "",
            "## Artifact Entry Points",
            "",
        ]
    )
    for label, route in manifest["artifacts"].items():
        lines.append(f"- {label}: `{route}`")
    lines.append("")
    return "\n".join(lines)


def _profile(agent: dict) -> dict:
    agent_id = agent["id"]
    return {
        "id": agent_id,
        "name": agent["name"],
        "role": agent["role"],
        "hermes_command": agent["hermes_command"],
        "slack_channel": agent["slack_channel"],
        "telegram_policy": agent["telegram_policy"],
        "description": agent["description"],
        "capabilities": agent["capabilities"],
        "artifacts": {
            "soul": f"/setup/profile-soul/{agent_id}.md",
            "manifest": f"/setup/profile-manifest/{agent_id}.json",
            "apply_script": f"/setup/profile-apply/{agent_id}.ps1",
            "profile_env": f"/setup/profile-env/{agent_id}.env",
            "llm_env": f"/setup/profile-llm-env/{agent_id}.env",
            "config": f"/setup/profile-config/{agent_id}.yaml",
            "slack_manifest": f"/setup/slack-manifest/{agent_id}.json",
        },
    }


def _setup_input(item: dict) -> dict:
    payload = {
        "key": item["key"],
        "group": item["group_name"],
        "label": item["label"],
        "required": bool(item["required"]),
        "secret_policy": item["secret_policy"],
        "status": "captured" if item["value"].strip() else "missing",
        "help_text": item["help_text"],
    }
    if item["secret_policy"] == "non_secret":
        payload["value"] = item["value"]
    else:
        payload["value"] = ""
        payload["status"] = "deferred" if not item["value"].strip() else "captured"
    return payload


def _schedule(schedule: dict) -> dict:
    return {
        "id": schedule["id"],
        "name": schedule["name"],
        "time": f"{schedule['hour']:02d}:{schedule['minute']:02d}",
        "timezone": schedule["timezone"],
        "slack_channel": schedule["slack_channel"],
        "telegram_policy": schedule["telegram_policy"],
        "active": bool(schedule["active"]),
    }


def _model_preference(preference: dict) -> dict:
    return {
        "agent_id": preference["agent_id"],
        "agent_name": preference["agent_name"],
        "hermes_command": preference["hermes_command"],
        "provider": preference["provider"],
        "model": preference["model"],
        "fallback_provider": preference["fallback_provider"],
        "fallback_model": preference["fallback_model"],
        "auth_method": preference["auth_method"],
        "status": preference["status"],
        "artifacts": {
            "llm_env": f"/setup/profile-llm-env/{preference['agent_id']}.env",
            "config": f"/setup/profile-config/{preference['agent_id']}.yaml",
        },
    }


def _secret_requirement(item: dict) -> dict:
    return {
        "id": item["id"],
        "owner_agent_id": item["owner_agent_id"],
        "owner_name": item["owner_name"],
        "category": item["category"],
        "label": item["label"],
        "environment_key": item["environment_key"],
        "destination": item["destination"],
        "status": item["status"],
    }


def _profile_acceptance_check(item: dict) -> dict:
    return {
        "id": item["id"],
        "agent_id": item["agent_id"],
        "agent_name": item["agent_name"],
        "title": item["title"],
        "status": item["status"],
        "has_evidence": bool(item.get("evidence", "").strip()),
    }


def _profile_installation_check(item: dict) -> dict:
    return {
        "id": item["id"],
        "agent_id": item["agent_id"],
        "agent_name": item["agent_name"],
        "label": item["label"],
        "status": item["status"],
        "has_evidence": bool(item.get("evidence", "").strip()),
    }


def _founder_decision_stub(item: dict) -> dict:
    return {
        "id": item["id"],
        "title": item["title"],
        "status": item["status"],
        "urgency": item["urgency"],
        "source": item["source"],
        "owner_agent_id": item["owner_agent_id"],
        "owner_name": item.get("owner_name") or "",
        "slack_channel": item["slack_channel"],
        "telegram_policy": item["telegram_policy"],
        "has_decision": bool(item["decision"].strip()),
    }


def _integration(item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "owner_agent_id": item["owner_agent_id"],
        "owner_name": item["owner_name"],
        "status": item["status"],
        "validation_command": item["validation_command"],
        "docs_url": item["docs_url"],
    }


def _workflow_template(item: dict) -> dict:
    return {
        "id": item["id"],
        "name": item["name"],
        "phase": item["phase"],
        "owner_agent_id": item["owner_agent_id"],
        "owner_name": item["owner_name"],
        "doc_type": item["doc_type"],
        "priority": item["priority"],
        "sort_order": item["sort_order"],
    }


def _verification_summary(checks: list[dict]) -> dict:
    return {
        "status": _status_counts(checks),
        "checks": [_check_stub(item) for item in checks],
    }


def _check_stub(item: dict) -> dict:
    payload = {
        "id": item["id"],
        "label": item["label"],
        "status": item["status"],
        "instructions": item["instructions"],
        "has_evidence": bool(item.get("evidence", "").strip()),
    }
    if "platform" in item:
        payload["platform"] = item["platform"]
        payload["owner_agent_id"] = item["owner_agent_id"]
    if "check_type" in item:
        payload["check_type"] = item["check_type"]
    if "schedule_id" in item:
        payload["schedule_id"] = item["schedule_id"]
    return payload


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
