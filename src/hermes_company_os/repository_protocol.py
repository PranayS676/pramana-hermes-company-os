from __future__ import annotations

from typing import Protocol

from hermes_company_os.agent_work_pickup import AutoPickupPolicy


class RepositoryProtocol(Protocol):
    """Structural interface implemented by :class:`CompanyRepository`.

    Service-layer functions accept ``repository`` arguments typed against this
    protocol so they depend on the data-access contract rather than the concrete
    repository implementation. Auto-generated from the public method surface;
    regenerate when repository methods change.
    """

    def active_schedule_verification_ready(self) -> bool: ...
    def agent_profile_installation_verified(self, agent_id: str) -> bool: ...
    def agent_work_queue_summary(self) -> dict: ...
    def approve_stage(self, project_id: str, stage_id: str) -> None: ...
    def assert_agent_exists(self, agent_id: str) -> None: ...
    def attach_kanban_task(self, task_id: str, kanban_task_id: str) -> None: ...
    def auto_pickup_agent_work_items(
        self,
        *,
        policy: AutoPickupPolicy,
        project_id: str = "",
        owner_agent_id: str = "",
    ) -> list[dict]: ...
    def block_stage(self, project_id: str, stage_id: str, notes: str = "") -> None: ...
    def configure_review_enforcement(self, enabled: bool) -> None: ...
    def complete_generation_run(
        self,
        run_id: str,
        artifact_id: str,
        source_artifact_ids: list[str] | tuple[str, ...] | None = None,
        memory_ids: list[str] | tuple[str, ...] | None = None,
    ) -> None: ...
    def complete_run(self, run_id: str, output: str, error: str = "") -> None: ...
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
    ) -> str: ...
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
    ) -> str: ...
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
    ) -> str: ...
    def create_document(
        self, title: str, doc_type: str, owner_agent_id: str, body: str, status: str = "draft"
    ) -> str: ...
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
    ) -> str: ...
    def create_generation_run(
        self,
        project_id: str,
        stage_id: str,
        generation_mode: str,
        source_artifact_ids: list[str] | tuple[str, ...] = (),
        memory_ids: list[str] | tuple[str, ...] = (),
    ) -> str: ...
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
    ) -> str: ...
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
    ) -> str: ...
    def create_project_with_workflow(self, name: str, founder_idea: str) -> str: ...
    def create_run(self, agent_id: str, run_type: str, prompt: str) -> str: ...
    def create_structured_project(
        self, name: str, founder_idea: str, intake: dict | None = None
    ) -> str: ...
    def create_task(
        self, title: str, owner_agent_id: str, priority: str, summary: str, status: str = "planned"
    ) -> str: ...
    def ensure_project_workflow_items(self, project_id: str) -> int: ...
    def fail_generation_run(self, run_id: str, error: str) -> None: ...
    def founder_decision_queue_ready(self) -> bool: ...
    def get_agent(self, agent_id: str) -> dict | None: ...
    def get_agent_work_item(self, work_item_id: str) -> dict | None: ...
    def get_codex_execution_run(self, run_id: str) -> dict | None: ...
    def get_external_dispatch_delivery(self, idempotency_key: str) -> dict | None: ...
    def get_founder_decision(self, decision_id: str) -> dict | None: ...
    def get_generation_run(self, run_id: str) -> dict | None: ...
    def get_kanban_check(self, check_id: str) -> dict | None: ...
    def get_messaging_check(self, check_id: str) -> dict | None: ...
    def get_model_preference(self, agent_id: str) -> dict | None: ...
    def get_profile_acceptance_check(self, check_id: str) -> dict | None: ...
    def get_profile_installation_check(self, check_id: str) -> dict | None: ...
    def get_project(self, project_id: str) -> dict | None: ...
    def get_project_memory_entry(self, memory_id: str) -> dict | None: ...
    def get_project_wizard_artifact(self, project_id: str, artifact_id: str) -> dict | None: ...
    def get_project_wizard_stage(self, project_id: str, stage_id: str) -> dict | None: ...
    def get_schedule(self, schedule_id: str) -> dict | None: ...
    def get_schedule_check(self, check_id: str) -> dict | None: ...
    def get_secret_requirement(self, requirement_id: str) -> dict | None: ...
    def get_task(self, task_id: str) -> dict | None: ...
    def kanban_verification_ready(self) -> bool: ...
    def latest_codex_execution_run(self, project_id: str) -> dict | None: ...
    def latest_generation_run(
        self, project_id: str, stage_id: str, artifact_id: str | None = None
    ) -> dict | None: ...
    def latest_project_stage_artifact(self, project_id: str, stage_id: str) -> dict | None: ...
    def latest_runs_by_type(self, run_type: str) -> dict[str, dict]: ...
    def list_agent_relationships(self) -> list[dict]: ...
    def list_agent_work_items(
        self,
        limit: int | None = None,
        *,
        project_id: str = "",
        owner_agent_id: str = "",
        status: str = "",
        include_done: bool = True,
    ) -> list[dict]: ...
    def list_agents(self) -> list[dict]: ...
    def list_audit_events(
        self, project_id: str = "", *, event_type: str = "", limit: int = 50
    ) -> list[dict]: ...
    def list_codex_execution_runs(
        self, project_id: str, *, status: str = "", limit: int = 20
    ) -> list[dict]: ...
    def list_documents(self) -> list[dict]: ...
    def list_external_dispatch_deliveries(
        self, project_id: str, *, limit: int = 50
    ) -> list[dict]: ...
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
    ) -> list[dict]: ...
    def list_generation_runs(
        self,
        project_id: str,
        stage_id: str | None = None,
        artifact_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]: ...
    def list_integrations(self) -> list[dict]: ...
    def list_kanban_checks(self) -> list[dict]: ...
    def list_messaging_checks(self) -> list[dict]: ...
    def list_model_preferences(self) -> list[dict]: ...
    def list_product_wizard_stage_definitions(self) -> list[dict]: ...
    def list_profile_acceptance_checks(self) -> list[dict]: ...
    def list_profile_installation_checks(self) -> list[dict]: ...
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
    ) -> list[dict]: ...
    def list_project_review_records(
        self, project_id: str, *, review_batch_id: str = "", limit: int = 50
    ) -> list[dict]: ...
    def list_project_stage_artifacts(self, project_id: str, stage_id: str) -> list[dict]: ...
    def list_project_wizard_stages(self, project_id: str) -> list[dict]: ...
    def list_project_workflow_items(self, project_id: str) -> list[dict]: ...
    def list_projects(self) -> list[dict]: ...
    def list_reusable_project_memory_entries(
        self, project_id: str = "", *, category: str = "", limit: int = 50
    ) -> list[dict]: ...
    def list_runs(self, limit: int = 12) -> list[dict]: ...
    def list_schedule_checks(self) -> list[dict]: ...
    def list_schedules(self) -> list[dict]: ...
    def list_secret_requirements(self) -> list[dict]: ...
    def list_setup_inputs(self) -> list[dict]: ...
    def list_setup_steps(self) -> list[dict]: ...
    def list_tasks(self) -> list[dict]: ...
    def list_workflow_templates(self) -> list[dict]: ...
    def messaging_platform_verified(self, platform: str) -> bool: ...
    def model_preference_map(self) -> dict[str, dict]: ...
    def next_actionable_stage(self, project_id: str) -> dict | None: ...
    def profile_acceptance_verified(self) -> bool: ...
    def profile_installation_verified(self) -> bool: ...
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
    ) -> dict: ...
    def request_stage_revision(
        self, project_id: str, stage_id: str, notes: str = "", reason: str = ""
    ) -> None: ...
    def resolve_project_stage_decisions(
        self,
        *,
        project_id: str,
        stage_id: str,
        status: str,
        decision: str,
        decision_types: set[str] | None = None,
    ) -> int: ...
    def save_stage_artifact_draft(
        self,
        project_id: str,
        stage_id: str,
        markdown_content: str,
        json_content: dict | list | str | None = None,
        owner_agent_id: str | None = None,
    ) -> str: ...
    def search_company_memory(
        self,
        *,
        query: str = "",
        category: str = "",
        status: str = "active",
        confidence: str = "",
        limit: int = 50,
    ) -> list[dict]: ...
    def setup_input_completion(self) -> dict: ...
    def stage_review_requirements(self, project_id: str, stage_id: str) -> dict: ...
    def setup_input_map(self) -> dict[str, str]: ...
    def sync_project_wizard_work_items(self, project_id: str) -> int: ...
    def update_agent_profile(
        self, agent_id: str, description: str, soul: str, capabilities: list[str]
    ) -> None: ...
    def update_agent_routing(
        self, agent_id: str, slack_channel: str, telegram_policy: str, hermes_command: str
    ) -> None: ...
    def update_agent_secret_requirements(
        self, agent_id: str, category: str, status: str, notes: str
    ) -> None: ...
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
    ) -> None: ...
    def update_codex_execution_run(
        self,
        run_id: str,
        *,
        status: str,
        runner_mode: str,
        external_execution_enabled: bool,
        audit: dict,
        error: str = "",
    ) -> None: ...
    def update_founder_decision(
        self, decision_id: str, status: str, decision: str, *, founder_confirmed: bool = False
    ) -> None: ...
    def update_integration_status(self, integration_id: str, status: str) -> None: ...
    def update_kanban_check(self, check_id: str, status: str, evidence: str) -> None: ...
    def update_messaging_check(self, check_id: str, status: str, evidence: str) -> None: ...
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
    ) -> None: ...
    def update_profile_acceptance_check(
        self, check_id: str, status: str, evidence: str
    ) -> None: ...
    def update_profile_installation_check(
        self, check_id: str, status: str, evidence: str
    ) -> None: ...
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
    ) -> None: ...
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
    ) -> None: ...
    def update_schedule_check(self, check_id: str, status: str, evidence: str) -> None: ...
    def update_secret_requirement(self, requirement_id: str, status: str, notes: str) -> None: ...
    def update_setup_inputs(self, values: dict[str, str]) -> None: ...
