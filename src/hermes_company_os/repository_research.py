from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from hermes_company_os.database import connect
from hermes_company_os.repository_support import decode_research_package, utc_now
from hermes_company_os.research_packages import (
    build_research_package,
    normalize_research_status,
)
from hermes_company_os.secret_guard import assert_no_secret_values


class ResearchPackagesMixin:
    """CRUD for UI/UX research packages (M1A).

    Mirrors the style of :class:`GenerationExecutionMixin`: each write validates
    references, normalizes the payload through :func:`build_research_package`,
    runs the secret guard, and records an audit event when project-scoped.
    """

    def create_research_package(
        self,
        *,
        title: str,
        research_thread: str,
        research_question: str,
        method: str,
        owner_agent_id: str = "ui-ux-research-agent",
        project_id: str = "",
        target_workflow: str = "",
        summary: str = "",
        findings: Sequence[Mapping[str, Any]] = (),
        recommendations: Sequence[Mapping[str, Any]] = (),
        founder_decisions_needed: Sequence[Mapping[str, Any]] = (),
        status: str = "active",
        source_key: str = "",
    ) -> str:
        normalized_project_id = project_id.strip()
        if normalized_project_id and self.get_project(normalized_project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {normalized_project_id}")
        # ``owner_agent_id`` is a label, not an FK: ``ui-ux-research-agent`` is a
        # docs-only role and is not seeded as a live agent yet (see the M1A
        # implementation plan). ``build_research_package`` validates it is non-empty.
        package = build_research_package(
            title=title,
            research_thread=research_thread,
            research_question=research_question,
            method=method,
            owner_agent_id=owner_agent_id,
            target_workflow=target_workflow,
            summary=summary,
            findings=findings,
            recommendations=recommendations,
            founder_decisions_needed=founder_decisions_needed,
            status=status,
        )
        findings_json = json.dumps(package["findings"], sort_keys=True)
        recommendations_json = json.dumps(package["recommendations"], sort_keys=True)
        decisions_json = json.dumps(package["founder_decisions_needed"], sort_keys=True)
        normalized_source_key = source_key.strip() or (
            f"research_package:{normalized_project_id or 'company'}:{uuid4().hex[:12]}"
        )
        assert_no_secret_values(
            {
                "research_package_source_key": normalized_source_key,
                "research_package_findings": findings_json,
                "research_package_recommendations": recommendations_json,
                "research_package_founder_decisions": decisions_json,
            }
        )
        package_id = f"research-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO research_packages (
                    id, source_key, project_id, title, research_thread,
                    research_question, method, owner_agent_id, target_workflow,
                    summary, status, findings_json, recommendations_json,
                    founder_decisions_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    normalized_source_key,
                    normalized_project_id or None,
                    package["title"],
                    package["research_thread"],
                    package["research_question"],
                    package["method"],
                    package["owner_agent_id"],
                    package["target_workflow"],
                    package["summary"],
                    package["status"],
                    findings_json,
                    recommendations_json,
                    decisions_json,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT id FROM research_packages WHERE source_key = ?",
                (normalized_source_key,),
            ).fetchone()
            if row is not None and cursor.rowcount > 0 and normalized_project_id:
                self._insert_audit_event(
                    connection,
                    project_id=normalized_project_id,
                    event_type="research_package_created",
                    status=package["status"],
                    actor_agent_id="chief-of-staff",
                    source_table="research_packages",
                    source_id=row["id"],
                    summary=f"UI/UX research package captured: {package['title']}",
                    payload={
                        "method": package["method"],
                        "status": package["status"],
                        "findings": len(package["findings"]),
                        "recommendations": len(package["recommendations"]),
                    },
                )
        if row is None:
            raise sqlite3.IntegrityError("Research package was not persisted.")
        return row["id"]

    def get_research_package(self, package_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM research_packages WHERE id = ?",
                (package_id,),
            ).fetchone()
        return decode_research_package(row) if row else None

    def list_research_packages(
        self,
        project_id: str = "",
        *,
        include_company_wide: bool = False,
        include_retired: bool = False,
        method: str = "",
        limit: int = 50,
    ) -> list[dict]:
        normalized_project_id = project_id.strip()
        if normalized_project_id and self.get_project(normalized_project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {normalized_project_id}")
        filters: list[str] = []
        parameters: list[str | int] = []
        if normalized_project_id:
            if include_company_wide:
                filters.append("(project_id = ? OR project_id IS NULL)")
            else:
                filters.append("project_id = ?")
            parameters.append(normalized_project_id)
        elif not include_company_wide:
            filters.append("project_id IS NULL")
        if not include_retired:
            filters.append("status != 'retired'")
        if method:
            filters.append("method = ?")
            parameters.append(method)
        parameters.append(max(1, min(limit, 200)))
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM research_packages
                {where_clause}
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [decode_research_package(row) for row in rows]

    def update_research_package_status(self, package_id: str, status: str) -> None:
        current = self.get_research_package(package_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown research package: {package_id}")
        normalized_status = normalize_research_status(status)
        now = utc_now()
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE research_packages
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (normalized_status, now, package_id),
            )
        if cursor.rowcount == 0:
            raise sqlite3.IntegrityError(f"Unknown research package: {package_id}")
        if current.get("project_id"):
            event_type = (
                "research_package_retired"
                if normalized_status == "retired"
                else "research_package_updated"
            )
            with connect(self.database_path) as connection:
                self._insert_audit_event(
                    connection,
                    project_id=current["project_id"],
                    event_type=event_type,
                    status=normalized_status,
                    actor_agent_id="chief-of-staff",
                    source_table="research_packages",
                    source_id=package_id,
                    summary=f"UI/UX research package {normalized_status}: {current['title']}",
                    payload={
                        "method": current["method"],
                        "status": normalized_status,
                    },
                )

    def retire_research_package(self, package_id: str) -> None:
        self.update_research_package_status(package_id, "retired")
