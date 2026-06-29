from __future__ import annotations

import sqlite3
from uuid import uuid4

from hermes_company_os.database import connect
from hermes_company_os.repository_support import (
    serialize_wizard_json_content,
    utc_now,
)
from hermes_company_os.secret_guard import assert_no_secret_values


class StageLifecycleMixin:
    def save_stage_artifact_draft(
        self,
        project_id: str,
        stage_id: str,
        markdown_content: str,
        json_content: dict | list | str | None = None,
        owner_agent_id: str | None = None,
    ) -> str:
        json_text = serialize_wizard_json_content(json_content)
        assert_no_secret_values(
            {
                "markdown_content": markdown_content,
                "json_content": json_text,
            }
        )
        stage = self.get_project_wizard_stage(project_id, stage_id)
        if stage is None:
            raise sqlite3.IntegrityError(
                f"Unknown product wizard stage: {project_id}/{stage_id}"
            )
        if stage["status"] == "waiting":
            raise ValueError("Cannot save a draft for a waiting product wizard stage.")
        if stage["status"] == "approved":
            raise ValueError("Request a revision before replacing an approved stage.")

        artifact_owner_id = owner_agent_id or stage["owner_agent_id"]
        self.assert_agent_exists(artifact_owner_id)
        artifact_id = f"wiz-artifact-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) + 1 AS next_version
                FROM product_wizard_artifacts
                WHERE project_stage_id = ?
                """,
                (stage["id"],),
            ).fetchone()
            next_version = row["next_version"]
            connection.execute(
                """
                INSERT INTO product_wizard_artifacts (
                    id, project_id, project_stage_id, stage_id, version, status,
                    markdown_content, json_content, owner_agent_id, created_at, approved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    project_id,
                    stage["id"],
                    stage_id,
                    next_version,
                    "draft",
                    markdown_content.strip(),
                    json_text,
                    artifact_owner_id,
                    now,
                    None,
                ),
            )
            connection.execute(
                """
                UPDATE product_wizard_project_stages
                SET status = ?,
                    owner_agent_id = ?,
                    updated_at = ?,
                    started_at = COALESCE(started_at, ?),
                    completed_at = NULL,
                    approved_at = NULL,
                    blocked_at = NULL
                WHERE id = ?
                """,
                ("draft", artifact_owner_id, now, now, stage["id"]),
            )
            connection.execute(
                """
                UPDATE company_projects
                SET updated_at = ?, status = ?
                WHERE id = ?
                """,
                (now, "wizard_active", project_id),
            )
        return artifact_id

    def approve_stage(self, project_id: str, stage_id: str) -> None:
        stage = self.get_project_wizard_stage(project_id, stage_id)
        if stage is None:
            raise sqlite3.IntegrityError(
                f"Unknown product wizard stage: {project_id}/{stage_id}"
            )
        if stage["status"] != "draft":
            raise ValueError("Only draft product wizard stages can be approved.")
        artifact = self.latest_project_stage_artifact(project_id, stage_id)
        if artifact is None or artifact["status"] != "draft":
            raise ValueError("Cannot approve a stage without a draft artifact.")

        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE product_wizard_artifacts
                SET status = ?, approved_at = ?
                WHERE id = ?
                """,
                ("approved", now, artifact["id"]),
            )
            connection.execute(
                """
                UPDATE product_wizard_project_stages
                SET status = ?,
                    revision_notes = '',
                    updated_at = ?,
                    completed_at = ?,
                    approved_at = ?,
                    revision_requested_at = NULL,
                    blocked_at = NULL
                WHERE id = ?
                """,
                ("approved", now, now, now, stage["id"]),
            )
            next_stage = connection.execute(
                """
                SELECT next_stages.*
                FROM product_wizard_project_stages AS next_stages
                JOIN product_wizard_stage_definitions AS definitions
                    ON definitions.id = next_stages.stage_id
                WHERE next_stages.project_id = ?
                  AND definitions.sort_order > ?
                ORDER BY definitions.sort_order, definitions.id
                LIMIT 1
                """,
                (project_id, stage["sort_order"]),
            ).fetchone()
            if next_stage is None:
                project_status = "wizard_complete"
                next_stage_id = ""
            else:
                project_status = "wizard_active"
                next_stage_id = next_stage["stage_id"]
                if next_stage["status"] == "waiting":
                    connection.execute(
                        """
                        UPDATE product_wizard_project_stages
                        SET status = ?,
                            updated_at = ?,
                            started_at = COALESCE(started_at, ?)
                        WHERE id = ?
                        """,
                        ("ready", now, now, next_stage["id"]),
                    )
            connection.execute(
                """
                UPDATE company_projects
                SET updated_at = ?, status = ?
                WHERE id = ?
                """,
                (now, project_status, project_id),
            )
            self._insert_audit_event(
                connection,
                project_id=project_id,
                event_type="stage_approved",
                status="approved",
                actor_agent_id=stage["owner_agent_id"],
                source_table="product_wizard_project_stages",
                source_id=stage["id"],
                summary=f"Stage approved: {stage_id}.",
                payload={
                    "stage_id": stage_id,
                    "artifact_id": artifact["id"],
                    "project_status": project_status,
                    "next_stage_id": next_stage_id,
                },
            )

    def request_stage_revision(
        self,
        project_id: str,
        stage_id: str,
        notes: str = "",
        reason: str = "",
    ) -> None:
        assert_no_secret_values({"revision_notes": notes, "revision_reason": reason})
        stage = self.get_project_wizard_stage(project_id, stage_id)
        if stage is None:
            raise sqlite3.IntegrityError(
                f"Unknown product wizard stage: {project_id}/{stage_id}"
            )
        if stage["status"] == "waiting":
            raise ValueError("Cannot request revision for a waiting product wizard stage.")

        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE product_wizard_project_stages
                SET status = ?,
                    revision_notes = ?,
                    updated_at = ?,
                    completed_at = NULL,
                    approved_at = NULL,
                    revision_requested_at = ?,
                    blocked_at = NULL
                WHERE id = ?
                """,
                ("needs_revision", notes.strip(), now, now, stage["id"]),
            )
            latest_artifact_id = stage.get("latest_artifact_id")
            if latest_artifact_id:
                connection.execute(
                    """
                    UPDATE product_wizard_artifacts
                    SET status = ?, approved_at = NULL
                    WHERE id = ?
                    """,
                    ("needs_revision", latest_artifact_id),
                )
            connection.execute(
                """
                UPDATE company_projects
                SET updated_at = ?, status = ?
                WHERE id = ?
                """,
                (now, "wizard_active", project_id),
            )
            self._insert_audit_event(
                connection,
                project_id=project_id,
                event_type="stage_revision_requested",
                status="needs_revision",
                actor_agent_id=stage["owner_agent_id"],
                source_table="product_wizard_project_stages",
                source_id=stage["id"],
                summary=f"Stage revision requested: {stage_id}.",
                payload={
                    "stage_id": stage_id,
                    "artifact_id": latest_artifact_id or "",
                    "reason": reason.strip(),
                    "notes": notes.strip(),
                },
            )

    def block_stage(
        self,
        project_id: str,
        stage_id: str,
        notes: str = "",
    ) -> None:
        assert_no_secret_values({"blocker_notes": notes})
        stage = self.get_project_wizard_stage(project_id, stage_id)
        if stage is None:
            raise sqlite3.IntegrityError(
                f"Unknown product wizard stage: {project_id}/{stage_id}"
            )
        if stage["status"] in {"waiting", "approved"}:
            raise ValueError("Only active product wizard stages can be blocked.")

        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE product_wizard_project_stages
                SET status = ?,
                    revision_notes = ?,
                    updated_at = ?,
                    blocked_at = ?
                WHERE id = ?
                """,
                ("blocked", notes.strip(), now, now, stage["id"]),
            )
            connection.execute(
                """
                UPDATE company_projects
                SET updated_at = ?, status = ?
                WHERE id = ?
                """,
                (now, "wizard_active", project_id),
            )

    def next_actionable_stage(self, project_id: str) -> dict | None:
        for stage in self.list_project_wizard_stages(project_id):
            if stage["status"] in {"ready", "draft", "needs_revision", "blocked"}:
                return stage
        return None
