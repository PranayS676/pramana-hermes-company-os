from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from hermes_company_os.profile_acceptance import ROLE_CASES
from hermes_company_os.seeds import (
    DEFAULT_AGENT_RELATIONSHIPS,
    DEFAULT_AGENTS,
    DEFAULT_FOUNDER_DECISIONS,
    DEFAULT_INTEGRATIONS,
    DEFAULT_PRODUCT_WIZARD_STAGES,
    DEFAULT_SETUP_INPUTS,
    DEFAULT_SETUP_STEPS,
    DEFAULT_STANDUPS,
    DEFAULT_WORKFLOW_TEMPLATES,
)

AGENT_WORK_ITEMS_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_work_items (
    id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    owner_agent_id TEXT NOT NULL REFERENCES agents(id),
    created_by_agent_id TEXT REFERENCES agents(id),
    project_id TEXT REFERENCES company_projects(id) ON DELETE CASCADE,
    stage_id TEXT,
    artifact_id TEXT,
    decision_id TEXT REFERENCES founder_decisions(id),
    task_id TEXT REFERENCES tasks(id),
    document_id TEXT REFERENCES documents(id),
    source TEXT NOT NULL,
    summary TEXT NOT NULL,
    blocked_reason TEXT NOT NULL DEFAULT '',
    blocked_owner TEXT NOT NULL DEFAULT '',
    founder_action_required INTEGER NOT NULL DEFAULT 0,
    external_handoff_status TEXT NOT NULL DEFAULT 'dashboard_source_of_truth',
    slack_channel TEXT NOT NULL DEFAULT '',
    telegram_policy TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

GENERATION_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS generation_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES company_projects(id) ON DELETE CASCADE,
    stage_id TEXT NOT NULL REFERENCES product_wizard_stage_definitions(id),
    artifact_id TEXT REFERENCES product_wizard_artifacts(id) ON DELETE SET NULL,
    generation_mode TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    source_artifact_ids_json TEXT NOT NULL DEFAULT '[]',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_generation_runs_project_stage_created
ON generation_runs(project_id, stage_id, created_at DESC);
"""

CODEX_EXECUTION_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS codex_execution_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES company_projects(id) ON DELETE CASCADE,
    decision_id TEXT NOT NULL REFERENCES founder_decisions(id),
    package_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'blocked', 'completed', 'failed', 'cancelled')
    ),
    runner_mode TEXT NOT NULL,
    external_execution_enabled INTEGER NOT NULL DEFAULT 0,
    branch_name TEXT NOT NULL,
    worktree_path TEXT NOT NULL,
    source_artifact_ids_json TEXT NOT NULL DEFAULT '[]',
    command_preview_json TEXT NOT NULL DEFAULT '[]',
    approval_snapshot_json TEXT NOT NULL DEFAULT '{}',
    audit_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_codex_execution_runs_project_created
ON codex_execution_runs(project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_codex_execution_runs_decision
ON codex_execution_runs(decision_id);
"""

PROJECT_REVIEW_RECORDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_review_records (
    id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL REFERENCES company_projects(id) ON DELETE CASCADE,
    review_batch_id TEXT NOT NULL,
    reviewer_agent_id TEXT NOT NULL,
    reviewer_name TEXT NOT NULL,
    reviewer_role TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('approved', 'needs_revision', 'blocked')),
    summary TEXT NOT NULL,
    artifact_ids_json TEXT NOT NULL DEFAULT '[]',
    checks_json TEXT NOT NULL DEFAULT '[]',
    findings_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_review_records_project_batch
ON project_review_records(project_id, review_batch_id);

CREATE INDEX IF NOT EXISTS idx_project_review_records_project_created
ON project_review_records(project_id, created_at DESC);
"""

PROJECT_MEMORY_ENTRIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS project_memory_entries (
    id TEXT PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    project_id TEXT REFERENCES company_projects(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    owner_agent_id TEXT NOT NULL REFERENCES agents(id),
    source TEXT NOT NULL,
    source_artifact_id TEXT DEFAULT '',
    source_decision_id TEXT REFERENCES founder_decisions(id),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'retired')),
    pinned INTEGER NOT NULL DEFAULT 0,
    review_after TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_memory_entries_project_status
ON project_memory_entries(project_id, status);

CREATE INDEX IF NOT EXISTS idx_project_memory_entries_category
ON project_memory_entries(category);

CREATE INDEX IF NOT EXISTS idx_project_memory_entries_updated
ON project_memory_entries(updated_at DESC);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                slack_channel TEXT NOT NULL,
                telegram_policy TEXT NOT NULL,
                hermes_command TEXT NOT NULL,
                description TEXT NOT NULL,
                soul TEXT NOT NULL,
                capabilities_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_relationships (
                id TEXT PRIMARY KEY,
                manager_agent_id TEXT NOT NULL REFERENCES agents(id),
                member_agent_id TEXT NOT NULL REFERENCES agents(id),
                relationship_type TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                responsibility TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS standup_schedules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                timezone TEXT NOT NULL,
                slack_channel TEXT NOT NULL,
                telegram_policy TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                kanban_task_id TEXT,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                run_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                output TEXT NOT NULL,
                error TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS integration_configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                owner_agent_id TEXT REFERENCES agents(id),
                status TEXT NOT NULL,
                required_inputs_json TEXT NOT NULL,
                setup_notes TEXT NOT NULL,
                validation_command TEXT NOT NULL,
                docs_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS setup_steps (
                id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                description TEXT NOT NULL,
                command TEXT NOT NULL,
                docs_url TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS setup_inputs (
                key TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                label TEXT NOT NULL,
                value TEXT NOT NULL,
                required INTEGER NOT NULL,
                secret_policy TEXT NOT NULL,
                help_text TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_model_preferences (
                agent_id TEXT PRIMARY KEY REFERENCES agents(id),
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                fallback_provider TEXT NOT NULL,
                fallback_model TEXT NOT NULL,
                auth_method TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS external_secret_requirements (
                id TEXT PRIMARY KEY,
                owner_agent_id TEXT REFERENCES agents(id),
                category TEXT NOT NULL,
                label TEXT NOT NULL,
                environment_key TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messaging_verification_checks (
                id TEXT PRIMARY KEY,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                platform TEXT NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                instructions TEXT NOT NULL,
                evidence TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS schedule_verification_checks (
                id TEXT PRIMARY KEY,
                schedule_id TEXT NOT NULL REFERENCES standup_schedules(id),
                check_type TEXT NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                instructions TEXT NOT NULL,
                evidence TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS kanban_verification_checks (
                id TEXT PRIMARY KEY,
                check_type TEXT NOT NULL,
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                instructions TEXT NOT NULL,
                evidence TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS profile_acceptance_checks (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                instructions TEXT NOT NULL,
                evidence TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS profile_installation_checks (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL REFERENCES agents(id),
                label TEXT NOT NULL,
                status TEXT NOT NULL,
                instructions TEXT NOT NULL,
                evidence TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS founder_decisions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                urgency TEXT NOT NULL,
                decision_type TEXT NOT NULL DEFAULT 'operating_decision',
                source TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                project_id TEXT,
                stage_id TEXT,
                artifact_id TEXT,
                slack_channel TEXT NOT NULL,
                telegram_policy TEXT NOT NULL,
                context TEXT NOT NULL,
                evidence TEXT NOT NULL DEFAULT '',
                decision TEXT NOT NULL,
                requires_founder_approval INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT,
                resolution_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS workflow_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phase TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                sort_order INTEGER NOT NULL,
                doc_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                title_template TEXT NOT NULL,
                prompt_template TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS company_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                founder_idea TEXT NOT NULL,
                intake_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS project_workflow_items (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES company_projects(id),
                template_id TEXT NOT NULL REFERENCES workflow_templates(id),
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                task_id TEXT REFERENCES tasks(id),
                document_id TEXT REFERENCES documents(id),
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS product_wizard_stage_definitions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                sort_order INTEGER NOT NULL,
                artifact_type TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS product_wizard_project_stages (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES company_projects(id) ON DELETE CASCADE,
                stage_id TEXT NOT NULL REFERENCES product_wizard_stage_definitions(id),
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                status TEXT NOT NULL,
                revision_notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                approved_at TEXT,
                revision_requested_at TEXT,
                blocked_at TEXT,
                UNIQUE(project_id, stage_id)
            );

            CREATE TABLE IF NOT EXISTS product_wizard_artifacts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES company_projects(id) ON DELETE CASCADE,
                project_stage_id TEXT NOT NULL
                    REFERENCES product_wizard_project_stages(id) ON DELETE CASCADE,
                stage_id TEXT NOT NULL REFERENCES product_wizard_stage_definitions(id),
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                markdown_content TEXT NOT NULL,
                json_content TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL REFERENCES agents(id),
                created_at TEXT NOT NULL,
                approved_at TEXT,
                UNIQUE(project_stage_id, version)
            );
            """
        )
        connection.executescript(AGENT_WORK_ITEMS_SCHEMA)
        connection.executescript(GENERATION_RUNS_SCHEMA)
        connection.executescript(CODEX_EXECUTION_RUNS_SCHEMA)
        connection.executescript(PROJECT_REVIEW_RECORDS_SCHEMA)
        connection.executescript(PROJECT_MEMORY_ENTRIES_SCHEMA)
        ensure_schema(connection)
        seed_defaults(connection)


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(AGENT_WORK_ITEMS_SCHEMA)
    connection.executescript(GENERATION_RUNS_SCHEMA)
    connection.executescript(CODEX_EXECUTION_RUNS_SCHEMA)
    connection.executescript(PROJECT_REVIEW_RECORDS_SCHEMA)
    connection.executescript(PROJECT_MEMORY_ENTRIES_SCHEMA)
    task_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
    }
    if "kanban_task_id" not in task_columns:
        connection.execute("ALTER TABLE tasks ADD COLUMN kanban_task_id TEXT")
    project_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(company_projects)").fetchall()
    }
    if "intake_json" not in project_columns:
        connection.execute(
            "ALTER TABLE company_projects ADD COLUMN intake_json TEXT NOT NULL DEFAULT '{}'"
        )
    decision_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(founder_decisions)").fetchall()
    }
    decision_column_defaults = {
        "decision_type": "TEXT NOT NULL DEFAULT 'operating_decision'",
        "project_id": "TEXT",
        "stage_id": "TEXT",
        "artifact_id": "TEXT",
        "evidence": "TEXT NOT NULL DEFAULT ''",
        "requires_founder_approval": "INTEGER NOT NULL DEFAULT 0",
        "resolved_at": "TEXT",
        "resolution_note": "TEXT NOT NULL DEFAULT ''",
    }
    for column, definition in decision_column_defaults.items():
        if column not in decision_columns:
            connection.execute(
                f"ALTER TABLE founder_decisions ADD COLUMN {column} {definition}"
            )


