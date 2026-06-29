from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from hermes_company_os.agent_work_queue import validate_queue_transition

# States an item must already be in for auto-pickup to consider it. We only ever
# nudge planned/assigned work forward; everything else is hands-off.
AUTO_PICKUP_ELIGIBLE_STATES = frozenset({"planned", "assigned"})

# States auto-pickup must never advance toward. These are founder-confirmed or
# terminal outcomes and stay strictly under founder control.
AUTO_PICKUP_FORBIDDEN_TARGETS = frozenset({"approved", "rejected", "done"})

# The forward step auto-pickup attempts for each eligible current state. Targets
# are still validated against the queue state machine, so this is a preference
# map, not an authority to bypass transition rules.
_AUTO_PICKUP_FORWARD = {
    "planned": "assigned",
    "assigned": "running",
}


@dataclass(frozen=True)
class AutoPickupPolicy:
    """Founder-controlled policy describing how far auto-pickup may advance work.

    ``enabled`` defaults to ``False`` so the mechanism is inert unless a founder
    explicitly opts in (mirrored by the ``HERMES_AUTO_PICKUP_ENABLED`` flag,
    which also defaults off). Autonomy is limited to queue-state orchestration:
    nothing here triggers live external execution.
    """

    enabled: bool = False
    allowed_agent_ids: frozenset[str] = field(default_factory=frozenset)
    max_items: int | None = None
    advance_to_running: bool = False
    skip_founder_required: bool = True

    def __post_init__(self) -> None:
        # Normalize the allowlist to a frozenset of trimmed ids so callers may
        # pass any iterable (list/tuple/set) without surprising membership checks.
        if not isinstance(self.allowed_agent_ids, frozenset):
            normalized = frozenset(
                str(agent_id).strip()
                for agent_id in self.allowed_agent_ids
                if str(agent_id).strip()
            )
            object.__setattr__(self, "allowed_agent_ids", normalized)


def eligible_for_auto_pickup(item: Mapping[str, object], policy: AutoPickupPolicy) -> bool:
    """Return whether ``item`` may be auto-advanced under ``policy``.

    Pure predicate — no DB access. Skips anything that is not a fresh
    planned/assigned item, anything awaiting founder action, and any owner not
    on the allowlist (when an allowlist is configured).
    """
    if not policy.enabled:
        return False

    status = str(item.get("status", "")).strip()
    if status not in AUTO_PICKUP_ELIGIBLE_STATES:
        return False

    if policy.skip_founder_required and item.get("founder_action_required"):
        return False

    owner_agent_id = str(item.get("owner_agent_id", "")).strip()
    if policy.allowed_agent_ids and owner_agent_id not in policy.allowed_agent_ids:
        return False

    # The item must have a legal forward step that auto-pickup is allowed to take.
    return next_auto_pickup_status(status, policy=policy) is not None


def next_auto_pickup_status(
    current: str,
    *,
    policy: AutoPickupPolicy | None = None,
) -> str | None:
    """Return the forward status auto-pickup would move ``current`` to, or ``None``.

    Defers to :func:`validate_queue_transition` with ``founder_confirmed=False``
    so this can never reach a founder-confirmed/terminal state. Returns ``None``
    when there is no allowed forward step (illegal transition, forbidden target,
    or running disabled by the policy).
    """
    current_status = str(current).strip()
    target = _AUTO_PICKUP_FORWARD.get(current_status)
    if target is None:
        return None

    # Never advance into a founder-confirmed or terminal state.
    if target in AUTO_PICKUP_FORBIDDEN_TARGETS:
        return None

    # Honor the policy's opt-in for the running step.
    if target == "running" and policy is not None and not policy.advance_to_running:
        return None

    try:
        validated = validate_queue_transition(
            current_status,
            target,
            founder_confirmed=False,
        )
    except ValueError:
        return None

    if validated in AUTO_PICKUP_FORBIDDEN_TARGETS:
        return None
    return validated
