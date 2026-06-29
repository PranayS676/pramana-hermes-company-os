from __future__ import annotations

import sqlite3
from uuid import uuid4

from hermes_company_os.agent_work_pickup import (
    AutoPickupPolicy,
    eligible_for_auto_pickup,
    next_auto_pickup_status,
)
from hermes_company_os.agent_work_queue import (
    QUEUE_STATES,
    validate_queue_priority,
    validate_queue_state,
    validate_queue_transition,
)
from hermes_company_os.database import connect
from hermes_company_os.founder_decisions import (
    RESOLVED_DECISION_STATUSES,
    SUPPORTED_DECISION_TYPES,
    founder_only_decision_type,
    normalize_decision_type,
)
from hermes_company_os.repository_support import (
    decode_agent_work_item,
    utc_now,
)
from hermes_company_os.secret_guard import assert_no_secret_values


class DecisionsAndWorkQueueMixin:
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

    def auto_pickup_agent_work_items(
        self,
        *,
        policy: AutoPickupPolicy,
        project_id: str = "",
        owner_agent_id: str = "",
    ) -> list[dict]:
        """Advance an agent's OWN planned/assigned work under a founder-gated policy.

        Pure queue-state orchestration: each eligible item is nudged one legal
        step forward (planned -> assigned, and assigned -> running only when the
        policy opts in) via ``validate_queue_transition`` with
        ``founder_confirmed=False`` so it can never reach approved/rejected/done.
        Every transition emits an audit event in the SAME transaction. No live
        external side effects are performed. When the policy is disabled this is
        a no-op returning an empty list.
        """
        if not policy.enabled:
            return []

        candidates = [
            item
            for item in self.list_agent_work_items(
                project_id=project_id,
                owner_agent_id=owner_agent_id,
            )
            if item["status"] in {"planned", "assigned"}
            and eligible_for_auto_pickup(item, policy)
        ]

        picked_up: list[dict] = []
        now = utc_now()
        with connect(self.database_path) as connection:
            for item in candidates:
                if policy.max_items is not None and len(picked_up) >= policy.max_items:
                    break
                current_status = item["status"]
                target_status = next_auto_pickup_status(current_status, policy=policy)
                if target_status is None:
                    continue
                # Re-run the state-machine guard inside the transaction; this
                # raises if a forbidden/illegal target ever slipped through and
                # never passes founder_confirmed=True.
                next_status = validate_queue_transition(
                    current_status,
                    target_status,
                    founder_confirmed=False,
                )
                event_type = (
                    "agent_work_item_auto_started"
                    if next_status == "running"
                    else "agent_work_item_auto_assigned"
                )
                payload = {
                    "from_status": current_status,
                    "to_status": next_status,
                    "policy": "auto_pickup",
                    "external_execution": False,
                }
                summary = (
                    f"Auto-pickup advanced '{item['title']}' "
                    f"from {current_status} to {next_status}."
                )
                assert_no_secret_values({"summary": summary})
                connection.execute(
                    """
                    UPDATE agent_work_items
                    SET status = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (next_status, now, item["id"]),
                )
                self._insert_audit_event(
                    connection,
                    project_id=(item.get("project_id") or "").strip() or None,
                    event_type=event_type,
                    status=next_status,
                    actor_agent_id=item["owner_agent_id"],
                    source_table="agent_work_items",
                    source_id=item["id"],
                    summary=summary,
                    payload=payload,
                )
                advanced = dict(item)
                advanced["status"] = next_status
                advanced["from_status"] = current_status
                advanced["updated_at"] = now
                picked_up.append(advanced)
        return picked_up

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
