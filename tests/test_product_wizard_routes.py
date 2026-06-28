from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from hermes_company_os.generation_service import (
    LIVE_HERMES_DRY_RUN_ADAPTER,
    LIVE_HERMES_DRY_RUN_STATUS,
    LIVE_HERMES_GENERATION_MODE,
    LIVE_HERMES_LIVE_ADAPTER,
    LIVE_HERMES_LIVE_STATUS,
    LiveHermesAdapterRawResult,
    StageGenerationRequest,
)
from hermes_company_os.live_hermes_readiness import (
    LIVE_HERMES_DECISION_SOURCE,
    LIVE_HERMES_DECISION_TYPE,
    LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
    LIVE_HERMES_RUN_CONFIRMATION_TYPE,
    evaluate_live_hermes_run_confirmation,
)
from hermes_company_os.main import (
    LIVE_HERMES_PILOT_CONFIRMATION_ERROR,
    LIVE_HERMES_PILOT_CONFIRMATION_PHRASE,
    create_app,
)
from hermes_company_os.product_wizard import generate_wizard_artifact
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

FAKE_OPENAI_ENV_SECRET = "OPENAI" + "_API" + "_KEY=" + "sk" + "-" + ("a" * 32)

STRUCTURED_INTAKE = {
    "wizard_version": "product-wizard-v1",
    "name": "Atlas Brief",
    "product_category": "saas",
    "founder_idea": "AI due-diligence workspace for acquisition teams.",
    "target_audience": "Corporate development teams reviewing small acquisitions.",
    "current_alternative": "Shared docs, spreadsheets, and ad hoc chat threads.",
    "problem_statement": "Teams lose the thread across diligence notes, risks, and asks.",
    "desired_outcome": "A reviewed risk brief with assigned follow-up questions.",
    "launch_tier": "t0_internal",
    "deadline_pressure": "normal",
    "constraints": "Use mock data only; no live customer files in the public demo.",
    "non_goals": "Do not build an enterprise data-room connector in V1.",
    "success_metrics": "Reduce first-pass diligence synthesis time by 40 percent.",
}

STRUCTURED_FIELD_NAMES = [
    "name",
    "product_category",
    "founder_idea",
    "target_audience",
    "current_alternative",
    "problem_statement",
    "desired_outcome",
    "launch_tier",
    "deadline_pressure",
    "constraints",
    "non_goals",
    "success_metrics",
]

STRUCTURED_FIELD_LABELS = [
    "Project name",
    "Product category",
    "Founder idea",
    "Target audience",
    "Current alternative",
    "Problem statement",
    "Desired outcome",
    "Launch tier",
    "Deadline pressure",
    "Constraints",
    "Non-goals",
    "Success metrics",
]

WIZARD_STAGE_IDS = ["research", "prd", "architecture", "tasks", "code_plan", "acceptance"]


class CapturingGenerationService:
    def __init__(self):
        self.requests: list[StageGenerationRequest] = []

    def generate_stage(self, request: StageGenerationRequest):
        self.requests.append(request)
        return generate_wizard_artifact(
            request.stage_id,
            request.intake,
            request.approved_sources,
            memory_context=request.memory_context,
            memory_policy=request.memory_policy,
        )


class FailingGenerationService:
    def __init__(self):
        self.requests: list[StageGenerationRequest] = []

    def generate_stage(self, request: StageGenerationRequest):
        self.requests.append(request)
        raise ValueError("Simulated generation failure.")


