from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from hermes_company_os.product_wizard import (
    ProductWizardArtifact,
    ProductWizardIntake,
    ProductWizardSourceArtifact,
    WizardStage,
    generate_wizard_artifact,
)

GenerationMode = Literal["local_fake_public_demo"]
LOCAL_DEMO_GENERATION_MODE: GenerationMode = "local_fake_public_demo"
ApprovedSourceInput = Iterable[
    ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any]
]


@dataclass(frozen=True)
class StageGenerationRequest:
    stage_id: WizardStage | str
    intake: ProductWizardIntake | Mapping[str, Any]
    approved_sources: ApprovedSourceInput = ()
    mode: GenerationMode = LOCAL_DEMO_GENERATION_MODE


class StageGenerationService(Protocol):
    def generate_stage(self, request: StageGenerationRequest) -> ProductWizardArtifact:
        """Generate one Product Wizard stage artifact."""


class LocalDemoGenerationService:
    mode: GenerationMode = LOCAL_DEMO_GENERATION_MODE

    def generate_stage(self, request: StageGenerationRequest) -> ProductWizardArtifact:
        if request.mode != self.mode:
            raise ValueError(
                f"Unsupported Product Wizard generation mode: {request.mode}"
            )
        return generate_wizard_artifact(
            request.stage_id,
            request.intake,
            request.approved_sources,
        )
