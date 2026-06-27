import json

import pytest

from hermes_company_os.generation_service import (
    LIVE_HERMES_DRY_RUN_ADAPTER,
    LIVE_HERMES_DRY_RUN_STATUS,
    LIVE_HERMES_GENERATION_MODE,
    LIVE_HERMES_LIVE_ADAPTER,
    LIVE_HERMES_LIVE_STATUS,
    LIVE_HERMES_LOCKED_MESSAGE,
    LOCAL_DEMO_GENERATION_MODE,
    DryRunLiveHermesAdapter,
    LiveHermesAdapterRawResult,
    LiveHermesCommandAdapter,
    LiveHermesGenerationGate,
    LiveHermesGenerationService,
    LocalDemoGenerationService,
    StageGenerationRequest,
    normalize_generation_mode,
)
from hermes_company_os.product_wizard import (
    ProductWizardIntake,
    generate_wizard_artifact,
)
from hermes_company_os.secret_guard import secret_violations

FAKE_OPENAI_SECRET = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"


def _intake() -> ProductWizardIntake:
    return ProductWizardIntake(
        project_name="Ops Copilot",
        founder_idea="A dashboard that turns operations requests into approved tasks.",
        target_customer="Founder operators coordinating a small AI implementation team.",
        problem="Plans lose context between research, product, architecture, and build.",
        constraints="Public-demo generation must stay local and deterministic.",
        success_metric="Accepted code plan in one founder review session.",
    )


class CapturingLiveHermesAdapter:
    def __init__(self, result: LiveHermesAdapterRawResult | None = None):
        self.requests = []
        self.result = result

    def execute(self, request):
        self.requests.append(request)
        if self.result:
            return self.result
        return DryRunLiveHermesAdapter().execute(request)


class FakeHermesCommandRunner:
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


def test_local_demo_generation_service_preserves_current_product_wizard_output():
    intake = _intake()
    request = StageGenerationRequest(stage_id="research", intake=intake)

    artifact = LocalDemoGenerationService().generate_stage(request)
    direct_artifact = generate_wizard_artifact("research", intake)

    assert artifact.to_dict() == direct_artifact.to_dict()
    assert artifact.generation_mode == LOCAL_DEMO_GENERATION_MODE
    assert artifact.metadata["generation_mode"] == LOCAL_DEMO_GENERATION_MODE
    assert secret_violations({"artifact": json.dumps(artifact.to_dict())}) == []


def test_local_demo_generation_service_uses_approved_source_artifacts():
    intake = _intake()
    approved_sources = [
        {
            "id": "research-approved",
            "stage": "research",
            "title": "Approved research",
            "content": "Founder operators need a visible approval trail.",
            "status": "approved",
        }
    ]

    artifact = LocalDemoGenerationService().generate_stage(
        StageGenerationRequest(
            stage_id="prd",
            intake=intake,
            approved_sources=approved_sources,
        )
    )

    assert artifact.stage == "prd"
    assert artifact.source_artifact_ids == ("research-approved",)
    assert "research-approved" in artifact.markdown


def test_local_demo_generation_service_rejects_unsupported_generation_mode():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )

    with pytest.raises(ValueError, match="Unsupported Product Wizard generation mode"):
        LocalDemoGenerationService().generate_stage(request)


def test_generation_mode_normalization_accepts_only_supported_modes():
    assert normalize_generation_mode("local_fake_public_demo") == LOCAL_DEMO_GENERATION_MODE
    assert normalize_generation_mode("live_hermes") == LIVE_HERMES_GENERATION_MODE

    with pytest.raises(ValueError, match="Unsupported Product Wizard generation mode"):
        normalize_generation_mode("live_hermes_draft")


def test_live_hermes_generation_service_fails_closed_until_gates_are_ready():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )

    with pytest.raises(ValueError, match="Live Hermes generation is locked"):
        LiveHermesGenerationService().generate_stage(request)

    enabled_without_approval = LiveHermesGenerationService(
        LiveHermesGenerationGate(enabled=True)
    )
    with pytest.raises(ValueError, match="founder approval"):
        enabled_without_approval.generate_stage(request)

    ready_gate = LiveHermesGenerationService(
        LiveHermesGenerationGate(
            enabled=True,
            founder_approved=True,
            runtime_ready=True,
        )
    )
    artifact = ready_gate.generate_stage(request)
    generation_metadata = artifact.metadata["generation_metadata"]

    assert artifact.generation_mode == LIVE_HERMES_GENERATION_MODE
    assert artifact.metadata["generation_mode"] == LIVE_HERMES_GENERATION_MODE
    assert generation_metadata["adapter"] == LIVE_HERMES_DRY_RUN_ADAPTER
    assert generation_metadata["status"] == LIVE_HERMES_DRY_RUN_STATUS
    assert generation_metadata["external_execution"] == "disabled"
    assert generation_metadata["command_preview"] == [
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
    assert generation_metadata["prompt_handoff"]["contract"] == (
        "product_wizard_prompt_contract_v1"
    )
    assert generation_metadata["output_parser"] == {
        "name": "product_wizard_artifact_v1",
        "status": "validated",
    }
    assert "## Live Hermes Dry Run" in artifact.markdown
    assert "External execution: `disabled`" in artifact.markdown
    assert secret_violations({"artifact": json.dumps(artifact.to_dict())}) == []

    assert secret_violations({"locked_message": LIVE_HERMES_LOCKED_MESSAGE}) == []


def test_live_hermes_generation_service_captures_adapter_failures():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )
    ready_gate = LiveHermesGenerationGate(
        enabled=True,
        founder_approved=True,
        runtime_ready=True,
    )
    failing_adapter = CapturingLiveHermesAdapter(
        LiveHermesAdapterRawResult(
            stdout="",
            stderr="Simulated adapter failure.",
            exit_code=1,
        )
    )

    with pytest.raises(ValueError, match="Simulated adapter failure"):
        LiveHermesGenerationService(
            ready_gate,
            adapter=failing_adapter,
        ).generate_stage(request)

    assert len(failing_adapter.requests) == 1
    assert failing_adapter.requests[0].prompt_contract["stage"] == "research"