class FakeLiveHermesCommandRunner:
    def __init__(self, result: LiveHermesAdapterRawResult):
        self.result = result
        self.calls = []

    def run(self, command, prompt, timeout_seconds):
        self.calls.append(
            {
                "command": command,
                "prompt": prompt,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.result


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient, **overrides: str) -> tuple[str, str]:
    response = client.post(
        "/projects",
        data={**STRUCTURED_INTAKE, **overrides},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    location = response.headers["location"]
    assert location.startswith("/projects/")
    return location.rsplit("/", 1)[-1], location


def future_iso(days: int = 30) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def past_iso(days: int = 1) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def mark_agent_runtime_ready(app, agent_id: str) -> None:
    repository = app.state.repository
    repository.update_profile_installation_check(
        check_id=f"{agent_id}-profile-installation",
        status="verified",
        evidence="Verified in route test.",
    )
    preference = repository.get_model_preference(agent_id)
    repository.update_model_preference(
        agent_id=agent_id,
        provider=preference["provider"],
        model=preference["model"],
        fallback_provider=preference["fallback_provider"],
        fallback_model=preference["fallback_model"],
        auth_method=preference["auth_method"],
        status="verified",
        notes="Verified in route test.",
    )
    for check in repository.list_profile_acceptance_checks():
        if check["agent_id"] == agent_id:
            repository.update_profile_acceptance_check(
                check_id=check["id"],
                status="verified",
                evidence="Verified in route test.",
            )


def approve_live_hermes_stage(app, project_id: str, stage_id: str) -> str:
    decision_id = app.state.repository.create_founder_decision(
        title="Approve live Hermes generation",
        urgency="urgent",
        decision_type=LIVE_HERMES_DECISION_TYPE,
        source=LIVE_HERMES_DECISION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id=stage_id,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if live generation blocks launch.",
        context="Approve live Hermes generation for this project stage.",
        evidence="Runtime gates are verified.",
        requires_founder_approval=True,
    )
    app.state.repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Approved for one live Hermes generation attempt.",
        founder_confirmed=True,
    )
    return decision_id


def confirm_one_live_hermes_run(app, project_id: str, stage_id: str) -> str:
    decision_id = app.state.repository.create_founder_decision(
        title="Confirm one live Hermes run",
        urgency="urgent",
        decision_type=LIVE_HERMES_RUN_CONFIRMATION_TYPE,
        source=LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id=stage_id,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if live generation blocks launch.",
        context="Confirm exactly one live Hermes generation attempt.",
        evidence="Readiness gates and command preview are verified.",
        requires_founder_approval=True,
    )
    app.state.repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Approved for exactly one live Hermes command runner attempt.",
        founder_confirmed=True,
    )
    return decision_id


def test_new_project_wizard_form_renders_structured_intake(tmp_path):
    _, client = app_and_client(tmp_path)

    response = client.get("/projects/new")

    assert response.status_code == 200
    assert "New product wizard" in response.text
    assert 'action="/projects"' in response.text
    assert 'method="post"' in response.text.lower()
    assert 'name="wizard_version"' in response.text
    assert 'value="product-wizard-v1"' in response.text
    for field_name in STRUCTURED_FIELD_NAMES:
        assert f'name="{field_name}"' in response.text
    for label in STRUCTURED_FIELD_LABELS:
        assert label in response.text


def test_create_project_uses_structured_wizard_flow_and_redirects_to_detail(tmp_path):
    app, client = app_and_client(tmp_path)

    project_id, location = create_structured_project(client)

    project = app.state.repository.get_project(project_id)
    assert project is not None
    assert project["name"] == STRUCTURED_INTAKE["name"]
    assert project["status"] == "wizard_active"
    stages = app.state.repository.list_project_wizard_stages(project_id)
    assert [stage["stage_id"] for stage in stages] == WIZARD_STAGE_IDS
    assert [stage["status"] for stage in stages] == [
        "ready",
        "waiting",
        "waiting",
        "waiting",
        "waiting",
        "waiting",
    ]
    assert app.state.repository.list_project_workflow_items(project_id) == []

    detail = client.get(location)
    assert detail.status_code == 200
    for value in (
        STRUCTURED_INTAKE["target_audience"],
        STRUCTURED_INTAKE["problem_statement"],
        STRUCTURED_INTAKE["constraints"],
        STRUCTURED_INTAKE["success_metrics"],
    ):
        assert value in detail.text
    assert secret_violations({"project_detail": detail.text}) == []


