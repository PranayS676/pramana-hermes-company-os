from __future__ import annotations

import json
from collections import Counter

RESOLVED_DECISION_STATUSES = {"approved", "rejected", "deferred"}
DECISION_TYPE_LABELS = {
    "operating_decision": "Operating decision",
    "artifact_approval": "Artifact approval",
    "revision_request": "Revision request",
    "agent_question": "Agent question",
    "blocker": "Blocker",
    "accepted_risk": "Accepted risk",
    "external_action_approval": "External action approval",
    "launch_decision": "Launch decision",
    "final_artifact_approval": "Final artifact approval",
}
SUPPORTED_DECISION_TYPES = frozenset(DECISION_TYPE_LABELS)
FOUNDER_ONLY_DECISION_TYPES = frozenset(
    {
        "accepted_risk",
        "external_action_approval",
        "launch_decision",
        "final_artifact_approval",
    }
)


def founder_only_decision_type(decision_type: str) -> bool:
    return decision_type in FOUNDER_ONLY_DECISION_TYPES


def normalize_decision_type(decision_type: str) -> str:
    normalized = (decision_type or "operating_decision").strip()
    if normalized not in SUPPORTED_DECISION_TYPES:
        raise ValueError(f"Unsupported founder decision type: {normalized}")
    return normalized


def founder_decisions_payload(decisions: list[dict]) -> dict:
    open_decisions = [
        item for item in decisions if item["status"] not in RESOLVED_DECISION_STATUSES
    ]
    resolved_decisions = [
        item
        for item in decisions
        if item["status"] in RESOLVED_DECISION_STATUSES and item["decision"].strip()
    ]
    return {
        "title": "Founder Decision Queue",
        "credential_boundary": (
            "This queue stores only non-secret founder decisions, context, routing "
            "metadata, and status. Do not paste Slack tokens, Telegram bot tokens, "
            "provider API keys, OAuth payloads, private endpoints, raw logs, or "
            "credentials into decision text."
        ),
        "summary": {
            "total": len(decisions),
            "open": len(open_decisions),
            "urgent_open": len(
                [item for item in open_decisions if item["urgency"] == "urgent"]
            ),
            "founder_only_open": len(
                [item for item in open_decisions if item.get("requires_founder_approval")]
            ),
            "project_linked": len([item for item in decisions if item.get("project_id")]),
            "resolved_with_decision": len(resolved_decisions),
            "status_counts": _status_counts(decisions),
            "type_counts": _type_counts(decisions),
        },
        "open_decisions": [_decision(item) for item in open_decisions],
        "decisions": [_decision(item) for item in decisions],
        "decision_types": [
            {"id": decision_type, "label": label}
            for decision_type, label in DECISION_TYPE_LABELS.items()
        ],
        "routing": {
            "slack_primary": "#decisions",
            "founder_command": "#founder-command",
            "telegram": "urgent founder approvals, blockers, and failed runs only",
        },
        "entry_points": {
            "dashboard": "/#founder-decisions",
            "inbox": "/decisions",
            "founder_next_actions": "/setup/founder-next-actions.md",
            "company_launch_drill": "/setup/company-launch-drill.md",
            "telegram_policy": "/setup/telegram-policy.md",
        },
    }


def founder_decisions_json(decisions: list[dict]) -> str:
    return json.dumps(
        founder_decisions_payload(decisions),
        indent=2,
        sort_keys=True,
    ) + "\n"


def founder_decisions_markdown(decisions: list[dict]) -> str:
    payload = founder_decisions_payload(decisions)
    summary = payload["summary"]
    lines = [
        "# Founder Decision Queue",
        "",
        "Use this as the durable steering log for founder approvals, deferrals, "
        "and urgent go/no-go decisions.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Summary",
        "",
        f"- Open decisions: {summary['open']}",
        f"- Urgent open decisions: {summary['urgent_open']}",
        f"- Founder-only open decisions: {summary['founder_only_open']}",
        f"- Project-linked decisions: {summary['project_linked']}",
        f"- Resolved with decision note: {summary['resolved_with_decision']}",
        f"- Status: {_format_counts(summary['status_counts'])}",
        f"- Type: {_format_counts(summary['type_counts'])}",
        "",
        "## Open Decisions",
        "",
    ]
    if payload["open_decisions"]:
        for item in payload["open_decisions"]:
            lines.extend(_decision_lines(item))
    else:
        lines.append("- None.")
        lines.append("")
    lines.extend(["## All Decisions", ""])
    for item in payload["decisions"]:
        lines.extend(_decision_lines(item))
    lines.extend(
        [
            "## Routing",
            "",
            "- Routine discussion stays in Slack.",
            "- Decisions that block work go to `#founder-command`.",
            "- Telegram is only for urgent founder approvals, blockers, and failed runs.",
            "",
            "## Exports",
            "",
            "- JSON queue: `/setup/founder-decisions.json`",
            "- Dashboard queue: `/#founder-decisions`",
            "",
        ]
    )
    return "\n".join(lines)


def _decision(item: dict) -> dict:
    decision_type = normalize_decision_type(item.get("decision_type", "operating_decision"))
    return {
        "id": item["id"],
        "title": item["title"],
        "status": item["status"],
        "urgency": item["urgency"],
        "decision_type": decision_type,
        "decision_type_label": DECISION_TYPE_LABELS[decision_type],
        "source": item["source"],
        "owner_agent_id": item["owner_agent_id"],
        "owner_name": item.get("owner_name") or "",
        "owner_command": item.get("owner_command") or "",
        "project_id": item.get("project_id") or "",
        "project_name": item.get("project_name") or "",
        "stage_id": item.get("stage_id") or "",
        "artifact_id": item.get("artifact_id") or "",
        "slack_channel": item["slack_channel"],
        "telegram_policy": item["telegram_policy"],
        "context": item["context"],
        "evidence": item.get("evidence") or "",
        "decision": item["decision"],
        "has_decision": bool(item["decision"].strip()),
        "requires_founder_approval": bool(item.get("requires_founder_approval")),
        "resolved_at": item.get("resolved_at") or "",
        "resolution_note": item.get("resolution_note") or item["decision"],
        "updated_at": item["updated_at"],
    }


def _decision_lines(item: dict) -> list[str]:
    decision = item["decision"].strip() or "not recorded"
    lines = [
        f"### {item['title']}",
        "",
        f"- ID: `{item['id']}`",
        f"- Status: `{item['status']}`",
        f"- Urgency: `{item['urgency']}`",
        f"- Type: {item['decision_type_label']}",
        f"- Founder-only: {'yes' if item['requires_founder_approval'] else 'no'}",
        f"- Owner: {item['owner_name']} (`{item['owner_command']}`)",
        f"- Slack: `{item['slack_channel']}`",
        f"- Telegram policy: {item['telegram_policy']}",
        f"- Context: {item['context']}",
        f"- Decision: {decision}",
    ]
    if item["project_id"]:
        lines.append(f"- Project: {item['project_name']} (`{item['project_id']}`)")
    if item["stage_id"]:
        lines.append(f"- Stage: `{item['stage_id']}`")
    if item["artifact_id"]:
        lines.append(f"- Artifact: `{item['artifact_id']}`")
    if item["evidence"]:
        lines.append(f"- Evidence: {item['evidence']}")
    lines.append("")
    return lines


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _type_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item.get("decision_type", "operating_decision") for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
