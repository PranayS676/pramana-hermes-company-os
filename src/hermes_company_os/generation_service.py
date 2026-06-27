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

GenerationMode = Literal["local_fake_public_demo", "live_hermes"]
LOCAL_DEMO_GENERATION_MODE: GenerationMode = "local_fake_public_demo"
LIVE_HERMES_GENERATION_MODE: GenerationMode = "live_hermes"
SUPPORTED_GENERATION_MODES: tuple[GenerationMode, ...] = (
    LOCAL_DEMO_GENERATION_MODE,
    LIVE_HERMES_GENERATION_MODE,
)
LIVE_HERMES_LOCKED_MESSAGE = (
    "Live Hermes generation is locked. Founder approval and Hermes readiness "
    "gates are required before live profile execution."
)
ApprovedSourceInput = Iterable[
    ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any]
]


def normalize_generation_mode(mode: str) -> GenerationMode:
    cleaned_mode = mode.strip()
    if cleaned_mode == LOCAL_DEMO_GENERATION_MODE:
        return LOCAL_DEMO_GENERATION_MODE
    if cleaned_mode == LIVE_HERMES_GENERATION_MODE:
        return LIVE_HERMES_GENERATION_MODE
    raise ValueError(f"Unsupported Product Wizard generation mode: {mode}")


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


@dataclass(frozen=True)
class LiveHermesGenerationGate:
    enabled: bool = False
    founder_approved: bool = False
    runtime_ready: bool = False

    def blocker(self) -> str:
        if not self.enabled:
            return LIVE_HERMES_LOCKED_MESSAGE
        if not self.founder_approved:
            return "Live Hermes generation is locked until founder approval is recorded."
        if not self.runtime_ready:
            return "Live Hermes generation is locked until Hermes readiness checks pass."
        return ""


class LiveHermesGenerationService:
    mode: GenerationMode = LIVE_HERMES_GENERATION_MODE

    def __init__(self, gate: LiveHermesGenerationGate | None = None):
        self.gate = gate or LiveHermesGenerationGate()

    def generate_stage(self, request: StageGenerationRequest) -> ProductWizardArtifact:
        if request.mode != self.mode:
            raise ValueError(
                f"Unsupported Product Wizard generation mode: {request.mode}"
            )
        blocker = self.gate.blocker()
        if blocker:
            raise ValueError(blocker)
        raise ValueError(
            "Live Hermes generation adapter is not implemented in this public demo."
        )
