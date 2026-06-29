import json

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.generation_service import (
    LIVE_HERMES_GENERATION_MODE,
    LIVE_HERMES_LOCKED_MESSAGE,
    LOCAL_DEMO_GENERATION_MODE,
    LiveHermesAdapterRawResult,
    available_generation_modes,
    generation_mode_option,
    normalize_selectable_generation_mode,
    resolve_generation_mode_selection,
    stage_profile_routing,
)
from hermes_company_os.main import create_app
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings


# ---------------------------------------------------------------------------
# Fake Hermes command runner (the unit suite never invokes the real `hermes`).
# ---------------------------------------------------------------------------
class FakeHermesCommandRunner:
    def __init__(self, result: LiveHermesAdapterRawResult):
        self.result = result
        self.calls = []

    def run(self, command, prompt, timeout_seconds):
        self.calls.append(
            {"command": command, "prompt": prompt, "timeout_seconds": timeout_seconds}
        )
        return self.result


# ---------------------------------------------------------------------------
# Catalog / resolution unit tests
# ---------------------------------------------------------------------------
def test_selectable_generation_mode_catalog_maps_to_engine_modes():
    local = generation_mode_option("local_demo")
    draft = generation_mode_option("live_hermes_draft")
    review = generation_mode_option("live_hermes_with_review")

    assert local.engine_mode == LOCAL_DEMO_GENERATION_MODE
    assert local.requires_live_hermes is False
    assert draft.engine_mode == LIVE_HERMES_GENERATION_MODE
    assert draft.requires_live_hermes is True
    assert draft.requires_review is False
    assert review.engine_mode == LIVE_HERMES_GENERATION_MODE
    assert review.requires_review is True


def test_normalize_selectable_generation_mode_rejects_unknown_mode():
    assert normalize_selectable_generation_mode("local_demo") == "local_demo"
    with pytest.raises(ValueError, match="Unsupported"):
        normalize_selectable_generation_mode("live_hermes")  # engine mode, not selectable


def test_resolve_generation_mode_local_demo_always_available():
    resolved = resolve_generation_mode_selection(
        "local_demo",
        live_execution_flag_enabled=False,
        readiness_ready=False,
        readiness_blocker="anything",
    )
    assert resolved.available is True
    assert resolved.blocker == ""
    assert resolved.engine_mode == LOCAL_DEMO_GENERATION_MODE


def test_resolve_generation_mode_live_blocked_when_flag_off():
    resolved = resolve_generation_mode_selection(
        "live_hermes_draft",
        live_execution_flag_enabled=False,
        readiness_ready=True,
    )
    assert resolved.available is False
    assert resolved.blocker == LIVE_HERMES_LOCKED_MESSAGE


def test_resolve_generation_mode_live_blocked_when_not_ready():
    resolved = resolve_generation_mode_selection(
        "live_hermes_with_review",
        live_execution_flag_enabled=True,
        readiness_ready=False,
        readiness_blocker="Profile installation blocked.",
    )
    assert resolved.available is False
    assert "Profile installation blocked." in resolved.blocker


def test_resolve_generation_mode_live_available_when_flag_and_ready():
    resolved = resolve_generation_mode_selection(
        "live_hermes_draft",
        live_execution_flag_enabled=True,
        readiness_ready=True,
    )
    assert resolved.available is True
    assert resolved.engine_mode == LIVE_HERMES_GENERATION_MODE


def test_available_generation_modes_marks_live_unavailable_by_default():
    modes = available_generation_modes(
        live_execution_flag_enabled=False,
        readiness_ready=False,
    )
    by_mode = {mode["mode"]: mode for mode in modes}
    assert by_mode["local_demo"]["available"] is True
    assert by_mode["live_hermes_draft"]["available"] is False
    assert by_mode["live_hermes_with_review"]["available"] is False
    assert secret_violations({"modes": json.dumps(modes)}) == []


def test_stage_profile_routing_is_data_driven():
    research = stage_profile_routing("research")
    code_plan = stage_profile_routing("code_plan")
    acceptance = stage_profile_routing("acceptance")

    assert research.owner_agent_id == "research-agent"
    assert code_plan.owner_agent_id == "backend-engineer"
    assert "frontend-engineer" in code_plan.supporting_agent_ids
    assert "cloud-infra-agent" in code_plan.supporting_agent_ids
    assert acceptance.owner_agent_id == "qa-critic"
    assert "test-automation-agent" in acceptance.supporting_agent_ids

    with pytest.raises(ValueError, match="Unknown product wizard stage"):
        stage_profile_routing("not-a-stage")


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------
def _app(tmp_path, *, live_enabled=False, runner=None):
    settings = Settings(
        database_path=tmp_path / "company.db",
        hermes_live_execution_enabled=live_enabled,
    )
    app = create_app(settings)
    if runner is not None:
        app.state.live_hermes_command_runner = runner
        app.state.live_hermes_runner_label = "fake_test_runner"
    return app


