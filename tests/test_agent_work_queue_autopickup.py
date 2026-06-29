from __future__ import annotations

import json

import pytest

from hermes_company_os.agent_work_pickup import (
    AUTO_PICKUP_ELIGIBLE_STATES,
    AUTO_PICKUP_FORBIDDEN_TARGETS,
    AutoPickupPolicy,
    eligible_for_auto_pickup,
    next_auto_pickup_status,
)
from hermes_company_os.agent_work_queue import QUEUE_STATES
from hermes_company_os.database import initialize_database
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def _make_item(**overrides) -> dict:
    item = {
        "id": "work-test",
        "status": "planned",
        "owner_agent_id": "research-agent",
        "founder_action_required": False,
    }
    item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# Pure-predicate unit tests
# ---------------------------------------------------------------------------


def test_disabled_policy_makes_everything_ineligible():
    policy = AutoPickupPolicy(enabled=False)
    for status in QUEUE_STATES:
        assert eligible_for_auto_pickup(_make_item(status=status), policy) is False


def test_eligible_states_cover_only_planned_and_assigned():
    assert sorted(AUTO_PICKUP_ELIGIBLE_STATES) == ["assigned", "planned"]


def test_pure_predicate_across_all_queue_states():
    # advance_to_running so assigned is eligible too.
    policy = AutoPickupPolicy(enabled=True, advance_to_running=True)
    expected_eligible = {"planned", "assigned"}
    for status in QUEUE_STATES:
        item = _make_item(status=status)
        assert eligible_for_auto_pickup(item, policy) is (status in expected_eligible), status


def test_assigned_not_eligible_without_advance_to_running():
    policy = AutoPickupPolicy(enabled=True, advance_to_running=False)
    assert eligible_for_auto_pickup(_make_item(status="assigned"), policy) is False
    assert eligible_for_auto_pickup(_make_item(status="planned"), policy) is True


def test_founder_action_required_items_are_skipped():
    policy = AutoPickupPolicy(enabled=True, advance_to_running=True)
    item = _make_item(status="planned", founder_action_required=True)
    assert eligible_for_auto_pickup(item, policy) is False


def test_needs_review_and_blocked_are_skipped():
    policy = AutoPickupPolicy(enabled=True, advance_to_running=True)
    assert eligible_for_auto_pickup(_make_item(status="needs_review"), policy) is False
    assert eligible_for_auto_pickup(_make_item(status="blocked"), policy) is False


def test_allowlist_filters_owner_agents():
    policy = AutoPickupPolicy(
        enabled=True,
        allowed_agent_ids=frozenset({"research-agent"}),
    )
    assert eligible_for_auto_pickup(
        _make_item(status="planned", owner_agent_id="research-agent"), policy
    ) is True
    assert eligible_for_auto_pickup(
        _make_item(status="planned", owner_agent_id="qa-critic"), policy
    ) is False


def test_allowlist_accepts_plain_iterables():
    policy = AutoPickupPolicy(enabled=True, allowed_agent_ids=["research-agent"])
    assert policy.allowed_agent_ids == frozenset({"research-agent"})


def test_next_auto_pickup_status_forward_steps():
    assert next_auto_pickup_status("planned") == "assigned"
    assert next_auto_pickup_status("assigned") == "running"


def test_next_auto_pickup_status_never_targets_terminal_states():
    for status in QUEUE_STATES:
        result = next_auto_pickup_status(status)
        assert result not in AUTO_PICKUP_FORBIDDEN_TARGETS
        if status not in {"planned", "assigned"}:
            assert result is None


def test_next_auto_pickup_status_respects_advance_to_running_policy():
    no_running = AutoPickupPolicy(enabled=True, advance_to_running=False)
    yes_running = AutoPickupPolicy(enabled=True, advance_to_running=True)
    assert next_auto_pickup_status("assigned", policy=no_running) is None
    assert next_auto_pickup_status("assigned", policy=yes_running) == "running"
    # planned->assigned is allowed regardless of the running opt-in.
    assert next_auto_pickup_status("planned", policy=no_running) == "assigned"


