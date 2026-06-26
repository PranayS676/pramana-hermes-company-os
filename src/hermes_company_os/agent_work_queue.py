from __future__ import annotations

QUEUE_STATES = (
    "planned",
    "assigned",
    "running",
    "blocked",
    "needs_review",
    "approved",
    "rejected",
    "done",
)

QUEUE_PRIORITIES = ("low", "medium", "high", "urgent")

QUEUE_STATE_LABELS = {
    "planned": "Planned",
    "assigned": "Assigned",
    "running": "Running",
    "blocked": "Blocked",
    "needs_review": "Needs review",
    "approved": "Approved",
    "rejected": "Rejected",
    "done": "Done",
}

QUEUE_PRIORITY_LABELS = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "urgent": "Urgent",
}

FOUNDER_CONFIRMED_STATES = {"approved", "rejected"}

QUEUE_TRANSITIONS = {
    "planned": {"assigned", "blocked", "rejected"},
    "assigned": {"running", "blocked", "needs_review", "rejected"},
    "running": {"blocked", "needs_review"},
    "blocked": {"planned", "assigned", "running", "needs_review", "rejected"},
    "needs_review": {"approved", "rejected", "blocked", "assigned"},
    "approved": {"done", "assigned", "blocked"},
    "rejected": {"planned", "assigned", "done"},
    "done": {"planned"},
}


def validate_queue_state(state: str) -> str:
    normalized = state.strip()
    if normalized not in QUEUE_STATES:
        raise ValueError(f"Unsupported agent work item status: {state}")
    return normalized


def validate_queue_priority(priority: str) -> str:
    normalized = priority.strip() or "medium"
    if normalized not in QUEUE_PRIORITIES:
        raise ValueError(f"Unsupported agent work item priority: {priority}")
    return normalized


def validate_queue_transition(
    current_status: str,
    next_status: str,
    *,
    founder_confirmed: bool = False,
) -> str:
    current = validate_queue_state(current_status)
    target = validate_queue_state(next_status)
    if current == target:
        return target
    if target not in QUEUE_TRANSITIONS[current]:
        raise ValueError(
            f"Cannot move agent work item from {current} to {target}."
        )
    if target in FOUNDER_CONFIRMED_STATES and not founder_confirmed:
        raise ValueError(
            "Founder confirmation is required before approving or rejecting queue work."
        )
    return target
