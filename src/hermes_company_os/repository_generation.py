from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from hermes_company_os.database import connect
from hermes_company_os.project_memory import (
    normalize_memory_category,
    normalize_memory_confidence,
    normalize_memory_status,
)
from hermes_company_os.repository_support import (
    decode_codex_execution_run,
    decode_external_dispatch_delivery,
    decode_generation_run,
    decode_project_memory_entry,
    decode_project_review_record,
    safe_generation_error,
    utc_now,
)
from hermes_company_os.secret_guard import assert_no_secret_values


class GenerationExecutionMixin:
    def create_generation_run(
        self,
        project_id: str,
        stage_id: str,
        generation_mode: str,
        source_artifact_ids: list[str] | tuple[str, ...] = (),
        memory_ids: list[str] | tuple[str, ...] = (),
    ) -> str:
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        stage = self.get_project_wizard_stage(project_id, stage_id)
        if stage is None:
            raise sqlite3.IntegrityError(
                f"Unknown product wizard stage: {project_id}/{stage_id}"
            )
        cleaned_sources = [str(source_id).strip() for source_id in source_artifact_ids]
        cleaned_sources = [source_id for source_id in cleaned_sources if source_id]
        cleaned_memory_ids = [str(memory_id).strip() for memory_id in memory_ids]
        cleaned_memory_ids = [memory_id for memory_id in cleaned_memory_ids if memory_id]
        source_json = json.dumps(cleaned_sources, sort_keys=True)
        memory_json = json.dumps(cleaned_memory_ids, sort_keys=True)
        cleaned_mode = generation_mode.strip()
        if not cleaned_mode:
            raise ValueError("Generation mode is required.")
        assert_no_secret_values(
            {
                "generation_mode": cleaned_mode,
                "source_artifact_ids": source_json,
                "memory_ids": memory_json,
            }
        )

        run_id = f"gen-run-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO generation_runs (
                    id, project_id, stage_id, artifact_id, generation_mode, status,
                    source_artifact_ids_json, memory_ids_json, error, created_at,
                    completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    stage_id,
                    None,
                    cleaned_mode,
                    "running",
                    source_json,
                    memory_json,
                    "",
                    now,
                    None,
                ),
            )
            self._insert_audit_event(
                connection,
                project_id=project_id,
                event_type="generation_started",
                status="running",
                actor_agent_id=stage["owner_agent_id"],
                source_table="generation_runs",
                source_id=run_id,
                summary=f"Generation started for {stage_id}.",
                payload={
                    "stage_id": stage_id,
                    "generation_mode": cleaned_mode,
                    "source_artifact_ids": cleaned_sources,
                    "memory_ids": cleaned_memory_ids,
                },
            )
        return run_id

    def complete_generation_run(
        self,
        run_id: str,
        artifact_id: str,
        source_artifact_ids: list[str] | tuple[str, ...] | None = None,
        memory_ids: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        current = self.get_generation_run(run_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown generation run: {run_id}")
        values_to_check = {"generation_run_id": run_id, "artifact_id": artifact_id}
        source_json = None
        memory_json = None
        if source_artifact_ids is not None:
            cleaned_sources = [str(source_id).strip() for source_id in source_artifact_ids]
            cleaned_sources = [source_id for source_id in cleaned_sources if source_id]
            source_json = json.dumps(cleaned_sources, sort_keys=True)
            values_to_check["source_artifact_ids"] = source_json
        if memory_ids is not None:
            cleaned_memory_ids = [str(memory_id).strip() for memory_id in memory_ids]
            cleaned_memory_ids = [memory_id for memory_id in cleaned_memory_ids if memory_id]
            memory_json = json.dumps(cleaned_memory_ids, sort_keys=True)
            values_to_check["memory_ids"] = memory_json
        assert_no_secret_values(values_to_check)
        now = utc_now()
        final_source_ids = current["source_artifact_ids"]
        final_memory_ids = current["memory_ids"]
        if source_json is not None:
            final_source_ids = json.loads(source_json)
        if memory_json is not None:
            final_memory_ids = json.loads(memory_json)
        stage = self.get_project_wizard_stage(current["project_id"], current["stage_id"])
        with connect(self.database_path) as connection:
            if source_json is None and memory_json is None:
                cursor = connection.execute(
                    """
                    UPDATE generation_runs
                    SET status = ?,
                        artifact_id = ?,
                        error = '',
                        completed_at = ?
                    WHERE id = ?
                    """,
                    ("succeeded", artifact_id, now, run_id),
                )
            elif source_json is None:
                cursor = connection.execute(
                    """
                    UPDATE generation_runs
                    SET status = ?,
                        artifact_id = ?,
                        memory_ids_json = ?,
                        error = '',
                        completed_at = ?
                    WHERE id = ?
                    """,
                    ("succeeded", artifact_id, memory_json, now, run_id),
                )
            elif memory_json is None:
                cursor = connection.execute(
                    """
                    UPDATE generation_runs
                    SET status = ?,
                        artifact_id = ?,
                        source_artifact_ids_json = ?,
                        error = '',
                        completed_at = ?
                    WHERE id = ?
                    """,
                    ("succeeded", artifact_id, source_json, now, run_id),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE generation_runs
                    SET status = ?,
                        artifact_id = ?,
                        source_artifact_ids_json = ?,
                        memory_ids_json = ?,
                        error = '',
                        completed_at = ?
                    WHERE id = ?
                    """,
                    ("succeeded", artifact_id, source_json, memory_json, now, run_id),
                )
        if cursor.rowcount == 0:
            raise sqlite3.IntegrityError(f"Unknown generation run: {run_id}")
        with connect(self.database_path) as connection:
            self._insert_audit_event(
                connection,
                project_id=current["project_id"],
                event_type="generation_succeeded",
                status="succeeded",
                actor_agent_id=stage["owner_agent_id"] if stage else None,
                source_table="generation_runs",
                source_id=run_id,
                summary=f"Generation succeeded for {current['stage_id']}.",
                payload={
                    "stage_id": current["stage_id"],
                    "generation_mode": current["generation_mode"],
                    "artifact_id": artifact_id,
                    "source_artifact_ids": final_source_ids,
                    "memory_ids": final_memory_ids,
                },
            )

    def fail_generation_run(self, run_id: str, error: str) -> None:
        current = self.get_generation_run(run_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown generation run: {run_id}")
        safe_error = safe_generation_error(error)
        assert_no_secret_values(
            {
                "generation_run_id": run_id,
                "generation_error": safe_error,
            }
        )
        now = utc_now()
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE generation_runs
                SET status = ?,
                    error = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                ("failed", safe_error, now, run_id),
            )
        if cursor.rowcount == 0:
            raise sqlite3.IntegrityError(f"Unknown generation run: {run_id}")
        stage = self.get_project_wizard_stage(current["project_id"], current["stage_id"])
        with connect(self.database_path) as connection:
            self._insert_audit_event(
                connection,
                project_id=current["project_id"],
                event_type="generation_failed",
                status="failed",
                actor_agent_id=stage["owner_agent_id"] if stage else None,
                source_table="generation_runs",
                source_id=run_id,
                summary=f"Generation failed for {current['stage_id']}.",
                payload={
                    "stage_id": current["stage_id"],
                    "generation_mode": current["generation_mode"],
                    "error": safe_error,
                },
            )

    def get_generation_run(self, run_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM generation_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return decode_generation_run(row) if row else None

    def list_generation_runs(
        self,
        project_id: str,
        stage_id: str | None = None,
        artifact_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        filters = ["project_id = ?"]
        parameters: list[str | int] = [project_id]
        if stage_id:
            filters.append("stage_id = ?")
            parameters.append(stage_id)
        if artifact_id:
            filters.append("artifact_id = ?")
            parameters.append(artifact_id)
        parameters.append(max(1, min(limit, 100)))
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM generation_runs
                WHERE {" AND ".join(filters)}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [decode_generation_run(row) for row in rows]

    def latest_generation_run(
        self,
        project_id: str,
        stage_id: str,
        artifact_id: str | None = None,
    ) -> dict | None:
        runs = self.list_generation_runs(
            project_id=project_id,
            stage_id=stage_id,
            artifact_id=artifact_id,
            limit=1,
        )
        return runs[0] if runs else None

    def create_codex_execution_run(
        self,
        *,
        run_id: str,
        project_id: str,
        decision_id: str,
        package_id: str,
        status: str,
        runner_mode: str,
        external_execution_enabled: bool,
        branch_name: str,
        worktree_path: str,
        source_artifact_ids: list[str] | tuple[str, ...],
        command_preview: list[dict] | tuple[dict, ...],
        approval_snapshot: dict,
        audit: dict,
        error: str = "",
    ) -> str:
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        decision = self.get_founder_decision(decision_id)
        if decision is None:
            raise sqlite3.IntegrityError(f"Unknown founder decision: {decision_id}")
        if status not in {"queued", "blocked", "completed", "failed", "cancelled"}:
            raise ValueError(f"Unsupported Codex execution status: {status}")
        source_json = json.dumps(list(source_artifact_ids), sort_keys=True)
        command_json = json.dumps(list(command_preview), sort_keys=True)
        approval_json = json.dumps(approval_snapshot, sort_keys=True)
        audit_json = json.dumps(audit, sort_keys=True)
        assert_no_secret_values(
            {
                "codex_execution_run_id": run_id,
                "codex_execution_package_id": package_id,
                "codex_execution_status": status,
                "codex_execution_runner_mode": runner_mode,
                "codex_execution_branch_name": branch_name,
                "codex_execution_worktree_path": worktree_path,
                "codex_execution_sources": source_json,
                "codex_execution_commands": command_json,
                "codex_execution_approval": approval_json,
                "codex_execution_audit": audit_json,
                "codex_execution_error": error,
            }
        )
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO codex_execution_runs (
                    id, project_id, decision_id, package_id, status, runner_mode,
                    external_execution_enabled, branch_name, worktree_path,
                    source_artifact_ids_json, command_preview_json,
                    approval_snapshot_json, audit_json, error, created_at,
                    completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    decision_id,
                    package_id.strip(),
                    status.strip(),
                    runner_mode.strip(),
                    1 if external_execution_enabled else 0,
                    branch_name.strip(),
                    worktree_path.strip(),
                    source_json,
                    command_json,
                    approval_json,
                    audit_json,
                    error.strip(),
                    now,
                    now if status in {"completed", "failed", "cancelled"} else None,
                ),
            )
            self._insert_audit_event(
                connection,
                project_id=project_id,
                event_type="codex_execution_queued",
                status=status.strip(),
                actor_agent_id=decision["owner_agent_id"],
                source_table="codex_execution_runs",
                source_id=run_id,
                summary=f"Codex execution {status.strip()} for {package_id.strip()}.",
                payload={
                    "decision_id": decision_id,
                    "package_id": package_id.strip(),
                    "runner_mode": runner_mode.strip(),
                    "external_execution_enabled": external_execution_enabled,
                    "branch_name": branch_name.strip(),
                    "source_artifact_ids": list(source_artifact_ids),
                },
            )
        return run_id

    def get_codex_execution_run(self, run_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM codex_execution_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return decode_codex_execution_run(row) if row else None

    def list_codex_execution_runs(
        self,
        project_id: str,
        *,
        status: str = "",
        limit: int = 20,
    ) -> list[dict]:
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        filters = ["project_id = ?"]
        parameters: list[str | int] = [project_id]
        if status:
            filters.append("status = ?")
            parameters.append(status)
        parameters.append(max(1, min(limit, 100)))
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM codex_execution_runs
                WHERE {" AND ".join(filters)}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [decode_codex_execution_run(row) for row in rows]

    def latest_codex_execution_run(self, project_id: str) -> dict | None:
        runs = self.list_codex_execution_runs(project_id=project_id, limit=1)
        return runs[0] if runs else None

    def update_codex_execution_run(
        self,
        run_id: str,
        *,
        status: str,
        runner_mode: str,
        external_execution_enabled: bool,
        audit: dict,
        error: str = "",
    ) -> None:
        current = self.get_codex_execution_run(run_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown Codex execution run: {run_id}")
        if status not in {"queued", "blocked", "completed", "failed", "cancelled"}:
            raise ValueError(f"Unsupported Codex execution status: {status}")
        audit_json = json.dumps(audit, sort_keys=True)
        assert_no_secret_values(
            {
                "codex_execution_status": status,
                "codex_execution_runner_mode": runner_mode,
                "codex_execution_audit": audit_json,
                "codex_execution_error": error,
            }
        )
        now = utc_now()
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE codex_execution_runs
                SET status = ?,
                    runner_mode = ?,
                    external_execution_enabled = ?,
                    audit_json = ?,
                    error = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status.strip(),
                    runner_mode.strip(),
                    1 if external_execution_enabled else 0,
                    audit_json,
                    error.strip(),
                    now if status in {"completed", "failed", "cancelled"} else None,
                    run_id,
                ),
            )
        if cursor.rowcount == 0:
            raise sqlite3.IntegrityError(f"Unknown Codex execution run: {run_id}")
        with connect(self.database_path) as connection:
            self._insert_audit_event(
                connection,
                project_id=current["project_id"],
                event_type="codex_execution_updated",
                status=status.strip(),
                actor_agent_id="chief-of-staff",
                source_table="codex_execution_runs",
                source_id=run_id,
                summary=f"Codex execution updated to {status.strip()}.",
                payload={
                    "decision_id": current["decision_id"],
                    "runner_mode": runner_mode.strip(),
                    "external_execution_enabled": external_execution_enabled,
                },
            )

    def record_external_dispatch_delivery(
        self,
        *,
        idempotency_key: str,
        project_id: str,
        item_id: str,
        platform: str,
        action: str,
        command_boundary: str,
        contract_sha256: str,
        argv_sha256: str,
        status: str,
        runner_label: str = "",
        external_id: str = "",
        result: dict | None = None,
    ) -> dict:
        """Record an idempotent external-dispatch delivery and return the stored row.

        Mirrors the ``INSERT OR IGNORE … WHERE idempotency_key=?`` + re-SELECT
        pattern: re-recording the same ``idempotency_key`` is a no-op and returns
        the original row, so the gated runner never double-sends.
        """
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise ValueError("External dispatch delivery requires an idempotency key.")
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        result_json = json.dumps(result or {}, sort_keys=True)
        assert_no_secret_values(
            {
                "external_dispatch_delivery_idempotency_key": normalized_key,
                "external_dispatch_delivery_item_id": item_id,
                "external_dispatch_delivery_platform": platform,
                "external_dispatch_delivery_action": action,
                "external_dispatch_delivery_command_boundary": command_boundary,
                "external_dispatch_delivery_contract_sha256": contract_sha256,
                "external_dispatch_delivery_argv_sha256": argv_sha256,
                "external_dispatch_delivery_runner_label": runner_label,
                "external_dispatch_delivery_status": status,
                "external_dispatch_delivery_external_id": external_id,
                "external_dispatch_delivery_result": result_json,
            }
        )
        delivery_id = f"dispatch-delivery-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO external_dispatch_deliveries (
                    id, idempotency_key, project_id, item_id, platform, action,
                    command_boundary, contract_sha256, argv_sha256, runner_label,
                    status, external_id, result_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_id,
                    normalized_key,
                    project_id,
                    item_id.strip(),
                    platform.strip(),
                    action.strip(),
                    command_boundary.strip(),
                    contract_sha256.strip(),
                    argv_sha256.strip(),
                    runner_label.strip(),
                    status.strip(),
                    external_id.strip(),
                    result_json,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM external_dispatch_deliveries WHERE idempotency_key = ?",
                (normalized_key,),
            ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError(
                "External dispatch delivery was not persisted."
            )
        return decode_external_dispatch_delivery(row)

    def get_external_dispatch_delivery(self, idempotency_key: str) -> dict | None:
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            return None
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM external_dispatch_deliveries WHERE idempotency_key = ?",
                (normalized_key,),
            ).fetchone()
        return decode_external_dispatch_delivery(row) if row else None

    def list_external_dispatch_deliveries(
        self,
        project_id: str,
        *,
        limit: int = 50,
    ) -> list[dict]:
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        bounded_limit = max(1, min(limit, 200))
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM external_dispatch_deliveries
                WHERE project_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (project_id, bounded_limit),
            ).fetchall()
        return [decode_external_dispatch_delivery(row) for row in rows]

    def create_project_review_record(
        self,
        *,
        source_key: str,
        project_id: str,
        review_batch_id: str,
        reviewer_agent_id: str,
        reviewer_name: str,
        reviewer_role: str,
        verdict: str,
        summary: str,
        artifact_ids: list[str] | tuple[str, ...],
        checks: list[dict] | tuple[dict, ...],
        findings: list[dict] | tuple[dict, ...],
    ) -> str:
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        if verdict not in {"approved", "needs_revision", "blocked"}:
            raise ValueError(f"Unsupported project review verdict: {verdict}")
        artifact_json = json.dumps(list(artifact_ids), sort_keys=True)
        checks_json = json.dumps(list(checks), sort_keys=True)
        findings_json = json.dumps(list(findings), sort_keys=True)
        assert_no_secret_values(
            {
                "project_review_source_key": source_key,
                "project_review_batch_id": review_batch_id,
                "project_review_reviewer_agent_id": reviewer_agent_id,
                "project_review_reviewer_name": reviewer_name,
                "project_review_reviewer_role": reviewer_role,
                "project_review_verdict": verdict,
                "project_review_summary": summary,
                "project_review_artifacts": artifact_json,
                "project_review_checks": checks_json,
                "project_review_findings": findings_json,
            }
        )
        review_id = f"review-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO project_review_records (
                    id, source_key, project_id, review_batch_id, reviewer_agent_id,
                    reviewer_name, reviewer_role, verdict, summary,
                    artifact_ids_json, checks_json, findings_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    source_key.strip(),
                    project_id,
                    review_batch_id.strip(),
                    reviewer_agent_id.strip(),
                    reviewer_name.strip(),
                    reviewer_role.strip(),
                    verdict.strip(),
                    summary.strip(),
                    artifact_json,
                    checks_json,
                    findings_json,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT id FROM project_review_records WHERE source_key = ?",
                (source_key.strip(),),
            ).fetchone()
        if row is None:
            raise sqlite3.IntegrityError("Project review record was not persisted.")
        return row["id"]

    def list_project_review_records(
        self,
        project_id: str,
        *,
        review_batch_id: str = "",
        limit: int = 50,
    ) -> list[dict]:
        if self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        filters = ["project_id = ?"]
        parameters: list[str | int] = [project_id]
        if review_batch_id:
            filters.append("review_batch_id = ?")
            parameters.append(review_batch_id)
        parameters.append(max(1, min(limit, 100)))
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM project_review_records
                WHERE {" AND ".join(filters)}
                ORDER BY
                    CASE reviewer_agent_id
                        WHEN 'qa-critic' THEN 1
                        WHEN 'test-automation-agent' THEN 2
                        WHEN 'product-manager' THEN 3
                        WHEN 'engineering-manager' THEN 4
                        WHEN 'ui-ux-research-agent' THEN 5
                        ELSE 99
                    END,
                    created_at DESC,
                    id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [decode_project_review_record(row) for row in rows]

    def create_project_memory_entry(
        self,
        *,
        source_key: str = "",
        project_id: str = "",
        category: str,
        memory_type: str,
        owner_agent_id: str,
        source: str,
        title: str,
        summary: str,
        body: str,
        confidence: str,
        status: str = "active",
        pinned: bool = False,
        review_after: str = "",
        expires_at: str = "",
        source_artifact_id: str = "",
        source_decision_id: str = "",
    ) -> str:
        normalized_project_id = project_id.strip()
        if normalized_project_id and self.get_project(normalized_project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {normalized_project_id}")
        self.assert_agent_exists(owner_agent_id)
        normalized_category = normalize_memory_category(category)
        normalized_confidence = normalize_memory_confidence(confidence)
        normalized_status = normalize_memory_status(status)
        if source_decision_id and self.get_founder_decision(source_decision_id) is None:
            raise sqlite3.IntegrityError(f"Unknown founder decision: {source_decision_id}")
        normalized_source_key = source_key.strip() or (
            f"project_memory:{normalized_project_id or 'company'}:{uuid4().hex[:12]}"
        )
        values_to_check = {
            "memory_source_key": normalized_source_key,
            "memory_category": normalized_category,
            "memory_type": memory_type,
            "memory_owner_agent_id": owner_agent_id,
            "memory_source": source,
            "memory_source_artifact_id": source_artifact_id,
            "memory_source_decision_id": source_decision_id,
            "memory_title": title,
            "memory_summary": summary,
            "memory_body": body,
            "memory_confidence": normalized_confidence,
            "memory_status": normalized_status,
            "memory_review_after": review_after,
            "memory_expires_at": expires_at,
        }
        assert_no_secret_values(values_to_check)
        memory_id = f"memory-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO project_memory_entries (
                    id, source_key, project_id, category, memory_type,
                    owner_agent_id, source, source_artifact_id, source_decision_id,
                    title, summary, body, confidence, status, pinned,
                    review_after, expires_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    normalized_source_key,
                    normalized_project_id or None,
                    normalized_category,
                    memory_type.strip(),
                    owner_agent_id.strip(),
                    source.strip(),
                    source_artifact_id.strip(),
                    source_decision_id.strip() or None,
                    title.strip(),
                    summary.strip(),
                    body.strip(),
                    normalized_confidence,
                    normalized_status,
                    1 if pinned else 0,
                    review_after.strip(),
                    expires_at.strip(),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT id FROM project_memory_entries WHERE source_key = ?",
                (normalized_source_key,),
            ).fetchone()
            if row is not None and cursor.rowcount > 0 and normalized_project_id:
                self._insert_audit_event(
                    connection,
                    project_id=normalized_project_id,
                    event_type="memory_created",
                    status=normalized_status,
                    actor_agent_id=owner_agent_id,
                    source_table="project_memory_entries",
                    source_id=row["id"],
                    summary=f"Project memory captured: {title.strip()}",
                    payload={
                        "category": normalized_category,
                        "memory_type": memory_type.strip(),
                        "status": normalized_status,
                        "pinned": pinned,
                    },
                )
        if row is None:
            raise sqlite3.IntegrityError("Project memory entry was not persisted.")
        return row["id"]

    def get_project_memory_entry(self, memory_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT project_memory_entries.*,
                       agents.name AS owner_name
                FROM project_memory_entries
                JOIN agents ON agents.id = project_memory_entries.owner_agent_id
                WHERE project_memory_entries.id = ?
                """,
                (memory_id,),
            ).fetchone()
        return decode_project_memory_entry(row) if row else None

    def list_project_memory_entries(
        self,
        project_id: str = "",
        *,
        include_company_wide: bool = False,
        include_retired: bool = False,
        include_expired: bool = False,
        reusable_only: bool = False,
        category: str = "",
        limit: int = 50,
    ) -> list[dict]:
        normalized_project_id = project_id.strip()
        if normalized_project_id and self.get_project(normalized_project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {normalized_project_id}")
        filters: list[str] = []
        parameters: list[str | int] = []
        if normalized_project_id:
            if include_company_wide:
                filters.append(
                    "(project_memory_entries.project_id = ? "
                    "OR project_memory_entries.project_id IS NULL)"
                )
            else:
                filters.append("project_memory_entries.project_id = ?")
            parameters.append(normalized_project_id)
        elif not include_company_wide:
            filters.append("project_memory_entries.project_id IS NULL")
        if not include_retired:
            filters.append("project_memory_entries.status != 'retired'")
        if reusable_only:
            filters.append("project_memory_entries.status = 'active'")
        if category:
            filters.append("project_memory_entries.category = ?")
            parameters.append(normalize_memory_category(category))
        parameters.append(max(1, min(limit, 200)))
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT project_memory_entries.*,
                       agents.name AS owner_name
                FROM project_memory_entries
                JOIN agents ON agents.id = project_memory_entries.owner_agent_id
                {where_clause}
                ORDER BY
                    CASE WHEN project_memory_entries.project_id IS NULL THEN 1 ELSE 0 END,
                    project_memory_entries.pinned DESC,
                    project_memory_entries.updated_at DESC,
                    project_memory_entries.title
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        entries = [decode_project_memory_entry(row) for row in rows]
        if not include_expired:
            entries = [
                entry
                for entry in entries
                if not entry["expired"] and not entry["review_due"]
            ]
        if reusable_only:
            entries = [entry for entry in entries if entry["reusable"]]
        return entries

    def list_reusable_project_memory_entries(
        self,
        project_id: str = "",
        *,
        category: str = "",
        limit: int = 50,
    ) -> list[dict]:
        return self.list_project_memory_entries(
            project_id=project_id,
            include_company_wide=True,
            include_retired=False,
            include_expired=False,
            reusable_only=True,
            category=category,
            limit=limit,
        )

    def update_project_memory_entry(
        self,
        memory_id: str,
        *,
        status: str | None = None,
        pinned: bool | None = None,
        title: str | None = None,
        summary: str | None = None,
        body: str | None = None,
        confidence: str | None = None,
        review_after: str | None = None,
        expires_at: str | None = None,
    ) -> None:
        current = self.get_project_memory_entry(memory_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown project memory entry: {memory_id}")
        updates: list[str] = []
        parameters: list[str | int] = []

        def set_text(column: str, value: str | None, *, normalize=None) -> None:
            if value is None:
                return
            normalized = normalize(value) if normalize else value.strip()
            updates.append(f"{column} = ?")
            parameters.append(normalized)

        set_text("status", status, normalize=normalize_memory_status)
        set_text("title", title)
        set_text("summary", summary)
        set_text("body", body)
        set_text("confidence", confidence, normalize=normalize_memory_confidence)
        set_text("review_after", review_after)
        set_text("expires_at", expires_at)
        if pinned is not None:
            updates.append("pinned = ?")
            parameters.append(1 if pinned else 0)
        if not updates:
            return
        next_status = (
            normalize_memory_status(status) if status is not None else current["status"]
        )
        next_pinned = bool(pinned) if pinned is not None else bool(current["pinned"])
        event_type = "memory_updated"
        if status is not None and next_status != current["status"]:
            event_type = {
                "retired": "memory_retired",
                "active": "memory_reactivated",
            }.get(next_status, "memory_updated")
        elif pinned is not None and next_pinned != bool(current["pinned"]):
            event_type = "memory_pinned" if next_pinned else "memory_unpinned"
        candidate = {
            "memory_status": status or current["status"],
            "memory_title": title if title is not None else current["title"],
            "memory_summary": summary if summary is not None else current["summary"],
            "memory_body": body if body is not None else current["body"],
            "memory_confidence": confidence or current["confidence"],
            "memory_review_after": (
                review_after if review_after is not None else current["review_after"]
            ),
            "memory_expires_at": (
                expires_at if expires_at is not None else current["expires_at"]
            ),
        }
        assert_no_secret_values(candidate)
        updates.append("updated_at = ?")
        parameters.append(utc_now())
        parameters.append(memory_id)
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                f"""
                UPDATE project_memory_entries
                SET {", ".join(updates)}
                WHERE id = ?
                """,
                parameters,
            )
        if cursor.rowcount == 0:
            raise sqlite3.IntegrityError(f"Unknown project memory entry: {memory_id}")
        if current.get("project_id"):
            with connect(self.database_path) as connection:
                self._insert_audit_event(
                    connection,
                    project_id=current["project_id"],
                    event_type=event_type,
                    status=next_status,
                    actor_agent_id=current["owner_agent_id"],
                    source_table="project_memory_entries",
                    source_id=memory_id,
                    summary=f"Project memory {next_status}: {current['title']}",
                    payload={
                        "category": current["category"],
                        "memory_type": current["memory_type"],
                        "status": next_status,
                        "pinned": next_pinned,
                    },
                )
