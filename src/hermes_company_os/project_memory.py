from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from hermes_company_os.product_wizard import (
    FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
    ProductWizardMemoryPolicy,
)
from hermes_company_os.secret_guard import assert_no_secret_values

PROJECT_MEMORY_SCHEMA = "project_memory_package_v1"

MEMORY_CATEGORIES: tuple[str, ...] = (
    "founder_preference",
    "product_strategy",
    "technical_standard",
    "accepted_risk",
    "rejected_idea",
    "launch_learning",
    "customer_evidence",
    "research_finding",
)

MEMORY_CATEGORY_LABELS: dict[str, str] = {
    "founder_preference": "Founder preference",
    "product_strategy": "Product strategy",
    "technical_standard": "Technical standard",
    "accepted_risk": "Accepted risk",
    "rejected_idea": "Rejected idea",
    "launch_learning": "Launch learning",
    "customer_evidence": "Customer evidence",
    "research_finding": "Research finding",
}

MEMORY_STATUSES: tuple[str, ...] = ("draft", "active", "retired")
MEMORY_CONFIDENCE_LEVELS: tuple[str, ...] = ("low", "medium", "high")


def memory_category_options() -> list[dict[str, str]]:
    return [
        {"id": category, "label": MEMORY_CATEGORY_LABELS[category]}
        for category in MEMORY_CATEGORIES
    ]


def memory_status_options() -> list[dict[str, str]]:
    return [{"id": status, "label": status.replace("_", " ").title()} for status in MEMORY_STATUSES]


def memory_confidence_options() -> list[dict[str, str]]:
    return [
        {"id": confidence, "label": confidence.title()}
        for confidence in MEMORY_CONFIDENCE_LEVELS
    ]


def normalize_memory_category(category: str) -> str:
    normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in MEMORY_CATEGORIES:
        raise ValueError(f"Unsupported memory category: {category}")
    return normalized


def normalize_memory_status(status: str) -> str:
    normalized = status.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in MEMORY_STATUSES:
        raise ValueError(f"Unsupported memory status: {status}")
    return normalized


def normalize_memory_confidence(confidence: str) -> str:
    normalized = confidence.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in MEMORY_CONFIDENCE_LEVELS:
        raise ValueError(f"Unsupported memory confidence: {confidence}")
    return normalized


def project_memory_package(repository, project_id: str) -> dict[str, Any]:
    project = repository.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")
    entries = repository.list_project_memory_entries(
        project_id=project_id,
        include_company_wide=True,
        include_retired=True,
        include_expired=True,
        limit=100,
    )
    reusable = [entry for entry in entries if entry["reusable"]]
    stale = [entry for entry in entries if entry["expired"] or entry["review_due"]]
    retired = [entry for entry in entries if entry["status"] == "retired"]
    payload = {
        "schema": PROJECT_MEMORY_SCHEMA,
        "project": {
            "id": project_id,
            "name": project["name"],
            "status": project["status"],
        },
        "aggregate": {
            "total_count": len(entries),
            "reusable_count": len(reusable),
            "stale_count": len(stale),
            "retired_count": len(retired),
        },
        "category_options": memory_category_options(),
        "status_options": memory_status_options(),
        "confidence_options": memory_confidence_options(),
        "entries": [_memory_payload(entry) for entry in entries],
        "reusable_entries": [_memory_payload(entry) for entry in reusable],
    }
    assert_no_secret_values({"project_memory_package": json.dumps(payload, sort_keys=True)})
    return payload


def project_memory_markdown(package: Mapping[str, Any]) -> str:
    lines = [
        f"# Project Memory Package: {package['project']['name']}",
        "",
        f"- Schema: `{package['schema']}`",
        f"- Project: `{package['project']['id']}`",
        f"- Total entries: {package['aggregate']['total_count']}",
        f"- Reusable entries: {package['aggregate']['reusable_count']}",
        f"- Stale entries: {package['aggregate']['stale_count']}",
        "",
        "## Reusable Context",
        "",
    ]
    if package["reusable_entries"]:
        for entry in package["reusable_entries"]:
            lines.extend(_entry_markdown_lines(entry))
    else:
        lines.append("- No reusable memory is approved for this project yet.")
        lines.append("")
    lines.extend(["## All Memory Entries", ""])
    if package["entries"]:
        for entry in package["entries"]:
            lines.extend(_entry_markdown_lines(entry))
    else:
        lines.append("- No project memory entries recorded.")
        lines.append("")
    markdown = "\n".join(lines)
    assert_no_secret_values({"project_memory_markdown": markdown})
    return markdown


