"""Read-only run-observability layer (M8).

Aggregates EXISTING run and audit records into founder-visible metrics. This
module performs no live behavior, defines no schema, and adds no repository
methods or env flags. Every metric is *derived* from records the repository
already exposes; when a denominator is zero the metric is emitted as ``null``
(``None``) rather than fabricated.

Run sources aggregated here:

* ``agent`` — rows in the legacy ``runs`` table (``list_runs``). These carry an
  explicit ``agent_id`` and are the only source that contributes to
  ``runs_by_agent``. They are company-wide and are only counted when the package
  is company-scoped (``project_id is None``).
* ``generation`` — product-wizard ``generation_runs`` (``list_generation_runs``).
* ``codex`` — ``codex_execution_runs`` (``list_codex_execution_runs``).

``retry_count`` is a DERIVED re-run proxy. No schema column records retries, so
it is computed as the number of *extra* generation runs per (project, stage)
beyond the first — i.e. ``max(0, runs_for_stage - 1)`` summed across stages. It
is an approximation of how often a stage had to be regenerated, not an exact
retry counter.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.secret_guard import assert_no_secret_values

RUN_OBSERVABILITY_SCHEMA = "run_observability_package_v1"

# High explicit limits so aggregation is not silently capped by per-method
# defaults. The repository caps these internally (generation/codex at 100), so
# these are the largest honest windows the read methods will return.
_RUN_LIMIT = 100
_GENERATION_LIMIT = 100
_CODEX_LIMIT = 100
_DECISION_LIMIT = 200
_REVIEW_LIMIT = 100

# Status normalization across the three run tables. ``runs`` uses
# completed/failed; generation uses succeeded/failed; codex uses
# queued/blocked/completed/failed/cancelled.
_SUCCEEDED_STATUSES = {"completed", "succeeded"}
_FAILED_STATUSES = {"failed", "cancelled"}


def run_observability_package(
    repository: RepositoryProtocol,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Aggregate run + audit records into a founder-visible metrics package.

    Company-wide when ``project_id`` is ``None`` (iterates ``list_projects()``);
    scoped to a single project otherwise. Raises ``ValueError`` for an unknown
    project, mirroring ``multi_agent_review_package``.
    """
    if project_id is None:
        projects = repository.list_projects()
        project_ids = [project["id"] for project in projects]
        include_legacy_runs = True
        scope_name = ""
    else:
        project = repository.get_project(project_id)
        if project is None:
            raise ValueError(f"Unknown project: {project_id}")
        project_ids = [project_id]
        include_legacy_runs = False
        scope_name = project["name"]

    runs = _runs_metrics(repository, project_ids, include_legacy_runs)
    blocked_work = _blocked_work_metrics(repository)
    open_decisions = _open_founder_decisions(repository, project_id)
    open_findings = _open_review_findings(repository, project_ids)

    payload: dict[str, Any] = {
        "schema": RUN_OBSERVABILITY_SCHEMA,
        "scope": {
            "project_id": project_id,
            "project_name": scope_name,
            "company_wide": project_id is None,
            "project_count": len(project_ids),
        },
        "runs": runs,
        "blocked_work": blocked_work,
        "open_founder_decisions": open_decisions,
        "open_review_findings": open_findings,
        "notes": {
            "retry_count": (
                "Derived re-run proxy: extra generation runs per (project, stage) "
                "beyond the first. No schema column records retries."
            ),
            "runs_by_agent": (
                "Aggregated from the legacy runs table only; generation and codex "
                "runs do not carry an explicit agent id."
            ),
            "null_metrics": "Rates and averages are null when the denominator is zero.",
        },
    }
    assert_no_secret_values({"run_observability_package": json.dumps(payload, sort_keys=True)})
    return payload


def run_observability_markdown(package: Mapping[str, Any]) -> str:
    runs = package["runs"]
    scope = package["scope"]
    blocked = package["blocked_work"]
    decisions = package["open_founder_decisions"]
    findings = package["open_review_findings"]
    scope_label = "Company-wide" if scope["company_wide"] else scope["project_name"]
    lines = [
        f"# Run Observability: {scope_label}",
        "",
        f"- Schema: `{package['schema']}`",
        f"- Scope: `{scope['project_id'] or 'company'}`",
        f"- Projects in scope: {scope['project_count']}",
        "",
        "## Runs",
        "",
        f"- Total: {runs['total']}",
        f"- Succeeded: {runs['succeeded']}",
        f"- Failed: {runs['failed']}",
        f"- Running: {runs['running']}",
        f"- Success rate: {_format_ratio(runs['success_rate'])}",
        f"- Average latency (s): {_format_number(runs['average_latency_seconds'])}",
        f"- Retry proxy: {runs['retry_count']}",
        "",
        "### Runs by source",
        "",
    ]
    for source, count in runs["runs_by_source"].items():
        lines.append(f"- `{source}`: {count}")
    lines.extend(["", "### Runs by agent", ""])
    if runs["runs_by_agent"]:
        for agent_id, count in sorted(runs["runs_by_agent"].items()):
            lines.append(f"- `{agent_id}`: {count}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Blocked Work",
            "",
            f"- Blocked: {blocked['blocked']}",
            f"- Needs review: {blocked['needs_review']}",
            f"- Founder required: {blocked['founder_required']}",
            f"- Open: {blocked['open']}",
            "",
            "## Open Founder Decisions",
            "",
            f"- Open: {decisions['total']}",
            f"- Urgent: {decisions['urgent']}",
            "",
            "## Open Review Findings",
            "",
            f"- Findings: {findings['total']}",
            f"- Non-approved records: {findings['records']}",
            "",
        ]
    )
    return "\n".join(lines)


