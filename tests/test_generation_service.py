import json

import pytest

from hermes_company_os.generation_service import (
    LIVE_HERMES_DRY_RUN_ADAPTER,
    LIVE_HERMES_DRY_RUN_STATUS,
    LIVE_HERMES_GENERATION_MODE,
    LIVE_HERMES_LOCKED_MESSAGE,
    LOCAL_DEMO_GENERATION_MODE,
    DryRunLiveHermesAdapter,
    LiveHermesAdapterRawResult,
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
