import json

import pytest

from hermes_company_os.generation_service import (
    LOCAL_DEMO_GENERATION_MODE,
    LocalDemoGenerationService,
    StageGenerationRequest,
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
        mode="live_hermes_draft",  # type: ignore[arg-type]
    )

    with pytest.raises(ValueError, match="Unsupported Product Wizard generation mode"):
        LocalDemoGenerationService().generate_stage(request)
