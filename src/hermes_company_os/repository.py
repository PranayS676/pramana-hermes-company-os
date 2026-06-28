from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from hermes_company_os.agent_work_queue import (
    QUEUE_STATES,
    validate_queue_priority,
    validate_queue_state,
    validate_queue_transition,
)
from hermes_company_os.audit_events import enrich_audit_event
from hermes_company_os.database import connect, decode_capabilities, decode_many
from hermes_company_os.founder_decisions import (
    RESOLVED_DECISION_STATUSES,
    SUPPORTED_DECISION_TYPES,
    founder_only_decision_type,
    normalize_decision_type,
)
from hermes_company_os.project_memory import (
    enrich_memory_entry,
    normalize_memory_category,
    normalize_memory_confidence,
    normalize_memory_status,
)
from hermes_company_os.secret_guard import assert_no_secret_values, secret_violations


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def serialize_wizard_json_content(json_content: dict | list | str | None) -> str:
    if json_content is None:
        return ""
    if isinstance(json_content, str):
        if not json_content.strip():
            return ""
        return json.dumps(json.loads(json_content), sort_keys=True)
    return json.dumps(json_content, sort_keys=True)


def decode_project(row: sqlite3.Row) -> dict:
    project = dict(row)
    raw_intake = project.get("intake_json", "").strip()
    project["intake"] = json.loads(raw_intake) if raw_intake else {}
    return project


def decode_wizard_artifact(row: sqlite3.Row) -> dict:
    artifact = dict(row)
    raw_json = artifact["json_content"].strip()
    artifact["json"] = json.loads(raw_json) if raw_json else {}
    return artifact


def decode_generation_run(row: sqlite3.Row) -> dict:
    run = dict(row)
    raw_sources = run.get("source_artifact_ids_json", "").strip()
    raw_memory_ids = run.get("memory_ids_json", "").strip()
    run["source_artifact_ids"] = json.loads(raw_sources) if raw_sources else []
    run["memory_ids"] = json.loads(raw_memory_ids) if raw_memory_ids else []
    return run


def decode_codex_execution_run(row: sqlite3.Row) -> dict:
    run = dict(row)
    run["external_execution_enabled"] = bool(run["external_execution_enabled"])
    for column, target, fallback in (
        ("source_artifact_ids_json", "source_artifact_ids", []),
        ("command_preview_json", "command_preview", []),
        ("approval_snapshot_json", "approval_snapshot", {}),
        ("audit_json", "audit", {}),
    ):
        raw_json = run.get(column, "").strip()
        run[target] = json.loads(raw_json) if raw_json else fallback
    return run


def decode_project_review_record(row: sqlite3.Row) -> dict:
    record = dict(row)
    for column, target, fallback in (
        ("artifact_ids_json", "artifact_ids", []),
        ("checks_json", "checks", []),
        ("findings_json", "findings", []),
    ):
        raw_json = record.get(column, "").strip()
        record[target] = json.loads(raw_json) if raw_json else fallback
    return record


def decode_project_memory_entry(row: sqlite3.Row) -> dict:
    return enrich_memory_entry(dict(row))


def decode_audit_event(row: sqlite3.Row) -> dict:
    event = dict(row)
    raw_payload = event["payload_json"].strip()
    event["payload"] = json.loads(raw_payload) if raw_payload else {}
    return enrich_audit_event(event)


