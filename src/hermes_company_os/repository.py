from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from hermes_company_os.database import connect, decode_capabilities, decode_many
from hermes_company_os.founder_decisions import (
    RESOLVED_DECISION_STATUSES,
    SUPPORTED_DECISION_TYPES,
    founder_only_decision_type,
    normalize_decision_type,
)
from hermes_company_os.secret_guard import assert_no_secret_values


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


class CompanyRepository:
    def __init__(self, database_path: Path):
        self.database_path = database_path

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
                    (project_id or "").strip() or None,
                    (stage_id or "").strip() or None,
                    (artifact_id or "").strip() or None,
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

    def latest_project_stage_artifact(
        self,
        project_id: str,
        stage_id: str,
    ) -> dict | None:
        artifacts = self.list_project_stage_artifacts(project_id, stage_id)
        return artifacts[0] if artifacts else None

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
            else:
                project_status = "wizard_active"
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

    def request_stage_revision(
        self,
        project_id: str,
        stage_id: str,
        notes: str = "",
    ) -> None:
        assert_no_secret_values({"revision_notes": notes})
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