def test_secret_shaped_structured_intake_is_rejected_and_not_persisted(tmp_path):
    app, client = app_and_client(tmp_path)

    response = client.post(
        "/projects",
        data={
            **STRUCTURED_INTAKE,
            "problem_statement": (
                "This should never persist because it contains " + FAKE_OPENAI_ENV_SECRET
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert app.state.repository.list_projects() == []
    projects_page = client.get("/projects")
    assert "sk-" not in projects_page.text
    assert "OPENAI_API_KEY" not in projects_page.text


def test_generate_current_stage_uses_public_demo_local_generation(tmp_path, monkeypatch):
    for env_name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "HERMES_API_KEY",
        "HERMES_COMMAND_PRODUCT_MANAGER",
        "HERMES_COMMAND_RESEARCH_AGENT",
    ):
        monkeypatch.delenv(env_name, raising=False)
    app, client = app_and_client(tmp_path)
    generation_service = CapturingGenerationService()
    app.state.generation_service = generation_service
    project_id, _ = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )

    assert response.status_code == 303, response.text
    assert len(generation_service.requests) == 1
    generation_request = generation_service.requests[0]
    assert generation_request.stage_id == "research"
    assert generation_request.mode == "local_fake_public_demo"
    assert list(generation_request.approved_sources) == []
    assert generation_request.intake.project_name == STRUCTURED_INTAKE["name"]
    artifact = app.state.repository.latest_project_stage_artifact(project_id, "research")
    assert artifact is not None
    assert artifact["status"] == "draft"
    assert artifact["version"] == 1
    generation_runs = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )
    assert len(generation_runs) == 1
    generation_run = generation_runs[0]
    assert generation_run["status"] == "succeeded"
    assert generation_run["generation_mode"] == "local_fake_public_demo"
    assert generation_run["artifact_id"] == artifact["id"]
    assert generation_run["source_artifact_ids"] == []
    assert generation_run["memory_ids"] == []
    raw_artifact = json.dumps(artifact, sort_keys=True)
    assert "local_fake_public_demo" in raw_artifact
    assert "Opportunity Research" in raw_artifact
    assert secret_violations({"artifact": raw_artifact}) == []

    detail = client.get(f"/projects/{project_id}")
    assert detail.status_code == 200
    assert "Artifact review contract" in detail.text
    assert "Live Hermes readiness" in detail.text
    assert "Live execution operator" in detail.text
    assert "HERMES_LIVE_EXECUTION_ENABLED" in detail.text
    assert "execution disabled" in detail.text
    assert (
        "hermes profiles run research-agent --stage research --dry-run --output "
        "product-wizard-artifact-json"
    ) in detail.text
    assert "Operator checklist" in detail.text
    assert "No adapter capture exists yet" in detail.text
    assert "Profile installation" in detail.text
    assert "Founder live-mode approval" in detail.text
    assert "Request founder approval" in detail.text
    assert "Pilot phrase" in detail.text
    assert LIVE_HERMES_PILOT_CONFIRMATION_PHRASE in detail.text
    assert "Generation mode" in detail.text
    assert "Generation run" in detail.text
    assert "Live Hermes locked" in detail.text
    assert "Complete execution flag, readiness, and one-run confirmation first." in detail.text
    assert generation_run["id"] in detail.text
    assert "succeeded" in detail.text
    assert "local_fake_public_demo" in detail.text
    assert "Quality checks" in detail.text
    assert "Target User" in detail.text
    assert "Next decision" in detail.text
    assert "Revision reason" in detail.text
    assert "Evidence gap" in detail.text
    assert "Codex Execution" in detail.text
    assert "approved code plan, approved acceptance package" in detail.text
    assert artifact["id"] in detail.text
    assert secret_violations({"project_detail": detail.text}) == []