def product_wizard_memory_context(
    repository,
    project_id: str,
    *,
    policy: ProductWizardMemoryPolicy = FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
) -> list[dict[str, Any]]:
    max_entries = max(0, min(policy.max_entries, 20))
    if not policy.enabled or not policy.allowed_categories or max_entries <= 0:
        return []
    allowed_categories = set(policy.allowed_categories)
    entries = repository.list_reusable_project_memory_entries(project_id, limit=200)
    context = [
        _memory_prompt_payload(entry)
        for entry in entries
        if entry["category"] in allowed_categories
    ][:max_entries]
    assert_no_secret_values(
        {"product_wizard_memory_context": json.dumps(context, sort_keys=True)}
    )
    return context


def enrich_memory_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(entry)
    enriched["project_id"] = enriched.get("project_id") or ""
    enriched["pinned"] = bool(enriched.get("pinned"))
    enriched["category_label"] = MEMORY_CATEGORY_LABELS.get(
        str(enriched.get("category", "")),
        str(enriched.get("category", "")).replace("_", " ").title(),
    )
    enriched["scope_label"] = "company-wide" if not enriched["project_id"] else "project"
    enriched["expired"] = _date_has_passed(enriched.get("expires_at", ""))
    enriched["review_due"] = _date_has_passed(enriched.get("review_after", ""))
    enriched["reusable"] = (
        enriched.get("status") == "active"
        and not enriched["expired"]
        and not enriched["review_due"]
    )
    return enriched


def _date_has_passed(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed <= datetime.now(UTC)


def _memory_payload(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "source_key": entry["source_key"],
        "project_id": entry.get("project_id") or "",
        "category": entry["category"],
        "category_label": entry["category_label"],
        "memory_type": entry["memory_type"],
        "owner_agent_id": entry["owner_agent_id"],
        "owner_name": entry.get("owner_name", ""),
        "source": entry["source"],
        "source_artifact_id": entry.get("source_artifact_id", ""),
        "source_decision_id": entry.get("source_decision_id", ""),
        "title": entry["title"],
        "summary": entry["summary"],
        "body": entry["body"],
        "confidence": entry["confidence"],
        "status": entry["status"],
        "pinned": bool(entry["pinned"]),
        "review_after": entry.get("review_after", ""),
        "expires_at": entry.get("expires_at", ""),
        "scope_label": entry["scope_label"],
        "expired": bool(entry["expired"]),
        "review_due": bool(entry["review_due"]),
        "reusable": bool(entry["reusable"]),
        "created_at": entry["created_at"],
        "updated_at": entry["updated_at"],
    }


def _memory_prompt_payload(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": entry["id"],
        "category": entry["category"],
        "title": entry["title"],
        "summary": entry["summary"],
        "body": entry["body"],
        "owner_agent_id": entry["owner_agent_id"],
        "source": entry["source"],
        "source_artifact_id": entry.get("source_artifact_id", ""),
        "source_decision_id": entry.get("source_decision_id", ""),
        "scope_label": entry["scope_label"],
        "confidence": entry["confidence"],
        "status": entry["status"],
        "reusable": bool(entry["reusable"]),
        "expired": bool(entry["expired"]),
        "review_due": bool(entry["review_due"]),
    }


def _entry_markdown_lines(entry: Mapping[str, Any]) -> list[str]:
    status_notes = []
    if entry["pinned"]:
        status_notes.append("pinned")
    if entry["expired"]:
        status_notes.append("expired")
    if entry["review_due"]:
        status_notes.append("review due")
    status = ", ".join(status_notes) if status_notes else "current"
    return [
        f"### {entry['title']}",
        "",
        f"- Category: `{entry['category']}`",
        f"- Scope: `{entry['scope_label']}`",
        f"- Status: `{entry['status']}` ({status})",
        f"- Confidence: `{entry['confidence']}`",
        f"- Owner: `{entry['owner_agent_id']}`",
        f"- Source: {entry['source']}",
        f"- Summary: {entry['summary']}",
        "",
        entry["body"],
        "",
    ]