def _project(app) -> str:
    repository: CompanyRepository = app.state.repository
    return repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI due-diligence workspace.",
    )


def _mark_agent_runtime_ready(repository: CompanyRepository, agent_id: str) -> None:
    repository.update_profile_installation_check(
        check_id=f"{agent_id}-profile-installation",
        status="verified",
        evidence="Verified in generation test.",
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
        notes="Verified in generation test.",
    )
    for check in repository.list_profile_acceptance_checks():
        if check["agent_id"] == agent_id:
            repository.update_profile_acceptance_check(
                check_id=check["id"],
                status="verified",
                evidence="Verified in generation test.",
            )


def _approve_live_decision(repository: CompanyRepository, project_id: str, stage_id: str):
    from hermes_company_os.live_hermes_readiness import (
        LIVE_HERMES_DECISION_SOURCE,
        LIVE_HERMES_DECISION_TYPE,
    )

    decision_id = repository.create_founder_decision(
        title="Approve live Hermes generation",
        urgency="urgent",
        decision_type=LIVE_HERMES_DECISION_TYPE,
        source=LIVE_HERMES_DECISION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id=stage_id,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if blocked.",
        context="Approve live Hermes generation.",
        evidence="Runtime gates verified.",
    )
    repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Founder approved live generation.",
        founder_confirmed=True,
    )


def test_generation_modes_json_reports_local_only_when_flag_off(tmp_path):
    app = _app(tmp_path)
    project_id = _project(app)
    client = TestClient(app)

    response = client.get(f"/projects/{project_id}/stages/research/generation-modes.json")
    assert response.status_code == 200
    body = response.json()
    assert body["live_execution_flag_enabled"] is False
    assert body["default_mode"] == "local_demo"
    assert body["routing"]["owner_agent_id"] == "research-agent"
    by_mode = {mode["mode"]: mode for mode in body["modes"]}
    assert by_mode["local_demo"]["available"] is True
    assert by_mode["live_hermes_draft"]["available"] is False
    assert by_mode["live_hermes_draft"]["blocker"] == LIVE_HERMES_LOCKED_MESSAGE
    assert secret_violations({"body": json.dumps(body)}) == []


def test_generation_modes_json_missing_project_returns_404(tmp_path):
    app = _app(tmp_path)
    client = TestClient(app)
    response = client.get("/projects/missing/stages/research/generation-modes.json")
    assert response.status_code == 404