# ---------------------------------------------------------------------------
# Repository orchestration tests
# ---------------------------------------------------------------------------


def test_disabled_by_default_is_a_no_op(tmp_path):
    repository = initialized_repository(tmp_path)
    work_item_id = repository.create_agent_work_item(
        title="Draft research brief",
        owner_agent_id="research-agent",
        status="planned",
        summary="Plan the research stage before any work begins.",
    )

    result = repository.auto_pickup_agent_work_items(policy=AutoPickupPolicy())

    assert result == []
    assert repository.get_agent_work_item(work_item_id)["status"] == "planned"
    assert repository.list_audit_events() == []


def test_enabled_advances_planned_to_assigned_only(tmp_path):
    repository = initialized_repository(tmp_path)
    work_item_id = repository.create_agent_work_item(
        title="Draft research brief",
        owner_agent_id="research-agent",
        status="planned",
        summary="Plan the research stage before any work begins.",
    )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True),
    )

    assert [item["id"] for item in result] == [work_item_id]
    assert result[0]["from_status"] == "planned"
    assert result[0]["status"] == "assigned"
    assert repository.get_agent_work_item(work_item_id)["status"] == "assigned"

    events = repository.list_audit_events()
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "agent_work_item_auto_assigned"
    assert event["status"] == "assigned"
    assert event["actor_agent_id"] == "research-agent"
    assert event["source_table"] == "agent_work_items"
    assert event["source_id"] == work_item_id
    assert event["payload"] == {
        "from_status": "planned",
        "to_status": "assigned",
        "policy": "auto_pickup",
        "external_execution": False,
    }


def test_enabled_advances_assigned_to_running_when_opted_in(tmp_path):
    repository = initialized_repository(tmp_path)
    work_item_id = repository.create_agent_work_item(
        title="Run research brief",
        owner_agent_id="research-agent",
        status="assigned",
        summary="The research stage is assigned and ready to start.",
    )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True, advance_to_running=True),
    )

    assert [item["status"] for item in result] == ["running"]
    assert repository.get_agent_work_item(work_item_id)["status"] == "running"

    events = repository.list_audit_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "agent_work_item_auto_started"
    assert events[0]["status"] == "running"
    assert events[0]["payload"]["to_status"] == "running"
    assert events[0]["payload"]["external_execution"] is False


def test_assigned_item_untouched_without_advance_to_running(tmp_path):
    repository = initialized_repository(tmp_path)
    work_item_id = repository.create_agent_work_item(
        title="Assigned research brief",
        owner_agent_id="research-agent",
        status="assigned",
        summary="The research stage is assigned but running must stay manual.",
    )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True, advance_to_running=False),
    )

    assert result == []
    assert repository.get_agent_work_item(work_item_id)["status"] == "assigned"
    assert repository.list_audit_events() == []


def test_skips_needs_review_blocked_and_founder_required(tmp_path):
    repository = initialized_repository(tmp_path)
    blocked_id = repository.create_agent_work_item(
        title="Blocked acceptance",
        owner_agent_id="qa-critic",
        status="blocked",
        summary="Cannot proceed until evidence is provided.",
        blocked_reason="Missing test evidence.",
        blocked_owner="Test Automation Agent",
    )
    review_id = repository.create_agent_work_item(
        title="Needs review brief",
        owner_agent_id="qa-critic",
        status="needs_review",
        summary="This item awaits founder review.",
    )
    founder_id = repository.create_agent_work_item(
        title="Planned but founder-flagged",
        owner_agent_id="qa-critic",
        status="planned",
        summary="Planned work that the founder must touch first.",
        founder_action_required=True,
    )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True, advance_to_running=True),
    )

    assert result == []
    assert repository.get_agent_work_item(blocked_id)["status"] == "blocked"
    assert repository.get_agent_work_item(review_id)["status"] == "needs_review"
    assert repository.get_agent_work_item(founder_id)["status"] == "planned"
    assert repository.list_audit_events() == []