def seed_defaults(connection: sqlite3.Connection) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO agents (
            id, name, role, slack_channel, telegram_policy, hermes_command,
            description, soul, capabilities_json
        )
        VALUES (
            :id, :name, :role, :slack_channel, :telegram_policy, :hermes_command,
            :description, :soul, :capabilities
        )
        """,
        DEFAULT_AGENTS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO agent_relationships (
            id, manager_agent_id, member_agent_id, relationship_type,
            sort_order, responsibility
        )
        VALUES (
            :id, :manager_agent_id, :member_agent_id, :relationship_type,
            :sort_order, :responsibility
        )
        """,
        DEFAULT_AGENT_RELATIONSHIPS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO standup_schedules (
            id, name, hour, minute, timezone, slack_channel, telegram_policy
        )
        VALUES (
            :id, :name, :hour, :minute, :timezone, :slack_channel, :telegram_policy
        )
        """,
        DEFAULT_STANDUPS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO integration_configs (
            id, name, category, owner_agent_id, status, required_inputs_json,
            setup_notes, validation_command, docs_url
        )
        VALUES (
            :id, :name, :category, :owner_agent_id, :status, :required_inputs,
            :setup_notes, :validation_command, :docs_url
        )
        """,
        DEFAULT_INTEGRATIONS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO setup_steps (
            id, phase, name, status, owner, sort_order, description, command, docs_url
        )
        VALUES (
            :id, :phase, :name, :status, :owner, :sort_order, :description,
            :command, :docs_url
        )
        """,
        DEFAULT_SETUP_STEPS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO setup_inputs (
            key, group_name, label, value, required, secret_policy, help_text, sort_order
        )
        VALUES (
            :key, :group_name, :label, :value, :required, :secret_policy,
            :help_text, :sort_order
        )
        """,
        DEFAULT_SETUP_INPUTS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO agent_model_preferences (
            agent_id, provider, model, fallback_provider, fallback_model,
            auth_method, status, notes
        )
        VALUES (
            :agent_id, :provider, :model, :fallback_provider, :fallback_model,
            :auth_method, :status, :notes
        )
        """,
        default_model_preferences(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO external_secret_requirements (
            id, owner_agent_id, category, label, environment_key,
            destination, status, notes
        )
        VALUES (
            :id, :owner_agent_id, :category, :label, :environment_key,
            :destination, :status, :notes
        )
        """,
        default_secret_requirements(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO messaging_verification_checks (
            id, owner_agent_id, platform, label, status, instructions, evidence, sort_order
        )
        VALUES (
            :id, :owner_agent_id, :platform, :label, :status,
            :instructions, :evidence, :sort_order
        )
        """,
        default_messaging_checks(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO schedule_verification_checks (
            id, schedule_id, check_type, label, status, instructions, evidence, sort_order
        )
        VALUES (
            :id, :schedule_id, :check_type, :label, :status,
            :instructions, :evidence, :sort_order
        )
        """,
        default_schedule_checks(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO kanban_verification_checks (
            id, check_type, label, status, instructions, evidence, sort_order
        )
        VALUES (
            :id, :check_type, :label, :status, :instructions, :evidence, :sort_order
        )
        """,
        default_kanban_checks(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO profile_acceptance_checks (
            id, agent_id, title, status, instructions, evidence, sort_order
        )
        VALUES (
            :id, :agent_id, :title, :status, :instructions, :evidence, :sort_order
        )
        """,
        default_profile_acceptance_checks(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO profile_installation_checks (
            id, agent_id, label, status, instructions, evidence, sort_order
        )
        VALUES (
            :id, :agent_id, :label, :status, :instructions, :evidence, :sort_order
        )
        """,
        default_profile_installation_checks(),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO founder_decisions (
            id, title, status, urgency, source, owner_agent_id, slack_channel,
            telegram_policy, context, decision
        )
        VALUES (
            :id, :title, :status, :urgency, :source, :owner_agent_id,
            :slack_channel, :telegram_policy, :context, :decision
        )
        """,
        DEFAULT_FOUNDER_DECISIONS,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO workflow_templates (
            id, name, phase, owner_agent_id, sort_order, doc_type, priority,
            title_template, prompt_template
        )
        VALUES (
            :id, :name, :phase, :owner_agent_id, :sort_order, :doc_type,
            :priority, :title_template, :prompt_template
        )
        """,
        DEFAULT_WORKFLOW_TEMPLATES,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO product_wizard_stage_definitions (
            id, name, description, owner_agent_id, sort_order, artifact_type
        )
        VALUES (
            :id, :name, :description, :owner_agent_id, :sort_order, :artifact_type
        )
        """,
        DEFAULT_PRODUCT_WIZARD_STAGES,
    )


def default_model_preferences() -> list[dict]:
    return [
        {
            "agent_id": agent["id"],
            "provider": "openai-codex",
            "model": "gpt-5-codex",
            "fallback_provider": "",
            "fallback_model": "",
            "auth_method": "deferred_profile_secret",
            "status": "planned",
            "notes": "Starter preference. Configure credentials last inside the Hermes profile.",
        }
        for agent in DEFAULT_AGENTS
    ]


def default_secret_requirements() -> list[dict]:
    requirements = []
    for agent in DEFAULT_AGENTS:
        destination = f"{agent['id']} Hermes profile .env"
        requirements.extend(
            [
                {
                    "id": f"{agent['id']}-slack-bot-token",
                    "owner_agent_id": agent["id"],
                    "category": "slack",
                    "label": f"{agent['name']} Slack bot token",
                    "environment_key": "SLACK_BOT_TOKEN",
                    "destination": destination,
                    "status": "needed",
                    "notes": "Token starts with xoxb-. Store it only in the Hermes profile.",
                },
                {
                    "id": f"{agent['id']}-slack-app-token",
                    "owner_agent_id": agent["id"],
                    "category": "slack",
                    "label": f"{agent['name']} Slack app token",
                    "environment_key": "SLACK_APP_TOKEN",
                    "destination": destination,
                    "status": "needed",
                    "notes": "Socket Mode app token starts with xapp-.",
                },
                {
                    "id": f"{agent['id']}-llm-provider-credential",
                    "owner_agent_id": agent["id"],
                    "category": "llm",
                    "label": f"{agent['name']} LLM provider credential",
                    "environment_key": "PROVIDER_API_KEY_OR_OAUTH",
                    "destination": destination,
                    "status": "deferred",
                    "notes": "Final provider credentials are configured after messaging is ready.",
                },
            ]
        )
    requirements.append(
        {
            "id": "chief-of-staff-telegram-bot-token",
            "owner_agent_id": "chief-of-staff",
            "category": "telegram",
            "label": "Chief of Staff Telegram bot token",
            "environment_key": "TELEGRAM_BOT_TOKEN",
            "destination": "chief-of-staff Hermes profile .env",
            "status": "needed",
            "notes": "Token comes from BotFather. Telegram is urgent-only.",
        }
    )
    return requirements


def default_messaging_checks() -> list[dict]:
    checks = []
    sort_order = 10
    for agent in DEFAULT_AGENTS:
        checks.extend(
            [
                {
                    "id": f"{agent['id']}-slack-gateway",
                    "owner_agent_id": agent["id"],
                    "platform": "slack",
                    "label": f"{agent['name']} Slack gateway running",
                    "status": "needed",
                    "instructions": (
                        f"Run `{agent['hermes_command']} gateway start` after Slack tokens "
                        "are loaded in the real Hermes profile."
                    ),
                    "evidence": "",
                    "sort_order": sort_order,
                },
                {
                    "id": f"{agent['id']}-slack-dm",
                    "owner_agent_id": agent["id"],
                    "platform": "slack",
                    "label": f"{agent['name']} Slack DM response",
                    "status": "needed",
                    "instructions": "Send a direct message from the founder Slack account.",
                    "evidence": "",
                    "sort_order": sort_order + 1,
                },
                {
                    "id": f"{agent['id']}-slack-channel",
                    "owner_agent_id": agent["id"],
                    "platform": "slack",
                    "label": f"{agent['name']} Slack channel mention",
                    "status": "needed",
                    "instructions": (
                        f"Mention the bot in {agent['slack_channel']} and confirm reply."
                    ),
                    "evidence": "",
                    "sort_order": sort_order + 2,
                },
            ]
        )
        sort_order += 10
    checks.append(
        {
            "id": "chief-of-staff-telegram-urgent-alert",
            "owner_agent_id": "chief-of-staff",
            "platform": "telegram",
            "label": "Chief of Staff Telegram urgent alert",
            "status": "needed",
            "instructions": (
                "Trigger an urgent-only founder alert from Chief of Staff after the "
                "Telegram bot token and founder chat ID are loaded externally."
            ),
            "evidence": "",
            "sort_order": sort_order,
        }
    )
    return checks


def default_kanban_checks() -> list[dict]:
    return [
        {
            "id": "kanban-board-initialized",
            "check_type": "init",
            "label": "Hermes Kanban board initialized",
            "status": "needed",
            "instructions": "Run `hermes kanban init` and confirm the board exists.",
            "evidence": "",
            "sort_order": 10,
        },
        {
            "id": "kanban-diagnostics-pass",
            "check_type": "diagnostics",
            "label": "Hermes Kanban diagnostics pass",
            "status": "needed",
            "instructions": (
                "Run dashboard Kanban diagnostics or `hermes kanban diagnostics --json`."
            ),
            "evidence": "",
            "sort_order": 20,
        },
        {
            "id": "kanban-task-create",
            "check_type": "task_create",
            "label": "Dashboard task creates Hermes Kanban task",
            "status": "needed",
            "instructions": (
                "Create one dashboard task, push it to Kanban, and confirm a remote task ID."
            ),
            "evidence": "",
            "sort_order": 30,
        },
    ]


def default_schedule_checks() -> list[dict]:
    checks = []
    sort_order = 10
    for schedule in DEFAULT_STANDUPS:
        checks.extend(
            [
                {
                    "id": f"{schedule['id']}-manual-run",
                    "schedule_id": schedule["id"],
                    "check_type": "manual_run",
                    "label": f"{schedule['name']} manual dashboard run",
                    "status": "needed",
                    "instructions": (
                        "Use the dashboard standup run button and confirm the summary "
                        f"appears in {schedule['slack_channel']} with Telegram following policy."
                    ),
                    "evidence": "",
                    "sort_order": sort_order,
                },
                {
                    "id": f"{schedule['id']}-cron-installed",
                    "schedule_id": schedule["id"],
                    "check_type": "cron_installed",
                    "label": f"{schedule['name']} cron installed",
                    "status": "needed",
                    "instructions": (
                        "Run the generated Chief of Staff cron command and confirm "
                        "`chief-of-staff cron list` shows this schedule."
                    ),
                    "evidence": "",
                    "sort_order": sort_order + 1,
                },
            ]
        )
        sort_order += 10
    return checks


def default_profile_acceptance_checks() -> list[dict]:
    checks = []
    for agent_index, agent in enumerate(DEFAULT_AGENTS, start=1):
        role_cases = ROLE_CASES.get(agent["id"], [])
        for case_index, case in enumerate(role_cases, start=1):
            checks.append(
                {
                    "id": f"{agent['id']}-acceptance-{case_index}",
                    "agent_id": agent["id"],
                    "title": case["title"],
                    "status": "needed",
                    "instructions": (
                        f"Run `{agent['hermes_command']}` with the matching "
                        "profile acceptance prompt, then compare expected and "
                        "failure signals before marking verified."
                    ),
                    "evidence": "",
                    "sort_order": agent_index * 100 + case_index,
                }
            )
    return checks


def default_profile_installation_checks() -> list[dict]:
    return [
        {
            "id": f"{agent['id']}-profile-installation",
            "agent_id": agent["id"],
            "label": f"{agent['name']} profile installation verified",
            "status": "needed",
            "instructions": (
                "Run `/setup/profile-installation.ps1` or manually confirm the "
                "Hermes profile directory, command alias, SOUL.md, capabilities.json, "
                "profile-manifest.json, .env.example, config.yaml.example, and "
                "presence-only live .env/config.yaml checks."
            ),
            "evidence": "",
            "sort_order": index * 10,
        }
        for index, agent in enumerate(DEFAULT_AGENTS, start=1)
    ]


def decode_capabilities(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["capabilities"] = json.loads(data.pop("capabilities_json"))
    return data


def decode_many(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [decode_capabilities(row) for row in rows]
