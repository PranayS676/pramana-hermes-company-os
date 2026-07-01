from __future__ import annotations

import re
from collections import defaultdict

AUDIT_LINE = re.compile(r"^\s*(FOUND|MISSING|DEFER)\s+([A-Za-z0-9_-]+)\s+(.+?)\s*$")
REQUIRED_LABELS = {
    "profile directory",
    "command alias",
    "SOUL.md",
    "capabilities.json",
    "profile-manifest.json",
    ".env.example",
    "config.yaml.example",
}
LIVE_LABELS = {".env presence", "config.yaml presence"}


def parse_profile_installation_audit(
    raw_text: str,
    profile_installation_checks: list[dict],
) -> dict:
    known_agent_ids = {check["agent_id"] for check in profile_installation_checks}
    by_agent: dict[str, list[dict]] = defaultdict(list)
    unknown_agent_ids: list[str] = []
    ignored_lines: list[str] = []

    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("```"):
            continue
        if cleaned.startswith("Profile installation audit finished"):
            continue
        match = AUDIT_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        status, agent_id, label = match.groups()
        if agent_id not in known_agent_ids:
            unknown_agent_ids.append(agent_id)
            continue
        by_agent[agent_id].append(
            {
                "status": status.lower(),
                "label": label.strip(),
            }
        )

    updates = {}
    incomplete_agent_ids: list[str] = []
    for check in profile_installation_checks:
        agent_id = check["agent_id"]
        if agent_id not in by_agent:
            continue
        result = _agent_result(by_agent[agent_id])
        if result is None:
            incomplete_agent_ids.append(agent_id)
            continue
        updates[check["id"]] = result

    return {
        "updates": updates,
        "imported": len(updates),
        "unknown_agent_ids": sorted(set(unknown_agent_ids)),
        "incomplete_agent_ids": sorted(set(incomplete_agent_ids)),
        "ignored_lines": ignored_lines,
    }


def profile_installation_import_redirect(summary: dict) -> str:
    return (
        "/setup/profiles?"
        f"profile_installation_imported={summary['imported']}"
        f"&profile_installation_unknown={len(summary['unknown_agent_ids'])}"
        f"&profile_installation_incomplete={len(summary['incomplete_agent_ids'])}"
        f"&profile_installation_ignored={len(summary['ignored_lines'])}"
        "#profile-installation-tracking"
    )


def _agent_result(items: list[dict]) -> dict | None:
    by_label = {item["label"]: item["status"] for item in items}
    observed_required = REQUIRED_LABELS.intersection(by_label)
    if not observed_required:
        return None

    missing_required = [
        label
        for label in sorted(REQUIRED_LABELS)
        if by_label.get(label) == "missing"
    ]
    if missing_required:
        return {
            "status": "blocked",
            "evidence": "Profile installation audit missing: "
            + ", ".join(missing_required)
            + ".",
        }

    unobserved_required = sorted(REQUIRED_LABELS - observed_required)
    if unobserved_required:
        return None

    live_deferred = [
        label
        for label in sorted(LIVE_LABELS)
        if by_label.get(label) == "defer"
    ]
    evidence = "Profile installation audit passed."
    if live_deferred:
        evidence += " Live files deferred: " + ", ".join(live_deferred) + "."
    return {
        "status": "verified",
        "evidence": evidence,
    }