def _runs_metrics(
    repository: RepositoryProtocol,
    project_ids: list[str],
    include_legacy_runs: bool,
) -> dict[str, Any]:
    total = 0
    succeeded = 0
    failed = 0
    running = 0
    latencies: list[float] = []
    runs_by_agent: Counter[str] = Counter()
    runs_by_source = {"agent": 0, "generation": 0, "codex": 0}
    retry_count = 0

    def record(status: str, created_at: str | None, completed_at: str | None) -> None:
        nonlocal total, succeeded, failed, running
        total += 1
        normalized = (status or "").strip().lower()
        if normalized in _SUCCEEDED_STATUSES:
            succeeded += 1
        elif normalized in _FAILED_STATUSES:
            failed += 1
        else:
            running += 1
        latency = _latency_seconds(created_at, completed_at)
        if latency is not None:
            latencies.append(latency)

    if include_legacy_runs:
        for run in repository.list_runs(limit=_RUN_LIMIT):
            runs_by_source["agent"] += 1
            agent_id = run.get("agent_id")
            if agent_id:
                runs_by_agent[agent_id] += 1
            record(run.get("status", ""), run.get("created_at"), run.get("completed_at"))

    for current_project_id in project_ids:
        generation_runs = repository.list_generation_runs(
            current_project_id,
            limit=_GENERATION_LIMIT,
        )
        runs_per_stage: Counter[str] = Counter()
        for run in generation_runs:
            runs_by_source["generation"] += 1
            runs_per_stage[run.get("stage_id", "")] += 1
            record(run.get("status", ""), run.get("created_at"), run.get("completed_at"))
        for stage_runs in runs_per_stage.values():
            retry_count += max(0, stage_runs - 1)

        for run in repository.list_codex_execution_runs(
            current_project_id,
            limit=_CODEX_LIMIT,
        ):
            runs_by_source["codex"] += 1
            record(run.get("status", ""), run.get("created_at"), run.get("completed_at"))

    success_rate = (succeeded / total) if total else None
    average_latency = (sum(latencies) / len(latencies)) if latencies else None
    return {
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "running": running,
        "success_rate": success_rate,
        "average_latency_seconds": average_latency,
        "retry_count": retry_count,
        "runs_by_agent": dict(runs_by_agent),
        "runs_by_source": runs_by_source,
    }


def _blocked_work_metrics(repository: RepositoryProtocol) -> dict[str, Any]:
    summary = repository.agent_work_queue_summary()
    return {
        "total": summary.get("total", 0),
        "open": summary.get("open", 0),
        "blocked": summary.get("blocked", 0),
        "needs_review": summary.get("needs_review", 0),
        "founder_required": summary.get("founder_required", 0),
    }


def _open_founder_decisions(
    repository: RepositoryProtocol,
    project_id: str | None,
) -> dict[str, Any]:
    decisions = repository.list_founder_decisions(
        limit=_DECISION_LIMIT,
        project_id=project_id or "",
    )
    open_decisions = [
        decision
        for decision in decisions
        if decision["status"] not in RESOLVED_DECISION_STATUSES
    ]
    urgent = [decision for decision in open_decisions if decision.get("urgency") == "urgent"]
    return {
        "total": len(open_decisions),
        "urgent": len(urgent),
        "ids": [decision["id"] for decision in open_decisions],
    }


def _open_review_findings(
    repository: RepositoryProtocol,
    project_ids: list[str],
) -> dict[str, Any]:
    finding_total = 0
    record_total = 0
    for current_project_id in project_ids:
        for record in repository.list_project_review_records(
            current_project_id,
            limit=_REVIEW_LIMIT,
        ):
            if record.get("verdict") == "approved":
                continue
            record_total += 1
            finding_total += len(record.get("findings", []))
    return {
        "total": finding_total,
        "records": record_total,
    }


def _latency_seconds(created_at: str | None, completed_at: str | None) -> float | None:
    if not created_at or not completed_at:
        return None
    try:
        start = datetime.fromisoformat(created_at)
        end = datetime.fromisoformat(completed_at)
    except (TypeError, ValueError):
        return None
    delta = (end - start).total_seconds()
    return delta if delta >= 0 else None


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _format_number(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"
