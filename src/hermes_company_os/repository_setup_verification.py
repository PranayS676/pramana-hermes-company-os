from __future__ import annotations

import sqlite3

from hermes_company_os.database import connect
from hermes_company_os.repository_support import (
    utc_now,
)


class SetupVerificationMixin:
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