def test_live_hermes_generation_service_reports_adapter_timeout():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )
    ready_gate = LiveHermesGenerationGate(
        enabled=True,
        founder_approved=True,
        runtime_ready=True,
    )
    timeout_adapter = CapturingLiveHermesAdapter(
        LiveHermesAdapterRawResult(stdout="", timed_out=True)
    )

    with pytest.raises(ValueError, match="timed out after 7 seconds"):
        LiveHermesGenerationService(
            ready_gate,
            adapter=timeout_adapter,
            timeout_seconds=7,
        ).generate_stage(request)


def test_real_hermes_command_adapter_is_disabled_by_default():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )
    ready_gate = LiveHermesGenerationGate(
        enabled=True,
        founder_approved=True,
        runtime_ready=True,
    )
    fake_runner = FakeHermesCommandRunner(
        LiveHermesAdapterRawResult(
            stdout="This fake runner must not be called.",
            duration_ms=9,
        )
    )
    adapter = LiveHermesCommandAdapter(
        live_execution_enabled=True,
        runner=fake_runner,
    )

    artifact = LiveHermesGenerationService(
        ready_gate,
        adapter=adapter,
    ).generate_stage(request)

    assert fake_runner.calls == []
    assert artifact.metadata["generation_metadata"]["adapter"] == (
        LIVE_HERMES_DRY_RUN_ADAPTER
    )
    assert artifact.metadata["generation_metadata"]["external_execution"] == "disabled"
    assert "--dry-run" in artifact.metadata["generation_metadata"]["command_preview"]


def test_real_hermes_command_adapter_uses_fake_runner_only_when_enabled():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )
    ready_gate = LiveHermesGenerationGate(
        enabled=True,
        founder_approved=True,
        runtime_ready=True,
    )
    fake_runner = FakeHermesCommandRunner(
        LiveHermesAdapterRawResult(
            stdout='{"artifact": "generated by fake runner"}',
            stderr="diagnostic note",
            duration_ms=17,
        )
    )
    adapter = LiveHermesCommandAdapter(
        live_execution_enabled=True,
        runner=fake_runner,
    )

    artifact = LiveHermesGenerationService(
        ready_gate,
        adapter=adapter,
        timeout_seconds=11,
        live_execution_enabled=True,
    ).generate_stage(request)
    metadata = artifact.metadata["generation_metadata"]

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
    assert fake_runner.calls[0]["timeout_seconds"] == 11
    assert metadata["adapter"] == LIVE_HERMES_LIVE_ADAPTER
    assert metadata["status"] == LIVE_HERMES_LIVE_STATUS
    assert metadata["external_execution"] == "enabled"
    assert metadata["stdout_capture"]["bytes"] > 0
    assert metadata["stdout_capture"]["redacted"] is False
    assert metadata["stderr_capture"]["bytes"] > 0
    assert "## Live Hermes Runner" in artifact.markdown
    assert "External execution: `enabled`" in artifact.markdown
    assert secret_violations({"artifact": json.dumps(artifact.to_dict())}) == []


def test_real_hermes_command_adapter_redacts_secret_shaped_errors():
    request = StageGenerationRequest(
        stage_id="research",
        intake=_intake(),
        mode=LIVE_HERMES_GENERATION_MODE,
    )
    ready_gate = LiveHermesGenerationGate(
        enabled=True,
        founder_approved=True,
        runtime_ready=True,
    )
    fake_runner = FakeHermesCommandRunner(
        LiveHermesAdapterRawResult(
            stdout="",
            stderr="failed with " + FAKE_OPENAI_SECRET,
            exit_code=1,
        )
    )
    adapter = LiveHermesCommandAdapter(
        live_execution_enabled=True,
        runner=fake_runner,
    )

    with pytest.raises(ValueError) as error:
        LiveHermesGenerationService(
            ready_gate,
            adapter=adapter,
            live_execution_enabled=True,
        ).generate_stage(request)

    assert "redacted" in str(error.value)
    assert FAKE_OPENAI_SECRET not in str(error.value)
    assert secret_violations({"error": str(error.value)}) == []
