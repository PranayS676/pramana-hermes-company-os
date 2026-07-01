from __future__ import annotations

import json
from collections import Counter

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES


def verification_evidence_payload(
    *,
    agents: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    profile_smoke_runs: dict[str, dict],
    profile_acceptance_checks: list[dict] | None = None,
    profile_installation_checks: list[dict] | None = None,
    founder_decisions: list[dict] | None = None,
) -> dict:
    active_schedule_checks = [
        check for check in schedule_checks if check.get("schedule_active", 1)
    ]
    phases = [
        _credential_phase(secret_requirements),
        _check_phase(
            phase_id="messaging",
            label="Slack and Telegram messaging evidence",
            anchor="/setup/messaging#messaging-verification",
            checks=messaging_checks,
        ),
        _check_phase(
            phase_id="kanban",
            label="Hermes Kanban evidence",
            anchor="/setup/verification#kanban-verification",
            checks=kanban_checks,
        ),
        _check_phase(
            phase_id="scheduling",
            label="Standup scheduling evidence",
            anchor="/setup/verification#schedule-verification",
            checks=active_schedule_checks,
        ),
        _check_phase(
            phase_id="profile_installation",
            label="Profile installation evidence",
            anchor="/setup/profiles#profile-installation-tracking",
            checks=profile_installation_checks or [],
        ),
        _profile_smoke_phase(agents, model_preferences, profile_smoke_runs),
        _check_phase(
            phase_id="profile_acceptance",
            label="Profile acceptance evidence",
            anchor="/setup/profiles#profile-acceptance-tracking",
            checks=profile_acceptance_checks or [],
        ),
    ]
    if founder_decisions is not None:
        phases.append(_founder_decision_phase(founder_decisions))
    return {
        "title": "Verification Evidence Pack",
        "credential_boundary": (
            "This pack summarizes statuses and whether evidence exists. It omits "
            "credential values, raw evidence text, profile prompts, profile outputs, "
            "request headers, OAuth payloads, private endpoints, and logs."
        ),
        "ready": all(phase["ready"] for phase in phases),
        "summary": {
            "phases": len(phases),
            "ready_phases": len([phase for phase in phases if phase["ready"]]),
            "open_items": sum(len(phase["open_items"]) for phase in phases),
            "missing_evidence": sum(len(phase["missing_evidence"]) for phase in phases),
        },
        "phases": phases,
        "entry_points": {
            "credential_loading": "/setup/credential-loading.md",
            "credential_status": "/setup/messaging#secret-status",
            "messaging_verification": "/setup/messaging#messaging-verification",
            "kanban_verification": "/setup/verification#kanban-verification",
            "schedule_verification": "/setup/verification#schedule-verification",
            "profile_installation": "/setup/profiles#profile-installation-tracking",
            "profile_smoke": "/setup/profiles#profile-smoke",
            "profile_acceptance": "/setup/profiles#profile-acceptance-tracking",
            "founder_decisions": "/#founder-decisions",
            "live_verification": "/setup/live-verification.md",
        },
    }


def verification_evidence_json(**kwargs) -> str:
    return json.dumps(
        verification_evidence_payload(**kwargs),
        indent=2,
        sort_keys=True,
    ) + "\n"


def verification_evidence_markdown(**kwargs) -> str:
    payload = verification_evidence_payload(**kwargs)
    summary = payload["summary"]
    lines = [
        "# Verification Evidence Pack",
        "",
        "Use this after running live checks to see what proof is still missing "
        "without exposing the proof text itself.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Summary",
        "",
        f"- Ready for final live activation: {'yes' if payload['ready'] else 'no'}",
        f"- Ready phases: {summary['ready_phases']} of {summary['phases']}",
        f"- Open items: {summary['open_items']}",
        f"- Verified checks missing evidence: {summary['missing_evidence']}",
        "",
        "## Phase Evidence",
        "",
    ]
    for phase in payload["phases"]:
        lines.extend(
            [
                f"### {phase['label']}",
                "",
                f"- Ready: {'yes' if phase['ready'] else 'no'}",
                f"- Dashboard: `{phase['anchor']}`",
                f"- Status: {_format_counts(phase['status_counts'])}",
                f"- Evidence present: {phase['evidence_present']} of "
                f"{phase['evidence_required']}",
                "",
            ]
        )
        if phase["open_items"]:
            lines.append("- Open items:")
            for item in phase["open_items"]:
                lines.append(
                    f"  - `{item['id']}`: {item['label']} "
                    f"(status `{item['status']}`)"
                )
            lines.append("")
        if phase["missing_evidence"]:
            lines.append("- Verified items missing evidence:")
            for item in phase["missing_evidence"]:
                lines.append(f"  - `{item['id']}`: {item['label']}")
            lines.append("")
        else:
            lines.extend(["- Verified items missing evidence: none", ""])
    lines.extend(
        [
            "## Evidence Rules",
            "",
            "- Store only short non-secret evidence in dashboard forms.",
            "- Good examples: `Founder DM reply observed`, `cron list shows job`, "
            "`Kanban diagnostics passed`.",
            "- Do not paste tokens, provider keys, OAuth payloads, request headers, "
            "private endpoints, profile outputs, or logs.",
            "",
        ]
    )
    return "\n".join(lines)


