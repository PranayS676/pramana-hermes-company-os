from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from hermes_company_os.database import connect
from hermes_company_os.repository_support import (
    decode_project,
    decode_wizard_artifact,
    serialize_wizard_json_content,
    utc_now,
)
from hermes_company_os.secret_guard import assert_no_secret_values


class ProjectWorkflowMixin:
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