def test_generate_current_stage_injects_founder_approved_memory(tmp_path):
    app, client = app_and_client(tmp_path)
    generation_service = CapturingGenerationService()
    app.state.generation_service = generation_service
    project_id, _ = create_structured_project(client)
    approved_memory_id = app.state.repository.create_project_memory_entry(
        source_key="project:atlas:founder-preference",
        project_id=project_id,
        category="founder_preference",
        memory_type="preference",
        owner_agent_id="chief-of-staff",
        source="founder-memory-form",
        title="Keep public demo data synthetic",
        summary="Founder prefers public demos that avoid customer files.",
        body="Use synthetic companies, fixture risks, and generated diligence notes.",
        confidence="high",
        status="active",
        pinned=True,
        review_after=future_iso(),
        expires_at=future_iso(60),
    )
    app.state.repository.create_project_memory_entry(
        source_key="project:atlas:customer-evidence",
        project_id=project_id,
        category="customer_evidence",
        memory_type="evidence",
        owner_agent_id="research-agent",
        source="research-notes",
        title="Customer quote requires explicit artifact approval",
        summary="Customer evidence should not be auto-injected from memory.",
        body="Keep customer-specific claims in approved research artifacts.",
        confidence="medium",
        status="active",
        pinned=True,
        review_after=future_iso(),
        expires_at=future_iso(60),
    )
    app.state.repository.create_project_memory_entry(
        source_key="project:atlas:stale-standard",
        project_id=project_id,
        category="technical_standard",
        memory_type="standard",
        owner_agent_id="engineering-manager",
        source="old-architecture",
        title="Stale architecture standard",
        summary="This entry needs founder review before reuse.",
        body="Do not use this stale standard in prompt context.",
        confidence="low",
        status="active",
        pinned=True,
        review_after=past_iso(),
        expires_at=future_iso(60),
    )

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    generation_request = generation_service.requests[0]
    artifact = app.state.repository.latest_project_stage_artifact(project_id, "research")
    generation_run = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )[0]
    raw_artifact = json.dumps(artifact, sort_keys=True)

    assert response.status_code == 303
    assert [memory["id"] for memory in generation_request.memory_context] == [
        approved_memory_id
    ]
    assert generation_request.memory_policy.enabled is True
    assert generation_request.memory_policy.source == (
        "founder_approved_product_wizard_memory_policy_v1"
    )
    assert artifact["json"]["memory_ids"] == [approved_memory_id]
    assert generation_run["memory_ids"] == [approved_memory_id]
    assert generation_run["source_artifact_ids"] == []
    assert "Keep public demo data synthetic" in artifact["markdown_content"]
    assert "Customer quote requires explicit artifact approval" not in raw_artifact
    assert "Stale architecture standard" not in raw_artifact
    assert secret_violations({"memory_artifact": raw_artifact}) == []


def test_live_operator_console_shows_enabled_config_without_running_command(tmp_path):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            hermes_timeout_seconds=42,
            hermes_live_execution_enabled=True,
        )
    )
    client = TestClient(app)
    project_id, _ = create_structured_project(client)

    detail = client.get(f"/projects/{project_id}")

    assert detail.status_code == 200
    assert "Live execution operator" in detail.text
    assert "execution enabled" in detail.text
    assert "Real Hermes command execution is enabled for this process." in detail.text
    assert "One-run confirmation" in detail.text
    assert "Request and approve a one-run token before real execution." in detail.text
    assert "Pilot status" in detail.text
    assert "blocked" in detail.text
    assert LIVE_HERMES_PILOT_CONFIRMATION_PHRASE in detail.text
    assert (
        "hermes profiles run research-agent --stage research --output "
        "product-wizard-artifact-json"
    ) in detail.text
    assert (
        "hermes profiles run research-agent --stage research --dry-run --output"
        not in detail.text
    )
    assert "42 seconds" in detail.text
    assert "Complete live Hermes readiness before a real runner attempt." in detail.text
    assert secret_violations({"project_detail": detail.text}) == []