def safe_generation_error(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        return "Generation failed without a detailed error."
    if secret_violations({"generation_error": cleaned}):
        return "Generation failed. Error contained secret-looking content and was redacted."
    return cleaned[:1000]


def age_label(timestamp: str) -> str:
    if not timestamp:
        return "unknown age"
    try:
        created = datetime.fromisoformat(timestamp)
    except ValueError:
        return "unknown age"
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    elapsed = datetime.now(UTC) - created
    days = elapsed.days
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''}"
    hours = elapsed.seconds // 3600
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    minutes = max(1, elapsed.seconds // 60)
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def decode_agent_work_item(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["founder_action_required"] = bool(item["founder_action_required"])
    item["blocked_age_label"] = (
        age_label(item["updated_at"]) if item["status"] == "blocked" else ""
    )
    return item


class CompanyRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path

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

    def list_schedules(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM standup_schedules ORDER BY hour, minute"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_schedule(self, schedule_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM standup_schedules WHERE id = ?", (schedule_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_schedule(
        self,
        schedule_id: str,
        name: str,
        hour: int,
        minute: int,
        timezone: str,
        slack_channel: str,
        telegram_policy: str,
        active: bool,
    ) -> None:
        if self.get_schedule(schedule_id) is None:
            raise sqlite3.IntegrityError(f"Unknown schedule: {schedule_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE standup_schedules
                SET name = ?,
                    hour = ?,
                    minute = ?,
                    timezone = ?,
                    slack_channel = ?,
                    telegram_policy = ?,
                    active = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    hour,
                    minute,
                    timezone.strip(),
                    slack_channel.strip(),
                    telegram_policy.strip(),
                    1 if active else 0,
                    schedule_id,
                ),
            )

    def list_model_preferences(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT agent_model_preferences.*,
                       agents.name AS agent_name,
                       agents.role AS agent_role,
                       agents.hermes_command AS hermes_command
                FROM agent_model_preferences
                JOIN agents ON agents.id = agent_model_preferences.agent_id
                ORDER BY agents.rowid
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_model_preference(self, agent_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT agent_model_preferences.*,
                       agents.name AS agent_name,
                       agents.role AS agent_role,
                       agents.hermes_command AS hermes_command
                FROM agent_model_preferences
                JOIN agents ON agents.id = agent_model_preferences.agent_id
                WHERE agent_model_preferences.agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
        return dict(row) if row else None

    def model_preference_map(self) -> dict[str, dict]:
        return {
            preference["agent_id"]: preference
            for preference in self.list_model_preferences()
        }

    def update_model_preference(
        self,
        agent_id: str,
        provider: str,
        model: str,
        fallback_provider: str,
        fallback_model: str,
        auth_method: str,
        status: str,
        notes: str,
    ) -> None:
        if self.get_agent(agent_id) is None:
            raise sqlite3.IntegrityError(f"Unknown agent: {agent_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO agent_model_preferences (
                    agent_id, provider, model, fallback_provider, fallback_model,
                    auth_method, status, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    provider = excluded.provider,
                    model = excluded.model,
                    fallback_provider = excluded.fallback_provider,
                    fallback_model = excluded.fallback_model,
                    auth_method = excluded.auth_method,
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    agent_id,
                    provider.strip(),
                    model.strip(),
                    fallback_provider.strip(),
                    fallback_model.strip(),
                    auth_method.strip(),
                    status.strip(),
                    notes.strip(),
                    utc_now(),
                ),
            )

    def list_secret_requirements(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT external_secret_requirements.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command
                FROM external_secret_requirements
                LEFT JOIN agents ON agents.id = external_secret_requirements.owner_agent_id
                ORDER BY
                    CASE external_secret_requirements.category
                        WHEN 'slack' THEN 1
                        WHEN 'telegram' THEN 2
                        WHEN 'llm' THEN 3
                        ELSE 9
                    END,
                    external_secret_requirements.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_secret_requirement(self, requirement_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT external_secret_requirements.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command
                FROM external_secret_requirements
                LEFT JOIN agents ON agents.id = external_secret_requirements.owner_agent_id
                WHERE external_secret_requirements.id = ?
                """,
                (requirement_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_secret_requirement(
        self,
        requirement_id: str,
        status: str,
        notes: str,
    ) -> None:
        if self.get_secret_requirement(requirement_id) is None:
            raise sqlite3.IntegrityError(f"Unknown secret requirement: {requirement_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE external_secret_requirements
                SET status = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.strip(), notes.strip(), utc_now(), requirement_id),
            )

    def update_agent_secret_requirements(
        self,
        agent_id: str,
        category: str,
        status: str,
        notes: str,
    ) -> None:
        if self.get_agent(agent_id) is None:
            raise sqlite3.IntegrityError(f"Unknown agent: {agent_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE external_secret_requirements
                SET status = ?, notes = ?, updated_at = ?
                WHERE owner_agent_id = ? AND category = ?
                """,
                (status.strip(), notes.strip(), utc_now(), agent_id, category.strip()),
            )

    def list_messaging_checks(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT messaging_verification_checks.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command,
                       agents.slack_channel AS owner_slack_channel
                FROM messaging_verification_checks
                JOIN agents ON agents.id = messaging_verification_checks.owner_agent_id
                ORDER BY messaging_verification_checks.sort_order,
                         messaging_verification_checks.label
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_messaging_check(self, check_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT messaging_verification_checks.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command,
                       agents.slack_channel AS owner_slack_channel
                FROM messaging_verification_checks
                JOIN agents ON agents.id = messaging_verification_checks.owner_agent_id
                WHERE messaging_verification_checks.id = ?
                """,
                (check_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_messaging_check(
        self,
        check_id: str,
        status: str,
        evidence: str,
    ) -> None:
        if self.get_messaging_check(check_id) is None:
            raise sqlite3.IntegrityError(f"Unknown messaging check: {check_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE messaging_verification_checks
                SET status = ?, evidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.strip(), evidence.strip(), utc_now(), check_id),
            )

    def messaging_platform_verified(self, platform: str) -> bool:
        checks = [item for item in self.list_messaging_checks() if item["platform"] == platform]
        return bool(checks) and all(item["status"] == "verified" for item in checks)

    def list_schedule_checks(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT schedule_verification_checks.*,
                       standup_schedules.name AS schedule_name,
                       standup_schedules.hour AS schedule_hour,
                       standup_schedules.minute AS schedule_minute,
                       standup_schedules.timezone AS schedule_timezone,
                       standup_schedules.slack_channel AS schedule_slack_channel,
                       standup_schedules.active AS schedule_active
                FROM schedule_verification_checks
                JOIN standup_schedules
                    ON standup_schedules.id = schedule_verification_checks.schedule_id
                ORDER BY schedule_verification_checks.sort_order,
                         schedule_verification_checks.label
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_schedule_check(self, check_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT schedule_verification_checks.*,
                       standup_schedules.name AS schedule_name,
                       standup_schedules.hour AS schedule_hour,
                       standup_schedules.minute AS schedule_minute,
                       standup_schedules.timezone AS schedule_timezone,
                       standup_schedules.slack_channel AS schedule_slack_channel,
                       standup_schedules.active AS schedule_active
                FROM schedule_verification_checks
                JOIN standup_schedules
                    ON standup_schedules.id = schedule_verification_checks.schedule_id
                WHERE schedule_verification_checks.id = ?
                """,
                (check_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_schedule_check(
        self,
        check_id: str,
        status: str,
        evidence: str,
    ) -> None:
        if self.get_schedule_check(check_id) is None:
            raise sqlite3.IntegrityError(f"Unknown schedule check: {check_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE schedule_verification_checks
                SET status = ?, evidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.strip(), evidence.strip(), utc_now(), check_id),
            )

    def active_schedule_verification_ready(self) -> bool:
        checks = [item for item in self.list_schedule_checks() if item["schedule_active"]]
        return bool(checks) and all(item["status"] == "verified" for item in checks)

    def list_kanban_checks(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM kanban_verification_checks
                ORDER BY sort_order, label
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_kanban_check(self, check_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM kanban_verification_checks WHERE id = ?",
                (check_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_kanban_check(
        self,
        check_id: str,
        status: str,
        evidence: str,
    ) -> None:
        if self.get_kanban_check(check_id) is None:
            raise sqlite3.IntegrityError(f"Unknown Kanban check: {check_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE kanban_verification_checks
                SET status = ?, evidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.strip(), evidence.strip(), utc_now(), check_id),
            )

    def kanban_verification_ready(self) -> bool:
        checks = self.list_kanban_checks()
        return bool(checks) and all(item["status"] == "verified" for item in checks)

    def list_profile_acceptance_checks(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT profile_acceptance_checks.*,
                       agents.name AS agent_name,
                       agents.role AS agent_role,
                       agents.hermes_command AS hermes_command
                FROM profile_acceptance_checks
                JOIN agents ON agents.id = profile_acceptance_checks.agent_id
                ORDER BY profile_acceptance_checks.sort_order,
                         profile_acceptance_checks.title
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_profile_acceptance_check(self, check_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT profile_acceptance_checks.*,
                       agents.name AS agent_name,
                       agents.role AS agent_role,
                       agents.hermes_command AS hermes_command
                FROM profile_acceptance_checks
                JOIN agents ON agents.id = profile_acceptance_checks.agent_id
                WHERE profile_acceptance_checks.id = ?
                """,
                (check_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_profile_acceptance_check(
        self,
        check_id: str,
        status: str,
        evidence: str,
    ) -> None:
        if self.get_profile_acceptance_check(check_id) is None:
            raise sqlite3.IntegrityError(f"Unknown profile acceptance check: {check_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE profile_acceptance_checks
                SET status = ?, evidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.strip(), evidence.strip(), utc_now(), check_id),
            )

    def profile_acceptance_verified(self) -> bool:
        checks = self.list_profile_acceptance_checks()
        return bool(checks) and all(item["status"] == "verified" for item in checks)

    def list_profile_installation_checks(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT profile_installation_checks.*,
                       agents.name AS agent_name,
                       agents.role AS agent_role,
                       agents.hermes_command AS hermes_command
                FROM profile_installation_checks
                JOIN agents ON agents.id = profile_installation_checks.agent_id
                ORDER BY profile_installation_checks.sort_order,
                         profile_installation_checks.label
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_profile_installation_check(self, check_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT profile_installation_checks.*,
                       agents.name AS agent_name,
                       agents.role AS agent_role,
                       agents.hermes_command AS hermes_command
                FROM profile_installation_checks
                JOIN agents ON agents.id = profile_installation_checks.agent_id
                WHERE profile_installation_checks.id = ?
                """,
                (check_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_profile_installation_check(
        self,
        check_id: str,
        status: str,
        evidence: str,
    ) -> None:
        if self.get_profile_installation_check(check_id) is None:
            raise sqlite3.IntegrityError(f"Unknown profile installation check: {check_id}")
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE profile_installation_checks
                SET status = ?, evidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.strip(), evidence.strip(), utc_now(), check_id),
            )

    def profile_installation_verified(self) -> bool:
        checks = self.list_profile_installation_checks()
        return bool(checks) and all(item["status"] == "verified" for item in checks)

    def agent_profile_installation_verified(self, agent_id: str) -> bool:
        check = self.get_profile_installation_check(f"{agent_id}-profile-installation")
        return bool(check and check["status"] == "verified")

    def list_founder_decisions(
        self,
        limit: int | None = None,
        *,
        project_id: str = "",
        stage_id: str = "",
        artifact_id: str = "",
        status: str = "",
        urgency: str = "",
        decision_type: str = "",
        owner_agent_id: str = "",
        include_resolved: bool = True,
    ) -> list[dict]:
        query = """
            SELECT founder_decisions.*,
                   agents.name AS owner_name,
                   agents.hermes_command AS owner_command,
                   company_projects.name AS project_name
            FROM founder_decisions
            JOIN agents ON agents.id = founder_decisions.owner_agent_id
            LEFT JOIN company_projects
                ON company_projects.id = founder_decisions.project_id
        """
        filters = []
        parameters: list[object] = []
        if project_id:
            filters.append("founder_decisions.project_id = ?")
            parameters.append(project_id)
        if stage_id:
            filters.append("founder_decisions.stage_id = ?")
            parameters.append(stage_id)
        if artifact_id:
            filters.append("founder_decisions.artifact_id = ?")
            parameters.append(artifact_id)
        if status:
            if status == "open":
                filters.append(
                    "founder_decisions.status NOT IN ({})".format(
                        ",".join("?" for _ in RESOLVED_DECISION_STATUSES)
                    )
                )
                parameters.extend(sorted(RESOLVED_DECISION_STATUSES))
            else:
                filters.append("founder_decisions.status = ?")
                parameters.append(status)
        elif not include_resolved:
            filters.append(
                "founder_decisions.status NOT IN ({})".format(
                    ",".join("?" for _ in RESOLVED_DECISION_STATUSES)
                )
            )
            parameters.extend(sorted(RESOLVED_DECISION_STATUSES))
        if urgency:
            filters.append("founder_decisions.urgency = ?")
            parameters.append(urgency)
        if decision_type:
            filters.append("founder_decisions.decision_type = ?")
            parameters.append(normalize_decision_type(decision_type))
        if owner_agent_id:
            filters.append("founder_decisions.owner_agent_id = ?")
            parameters.append(owner_agent_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += """
            ORDER BY
                CASE founder_decisions.status
                    WHEN 'blocked' THEN 1
                    WHEN 'needed' THEN 2
                    ELSE 3
                END,
                founder_decisions.requires_founder_approval DESC,
                CASE founder_decisions.urgency
                    WHEN 'urgent' THEN 1
                    ELSE 2
                END,
                founder_decisions.updated_at DESC,
                founder_decisions.title
        """
        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)
        with connect(self.database_path) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [dict(row) for row in rows]

    def get_founder_decision(self, decision_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT founder_decisions.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command,
                       company_projects.name AS project_name
                FROM founder_decisions
                JOIN agents ON agents.id = founder_decisions.owner_agent_id
                LEFT JOIN company_projects
                    ON company_projects.id = founder_decisions.project_id
                WHERE founder_decisions.id = ?
                """,
                (decision_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_founder_decision(
        self,
        *,
        title: str,
        urgency: str,
        source: str,
        owner_agent_id: str,
        slack_channel: str,
        telegram_policy: str,
        context: str,
        status: str = "needed",
        decision_type: str = "operating_decision",
        project_id: str | None = None,
        stage_id: str | None = None,
        artifact_id: str | None = None,
        evidence: str = "",
        requires_founder_approval: bool | None = None,
    ) -> str:
        normalized_type = normalize_decision_type(decision_type)
        self.assert_agent_exists(owner_agent_id)
        if project_id and self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        assert_no_secret_values(
            {
                "title": title,
                "urgency": urgency,
                "source": source,
                "owner_agent_id": owner_agent_id,
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
                "context": context,
                "evidence": evidence,
            }
        )
        decision_id = f"decision-{uuid4().hex[:10]}"
        now = utc_now()
        normalized_project_id = (project_id or "").strip()
        normalized_stage_id = (stage_id or "").strip()
        normalized_artifact_id = (artifact_id or "").strip()
        founder_required = (
            founder_only_decision_type(normalized_type)
            if requires_founder_approval is None
            else requires_founder_approval
        )
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO founder_decisions (
                    id, title, status, urgency, decision_type, source,
                    owner_agent_id, project_id, stage_id, artifact_id,
                    slack_channel, telegram_policy, context, evidence, decision,
                    requires_founder_approval, resolved_at, resolution_note,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    title.strip(),
                    status.strip(),
                    urgency.strip(),
                    normalized_type,
                    source.strip(),
                    owner_agent_id,
                    normalized_project_id or None,
                    normalized_stage_id or None,
                    normalized_artifact_id or None,
                    slack_channel.strip(),
                    telegram_policy.strip(),
                    context.strip(),
                    evidence.strip(),
                    "",
                    1 if founder_required else 0,
                    None,
                    "",
                    now,
                    now,
                ),
            )
            if normalized_project_id:
                self._insert_audit_event(
                    connection,
                    project_id=normalized_project_id,
                    event_type="founder_decision_created",
                    status=status.strip(),
                    actor_agent_id=owner_agent_id,
                    source_table="founder_decisions",
                    source_id=decision_id,
                    summary=f"Founder decision opened: {title.strip()}",
                    payload={
                        "decision_type": normalized_type,
                        "status": status.strip(),
                        "stage_id": normalized_stage_id,
                        "artifact_id": normalized_artifact_id,
                        "requires_founder_approval": founder_required,
                    },
                )
        return decision_id

    def update_founder_decision(
        self,
        decision_id: str,
        status: str,
        decision: str,
        *,
        founder_confirmed: bool = False,
    ) -> None:
        current = self.get_founder_decision(decision_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown founder decision: {decision_id}")
        if status not in {"needed", "blocked"} | RESOLVED_DECISION_STATUSES:
            raise ValueError(f"Unsupported founder decision status: {status}")
        if status in RESOLVED_DECISION_STATUSES and not decision.strip():
            raise ValueError("A decision note is required before resolving a decision.")
        if (
            current["requires_founder_approval"]
            and status in RESOLVED_DECISION_STATUSES
            and not founder_confirmed
        ):
            raise ValueError(
                "Founder confirmation is required before resolving this decision."
            )
        now = utc_now()
        resolved_at = now if status in RESOLVED_DECISION_STATUSES else None
        resolution_note = decision.strip() if status in RESOLVED_DECISION_STATUSES else ""
        assert_no_secret_values({"status": status, "decision": decision})
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE founder_decisions
                SET status = ?,
                    decision = ?,
                    resolved_at = ?,
                    resolution_note = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status.strip(),
                    decision.strip(),
                    resolved_at,
                    resolution_note,
                    now,
                    decision_id,
                ),
            )
            if current.get("project_id"):
                event_type = (
                    "founder_decision_resolved"
                    if status in RESOLVED_DECISION_STATUSES
                    else "founder_decision_updated"
                )
                self._insert_audit_event(
                    connection,
                    project_id=current["project_id"],
                    event_type=event_type,
                    status=status.strip(),
                    actor_agent_id=current["owner_agent_id"],
                    source_table="founder_decisions",
                    source_id=decision_id,
                    summary=f"Founder decision {status.strip()}: {current['title']}",
                    payload={
                        "decision_type": current["decision_type"],
                        "status": status.strip(),
                        "stage_id": current.get("stage_id") or "",
                        "artifact_id": current.get("artifact_id") or "",
                        "resolved_at": resolved_at or "",
                    },
                )

    def resolve_project_stage_decisions(
        self,
        *,
        project_id: str,
        stage_id: str,
        status: str,
        decision: str,
        decision_types: set[str] | None = None,
    ) -> int:
        if decision_types:
            unsupported = decision_types - SUPPORTED_DECISION_TYPES
            if unsupported:
                raise ValueError(f"Unsupported founder decision types: {unsupported}")
        decisions = self.list_founder_decisions(
            project_id=project_id,
            stage_id=stage_id,
            include_resolved=False,
        )
        resolved_count = 0
        for item in decisions:
            if decision_types and item["decision_type"] not in decision_types:
                continue
            self.update_founder_decision(
                item["id"],
                status=status,
                decision=decision,
                founder_confirmed=True,
            )
            resolved_count += 1
        return resolved_count

    def list_agent_work_items(
        self,
        limit: int | None = None,
        *,
        project_id: str = "",
        owner_agent_id: str = "",
        status: str = "",
        include_done: bool = True,
    ) -> list[dict]:
        query = """
            SELECT agent_work_items.*,
                   owners.name AS owner_name,
                   owners.role AS owner_role,
                   owners.hermes_command AS owner_command,
                   owners.slack_channel AS owner_slack_channel,
                   creators.name AS creator_name,
                   company_projects.name AS project_name,
                   product_wizard_stage_definitions.name AS stage_name,
                   founder_decisions.title AS decision_title,
                   founder_decisions.status AS decision_status
            FROM agent_work_items
            JOIN agents AS owners
                ON owners.id = agent_work_items.owner_agent_id
            LEFT JOIN agents AS creators
                ON creators.id = agent_work_items.created_by_agent_id
            LEFT JOIN company_projects
                ON company_projects.id = agent_work_items.project_id
            LEFT JOIN product_wizard_stage_definitions
                ON product_wizard_stage_definitions.id = agent_work_items.stage_id
            LEFT JOIN founder_decisions
                ON founder_decisions.id = agent_work_items.decision_id
        """
        filters = []
        parameters: list[object] = []
        if project_id:
            filters.append("agent_work_items.project_id = ?")
            parameters.append(project_id)
        if owner_agent_id:
            filters.append("agent_work_items.owner_agent_id = ?")
            parameters.append(owner_agent_id)
        if status:
            filters.append("agent_work_items.status = ?")
            parameters.append(validate_queue_state(status))
        elif not include_done:
            filters.append("agent_work_items.status != ?")
            parameters.append("done")
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += """
            ORDER BY
                CASE agent_work_items.status
                    WHEN 'blocked' THEN 1
                    WHEN 'needs_review' THEN 2
                    WHEN 'running' THEN 3
                    WHEN 'assigned' THEN 4
                    WHEN 'planned' THEN 5
                    WHEN 'approved' THEN 6
                    WHEN 'rejected' THEN 7
                    ELSE 8
                END,
                agent_work_items.founder_action_required DESC,
                CASE agent_work_items.priority
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    ELSE 4
                END,
                agent_work_items.updated_at DESC,
                agent_work_items.title
        """
        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)
        with connect(self.database_path) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [decode_agent_work_item(row) for row in rows]

    def get_agent_work_item(self, work_item_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT agent_work_items.*,
                       owners.name AS owner_name,
                       owners.role AS owner_role,
                       owners.hermes_command AS owner_command,
                       owners.slack_channel AS owner_slack_channel,
                       creators.name AS creator_name,
                       company_projects.name AS project_name,
                       product_wizard_stage_definitions.name AS stage_name,
                       founder_decisions.title AS decision_title,
                       founder_decisions.status AS decision_status
                FROM agent_work_items
                JOIN agents AS owners
                    ON owners.id = agent_work_items.owner_agent_id
                LEFT JOIN agents AS creators
                    ON creators.id = agent_work_items.created_by_agent_id
                LEFT JOIN company_projects
                    ON company_projects.id = agent_work_items.project_id
                LEFT JOIN product_wizard_stage_definitions
                    ON product_wizard_stage_definitions.id = agent_work_items.stage_id
                LEFT JOIN founder_decisions
                    ON founder_decisions.id = agent_work_items.decision_id
                WHERE agent_work_items.id = ?
                """,
                (work_item_id,),
            ).fetchone()
        return decode_agent_work_item(row) if row else None

    def agent_work_queue_summary(self) -> dict:
        items = self.list_agent_work_items()
        by_status = {state: 0 for state in QUEUE_STATES}
        for item in items:
            by_status[item["status"]] += 1
        return {
            "total": len(items),
            "open": sum(
                count
                for state, count in by_status.items()
                if state not in {"approved", "rejected", "done"}
            ),
            "blocked": by_status["blocked"],
            "needs_review": by_status["needs_review"],
            "founder_required": sum(
                1
                for item in items
                if item["founder_action_required"]
                and item["status"] not in {"approved", "rejected", "done"}
            ),
            "by_status": by_status,
        }

    def create_agent_work_item(
        self,
        *,
        title: str,
        owner_agent_id: str,
        summary: str,
        status: str = "planned",
        priority: str = "medium",
        created_by_agent_id: str | None = "chief-of-staff",
        project_id: str | None = None,
        stage_id: str | None = None,
        artifact_id: str | None = None,
        decision_id: str | None = None,
        task_id: str | None = None,
        document_id: str | None = None,
        source: str = "manual",
        source_key: str | None = None,
        blocked_reason: str = "",
        blocked_owner: str = "",
        founder_action_required: bool = False,
        external_handoff_status: str = "dashboard_source_of_truth",
        slack_channel: str = "",
        telegram_policy: str = "",
    ) -> str:
        normalized_status = validate_queue_state(status)
        normalized_priority = validate_queue_priority(priority)
        self.assert_agent_exists(owner_agent_id)
        if created_by_agent_id:
            self.assert_agent_exists(created_by_agent_id)
        if project_id and self.get_project(project_id) is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        if decision_id and self.get_founder_decision(decision_id) is None:
            raise sqlite3.IntegrityError(f"Unknown founder decision: {decision_id}")
        if task_id and self.get_task(task_id) is None:
            raise sqlite3.IntegrityError(f"Unknown task: {task_id}")
        if normalized_status == "blocked" and not blocked_reason.strip():
            raise ValueError("Blocked work items require a blocker reason.")
        if not title.strip() or not summary.strip():
            raise ValueError("Queue work items require a title and summary.")
        assert_no_secret_values(
            {
                "title": title,
                "summary": summary,
                "status": normalized_status,
                "priority": normalized_priority,
                "source": source,
                "blocked_reason": blocked_reason,
                "blocked_owner": blocked_owner,
                "external_handoff_status": external_handoff_status,
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
            }
        )
        work_item_id = f"work-{uuid4().hex[:10]}"
        resolved_source_key = source_key or f"manual:{work_item_id}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO agent_work_items (
                    id, source_key, title, status, priority, owner_agent_id,
                    created_by_agent_id, project_id, stage_id, artifact_id,
                    decision_id, task_id, document_id, source, summary,
                    blocked_reason, blocked_owner, founder_action_required,
                    external_handoff_status, slack_channel, telegram_policy,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    work_item_id,
                    resolved_source_key.strip(),
                    title.strip(),
                    normalized_status,
                    normalized_priority,
                    owner_agent_id,
                    created_by_agent_id,
                    (project_id or "").strip() or None,
                    (stage_id or "").strip() or None,
                    (artifact_id or "").strip() or None,
                    (decision_id or "").strip() or None,
                    (task_id or "").strip() or None,
                    (document_id or "").strip() or None,
                    source.strip(),
                    summary.strip(),
                    blocked_reason.strip(),
                    blocked_owner.strip(),
                    1 if founder_action_required or normalized_status == "needs_review" else 0,
                    external_handoff_status.strip(),
                    slack_channel.strip(),
                    telegram_policy.strip(),
                    now,
                    now,
                ),
            )
        return work_item_id

    def update_agent_work_item(
        self,
        work_item_id: str,
        *,
        status: str,
        priority: str | None = None,
        owner_agent_id: str | None = None,
        blocked_reason: str = "",
        blocked_owner: str = "",
        founder_action_required: bool = False,
        founder_confirmed: bool = False,
    ) -> None:
        current = self.get_agent_work_item(work_item_id)
        if current is None:
            raise sqlite3.IntegrityError(f"Unknown agent work item: {work_item_id}")
        normalized_status = validate_queue_transition(
            current["status"],
            status,
            founder_confirmed=founder_confirmed,
        )
        normalized_priority = (
            validate_queue_priority(priority) if priority else current["priority"]
        )
        next_owner_agent_id = owner_agent_id or current["owner_agent_id"]
        self.assert_agent_exists(next_owner_agent_id)
        clean_blocked_reason = blocked_reason.strip()
        clean_blocked_owner = blocked_owner.strip()
        if normalized_status == "blocked" and not clean_blocked_reason:
            raise ValueError("Blocked work items require a blocker reason.")
        if normalized_status != "blocked":
            clean_blocked_reason = ""
            clean_blocked_owner = ""
        next_founder_required = founder_action_required or normalized_status == "needs_review"
        if normalized_status in {"approved", "rejected", "done"}:
            next_founder_required = False
        assert_no_secret_values(
            {
                "status": normalized_status,
                "priority": normalized_priority,
                "blocked_reason": clean_blocked_reason,
                "blocked_owner": clean_blocked_owner,
            }
        )
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE agent_work_items
                SET status = ?,
                    priority = ?,
                    owner_agent_id = ?,
                    blocked_reason = ?,
                    blocked_owner = ?,
                    founder_action_required = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    normalized_status,
                    normalized_priority,
                    next_owner_agent_id,
                    clean_blocked_reason,
                    clean_blocked_owner,
                    1 if next_founder_required else 0,
                    utc_now(),
                    work_item_id,
                ),
            )

    def sync_project_wizard_work_items(self, project_id: str) -> int:
        project = self.get_project(project_id)
        if project is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        stages = self.list_project_wizard_stages(project_id)
        if not stages:
            return 0

        payloads = []
        for stage in stages:
            latest_artifact = self.latest_project_stage_artifact(
                project_id,
                stage["stage_id"],
            )
            decision_id = None
            if latest_artifact:
                decisions = self.list_founder_decisions(
                    project_id=project_id,
                    stage_id=stage["stage_id"],
                    artifact_id=latest_artifact["id"],
                    include_resolved=False,
                    limit=1,
                )
                decision_id = decisions[0]["id"] if decisions else None
            status, priority, summary, blocked_reason, blocked_owner = (
                self._wizard_queue_state(stage, bool(latest_artifact), project["name"])
            )
            founder_required = bool(decision_id) or status == "needs_review"
            payloads.append(
                {
                    "source_key": f"product_wizard:{project_id}:{stage['stage_id']}",
                    "title": f"{stage['name']} for {project['name']}",
                    "status": status,
                    "priority": priority,
                    "owner_agent_id": stage["owner_agent_id"],
                    "created_by_agent_id": "chief-of-staff",
                    "project_id": project_id,
                    "stage_id": stage["stage_id"],
                    "artifact_id": latest_artifact["id"] if latest_artifact else None,
                    "decision_id": decision_id,
                    "source": "product_wizard",
                    "summary": summary,
                    "blocked_reason": blocked_reason,
                    "blocked_owner": blocked_owner,
                    "founder_action_required": 1 if founder_required else 0,
                    "external_handoff_status": "dashboard_source_of_truth",
                    "slack_channel": (
                        "#decisions"
                        if founder_required
                        else stage["owner_slack_channel"]
                    ),
                    "telegram_policy": (
                        "Telegram only if this queue item blocks launch."
                        if founder_required
                        else "Dashboard remains source of truth; no external alert sent."
                    ),
                }
            )

        now = utc_now()
        with connect(self.database_path) as connection:
            for payload in payloads:
                assert_no_secret_values(
                    {
                        "title": payload["title"],
                        "summary": payload["summary"],
                        "blocked_reason": payload["blocked_reason"],
                        "blocked_owner": payload["blocked_owner"],
                        "slack_channel": payload["slack_channel"],
                        "telegram_policy": payload["telegram_policy"],
                    }
                )
                connection.execute(
                    """
                    INSERT INTO agent_work_items (
                        id, source_key, title, status, priority, owner_agent_id,
                        created_by_agent_id, project_id, stage_id, artifact_id,
                        decision_id, task_id, document_id, source, summary,
                        blocked_reason, blocked_owner, founder_action_required,
                        external_handoff_status, slack_channel, telegram_policy,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_key) DO UPDATE SET
                        title = excluded.title,
                        status = excluded.status,
                        priority = excluded.priority,
                        owner_agent_id = excluded.owner_agent_id,
                        artifact_id = excluded.artifact_id,
                        decision_id = excluded.decision_id,
                        summary = excluded.summary,
                        blocked_reason = excluded.blocked_reason,
                        blocked_owner = excluded.blocked_owner,
                        founder_action_required = excluded.founder_action_required,
                        external_handoff_status = excluded.external_handoff_status,
                        slack_channel = excluded.slack_channel,
                        telegram_policy = excluded.telegram_policy,
                        updated_at = excluded.updated_at
                    """,
                    (
                        f"work-{uuid4().hex[:10]}",
                        payload["source_key"],
                        payload["title"],
                        payload["status"],
                        payload["priority"],
                        payload["owner_agent_id"],
                        payload["created_by_agent_id"],
                        payload["project_id"],
                        payload["stage_id"],
                        payload["artifact_id"],
                        payload["decision_id"],
                        None,
                        None,
                        payload["source"],
                        payload["summary"],
                        payload["blocked_reason"],
                        payload["blocked_owner"],
                        payload["founder_action_required"],
                        payload["external_handoff_status"],
                        payload["slack_channel"],
                        payload["telegram_policy"],
                        now,
                        now,
                    ),
                )
        return len(payloads)

    def _wizard_queue_state(
        self,
        stage: dict,
        has_artifact: bool,
        project_name: str,
    ) -> tuple[str, str, str, str, str]:
        stage_status = stage["status"]
        owner = stage["owner_name"]
        stage_name = stage["name"]
        if stage_status == "waiting":
            return (
                "planned",
                "medium",
                f"{stage_name} is planned for {project_name} after prior stage approval.",
                "",
                "",
            )
        if stage_status == "ready":
            return (
                "assigned",
                "high",
                (
                    f"{stage_name} is ready for {owner}. This queue item is read-first "
                    "and does not start live Hermes execution."
                ),
                "",
                "",
            )
        if stage_status == "draft" and has_artifact:
            return (
                "needs_review",
                "urgent",
                (
                    f"{stage_name} artifact is ready for founder review. Approval is "
                    "tracked through the project decision record."
                ),
                "",
                "",
            )
        if stage_status in {"needs_revision", "blocked"}:
            reason = stage["revision_notes"].strip() or (
                f"{stage_name} cannot proceed until the blocker is resolved."
            )
            return ("blocked", "urgent", reason, reason, owner)
        if stage_status == "approved":
            return (
                "approved",
                "medium",
                f"{stage_name} has founder approval and can feed downstream planning.",
                "",
                "",
            )
        return (
            "planned",
            "medium",
            f"{stage_name} is tracked for {project_name}.",
            "",
            "",
        )

    def founder_decision_queue_ready(self) -> bool:
        decisions = self.list_founder_decisions()
        return bool(decisions) and all(
            item["status"] in RESOLVED_DECISION_STATUSES and item["decision"].strip()
            for item in decisions
        )

    def list_tasks(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT tasks.*, agents.name AS owner_name
                FROM tasks
                JOIN agents ON agents.id = tasks.owner_agent_id
                ORDER BY tasks.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_task(self, task_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT tasks.*, agents.name AS owner_name, agents.hermes_command AS owner_command
                FROM tasks
                JOIN agents ON agents.id = tasks.owner_agent_id
                WHERE tasks.id = ?
                """,
                (task_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_task(
        self,
        title: str,
        owner_agent_id: str,
        priority: str,
        summary: str,
        status: str = "planned",
    ) -> str:
        task_id = f"task-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id, title, owner_agent_id, kanban_task_id, status, priority, summary,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, title, owner_agent_id, None, status, priority, summary, now, now),
            )
        return task_id

    def attach_kanban_task(self, task_id: str, kanban_task_id: str) -> None:
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE tasks
                SET kanban_task_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (kanban_task_id, utc_now(), task_id),
            )

    def list_documents(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT documents.*, agents.name AS owner_name
                FROM documents
                JOIN agents ON agents.id = documents.owner_agent_id
                ORDER BY documents.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def create_document(
        self,
        title: str,
        doc_type: str,
        owner_agent_id: str,
        body: str,
        status: str = "draft",
    ) -> str:
        document_id = f"doc-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    id, title, doc_type, owner_agent_id, status, body, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, title, doc_type, owner_agent_id, status, body, now, now),
            )
        return document_id

    def list_runs(self, limit: int = 12) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT runs.*, agents.name AS agent_name
                FROM runs
                JOIN agents ON agents.id = runs.agent_id
                ORDER BY runs.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def latest_runs_by_type(self, run_type: str) -> dict[str, dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT runs.*, agents.name AS agent_name
                FROM runs
                JOIN agents ON agents.id = runs.agent_id
                WHERE runs.run_type = ?
                ORDER BY runs.created_at DESC
                """,
                (run_type,),
            ).fetchall()
        latest: dict[str, dict] = {}
        for row in rows:
            run = dict(row)
            latest.setdefault(run["agent_id"], run)
        return latest

    def create_run(self, agent_id: str, run_type: str, prompt: str) -> str:
        run_id = f"run-{uuid4().hex[:10]}"
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, agent_id, run_type, prompt, status, output, error, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, agent_id, run_type, prompt, "running", "", "", utc_now()),
            )
        return run_id

    def complete_run(self, run_id: str, output: str, error: str = "") -> None:
        status = "failed" if error else "completed"
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE runs
                SET status = ?, output = ?, error = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, output, error, utc_now(), run_id),
            )

    def assert_agent_exists(self, agent_id: str) -> None:
        if self.get_agent(agent_id) is None:
            raise sqlite3.IntegrityError(f"Unknown agent: {agent_id}")

    def list_integrations(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT integration_configs.*, agents.name AS owner_name
                FROM integration_configs
                LEFT JOIN agents ON agents.id = integration_configs.owner_agent_id
                ORDER BY
                    CASE category
                        WHEN 'runtime' THEN 1
                        WHEN 'slack' THEN 2
                        WHEN 'telegram' THEN 3
                        WHEN 'kanban' THEN 4
                        WHEN 'schedule' THEN 5
                        ELSE 9
                    END,
                    integration_configs.name
                """
            ).fetchall()
        integrations = []
        for row in rows:
            data = dict(row)
            data["required_inputs"] = json.loads(data.pop("required_inputs_json"))
            integrations.append(data)
        return integrations

    def update_integration_status(self, integration_id: str, status: str) -> None:
        with connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE integration_configs
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, utc_now(), integration_id),
            )

    def list_setup_steps(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM setup_steps ORDER BY sort_order, name"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_setup_inputs(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM setup_inputs ORDER BY sort_order, key"
            ).fetchall()
        return [dict(row) for row in rows]

    def setup_input_map(self) -> dict[str, str]:
        return {item["key"]: item["value"] for item in self.list_setup_inputs()}

    def update_setup_inputs(self, values: dict[str, str]) -> None:
        allowed_keys = {item["key"] for item in self.list_setup_inputs()}
        now = utc_now()
        with connect(self.database_path) as connection:
            for key, value in values.items():
                if key not in allowed_keys:
                    continue
                connection.execute(
                    """
                    UPDATE setup_inputs
                    SET value = ?, updated_at = ?
                    WHERE key = ?
                    """,
                    (value.strip(), now, key),
                )

    def setup_input_completion(self) -> dict:
        items = self.list_setup_inputs()
        required = [
            item
            for item in items
            if item["required"] and item["secret_policy"] == "non_secret"
        ]
        completed = [item for item in required if item["value"].strip()]
        return {
            "completed": len(completed),
            "required": len(required),
            "ready": len(completed) == len(required),
        }

    def list_workflow_templates(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT workflow_templates.*, agents.name AS owner_name
                FROM workflow_templates
                JOIN agents ON agents.id = workflow_templates.owner_agent_id
                ORDER BY workflow_templates.sort_order, workflow_templates.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_product_wizard_stage_definitions(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT product_wizard_stage_definitions.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command
                FROM product_wizard_stage_definitions
                JOIN agents
                    ON agents.id = product_wizard_stage_definitions.owner_agent_id
                ORDER BY product_wizard_stage_definitions.sort_order,
                         product_wizard_stage_definitions.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_projects(self) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT company_projects.*,
                       COUNT(project_workflow_items.id) AS workflow_count
                FROM company_projects
                LEFT JOIN project_workflow_items
                    ON project_workflow_items.project_id = company_projects.id
                GROUP BY company_projects.id
                ORDER BY company_projects.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM company_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return decode_project(row) if row else None

    def list_project_workflow_items(self, project_id: str) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT project_workflow_items.*,
                       agents.name AS owner_name,
                       workflow_templates.phase,
                       workflow_templates.doc_type,
                       tasks.kanban_task_id
                FROM project_workflow_items
                JOIN agents ON agents.id = project_workflow_items.owner_agent_id
                JOIN workflow_templates
                    ON workflow_templates.id = project_workflow_items.template_id
                LEFT JOIN tasks ON tasks.id = project_workflow_items.task_id
                WHERE project_workflow_items.project_id = ?
                ORDER BY project_workflow_items.sort_order, project_workflow_items.title
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_project_with_workflow(self, name: str, founder_idea: str) -> str:
        project_id = f"proj-{uuid4().hex[:10]}"
        now = utc_now()
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO company_projects (
                    id, name, founder_idea, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, name, founder_idea, "planning", now, now),
            )
            templates = connection.execute(
                "SELECT * FROM workflow_templates ORDER BY sort_order, name"
            ).fetchall()
            for template in templates:
                title = template["title_template"].format(project_name=name, idea=founder_idea)
                prompt = template["prompt_template"].format(project_name=name, idea=founder_idea)
                task_id = f"task-{uuid4().hex[:10]}"
                document_id = f"doc-{uuid4().hex[:10]}"
                workflow_item_id = f"wf-{uuid4().hex[:10]}"
                connection.execute(
                    """
                    INSERT INTO tasks (
                        id, title, owner_agent_id, kanban_task_id, status, priority,
                        summary, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        title,
                        template["owner_agent_id"],
                        None,
                        "planned",
                        template["priority"],
                        prompt,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO documents (
                        id, title, doc_type, owner_agent_id, status, body,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        title,
                        template["doc_type"],
                        template["owner_agent_id"],
                        "draft",
                        prompt,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO project_workflow_items (
                        id, project_id, template_id, owner_agent_id, task_id,
                        document_id, title, status, sort_order, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workflow_item_id,
                        project_id,
                        template["id"],
                        template["owner_agent_id"],
                        task_id,
                        document_id,
                        title,
                        "planned",
                        template["sort_order"],
                        now,
                        now,
                    ),
                )
        return project_id

    def create_structured_project(
        self,
        name: str,
        founder_idea: str,
        intake: dict | None = None,
    ) -> str:
        project_id = f"proj-{uuid4().hex[:10]}"
        now = utc_now()
        intake_text = serialize_wizard_json_content(intake or {})
        assert_no_secret_values(
            {
                "name": name,
                "founder_idea": founder_idea,
                "intake": intake_text,
            }
        )
        with connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO company_projects (
                    id, name, founder_idea, intake_json, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    name.strip(),
                    founder_idea.strip(),
                    intake_text,
                    "wizard_active",
                    now,
                    now,
                ),
            )
            definitions = connection.execute(
                """
                SELECT *
                FROM product_wizard_stage_definitions
                ORDER BY sort_order, id
                """
            ).fetchall()
            for index, definition in enumerate(definitions):
                connection.execute(
                    """
                    INSERT INTO product_wizard_project_stages (
                        id, project_id, stage_id, owner_agent_id, status,
                        revision_notes, created_at, updated_at, started_at,
                        completed_at, approved_at, revision_requested_at, blocked_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"wiz-stage-{uuid4().hex[:10]}",
                        project_id,
                        definition["id"],
                        definition["owner_agent_id"],
                        "ready" if index == 0 else "waiting",
                        "",
                        now,
                        now,
                        now if index == 0 else None,
                        None,
                        None,
                        None,
                        None,
                    ),
                )
        return project_id

    def ensure_project_workflow_items(self, project_id: str) -> int:
        project = self.get_project(project_id)
        if project is None:
            raise sqlite3.IntegrityError(f"Unknown project: {project_id}")
        with connect(self.database_path) as connection:
            existing = connection.execute(
                "SELECT COUNT(*) AS item_count FROM project_workflow_items WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if existing["item_count"]:
                return 0

            now = utc_now()
            templates = connection.execute(
                "SELECT * FROM workflow_templates ORDER BY sort_order, name"
            ).fetchall()
            for template in templates:
                title = template["title_template"].format(
                    project_name=project["name"],
                    idea=project["founder_idea"],
                )
                prompt = template["prompt_template"].format(
                    project_name=project["name"],
                    idea=project["founder_idea"],
                )
                task_id = f"task-{uuid4().hex[:10]}"
                document_id = f"doc-{uuid4().hex[:10]}"
                workflow_item_id = f"wf-{uuid4().hex[:10]}"
                connection.execute(
                    """
                    INSERT INTO tasks (
                        id, title, owner_agent_id, kanban_task_id, status, priority,
                        summary, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        title,
                        template["owner_agent_id"],
                        None,
                        "planned",
                        template["priority"],
                        prompt,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO documents (
                        id, title, doc_type, owner_agent_id, status, body,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        title,
                        template["doc_type"],
                        template["owner_agent_id"],
                        "draft",
                        prompt,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO project_workflow_items (
                        id, project_id, template_id, owner_agent_id, task_id,
                        document_id, title, status, sort_order, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workflow_item_id,
                        project_id,
                        template["id"],
                        template["owner_agent_id"],
                        task_id,
                        document_id,
                        title,
                        "planned",
                        template["sort_order"],
                        now,
                        now,
                    ),
                )
            connection.execute(
                """
                UPDATE company_projects
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, project_id),
            )
        return len(templates)

    def list_project_wizard_stages(self, project_id: str) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT stages.*,
                       definitions.name,
                       definitions.description,
                       definitions.sort_order,
                       definitions.artifact_type,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command,
                       agents.slack_channel AS owner_slack_channel,
                       latest.id AS latest_artifact_id,
                       latest.version AS latest_artifact_version,
                       latest.status AS latest_artifact_status,
                       latest.created_at AS latest_artifact_created_at,
                       latest.approved_at AS latest_artifact_approved_at
                FROM product_wizard_project_stages AS stages
                JOIN product_wizard_stage_definitions AS definitions
                    ON definitions.id = stages.stage_id
                JOIN agents
                    ON agents.id = stages.owner_agent_id
                LEFT JOIN product_wizard_artifacts AS latest
                    ON latest.project_stage_id = stages.id
                   AND latest.version = (
                        SELECT MAX(version)
                        FROM product_wizard_artifacts
                        WHERE project_stage_id = stages.id
                   )
                WHERE stages.project_id = ?
                ORDER BY definitions.sort_order, definitions.id
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project_wizard_stage(self, project_id: str, stage_id: str) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT stages.*,
                       definitions.name,
                       definitions.description,
                       definitions.sort_order,
                       definitions.artifact_type,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command,
                       agents.slack_channel AS owner_slack_channel,
                       latest.id AS latest_artifact_id,
                       latest.version AS latest_artifact_version,
                       latest.status AS latest_artifact_status,
                       latest.created_at AS latest_artifact_created_at,
                       latest.approved_at AS latest_artifact_approved_at
                FROM product_wizard_project_stages AS stages
                JOIN product_wizard_stage_definitions AS definitions
                    ON definitions.id = stages.stage_id
                JOIN agents
                    ON agents.id = stages.owner_agent_id
                LEFT JOIN product_wizard_artifacts AS latest
                    ON latest.project_stage_id = stages.id
                   AND latest.version = (
                        SELECT MAX(version)
                        FROM product_wizard_artifacts
                        WHERE project_stage_id = stages.id
                   )
                WHERE stages.project_id = ? AND stages.stage_id = ?
                """,
                (project_id, stage_id),
            ).fetchone()
        return dict(row) if row else None

    def list_project_stage_artifacts(self, project_id: str, stage_id: str) -> list[dict]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT artifacts.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command
                FROM product_wizard_artifacts AS artifacts
                JOIN agents ON agents.id = artifacts.owner_agent_id
                WHERE artifacts.project_id = ? AND artifacts.stage_id = ?
                ORDER BY artifacts.version DESC
                """,
                (project_id, stage_id),
            ).fetchall()
        return [decode_wizard_artifact(row) for row in rows]

    def get_project_wizard_artifact(
        self,
        project_id: str,
        artifact_id: str,
    ) -> dict | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT artifacts.*,
                       agents.name AS owner_name,
                       agents.hermes_command AS owner_command,
                       definitions.name AS stage_name,
                       stages.revision_notes AS stage_revision_notes
                FROM product_wizard_artifacts AS artifacts
                JOIN agents ON agents.id = artifacts.owner_agent_id
                JOIN product_wizard_project_stages AS stages
                    ON stages.id = artifacts.project_stage_id
                JOIN product_wizard_stage_definitions AS definitions
                    ON definitions.id = artifacts.stage_id
                WHERE artifacts.project_id = ? AND artifacts.id = ?
                """,
                (project_id, artifact_id),
            ).fetchone()
        return decode_wizard_artifact(row) if row else None

    def latest_project_stage_artifact(
        self,
        project_id: str,
        stage_id: str,
    ) -> dict | None:
        artifacts = self.list_project_stage_artifacts(project_id, stage_id)
        return artifacts[0] if artifacts else None

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