def test_respects_allowlist(tmp_path):
    repository = initialized_repository(tmp_path)
    allowed_id = repository.create_agent_work_item(
        title="Research planned",
        owner_agent_id="research-agent",
        status="planned",
        summary="Owned by an allowlisted agent.",
    )
    blocked_owner_id = repository.create_agent_work_item(
        title="QA planned",
        owner_agent_id="qa-critic",
        status="planned",
        summary="Owned by an agent that is not on the allowlist.",
    )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(
            enabled=True,
            allowed_agent_ids=frozenset({"research-agent"}),
        ),
    )

    assert [item["id"] for item in result] == [allowed_id]
    assert repository.get_agent_work_item(allowed_id)["status"] == "assigned"
    assert repository.get_agent_work_item(blocked_owner_id)["status"] == "planned"


def test_respects_max_items(tmp_path):
    repository = initialized_repository(tmp_path)
    for index in range(3):
        repository.create_agent_work_item(
            title=f"Planned brief {index}",
            owner_agent_id="research-agent",
            status="planned",
            summary=f"Planned research work number {index}.",
        )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True, max_items=2),
    )

    assert len(result) == 2
    assigned = repository.list_agent_work_items(status="assigned")
    planned = repository.list_agent_work_items(status="planned")
    assert len(assigned) == 2
    assert len(planned) == 1
    assert len(repository.list_audit_events()) == 2


def test_never_reaches_terminal_states(tmp_path):
    repository = initialized_repository(tmp_path)
    # Drive an item up to needs_review, which auto-pickup must never touch.
    work_item_id = repository.create_agent_work_item(
        title="Approval candidate",
        owner_agent_id="qa-critic",
        status="assigned",
        summary="An item that has reached the founder review gate.",
    )
    repository.update_agent_work_item(work_item_id, status="needs_review")

    # Confirm the underlying transition guard refuses approval without founder
    # confirmation (auto-pickup always passes founder_confirmed=False).
    with pytest.raises(ValueError, match="Founder confirmation"):
        repository.update_agent_work_item(work_item_id, status="approved")

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True, advance_to_running=True),
    )

    assert result == []
    item = repository.get_agent_work_item(work_item_id)
    assert item["status"] == "needs_review"
    assert item["status"] not in {"approved", "rejected", "done"}


def test_filters_by_owner_agent_scope(tmp_path):
    repository = initialized_repository(tmp_path)
    research_id = repository.create_agent_work_item(
        title="Research planned",
        owner_agent_id="research-agent",
        status="planned",
        summary="Research work that should be advanced.",
    )
    repository.create_agent_work_item(
        title="QA planned",
        owner_agent_id="qa-critic",
        status="planned",
        summary="QA work outside the requested scope.",
    )

    result = repository.auto_pickup_agent_work_items(
        policy=AutoPickupPolicy(enabled=True),
        owner_agent_id="research-agent",
    )

    assert [item["id"] for item in result] == [research_id]
    assert repository.get_agent_work_item(research_id)["status"] == "assigned"


def test_audit_payloads_are_secret_safe(tmp_path):
    repository = initialized_repository(tmp_path)
    repository.create_agent_work_item(
        title="Research planned",
        owner_agent_id="research-agent",
        status="planned",
        summary="Plain summary with no secrets.",
    )

    repository.auto_pickup_agent_work_items(policy=AutoPickupPolicy(enabled=True))

    events = repository.list_audit_events()
    assert events
    serialized = {
        f"event_{index}": json.dumps(event["payload"], sort_keys=True) + event["summary"]
        for index, event in enumerate(events)
    }
    assert secret_violations(serialized) == []