def test_live_execution_enabled_blocks_without_one_run_confirmation(tmp_path):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            hermes_live_execution_enabled=True,
        )
    )
    client = TestClient(app)
    project_id, _ = create_structured_project(client)
    mark_agent_runtime_ready(app, "research-agent")
    approve_live_hermes_stage(app, project_id, "research")

    project_page = client.get(f"/projects/{project_id}")
    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        data={
            "generation_mode": LIVE_HERMES_GENERATION_MODE,
            "live_pilot_confirmation": LIVE_HERMES_PILOT_CONFIRMATION_PHRASE,
        },
        follow_redirects=False,
    )
    generation_run = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )[0]

    assert project_page.status_code == 200
    assert "Request one-run confirmation" in project_page.text
    assert response.status_code == 409
    assert "one-run confirmation blocked" in response.json()["detail"]
    assert generation_run["status"] == "failed"
    assert generation_run["artifact_id"] is None
    assert "one-run confirmation blocked" in generation_run["error"]
    assert app.state.repository.latest_project_stage_artifact(project_id, "research") is None
    assert secret_violations({"project_detail": project_page.text}) == []


def test_request_one_run_confirmation_creates_founder_decision_once(tmp_path):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            hermes_live_execution_enabled=True,
        )
    )
    client = TestClient(app)
    project_id, _ = create_structured_project(client)
    mark_agent_runtime_ready(app, "research-agent")
    approve_live_hermes_stage(app, project_id, "research")

    first = client.post(
        f"/projects/{project_id}/stages/current/live-hermes-run-confirmation",
        follow_redirects=False,
    )
    second = client.post(
        f"/projects/{project_id}/stages/current/live-hermes-run-confirmation",
        follow_redirects=False,
    )
    decisions = app.state.repository.list_founder_decisions(
        project_id=project_id,
        stage_id="research",
        decision_type=LIVE_HERMES_RUN_CONFIRMATION_TYPE,
        include_resolved=False,
    )
    confirmations = [
        decision
        for decision in decisions
        if decision["source"] == LIVE_HERMES_RUN_CONFIRMATION_SOURCE
    ]
    project_page = client.get(f"/projects/{project_id}")

    assert first.status_code == 303
    assert second.status_code == 303
    assert len(confirmations) == 1
    assert confirmations[0]["requires_founder_approval"] == 1
    assert confirmations[0]["status"] == "needed"
    assert "Open run confirmation" in project_page.text
    assert confirmations[0]["id"] in project_page.text
    assert secret_violations({"project_detail": project_page.text}) == []


def test_generation_failure_records_failed_run_without_artifact(tmp_path):
    app, client = app_and_client(tmp_path)
    generation_service = FailingGenerationService()
    app.state.generation_service = generation_service
    project_id, _ = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Simulated generation failure."
    assert len(generation_service.requests) == 1
    assert app.state.repository.latest_project_stage_artifact(project_id, "research") is None
    generation_runs = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )
    assert len(generation_runs) == 1
    generation_run = generation_runs[0]
    assert generation_run["status"] == "failed"
    assert generation_run["artifact_id"] is None
    assert generation_run["error"] == "Simulated generation failure."

    detail = client.get(f"/projects/{project_id}")

    assert detail.status_code == 200
    assert "Generation run" in detail.text
    assert generation_run["id"] in detail.text
    assert "failed" in detail.text
    assert "Simulated generation failure." in detail.text
    assert secret_violations({"project_detail": detail.text}) == []


