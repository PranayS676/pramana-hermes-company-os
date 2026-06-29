from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.database import connect, initialize_database
from hermes_company_os.main import create_app
from hermes_company_os.observability import (
    RUN_OBSERVABILITY_SCHEMA,
    run_observability_markdown,
    run_observability_package,
)
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def _seed_project(repository: CompanyRepository, name: str = "Atlas Brief") -> str:
    return repository.create_structured_project(
        name=name,
        founder_idea="AI diligence workspace.",
    )


def _seed_plain_run(
    repository: CompanyRepository,
    *,
    agent_id: str,
    status: str,
    created_at: str,
    completed_at: str | None,
) -> str:
    """Insert a row into the legacy ``runs`` table with explicit timestamps."""
    run_id = repository.create_run(agent_id=agent_id, run_type="agent", prompt="Do work.")
    with connect(repository.database_path) as connection:
        connection.execute(
            "UPDATE runs SET status = ?, created_at = ?, completed_at = ? WHERE id = ?",
            (status, created_at, completed_at, run_id),
        )
    return run_id


def test_empty_repo_returns_zeroed_package(tmp_path):
    repository = initialized_repository(tmp_path)

    package = run_observability_package(repository)

    runs = package["runs"]
    assert package["schema"] == RUN_OBSERVABILITY_SCHEMA
    assert package["scope"]["project_id"] is None
    assert runs["total"] == 0
    assert runs["succeeded"] == 0
    assert runs["failed"] == 0
    assert runs["running"] == 0
    assert runs["success_rate"] is None
    assert runs["average_latency_seconds"] is None
    assert runs["runs_by_agent"] == {}
    assert runs["runs_by_source"] == {"agent": 0, "generation": 0, "codex": 0}
    assert runs["retry_count"] == 0
    assert package["blocked_work"]["blocked"] == 0
    # No runs and no review records exist, but a fresh DB may seed default
    # founder decisions; the package must mirror the repository, not assume zero.
    seeded_open = [
        decision
        for decision in repository.list_founder_decisions(limit=200)
        if decision["status"] not in {"approved", "rejected", "deferred"}
    ]
    assert package["open_founder_decisions"]["total"] == len(seeded_open)
    assert package["open_review_findings"]["total"] == 0


def test_runs_by_agent_aggregation_and_success_failure_counts(tmp_path):
    repository = initialized_repository(tmp_path)
    agents = [agent["id"] for agent in repository.list_agents()]
    first_agent, second_agent = agents[0], agents[1]
    base = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

    _seed_plain_run(
        repository,
        agent_id=first_agent,
        status="completed",
        created_at=base.isoformat(),
        completed_at=(base + timedelta(seconds=10)).isoformat(),
    )
    _seed_plain_run(
        repository,
        agent_id=first_agent,
        status="failed",
        created_at=base.isoformat(),
        completed_at=(base + timedelta(seconds=30)).isoformat(),
    )
    _seed_plain_run(
        repository,
        agent_id=second_agent,
        status="running",
        created_at=base.isoformat(),
        completed_at=None,
    )

    package = run_observability_package(repository)
    runs = package["runs"]

    assert runs["total"] == 3
    assert runs["succeeded"] == 1
    assert runs["failed"] == 1
    assert runs["running"] == 1
    assert runs["success_rate"] == pytest.approx(1 / 3)
    assert runs["runs_by_agent"][first_agent] == 2
    assert runs["runs_by_agent"][second_agent] == 1
    assert runs["runs_by_source"]["agent"] == 3


def test_average_latency_computed_with_tolerance(tmp_path):
    repository = initialized_repository(tmp_path)
    agent_id = repository.list_agents()[0]["id"]
    base = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

    _seed_plain_run(
        repository,
        agent_id=agent_id,
        status="completed",
        created_at=base.isoformat(),
        completed_at=(base + timedelta(seconds=10)).isoformat(),
    )
    _seed_plain_run(
        repository,
        agent_id=agent_id,
        status="failed",
        created_at=base.isoformat(),
        completed_at=(base + timedelta(seconds=30)).isoformat(),
    )

    package = run_observability_package(repository)

    # Mean of 10s and 30s == 20s.
    assert package["runs"]["average_latency_seconds"] == pytest.approx(20.0, abs=0.01)


def test_average_latency_null_when_nothing_completed(tmp_path):
    repository = initialized_repository(tmp_path)
    agent_id = repository.list_agents()[0]["id"]
    base = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

    _seed_plain_run(
        repository,
        agent_id=agent_id,
        status="running",
        created_at=base.isoformat(),
        completed_at=None,
    )

    package = run_observability_package(repository)

    assert package["runs"]["average_latency_seconds"] is None


