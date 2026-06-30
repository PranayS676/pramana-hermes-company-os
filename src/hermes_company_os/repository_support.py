from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from hermes_company_os.audit_events import enrich_audit_event
from hermes_company_os.project_memory import (
    enrich_memory_entry,
)
from hermes_company_os.secret_guard import secret_violations


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def serialize_wizard_json_content(json_content: dict | list | str | None) -> str:
    if json_content is None:
        return ""
    if isinstance(json_content, str):
        if not json_content.strip():
            return ""
        return json.dumps(json.loads(json_content), sort_keys=True)
    return json.dumps(json_content, sort_keys=True)


def decode_project(row: sqlite3.Row) -> dict:
    project = dict(row)
    raw_intake = project.get("intake_json", "").strip()
    project["intake"] = json.loads(raw_intake) if raw_intake else {}
    return project


def decode_wizard_artifact(row: sqlite3.Row) -> dict:
    artifact = dict(row)
    raw_json = artifact["json_content"].strip()
    artifact["json"] = json.loads(raw_json) if raw_json else {}
    return artifact


def decode_generation_run(row: sqlite3.Row) -> dict:
    run = dict(row)
    raw_sources = run.get("source_artifact_ids_json", "").strip()
    raw_memory_ids = run.get("memory_ids_json", "").strip()
    run["source_artifact_ids"] = json.loads(raw_sources) if raw_sources else []
    run["memory_ids"] = json.loads(raw_memory_ids) if raw_memory_ids else []
    return run


def decode_codex_execution_run(row: sqlite3.Row) -> dict:
    run = dict(row)
    run["external_execution_enabled"] = bool(run["external_execution_enabled"])
    for column, target, fallback in (
        ("source_artifact_ids_json", "source_artifact_ids", []),
        ("command_preview_json", "command_preview", []),
        ("approval_snapshot_json", "approval_snapshot", {}),
        ("audit_json", "audit", {}),
    ):
        raw_json = run.get(column, "").strip()
        run[target] = json.loads(raw_json) if raw_json else fallback
    return run


def decode_project_review_record(row: sqlite3.Row) -> dict:
    record = dict(row)
    for column, target, fallback in (
        ("artifact_ids_json", "artifact_ids", []),
        ("checks_json", "checks", []),
        ("findings_json", "findings", []),
    ):
        raw_json = record.get(column, "").strip()
        record[target] = json.loads(raw_json) if raw_json else fallback
    return record


def decode_project_memory_entry(row: sqlite3.Row) -> dict:
    return enrich_memory_entry(dict(row))


def decode_research_package(row: sqlite3.Row) -> dict:
    record = dict(row)
    for column, target, fallback in (
        ("findings_json", "findings", []),
        ("recommendations_json", "recommendations", []),
        ("founder_decisions_json", "founder_decisions_needed", []),
    ):
        raw_json = record.get(column, "").strip()
        record[target] = json.loads(raw_json) if raw_json else fallback
    return record


def decode_external_dispatch_delivery(row: sqlite3.Row) -> dict:
    delivery = dict(row)
    raw_result = delivery.get("result_json", "").strip()
    delivery["result"] = json.loads(raw_result) if raw_result else {}
    return delivery


def decode_audit_event(row: sqlite3.Row) -> dict:
    event = dict(row)
    raw_payload = event["payload_json"].strip()
    event["payload"] = json.loads(raw_payload) if raw_payload else {}
    return enrich_audit_event(event)


def safe_generation_error(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        return "Generation failed without a detailed error."
    if secret_violations({"generation_error": cleaned}):
        return "Generation failed. Error contained secret-looking content and was redacted."
    return cleaned[:1000]


def age_label(timestamp: str) -> str:
    if not timestamp:
        return "unknown age"
    try:
        created = datetime.fromisoformat(timestamp)
    except ValueError:
        return "unknown age"
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    elapsed = datetime.now(UTC) - created
    days = elapsed.days
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''}"
    hours = elapsed.seconds // 3600
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    minutes = max(1, elapsed.seconds // 60)
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def decode_agent_work_item(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["founder_action_required"] = bool(item["founder_action_required"])
    item["blocked_age_label"] = (
        age_label(item["updated_at"]) if item["status"] == "blocked" else ""
    )
    return item
