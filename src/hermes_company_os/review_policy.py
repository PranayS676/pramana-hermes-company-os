"""Cross-agent review policy (Milestone 6).

Defines, per gated wizard stage, which reviewer agents must have a recorded
review before that stage may be approved, and exposes read-only helpers used by
the stage-approval enforcement path and the review-requirements API.

The policy is data-driven (``STAGE_REVIEW_POLICIES``) so new gated stages can be
added without touching the enforcement logic. Required reviewer ids reference
``multi_agent_review.REVIEWERS``.

Enforcement itself is gated behind the ``HERMES_REVIEW_ENFORCEMENT_ENABLED``
settings flag (default off) so the public demo and existing happy-path tests
keep their current behaviour. This module only describes/evaluates the policy;
the repository decides whether to enforce it.
"""

from __future__ import annotations

from typing import Any

from hermes_company_os.multi_agent_review import REVIEWERS

# Reviewer verdicts that block a gated stage from being approved.
BLOCKING_VERDICTS: frozenset[str] = frozenset({"blocked", "needs_revision"})

# Per-stage required reviewer agent ids. Keep this data-driven and easy to
# extend: add a stage id mapped to the reviewer agent ids it gates on.
# Roadmap M6: QA Critic + Test Automation are required before ``acceptance``.
STAGE_REVIEW_POLICIES: dict[str, tuple[str, ...]] = {
    "acceptance": ("qa-critic", "test-automation-agent"),
}

_REVIEWER_BY_ID: dict[str, dict[str, str]] = {
    reviewer["agent_id"]: dict(reviewer) for reviewer in REVIEWERS
}


def required_reviewer_ids(stage_id: str) -> tuple[str, ...]:
    """Return the required reviewer agent ids for ``stage_id`` (empty if ungated)."""

    return STAGE_REVIEW_POLICIES.get(stage_id, ())


def required_reviewers(stage_id: str) -> list[dict[str, str]]:
    """Return the reviewer descriptors required before ``stage_id`` is approved."""

    reviewers: list[dict[str, str]] = []
    for agent_id in required_reviewer_ids(stage_id):
        reviewer = _REVIEWER_BY_ID.get(agent_id)
        if reviewer is None:
            # Policy references an unknown reviewer; surface it explicitly rather
            # than silently dropping the requirement.
            reviewer = {
                "agent_id": agent_id,
                "name": agent_id,
                "role": "Unknown reviewer referenced by review policy.",
            }
        reviewers.append(dict(reviewer))
    return reviewers


def stage_is_gated(stage_id: str) -> bool:
    """Return ``True`` when ``stage_id`` has any required reviewers."""

    return bool(required_reviewer_ids(stage_id))


def stage_review_requirements(
    repository: Any,
    project_id: str,
    stage_id: str,
) -> dict[str, Any]:
    """Describe the review requirements for ``stage_id`` (read-only).

    Returns the required reviewers, which exist, which are missing, any blocking
    reviewer verdicts, and whether approval is currently allowed by the policy.
    Does not consider the enforcement flag — callers decide whether to enforce.
    """

    required = required_reviewers(stage_id)
    required_ids = [reviewer["agent_id"] for reviewer in required]
    latest_by_reviewer = _latest_reviews_by_reviewer(repository, project_id, required_ids)

    present_ids: list[str] = []
    missing_ids: list[str] = []
    blocking: list[dict[str, str]] = []
    for agent_id in required_ids:
        record = latest_by_reviewer.get(agent_id)
        if record is None:
            missing_ids.append(agent_id)
            continue
        present_ids.append(agent_id)
        if record["verdict"] in BLOCKING_VERDICTS:
            blocking.append(
                {
                    "reviewer_agent_id": agent_id,
                    "verdict": record["verdict"],
                }
            )

    approval_allowed = not missing_ids and not blocking
    return {
        "project_id": project_id,
        "stage_id": stage_id,
        "gated": bool(required_ids),
        "required_reviewers": required,
        "required_reviewer_ids": required_ids,
        "present_reviewer_ids": present_ids,
        "missing_reviewer_ids": missing_ids,
        "blocking_reviewers": blocking,
        "approval_allowed": approval_allowed,
    }


def review_policy_blocker(requirements: dict[str, Any]) -> str:
    """Return a clear blocker message for unmet review requirements (empty if met)."""

    if not requirements["gated"] or requirements["approval_allowed"]:
        return ""
    stage_id = requirements["stage_id"]
    parts: list[str] = []
    missing = requirements["missing_reviewer_ids"]
    if missing:
        parts.append("missing required reviews from: " + ", ".join(missing))
    blocking = requirements["blocking_reviewers"]
    if blocking:
        parts.append(
            "blocking reviewer verdicts from: "
            + ", ".join(
                f"{item['reviewer_agent_id']} ({item['verdict']})" for item in blocking
            )
        )
    detail = "; ".join(parts)
    return (
        f"Cannot approve stage '{stage_id}' until required cross-agent reviews pass: "
        f"{detail}."
    )


def _latest_reviews_by_reviewer(
    repository: Any,
    project_id: str,
    reviewer_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not reviewer_ids:
        return {}
    wanted = set(reviewer_ids)
    latest: dict[str, dict[str, Any]] = {}
    # Records come ordered newest-first per reviewer; keep the first seen.
    for record in repository.list_project_review_records(project_id, limit=100):
        agent_id = record["reviewer_agent_id"]
        if agent_id in wanted and agent_id not in latest:
            latest[agent_id] = record
    return latest
