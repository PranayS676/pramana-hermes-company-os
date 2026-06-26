from __future__ import annotations

import json
from collections import Counter

RESOLVED_DECISION_STATUSES = {"approved", "rejected", "deferred"}


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
            "resolved_with_decision": len(resolved_decisions),
            "status_counts": _status_counts(decisions),
        },
        "open_decisions": [_decision(item) for item in open_decisions],
        "decisions": [_decision(item) for item in decisions],
        "routing": {
            "slack_primary": "#decisions",
            "founder_command": "#founder-command",
            "telegram": "urgent founder approvals, blockers, and failed runs only",
        },
        "entry_points": {
            "dashboard": "/#founder-decisions",
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
        f"- Resolved with decision note: {summary['resolved_with_decision']}",
        f"- Status: {_format_counts(summary['status_counts'])}",
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
    return {
        "id": item["id"],
        "title": item["title"],
        "status": item["status"],
        "urgency": item["urgency"],
        "source": item["source"],
        "owner_agent_id": item["owner_agent_id"],
        "owner_name": item.get("owner_name") or "",
        "owner_command": item.get("owner_command") or "",
        "slack_channel": item["slack_channel"],
        "telegram_policy": item["telegram_policy"],
        "context": item["context"],
        "decision": item["decision"],
        "has_decision": bool(item["decision"].strip()),
        "updated_at": item["updated_at"],
    }


def _decision_lines(item: dict) -> list[str]:
    decision = item["decision"].strip() or "not recorded"
    return [
        f"### {item['title']}",
        "",
        f"- ID: `{item['id']}`",
        f"- Status: `{item['status']}`",
        f"- Urgency: `{item['urgency']}`",
        f"- Owner: {item['owner_name']} (`{item['owner_command']}`)",
        f"- Slack: `{item['slack_channel']}`",
        f"- Telegram policy: {item['telegram_policy']}",
        f"- Context: {item['context']}",
        f"- Decision: {decision}",
        "",
    ]


def _status_counts(items: list[dict]) -> dict[str, int]:
    return dict(Counter(item["status"] for item in items))


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
