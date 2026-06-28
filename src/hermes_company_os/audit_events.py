from __future__ import annotations

PROJECT_AUDIT_EVENT_LABELS = {
    "generation_started": "Generation started",
    "generation_succeeded": "Generation succeeded",
    "generation_failed": "Generation failed",
    "stage_approved": "Stage approved",
    "stage_revision_requested": "Stage revision requested",
    "founder_decision_created": "Founder decision opened",
    "founder_decision_resolved": "Founder decision resolved",
    "founder_decision_updated": "Founder decision updated",
    "multi_agent_review_blocked": "Multi-agent review blocked",
    "multi_agent_review_completed": "Multi-agent review completed",
    "memory_created": "Memory captured",
    "memory_retired": "Memory retired",
    "memory_reactivated": "Memory reactivated",
    "memory_pinned": "Memory pinned",
    "memory_unpinned": "Memory unpinned",
    "memory_updated": "Memory updated",
    "kanban_push_blocked": "Kanban push blocked",
    "kanban_push_started": "Kanban push started",
    "kanban_task_linked": "Kanban task linked",
    "codex_execution_queued": "Codex execution queued",
    "codex_execution_updated": "Codex execution updated",
}


def audit_event_label(event_type: str) -> str:
    return PROJECT_AUDIT_EVENT_LABELS.get(
        event_type,
        event_type.replace("_", " ").title(),
    )


def enrich_audit_event(event: dict) -> dict:
    return {
        **event,
        "event_label": audit_event_label(event["event_type"]),
    }