def test_live_hermes_mode_is_locked_and_records_failed_run(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id, _ = create_structured_project(client)

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        data={
            "generation_mode": LIVE_HERMES_GENERATION_MODE,
            "live_pilot_confirmation": LIVE_HERMES_PILOT_CONFIRMATION_PHRASE,
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Live Hermes readiness blocked: Profile installation" in (
        response.json()["detail"]
    )
    assert app.state.repository.latest_project_stage_artifact(project_id, "research") is None
    generation_runs = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )
    assert len(generation_runs) == 1
    generation_run = generation_runs[0]
    assert generation_run["status"] == "failed"
    assert generation_run["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    assert generation_run["artifact_id"] is None
    assert "Live Hermes readiness blocked: Profile installation" in generation_run["error"]

    detail = client.get(f"/projects/{project_id}")

    assert detail.status_code == 200
    assert "Live Hermes locked" in detail.text
    assert "Run status" in detail.text
    assert "failed" in detail.text
    assert LIVE_HERMES_GENERATION_MODE in detail.text
    assert generation_run["id"] in detail.text
    assert "Verify profile installation for: research-agent." in detail.text
    assert secret_violations({"project_detail": detail.text}) == []


def test_request_live_hermes_approval_creates_founder_decision_once(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id, _ = create_structured_project(client)

    first = client.post(
        f"/projects/{project_id}/stages/current/live-hermes-approval",
        follow_redirects=False,
    )
    second = client.post(
        f"/projects/{project_id}/stages/current/live-hermes-approval",
        follow_redirects=False,
    )
    decisions = app.state.repository.list_founder_decisions(
        project_id=project_id,
        stage_id="research",
        decision_type=LIVE_HERMES_DECISION_TYPE,
        include_resolved=False,
    )
    live_decisions = [
        decision
        for decision in decisions
        if decision["source"] == LIVE_HERMES_DECISION_SOURCE
    ]
    project_page = client.get(f"/projects/{project_id}")

    assert first.status_code == 303
    assert second.status_code == 303
    assert len(live_decisions) == 1
    assert live_decisions[0]["requires_founder_approval"] == 1
    assert live_decisions[0]["status"] == "needed"
    assert project_page.status_code == 200
    assert "Open approval decision" in project_page.text
    assert live_decisions[0]["id"] in project_page.text
    assert secret_violations({"project_detail": project_page.text}) == []


def test_live_hermes_runtime_ready_still_requires_founder_approval(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id, _ = create_structured_project(client)
    mark_agent_runtime_ready(app, "research-agent")

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        data={"generation_mode": LIVE_HERMES_GENERATION_MODE},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Founder live-mode approval" in response.json()["detail"]
    assert app.state.repository.latest_project_stage_artifact(project_id, "research") is None


def test_live_hermes_all_gates_ready_creates_dry_run_artifact(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id, _ = create_structured_project(client)
    mark_agent_runtime_ready(app, "research-agent")
    decision_id = approve_live_hermes_stage(app, project_id, "research")

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        data={"generation_mode": LIVE_HERMES_GENERATION_MODE},
        follow_redirects=False,
    )
    generation_run = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )[0]
    project_page = client.get(f"/projects/{project_id}")
    artifact = app.state.repository.latest_project_stage_artifact(
        project_id,
        "research",
    )
    raw_artifact = json.dumps(artifact, sort_keys=True)

    assert response.status_code == 303
    assert generation_run["status"] == "succeeded"
    assert generation_run["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    assert artifact is not None
    assert generation_run["artifact_id"] == artifact["id"]
    assert artifact["json"]["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    assert artifact["json"]["generation_metadata"]["adapter"] == LIVE_HERMES_DRY_RUN_ADAPTER
    assert artifact["json"]["generation_metadata"]["status"] == LIVE_HERMES_DRY_RUN_STATUS
    assert artifact["json"]["generation_metadata"]["external_execution"] == "disabled"
    assert artifact["json"]["generation_metadata"]["command_preview"] == [
        "hermes",
        "profiles",
        "run",
        "research-agent",
        "--stage",
        "research",
        "--dry-run",
        "--output",
        "product-wizard-artifact-json",
    ]
    assert "## Live Hermes Dry Run" in artifact["markdown_content"]
    assert "Live Hermes gates are satisfied" in project_page.text
    assert "Last adapter capture" in project_page.text
    assert (
        "hermes profiles run research-agent --stage research --dry-run --output "
        "product-wizard-artifact-json"
    ) in project_page.text
    assert "Live Hermes Dry Run" in project_page.text
    assert "dry_run_live_hermes" in project_page.text
    assert decision_id in project_page.text
    assert secret_violations({"artifact": raw_artifact}) == []
    assert secret_violations({"project_detail": project_page.text}) == []


def test_live_execution_enabled_requires_manual_pilot_confirmation(tmp_path):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            hermes_live_execution_enabled=True,
        )
    )
    fake_runner = FakeLiveHermesCommandRunner(
        LiveHermesAdapterRawResult(stdout='{"artifact": "should not run"}')
    )
    app.state.live_hermes_command_runner = fake_runner
    client = TestClient(app)
    project_id, _ = create_structured_project(client)
    mark_agent_runtime_ready(app, "research-agent")
    approve_live_hermes_stage(app, project_id, "research")
    run_confirmation_id = confirm_one_live_hermes_run(app, project_id, "research")

    project_page = client.get(f"/projects/{project_id}")
    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        data={"generation_mode": LIVE_HERMES_GENERATION_MODE},
        follow_redirects=False,
    )
    generation_run = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )[0]
    run_confirmation = evaluate_live_hermes_run_confirmation(
        app.state.repository,
        project_id,
        "research",
    )

    assert project_page.status_code == 200
    assert "Run live Hermes pilot" in project_page.text
    assert LIVE_HERMES_PILOT_CONFIRMATION_PHRASE in project_page.text
    assert response.status_code == 409
    assert response.json()["detail"] == LIVE_HERMES_PILOT_CONFIRMATION_ERROR
    assert fake_runner.calls == []
    assert generation_run["status"] == "failed"
    assert generation_run["artifact_id"] is None
    assert generation_run["error"] == LIVE_HERMES_PILOT_CONFIRMATION_ERROR
    assert run_confirmation.decision_id == run_confirmation_id
    assert run_confirmation.fresh is False
    assert app.state.repository.latest_project_stage_artifact(project_id, "research") is None
    assert secret_violations({"project_detail": project_page.text}) == []


