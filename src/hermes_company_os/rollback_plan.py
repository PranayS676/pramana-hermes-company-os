"""Founder-facing rollback-plan artifact (Milestone 9, Launch & Release).

Builds a demo-safe, credential-free rollback plan for a project, tied to its
launch tier and (when present) its acceptance/launch artifacts. The plan is
generated on demand from existing repository data; nothing is persisted and no
schema is touched. As with ``multi_agent_review``, the package is a plain dict
plus a ``rollback_plan_markdown(...)`` export, and the package is run through
``assert_no_secret_values(...)`` before it is returned.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from hermes_company_os.secret_guard import assert_no_secret_values

ROLLBACK_PLAN_SCHEMA = "rollback_plan_package_v1"

CREDENTIAL_BOUNDARY = (
    "This rollback plan references launch tier, ordered steps, owners, and "
    "verification checks only. It does not include Slack tokens, Telegram bot "
    "tokens, provider keys, OAuth values, request headers, raw logs, or any "
    "secret values."
)

# Stages whose presence/approval informs how confident the rollback plan can be.
_LAUNCH_SOURCE_STAGES: tuple[str, ...] = ("code_plan", "acceptance")

# Launch tier policy: how much rollback rigor each tier demands. Tier slugs match
# the product-wizard intake (`t0_internal`, `t1_private`, `t2_beta`, `t3_ga`).
_DEFAULT_TIER = "t0_internal"

_LAUNCH_TIERS: dict[str, dict[str, Any]] = {
    "t0_internal": {
        "id": "t0_internal",
        "name": "T0 Internal Experiment",
        "blast_radius": "internal-only",
        "rollback_objective": (
            "Stop the experiment and restore the prior internal state without "
            "external exposure."
        ),
        "founder_sign_off_required": False,
    },
    "t1_private": {
        "id": "t1_private",
        "name": "T1 Private Beta",
        "blast_radius": "invited beta cohort",
        "rollback_objective": (
            "Disable the feature for invited users and notify the beta cohort "
            "of the reversal."
        ),
        "founder_sign_off_required": True,
    },
    "t2_beta": {
        "id": "t2_beta",
        "name": "T2 Public Beta",
        "blast_radius": "self-serve public beta users",
        "rollback_objective": (
            "Return public-beta users to the last known-good build and "
            "communicate the rollback publicly."
        ),
        "founder_sign_off_required": True,
    },
    "t3_ga": {
        "id": "t3_ga",
        "name": "T3 General Availability",
        "blast_radius": "all production users",
        "rollback_objective": (
            "Restore the last known-good GA release, reconcile data, and issue "
            "a founder-approved customer communication."
        ),
        "founder_sign_off_required": True,
    },
}


def rollback_plan_package(repository, project_id: str) -> dict[str, Any]:
    """Build the no-secret rollback-plan package for ``project_id``.

    Raises ``ValueError`` for an unknown project (the route maps this to 404).
    Degrades gracefully when launch/acceptance artifacts are missing.
    """

    project = repository.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")

    tier = _resolve_tier(project)
    source_artifacts = _source_artifacts(repository, project_id)
    artifacts_available = bool(source_artifacts)
    acceptance_approved = any(
        item["stage_id"] == "acceptance" and item["status"] == "approved"
        for item in source_artifacts
    )

    payload = {
        "schema": ROLLBACK_PLAN_SCHEMA,
        "title": f"Rollback Plan: {project['name']}",
        "purpose": (
            "Give the founder a pre-agreed, ordered way to reverse this launch "
            "if a trigger condition fires."
        ),
        "credential_boundary": CREDENTIAL_BOUNDARY,
        "project": {
            "id": project_id,
            "name": project["name"],
            "status": project["status"],
        },
        "launch_tier": tier,
        "artifacts_available": artifacts_available,
        "acceptance_approved": acceptance_approved,
        "source_artifacts": source_artifacts,
        "readiness_note": _readiness_note(artifacts_available, acceptance_approved),
        "trigger_conditions": _trigger_conditions(tier),
        "rollback_steps": _rollback_steps(tier),
        "verification_checks": _verification_checks(tier),
        "data_reversal_notes": _data_reversal_notes(tier),
        "founder_sign_off": _founder_sign_off(tier),
    }
    assert_no_secret_values(
        {"rollback_plan_package": json.dumps(payload, sort_keys=True)}
    )
    return payload


def rollback_plan_markdown(package: Mapping[str, Any]) -> str:
    tier = package["launch_tier"]
    lines = [
        f"# Rollback Plan: {package['project']['name']}",
        "",
        package["purpose"],
        "",
        "## Credential Boundary",
        "",
        package["credential_boundary"],
        "",
        "## Launch Context",
        "",
        f"- Project: `{package['project']['id']}` ({package['project']['status']})",
        f"- Launch tier: `{tier['id']}` - {tier['name']}",
        f"- Blast radius: {tier['blast_radius']}",
        f"- Rollback objective: {tier['rollback_objective']}",
        f"- Launch artifacts available: {'yes' if package['artifacts_available'] else 'no'}",
        f"- Acceptance approved: {'yes' if package['acceptance_approved'] else 'no'}",
        f"- Readiness note: {package['readiness_note']}",
        "",
        "## Source Artifacts",
        "",
    ]
    if package["source_artifacts"]:
        for artifact in package["source_artifacts"]:
            lines.append(
                f"- `{artifact['stage_id']}`: {artifact['id']} "
                f"v{artifact['version']} ({artifact['status']})"
            )
    else:
        lines.append("- No launch/acceptance artifacts yet; plan is generic for the tier.")
    lines.extend(["", "## Trigger Conditions", ""])
    for condition in package["trigger_conditions"]:
        lines.append(f"- `{condition['id']}`: {condition['label']}")
    lines.extend(["", "## Rollback Steps", ""])
    for step in package["rollback_steps"]:
        lines.append(
            f"{step['order']}. {step['action']} "
            f"(owner: {step['owner']})"
        )
    lines.extend(["", "## Verification Checks", ""])
    for check in package["verification_checks"]:
        lines.append(f"- `{check['id']}`: {check['label']}")
    lines.extend(["", "## Data And Migration Reversal", ""])
    for note in package["data_reversal_notes"]:
        lines.append(f"- {note}")
    sign_off = package["founder_sign_off"]
    lines.extend(
        [
            "",
            "## Founder Sign-Off",
            "",
            f"- Required: {'yes' if sign_off['required'] else 'no'}",
            f"- Status: `{sign_off['status']}`",
            f"- Prompt: {sign_off['prompt']}",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_tier(project: Mapping[str, Any]) -> dict[str, Any]:
    intake = project.get("intake") or {}
    raw = str(intake.get("launch_tier", "")).strip().lower()
    tier = _LAUNCH_TIERS.get(raw, _LAUNCH_TIERS[_DEFAULT_TIER])
    return dict(tier)


def _source_artifacts(repository, project_id: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for stage_id in _LAUNCH_SOURCE_STAGES:
        latest = repository.latest_project_stage_artifact(project_id, stage_id)
        summary = _artifact_summary(latest)
        if summary:
            artifacts.append(summary)
    return artifacts


def _artifact_summary(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    metadata = artifact.get("json") or {}
    return {
        "id": artifact["id"],
        "stage_id": artifact["stage_id"],
        "status": artifact["status"],
        "version": artifact["version"],
        "title": metadata.get("title", artifact["stage_id"]),
    }


def _readiness_note(artifacts_available: bool, acceptance_approved: bool) -> str:
    if acceptance_approved:
        return (
            "Acceptance is approved; rollback steps are tied to a reviewed launch "
            "candidate."
        )
    if artifacts_available:
        return (
            "Launch artifacts exist but acceptance is not yet approved; treat this "
            "plan as a draft until acceptance is approved."
        )
    return (
        "No launch/acceptance artifacts yet; this is a generic tier-level plan to "
        "fill in as the project reaches launch readiness."
    )


def _trigger_conditions(tier: Mapping[str, Any]) -> list[dict[str, str]]:
    conditions = [
        {
            "id": "acceptance_regression",
            "label": (
                "A previously approved acceptance check fails after launch."
            ),
        },
        {
            "id": "critical_defect",
            "label": (
                "A founder- or QA-classified critical defect reaches the launch "
                "audience."
            ),
        },
        {
            "id": "data_integrity_risk",
            "label": (
                "A data or migration issue risks losing or corrupting founder or "
                "user data."
            ),
        },
        {
            "id": "founder_stop_call",
            "label": "The founder calls a stop for any reason.",
        },
    ]
    if tier["id"] in {"t2_beta", "t3_ga"}:
        conditions.append(
            {
                "id": "external_trust_risk",
                "label": (
                    "A public-trust, security, or compliance signal warrants "
                    "pulling the launch."
                ),
            }
        )
    return conditions


def _rollback_steps(tier: Mapping[str, Any]) -> list[dict[str, Any]]:
    steps = [
        {
            "order": 1,
            "action": (
                "Founder confirms the rollback decision and records the trigger "
                "that fired."
            ),
            "owner": "founder",
        },
        {
            "order": 2,
            "action": (
                "Disable or gate the new behavior so no further users hit the "
                "broken path."
            ),
            "owner": "engineering-manager",
        },
        {
            "order": 3,
            "action": "Restore the last known-good build or configuration.",
            "owner": "cloud-infra-agent",
        },
        {
            "order": 4,
            "action": (
                "Reverse or quarantine any data/migration changes per the data "
                "reversal notes."
            ),
            "owner": "backend-engineer",
        },
        {
            "order": 5,
            "action": (
                "Run the verification checks to confirm the prior state is "
                "restored."
            ),
            "owner": "test-automation-agent",
        },
    ]
    if tier["id"] in {"t1_private", "t2_beta", "t3_ga"}:
        steps.append(
            {
                "order": len(steps) + 1,
                "action": (
                    "Prepare a founder-approved communication for the launch "
                    "audience about the rollback."
                ),
                "owner": "marketing-agent",
            }
        )
    steps.append(
        {
            "order": len(steps) + 1,
            "action": (
                "Log the rollback and root-cause owner in company memory before "
                "re-attempting the launch."
            ),
            "owner": "chief-of-staff",
        }
    )
    return steps


def _verification_checks(tier: Mapping[str, Any]) -> list[dict[str, str]]:
    checks = [
        {
            "id": "service_healthy",
            "label": "The restored build is healthy and serving the prior behavior.",
        },
        {
            "id": "acceptance_recheck",
            "label": (
                "The acceptance checks that backed the launch pass again on the "
                "restored state."
            ),
        },
        {
            "id": "data_consistent",
            "label": "Data and migrations are consistent with the restored state.",
        },
    ]
    if tier["id"] in {"t2_beta", "t3_ga"}:
        checks.append(
            {
                "id": "user_facing_confirmed",
                "label": (
                    "A founder-facing spot check confirms users no longer hit the "
                    "failed path."
                ),
            }
        )
    return checks


def _data_reversal_notes(tier: Mapping[str, Any]) -> list[str]:
    notes = [
        "Prefer additive, reversible migrations so rollback does not require "
        "destructive data changes.",
        "If a migration is not reversible, snapshot or back up affected data "
        "before launch so it can be restored.",
        "Reconcile any records written during the launch window against the "
        "restored schema before re-enabling.",
    ]
    if tier["id"] == "t3_ga":
        notes.append(
            "For GA, confirm the data reconciliation plan with the founder before "
            "executing it against production data."
        )
    return notes


def _founder_sign_off(tier: Mapping[str, Any]) -> dict[str, Any]:
    required = bool(tier["founder_sign_off_required"])
    return {
        "required": required,
        "status": "pending",
        "prompt": (
            "Founder confirms this rollback plan is acceptable for the "
            f"{tier['name']} launch before approving the launch."
            if required
            else (
                "Founder may acknowledge this rollback plan; sign-off is optional "
                f"for the {tier['name']} tier."
            )
        ),
    }