def test_generate_mode_local_demo_succeeds_and_records_run(tmp_path):
    app = _app(tmp_path)
    project_id = _project(app)
    client = TestClient(app)

    response = client.post(
        f"/projects/{project_id}/stages/research/generate-mode",
        data={"generation_mode": "local_demo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "generated"
    assert body["engine_mode"] == LOCAL_DEMO_GENERATION_MODE

    repository: CompanyRepository = app.state.repository
    run = repository.get_generation_run(body["generation_run_id"])
    assert run["status"] == "succeeded"
    assert run["generation_mode"] == LOCAL_DEMO_GENERATION_MODE
    assert run["artifact_id"] == body["artifact_id"]

    artifact = repository.latest_project_stage_artifact(project_id, "research")
    assert artifact["id"] == body["artifact_id"]
    assert secret_violations({"markdown": artifact["markdown_content"]}) == []


def test_generate_mode_invalid_mode_returns_409(tmp_path):
    app = _app(tmp_path)
    project_id = _project(app)
    client = TestClient(app)
    response = client.post(
        f"/projects/{project_id}/stages/research/generate-mode",
        data={"generation_mode": "totally-bogus"},
    )
    assert response.status_code == 409


def test_generate_mode_live_blocked_when_flag_off_records_blocked_run(tmp_path):
    app = _app(tmp_path)  # flag OFF (default)
    project_id = _project(app)
    client = TestClient(app)

    response = client.post(
        f"/projects/{project_id}/stages/research/generate-mode",
        data={"generation_mode": "live_hermes_draft"},
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["state"] == "blocked"
    assert detail["blocker"] == LIVE_HERMES_LOCKED_MESSAGE

    repository: CompanyRepository = app.state.repository
    run = repository.get_generation_run(detail["generation_run_id"])
    assert run["status"] == "failed"
    # No artifact was produced for the blocked attempt.
    assert run["artifact_id"] in (None, "")
    assert repository.latest_project_stage_artifact(project_id, "research") is None


def test_generate_mode_live_blocked_when_readiness_not_met(tmp_path):
    # Flag is ON but readiness gates have not been satisfied -> blocked state.
    app = _app(tmp_path, live_enabled=True)
    project_id = _project(app)
    client = TestClient(app)

    response = client.post(
        f"/projects/{project_id}/stages/research/generate-mode",
        data={"generation_mode": "live_hermes_draft"},
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["state"] == "blocked"
    assert detail["blocker"]  # a readiness blocker string

    repository: CompanyRepository = app.state.repository
    run = repository.get_generation_run(detail["generation_run_id"])
    assert run["status"] == "failed"


def _approve_run_confirmation(
    repository: CompanyRepository, project_id: str, stage_id: str
):
    from hermes_company_os.live_hermes_readiness import (
        LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
        LIVE_HERMES_RUN_CONFIRMATION_TYPE,
    )

    decision_id = repository.create_founder_decision(
        title="Confirm one live Hermes run",
        urgency="urgent",
        decision_type=LIVE_HERMES_RUN_CONFIRMATION_TYPE,
        source=LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id=stage_id,
        slack_channel="#founder-command",
        telegram_policy="Telegram only if blocked.",
        context="Confirm a single live run.",
        evidence="Founder is present.",
    )
    repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Founder confirmed one run.",
        founder_confirmed=True,
    )


def test_generate_mode_live_draft_succeeds_when_ready_with_fake_runner(tmp_path):
    # Flag ON, readiness + founder approval + fresh one-run confirmation satisfied.
    # The gated live engine invokes the (fake) command runner via the boundary.
    fake_runner = FakeHermesCommandRunner(
        LiveHermesAdapterRawResult(
            stdout='{"profile_output": "generated by fake runner"}',
            stderr="diagnostic note",
            duration_ms=5,
        )
    )
    app = _app(tmp_path, live_enabled=True, runner=fake_runner)
    repository: CompanyRepository = app.state.repository
    project_id = _project(app)
    _mark_agent_runtime_ready(repository, "research-agent")
    _approve_live_decision(repository, project_id, "research")
    _approve_run_confirmation(repository, project_id, "research")
    client = TestClient(app)

    response = client.post(
        f"/projects/{project_id}/stages/research/generate-mode",
        data={"generation_mode": "live_hermes_with_review"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["engine_mode"] == LIVE_HERMES_GENERATION_MODE
    assert body["requires_review"] is True
    assert body["state"] == "generated"
    # Flag is on + confirmation fresh -> the gated runner IS invoked.
    assert len(fake_runner.calls) == 1

    run = repository.get_generation_run(body["generation_run_id"])
    assert run["status"] == "succeeded"
    assert run["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    artifact = repository.latest_project_stage_artifact(project_id, "research")
    assert "Live Hermes Runner" in artifact["markdown_content"]
    assert secret_violations({"markdown": artifact["markdown_content"]}) == []


def test_generate_mode_live_failure_records_blocked_run(tmp_path):
    # Flag ON, ready, fresh run confirmation, but the runner fails -> blocked run.
    from hermes_company_os.live_hermes_readiness import (
        LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
        LIVE_HERMES_RUN_CONFIRMATION_TYPE,
    )

    fake_runner = FakeHermesCommandRunner(
        LiveHermesAdapterRawResult(
            stdout="", stderr="Simulated runner failure.", exit_code=1
        )
    )
    app = _app(tmp_path, live_enabled=True, runner=fake_runner)
    repository: CompanyRepository = app.state.repository
    project_id = _project(app)
    _mark_agent_runtime_ready(repository, "research-agent")
    _approve_live_decision(repository, project_id, "research")
    run_confirmation_id = repository.create_founder_decision(
        title="Confirm one live Hermes run",
        urgency="urgent",
        decision_type=LIVE_HERMES_RUN_CONFIRMATION_TYPE,
        source=LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id="research",
        slack_channel="#founder-command",
        telegram_policy="Telegram only if blocked.",
        context="Confirm a single live run.",
        evidence="Founder is present.",
    )
    repository.update_founder_decision(
        run_confirmation_id,
        status="approved",
        decision="Founder confirmed one run.",
        founder_confirmed=True,
    )
    client = TestClient(app)

    response = client.post(
        f"/projects/{project_id}/stages/research/generate-mode",
        data={"generation_mode": "live_hermes_draft"},
    )
    assert response.status_code == 409
    assert "Simulated runner failure" in str(response.json()["detail"])
    assert len(fake_runner.calls) == 1

    runs = repository.list_generation_runs(project_id, stage_id="research")
    assert runs[0]["status"] == "failed"


def test_generate_mode_does_not_change_local_demo_default(tmp_path):
    # Posting with no mode form field uses the local_demo default.
    app = _app(tmp_path)
    project_id = _project(app)
    client = TestClient(app)
    response = client.post(f"/projects/{project_id}/stages/research/generate-mode")
    assert response.status_code == 200
    assert response.json()["selected_mode"] == "local_demo"
