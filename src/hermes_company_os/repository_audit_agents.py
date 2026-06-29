from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from hermes_company_os.database import connect, decode_capabilities, decode_many
from hermes_company_os.repository_support import (
    decode_audit_event,
    utc_now,
)
from hermes_company_os.secret_guard import assert_no_secret_values


class AuditAndAgentsMixin:
    def _insert_audit_event(
        self,
        connection: sqlite3.Connection,
        *,
        project_id: str | None,
        event_type: str,
        status: str,
        actor_agent_id: str | None,
        source_table: str,
        source_id: str,
        summary: str,
        payload: dict | None = None,
    ) -> str:
        cleaned = {
            "project_id": (project_id or "").strip(),
            "event_type": event_type.strip(),
            "status": status.strip(),
            "actor_agent_id": (actor_agent_id or "").strip(),
            "source_table": source_table.strip(),
            "source_id": source_id.strip(),
            "summary": summary.strip(),
        }
        required = ("event_type", "status", "source_table", "source_id", "summary")
        missing = [field for field in required if not cleaned[field]]
        if missing:
            raise ValueError(f"Missing audit event fields: {', '.join(missing)}")
        try:
            payload_json = json.dumps(payload or {}, sort_keys=True)
        except TypeError as exc:
            raise ValueError("Audit event payload must be JSON serializable.") from exc
        assert_no_secret_values(
            {
                **cleaned,
                "payload_json": payload_json,
            }
        )
        event_id = f"audit-{uuid4().hex[:10]}"
        connection.execute(
            """
            INSERT INTO audit_events (
                id, project_id, event_type, status, actor_agent_id,
                source_table, source_id, summary, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                cleaned["project_id"] or None,
                cleaned["event_type"],
                cleaned["status"],
                cleaned["actor_agent_id"] or None,
                cleaned["source_table"],
                cleaned["source_id"],
                cleaned["summary"],
                payload_json,
                utc_now(),
            ),
        )
        return event_id

    def create_audit_event(
        self,
        *,
        project_id: str = "",
        event_type: str,
        status: str,
        actor_agent_id: str = "",
        source_table: str,
        source_id: str,
        summary: str,
        payload: dict | None = None,
    ) -> str:
        normalized_project_id = project_id.strip()
        normalized_actor_id = actor_agent_id.strip()
        if normalized_project_id and self.get_project(normalized_project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {normalized_project_id}")
        if normalized_actor_id:
            self.assert_agent_exists(normalized_actor_id)
        with connect(self.database_path) as connection:
            return self._insert_audit_event(
                connection,
                project_id=normalized_project_id,
                event_type=event_type,
                status=status,
                actor_agent_id=normalized_actor_id,
                source_table=source_table,
                source_id=source_id,
                summary=summary,
                payload=payload,
            )

    def list_audit_events(
        self,
        project_id: str = "",
        *,
        event_type: str = "",
        limit: int = 50,
    ) -> list[dict]:
        normalized_project_id = project_id.strip()
        if normalized_project_id and self.get_project(normalized_project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {normalized_project_id}")
        filters: list[str] = []
        parameters: list[str | int] = []
        if normalized_project_id:
            filters.append("project_id = ?")
            parameters.append(normalized_project_id)
        if event_type:
            filters.append("event_type = ?")
            parameters.append(event_type.strip())
        parameters.append(max(1, min(limit, 200)))
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with connect(self.database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT audit_events.*,
                       agents.name AS actor_name
                FROM audit_events
                LEFT JOIN agents ON agents.id = audit_events.actor_agent_id
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [decode_audit_event(row) for row in rows]

    def list_agents(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM agents ORDER BY rowid").fetchall()
        return decode_many(rows)

    def get_agent(self, agent_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return decode_capabilities(row) if row else None

    def update_agent_profile(
        self,
        agent_id: str,
        description: str,
        soul: str,
        capabilities: list[str],
    ) -> None:
        if self.get_agent(agent_id) is None:
            raise sqlite3.IntegrityError(f"Unknown agent: {agent_id}")
        cleaned_capabilities = [item.strip() for item in capabilities if item.strip()]
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE agents
                SET description = ?, soul = ?, capabilities_json = ?
                WHERE id = ?
                """,
                (
                    description.strip(),
                    soul.strip(),
                    json.dumps(cleaned_capabilities),
                    agent_id,
                ),
            )

    def update_agent_routing(
        self,
        agent_id: str,
        slack_channel: str,
        telegram_policy: str,
        hermes_command: str,
    ) -> None:
        if self.get_agent(agent_id) is None:
            raise sqlite3.IntegrityError(f"Unknown agent: {agent_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE agents
                SET slack_channel = ?,
                    telegram_policy = ?,
                    hermes_command = ?
                WHERE id = ?
                """,
                (
                    slack_channel.strip(),
                    telegram_policy.strip(),
                    hermes_command.strip(),
                    agent_id,
                ),
            )

    def list_agent_relationships(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT agent_relationships.*,
                       managers.name AS manager_name,
                       managers.role AS manager_role,
                       managers.hermes_command AS manager_command,
                       members.name AS member_name,
                       members.role AS member_role,
                       members.hermes_command AS member_command,
                       members.slack_channel AS member_slack_channel
                FROM agent_relationships
                JOIN agents AS managers
                    ON managers.id = agent_relationships.manager_agent_id
                JOIN agents AS members
                    ON members.id = agent_relationships.member_agent_id
                ORDER BY agent_relationships.sort_order, agent_relationships.id
                """
            ).fetchall()
        return [dict(row) for row in rows]