def _credential_phase(secret_requirements: list[dict]) -> dict:
    items = [
        {
            "id": item["id"],
            "label": item["label"],
            "status": item["status"],
            "has_evidence": item["status"] in {"loaded", "verified"},
        }
        for item in secret_requirements
    ]
    return _phase(
        phase_id="credentials",
        label="External credential status evidence",
        anchor="/setup/messaging#secret-status",
        items=items,
        ready_statuses={"loaded", "verified"},
        evidence_required_statuses={"loaded", "verified"},
    )


def _check_phase(
    *,
    phase_id: str,
    label: str,
    anchor: str,
    checks: list[dict],
) -> dict:
    items = [
        {
            "id": check["id"],
            "label": check.get("label") or check["title"],
            "status": check["status"],
            "has_evidence": bool(check.get("evidence", "").strip()),
        }
        for check in checks
    ]
    return _phase(
        phase_id=phase_id,
        label=label,
        anchor=anchor,
        items=items,
        ready_statuses={"verified"},
        evidence_required_statuses={"verified"},
    )


def _profile_smoke_phase(
    agents: list[dict],
    model_preferences: list[dict],
    profile_smoke_runs: dict[str, dict],
) -> dict:
    preferences_by_agent = {
        preference["agent_id"]: preference for preference in model_preferences
    }
    items = []
    for agent in agents:
        run = profile_smoke_runs.get(agent["id"])
        preference = preferences_by_agent.get(agent["id"], {})
        status = run["status"] if run else preference.get("status", "missing")
        items.append(
            {
                "id": agent["id"],
                "label": agent["name"],
                "status": status,
                "has_evidence": bool(run and run.get("completed_at")),
            }
        )
    return _phase(
        phase_id="profile_smoke",
        label="Profile smoke evidence",
        anchor="/setup/profiles#profile-smoke",
        items=items,
        ready_statuses={"completed", "verified"},
        evidence_required_statuses={"completed", "verified"},
    )


def _founder_decision_phase(founder_decisions: list[dict]) -> dict:
    items = [
        {
            "id": item["id"],
            "label": item["title"],
            "status": item["status"],
            "has_evidence": bool(item["decision"].strip()),
        }
        for item in founder_decisions
    ]
    return _phase(
        phase_id="founder_decisions",
        label="Founder decision evidence",
        anchor="/#founder-decisions",
        items=items,
        ready_statuses=RESOLVED_DECISION_STATUSES,
        evidence_required_statuses=RESOLVED_DECISION_STATUSES,
    )


def _phase(
    *,
    phase_id: str,
    label: str,
    anchor: str,
    items: list[dict],
    ready_statuses: set[str],
    evidence_required_statuses: set[str],
) -> dict:
    open_items = [item for item in items if item["status"] not in ready_statuses]
    evidence_items = [
        item for item in items if item["status"] in evidence_required_statuses
    ]
    missing_evidence = [item for item in evidence_items if not item["has_evidence"]]
    return {
        "id": phase_id,
        "label": label,
        "anchor": anchor,
        "ready": bool(items) and not open_items and not missing_evidence,
        "status_counts": dict(Counter(item["status"] for item in items)),
        "evidence_required": len(evidence_items),
        "evidence_present": len(evidence_items) - len(missing_evidence),
        "open_items": [_public_item(item) for item in open_items],
        "missing_evidence": [_public_item(item) for item in missing_evidence],
    }


def _public_item(item: dict) -> dict:
    return {
        "id": _safe_public_id(item["id"]),
        "label": item["label"],
        "status": item["status"],
    }


def _safe_public_id(value: str) -> str:
    return value.replace("sk-", "sk_")


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