def test_live_execution_enabled_uses_injected_runner_and_records_ui_evidence(tmp_path):
    app = create_app(
        Settings(
            database_path=tmp_path / "company.db",
            hermes_timeout_seconds=13,
            hermes_live_execution_enabled=True,
        )
    )
    fake_runner = FakeLiveHermesCommandRunner(
        LiveHermesAdapterRawResult(
            stdout='{"artifact": "fake live output"}',
            stderr="fake runner diagnostic",
            duration_ms=17,
        )
    )
    app.state.live_hermes_command_runner = fake_runner
    app.state.live_hermes_runner_label = "fake_test_runner"
    client = TestClient(app)
    project_id, _ = create_structured_project(client)
    mark_agent_runtime_ready(app, "research-agent")
    live_decision_id = approve_live_hermes_stage(app, project_id, "research")
    run_confirmation_id = confirm_one_live_hermes_run(app, project_id, "research")

    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        data={
            "generation_mode": LIVE_HERMES_GENERATION_MODE,
            "live_pilot_confirmation": LIVE_HERMES_PILOT_CONFIRMATION_PHRASE,
        },
        follow_redirects=False,
    )
    generation_run = app.state.repository.list_generation_runs(
        project_id=project_id,
        stage_id="research",
    )[0]
    artifact = app.state.repository.latest_project_stage_artifact(
        project_id,
        "research",
    )
    project_page = client.get(f"/projects/{project_id}")
    run_confirmation = evaluate_live_hermes_run_confirmation(
        app.state.repository,
        project_id,
        "research",
    )
    raw_artifact = json.dumps(artifact, sort_keys=True)

    assert response.status_code == 303
    assert len(fake_runner.calls) == 1
    assert fake_runner.calls[0]["command"] == (
        "hermes",
        "profiles",
        "run",
        "research-agent",
        "--stage",
        "research",
        "--output",
        "product-wizard-artifact-json",
    )
    assert "--dry-run" not in fake_runner.calls[0]["command"]
    assert "You are `research-agent`" in fake_runner.calls[0]["prompt"]
    assert fake_runner.calls[0]["timeout_seconds"] == 13
    assert generation_run["status"] == "succeeded"
    assert generation_run["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    assert artifact is not None
    assert generation_run["artifact_id"] == artifact["id"]
    assert artifact["json"]["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    metadata = artifact["json"]["generation_metadata"]
    assert metadata["adapter"] == LIVE_HERMES_LIVE_ADAPTER
    assert metadata["status"] == LIVE_HERMES_LIVE_STATUS
    assert metadata["external_execution"] == "enabled"
    assert metadata["runner"]["label"] == "fake_test_runner"
    assert metadata["operator_preflight"]["manual_pilot_confirmation"] == "verified"
    assert metadata["operator_preflight"]["run_confirmation_decision_id"] == (
        run_confirmation_id
    )
    assert metadata["operator_preflight"]["external_execution_enabled"] is True
    audit = metadata["execution_audit"]
    assert audit["schema"] == "live_hermes_execution_audit_v1"
    assert audit["immutable"] is True
    assert audit["generation_run_id"] == generation_run["id"]
    assert audit["command_fingerprint"]["sha256"]
    assert audit["command_fingerprint"]["command_preview"] == metadata["command_preview"]
    assert audit["prompt_fingerprint"]["sha256"] == metadata["prompt_handoff"]["sha256"]
    assert audit["approval_consumption"]["decision_id"] == run_confirmation_id
    assert audit["approval_consumption"]["consumed_by_generation_run_id"] == (
        generation_run["id"]
    )
    assert audit["approval_consumption"]["status"] == "consumed"
    assert audit["output_fingerprints"]["stdout_sha256"] == (
        metadata["stdout_capture"]["sha256"]
    )
    assert audit["post_run_review"]["status"] == "awaiting_founder_review"
    assert metadata["duration_ms"] == 17
    assert metadata["stdout_capture"]["bytes"] > 0
    assert metadata["stderr_capture"]["bytes"] > 0
    assert "--dry-run" not in metadata["command_preview"]
    assert "## Live Hermes Runner" in artifact["markdown_content"]
    assert "Runner: `fake_test_runner`" in artifact["markdown_content"]
    assert project_page.status_code == 200
    assert "Live Hermes Runner" in project_page.text
    assert "External execution" in project_page.text
    assert "enabled" in project_page.text
    assert LIVE_HERMES_LIVE_ADAPTER in project_page.text
    assert LIVE_HERMES_LIVE_STATUS in project_page.text
    assert "Last adapter capture" in project_page.text
    assert "fake_test_runner" in project_page.text
    assert "Pilot confirmation" in project_page.text
    assert "verified" in project_page.text
    assert "Execution audit" in project_page.text
    assert "Approval consumed" in project_page.text
    assert generation_run["id"] in project_page.text
    assert "one-run confirmation ready" not in project_page.text
    assert "Request one-run confirmation" in project_page.text
    assert live_decision_id in project_page.text
    assert run_confirmation.decision_id == run_confirmation_id
    assert run_confirmation.fresh is False
    assert run_confirmation.latest_live_run_id == generation_run["id"]
    assert secret_violations({"artifact": raw_artifact}) == []
    assert secret_violations({"project_detail": project_page.text}) == []