def test_retry_proxy_increments_on_rerun(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = _seed_project(repository)

    # Two generation runs for the same stage == one re-run beyond the first.
    repository.create_generation_run(project_id, "research", "wizard")
    repository.create_generation_run(project_id, "research", "wizard")
    # A single run for another stage contributes no retries.
    repository.create_generation_run(project_id, "prd", "wizard")

    package = run_observability_package(repository, project_id)

    assert package["runs"]["retry_count"] == 1


def test_open_decisions_exclude_resolved(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = _seed_project(repository)

    open_id = repository.create_founder_decision(
        title="Approve launch tier",
        urgency="urgent",
        source="observability-test",
        owner_agent_id="product-manager",
        project_id=project_id,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if launch is blocked.",
        context="Founder needs to confirm the launch tier.",
        requires_founder_approval=True,
    )
    resolved_id = repository.create_founder_decision(
        title="Confirm scope cut",
        urgency="normal",
        source="observability-test",
        owner_agent_id="product-manager",
        project_id=project_id,
        slack_channel="#decisions",
        telegram_policy="No Telegram.",
        context="Scope cut already decided.",
    )
    repository.update_founder_decision(
        resolved_id,
        status="approved",
        decision="Scope cut approved.",
        founder_confirmed=True,
    )

    package = run_observability_package(repository, project_id)
    decisions = package["open_founder_decisions"]

    assert decisions["total"] == 1
    assert decisions["urgent"] == 1
    assert open_id in decisions["ids"]
    assert resolved_id not in decisions["ids"]


def test_open_findings_count_non_approved_verdicts(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = _seed_project(repository)

    repository.create_project_review_record(
        source_key="obs:approved",
        project_id=project_id,
        review_batch_id="batch-1",
        reviewer_agent_id="qa-critic",
        reviewer_name="QA Critic",
        reviewer_role="Risk review",
        verdict="approved",
        summary="No blockers.",
        artifact_ids=["artifact-1"],
        checks=[{"id": "c1", "status": "passed", "detail": "ok"}],
        findings=[{"severity": "info", "title": "All good", "detail": "ok"}],
    )
    repository.create_project_review_record(
        source_key="obs:needs",
        project_id=project_id,
        review_batch_id="batch-1",
        reviewer_agent_id="engineering-manager",
        reviewer_name="Engineering Manager",
        reviewer_role="Feasibility review",
        verdict="needs_revision",
        summary="Two gaps to close.",
        artifact_ids=["artifact-1"],
        checks=[{"id": "c2", "status": "failed", "detail": "gap"}],
        findings=[
            {"severity": "high", "title": "Missing rollback", "detail": "Add rollback."},
            {"severity": "medium", "title": "No metric", "detail": "Add metric."},
        ],
    )

    package = run_observability_package(repository, project_id)
    findings = package["open_review_findings"]

    # Only the non-approved record's findings count.
    assert findings["total"] == 2
    assert findings["records"] == 1


def test_blocked_work_mirrors_queue_summary(tmp_path):
    repository = initialized_repository(tmp_path)
    repository.create_agent_work_item(
        title="Resolve blocked handoff",
        owner_agent_id="product-manager",
        summary="A blocked item that needs founder attention.",
        status="blocked",
        blocked_reason="Waiting on founder approval.",
        founder_action_required=True,
    )

    package = run_observability_package(repository)
    summary = repository.agent_work_queue_summary()

    assert package["blocked_work"]["blocked"] == summary["blocked"]
    assert package["blocked_work"]["blocked"] == 1
    assert package["blocked_work"]["needs_review"] == summary["needs_review"]
    assert package["blocked_work"]["founder_required"] == summary["founder_required"]


def test_project_scope_filters_to_one_project(tmp_path):
    repository = initialized_repository(tmp_path)
    project_a = _seed_project(repository, name="Atlas Brief")
    project_b = _seed_project(repository, name="Beacon Brief")

    repository.create_generation_run(project_a, "research", "wizard")
    repository.create_generation_run(project_b, "research", "wizard")
    repository.create_generation_run(project_b, "prd", "wizard")

    package_a = run_observability_package(repository, project_a)
    package_b = run_observability_package(repository, project_b)

    assert package_a["scope"]["project_id"] == project_a
    assert package_a["runs"]["runs_by_source"]["generation"] == 1
    assert package_b["runs"]["runs_by_source"]["generation"] == 2


def test_unknown_project_raises_value_error(tmp_path):
    repository = initialized_repository(tmp_path)

    with pytest.raises(ValueError):
        run_observability_package(repository, "does-not-exist")


def test_package_is_no_secret(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = _seed_project(repository)
    repository.create_generation_run(project_id, "research", "wizard")

    package = run_observability_package(repository, project_id)
    markdown = run_observability_markdown(package)

    assert secret_violations(
        {
            "package": json.dumps(package, sort_keys=True),
            "markdown": markdown,
        }
    ) == []


def test_company_observability_route_success(tmp_path):
    app, client = app_and_client(tmp_path)

    response = client.get("/observability.json")
    payload = response.json()

    assert response.status_code == 200
    assert payload["schema"] == RUN_OBSERVABILITY_SCHEMA
    assert payload["scope"]["project_id"] is None
    assert "runs" in payload
    assert secret_violations({"payload": json.dumps(payload, sort_keys=True)}) == []


def test_scoped_observability_route_success(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    response = client.get(f"/projects/{project_id}/observability.json")
    payload = response.json()

    assert response.status_code == 200
    assert payload["scope"]["project_id"] == project_id


def test_scoped_observability_route_missing_project_404(tmp_path):
    app, client = app_and_client(tmp_path)

    response = client.get("/projects/does-not-exist/observability.json")

    assert response.status_code == 404


def test_observability_markdown_route_is_plain_text(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = _seed_project(app.state.repository)

    response = client.get(f"/projects/{project_id}/observability.md")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Run Observability" in response.text
    assert secret_violations({"markdown": response.text}) == []


def test_scoped_markdown_route_missing_project_404(tmp_path):
    app, client = app_and_client(tmp_path)

    response = client.get("/projects/does-not-exist/observability.md")

    assert response.status_code == 404


def test_create_run_table_exists(tmp_path):
    """Guard: legacy runs table is reachable for the latency seed helper."""
    repository = initialized_repository(tmp_path)
    with connect(repository.database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(runs)")
        }
    assert {"created_at", "completed_at", "status", "agent_id"}.issubset(columns)
    # sqlite3 import kept meaningful for static readers.
    assert sqlite3.sqlite_version
