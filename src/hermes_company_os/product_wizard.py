from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from hermes_company_os.secret_guard import SECRET_PATTERNS

WizardStage = Literal["research", "prd", "architecture", "tasks", "code_plan", "acceptance"]

WIZARD_STAGES: tuple[WizardStage, ...] = (
    "research",
    "prd",
    "architecture",
    "tasks",
    "code_plan",
    "acceptance",
)

APPROVED_SOURCE_STATUSES = frozenset({"approved", "accepted", "complete", "verified"})

COMMON_QUALITY_CHECKS: tuple[tuple[str, str], ...] = (
    ("target_user", "Names the target user or buyer."),
    ("problem", "States the problem and why it matters."),
    ("scope", "Defines the current scope and explicit non-goals."),
    ("risks", "Calls out product, technical, and operational risks."),
    ("test_plan", "Includes a validation or testing plan."),
    ("acceptance_mapping", "Maps work back to acceptance criteria."),
    ("prior_artifacts", "Uses approved prior artifacts when the stage depends on them."),
    ("secret_safety", "Avoids fake or real secret-looking literals."),
)


@dataclass(frozen=True)
class ProductWizardIntake:
    project_name: str
    founder_idea: str
    target_customer: str = ""
    problem: str = ""
    current_alternatives: str = ""
    why_now: str = ""
    desired_outcome: str = ""
    constraints: str = ""
    technical_preferences: str = ""
    go_to_market: str = ""
    success_metric: str = ""
    open_questions: str = ""

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> ProductWizardIntake:
        return cls(
            project_name=_safe_text(values.get("project_name", "")) or "Untitled Product",
            founder_idea=_safe_text(values.get("founder_idea", "")) or "Founder idea not supplied.",
            target_customer=_safe_text(values.get("target_customer", "")),
            problem=_safe_text(values.get("problem", "")),
            current_alternatives=_safe_text(values.get("current_alternatives", "")),
            why_now=_safe_text(values.get("why_now", "")),
            desired_outcome=_safe_text(values.get("desired_outcome", "")),
            constraints=_safe_text(values.get("constraints", "")),
            technical_preferences=_safe_text(values.get("technical_preferences", "")),
            go_to_market=_safe_text(values.get("go_to_market", "")),
            success_metric=_safe_text(values.get("success_metric", "")),
            open_questions=_safe_text(values.get("open_questions", "")),
        )

    def to_context_dict(self) -> dict[str, str]:
        return {
            "project_name": self.project_name,
            "founder_idea": self.founder_idea,
            "target_customer": self.target_customer
            or "First reachable target user is not specified.",
            "problem": self.problem or "Problem statement should be sharpened in research.",
            "current_alternatives": self.current_alternatives
            or "Current alternatives are unknown and need discovery.",
            "why_now": self.why_now or "Timing advantage needs evidence.",
            "desired_outcome": self.desired_outcome
            or "A narrow useful first version should be defined.",
            "constraints": self.constraints or "No explicit constraints supplied.",
            "technical_preferences": self.technical_preferences
            or "Use the simplest stack that can prove the workflow.",
            "go_to_market": self.go_to_market or "First channel needs validation.",
            "success_metric": self.success_metric or "Define one measurable first proof point.",
            "open_questions": self.open_questions or "No open questions supplied.",
        }


@dataclass(frozen=True)
class ProductWizardStageContract:
    stage: WizardStage
    title: str
    owner_agent_id: str
    supporting_agent_ids: tuple[str, ...] = ()
    required_prior_stages: tuple[WizardStage, ...] = ()
    output_sections: tuple[str, ...] = ()
    quality_check_ids: tuple[str, ...] = tuple(check_id for check_id, _ in COMMON_QUALITY_CHECKS)
    next_decision: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "title": self.title,
            "owner_agent_id": self.owner_agent_id,
            "supporting_agent_ids": list(self.supporting_agent_ids),
            "required_prior_stages": list(self.required_prior_stages),
            "output_sections": list(self.output_sections),
            "quality_check_ids": list(self.quality_check_ids),
            "next_decision": self.next_decision,
        }


@dataclass(frozen=True)
class ProductWizardSourceArtifact:
    id: str
    stage: str
    title: str
    content: str
    approved: bool = True


@dataclass(frozen=True)
class ProductWizardArtifact:
    id: str
    stage: WizardStage
    title: str
    owner_agent_id: str
    markdown: str
    source_artifact_ids: tuple[str, ...]
    checks: tuple[dict[str, str], ...]
    next_decision: str
    supporting_agent_ids: tuple[str, ...] = ()
    generation_mode: str = "local_fake_public_demo"
    generation_metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def metadata(self) -> dict[str, Any]:
        metadata = {
            "stage": self.stage,
            "title": self.title,
            "owner_agent_id": self.owner_agent_id,
            "supporting_agent_ids": list(self.supporting_agent_ids),
            "source_artifact_ids": list(self.source_artifact_ids),
            "checks": [dict(check) for check in self.checks],
            "next_decision": self.next_decision,
            "generation_mode": self.generation_mode,
        }
        if self.generation_metadata:
            metadata["generation_metadata"] = dict(self.generation_metadata)
        return metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "markdown": self.markdown,
            "metadata": self.metadata,
        }


STAGE_CONTRACTS: dict[WizardStage, ProductWizardStageContract] = {
    "research": ProductWizardStageContract(
        stage="research",
        title="Opportunity Research",
        owner_agent_id="research-agent",
        output_sections=(
            "Target User",
            "Problem",
            "Discovery Scope",
            "Risks",
            "Validation And Test Plan",
            "Acceptance Mapping",
        ),
        next_decision="Approve the research direction or revise the target user/problem.",
    ),
    "prd": ProductWizardStageContract(
        stage="prd",
        title="Lean PRD",
        owner_agent_id="product-manager",
        required_prior_stages=("research",),
        output_sections=(
            "Target User",
            "Problem",
            "Scope",
            "Requirements",
            "Risks",
            "Test Plan",
            "Acceptance Mapping",
        ),
        next_decision="Approve the PRD scope before architecture starts.",
    ),
    "architecture": ProductWizardStageContract(
        stage="architecture",
        title="Architecture Plan",
        owner_agent_id="engineering-manager",
        required_prior_stages=("research", "prd"),
        output_sections=(
            "Target User",
            "Problem",
            "System Scope",
            "Architecture",
            "Risks",
            "Test Plan",
            "Acceptance Mapping",
        ),
        next_decision="Approve the architecture boundary and operational risk posture.",
    ),
    "tasks": ProductWizardStageContract(
        stage="tasks",
        title="Implementation Task Breakdown",
        owner_agent_id="engineering-manager",
        supporting_agent_ids=("chief-of-staff",),
        required_prior_stages=("prd", "architecture"),
        output_sections=(
            "Target User",
            "Problem",
            "Task Scope",
            "Backlog",
            "Risks",
            "Test Plan",
            "Acceptance Mapping",
        ),
        next_decision="Approve the first implementation slice and founder decision gate.",
    ),
    "code_plan": ProductWizardStageContract(
        stage="code_plan",
        title="Code Implementation Plan",
        owner_agent_id="backend-engineer",
        supporting_agent_ids=("frontend-engineer", "cloud-infra-agent"),
        required_prior_stages=("architecture", "tasks"),
        output_sections=(
            "Target User",
            "Problem",
            "Code Scope",
            "Implementation Plan",
            "Risks",
            "Test Plan",
            "Acceptance Mapping",
        ),
        next_decision="Approve the engineering plan before code work begins.",
    ),
    "acceptance": ProductWizardStageContract(
        stage="acceptance",
        title="Acceptance And QA Plan",
        owner_agent_id="qa-critic",
        supporting_agent_ids=("test-automation-agent",),
        required_prior_stages=("prd", "tasks", "code_plan"),
        output_sections=(
            "Target User",
            "Problem",
            "Acceptance Scope",
            "Acceptance Criteria",
            "Risks",
            "Test Plan",
            "Acceptance Mapping",
        ),
        next_decision="Approve launch readiness only after acceptance evidence is captured.",
    ),
}


def product_wizard_contracts() -> dict[str, Any]:
    return {
        "generation_mode": "local_fake_public_demo",
        "stages": [STAGE_CONTRACTS[stage].to_dict() for stage in WIZARD_STAGES],
        "artifact_metadata_contract": [
            "stage",
            "title",
            "owner_agent_id",
            "source_artifact_ids",
            "checks",
            "next_decision",
        ],
    }


def build_wizard_prompt_contract(
    stage: WizardStage | str,
    intake: ProductWizardIntake | Mapping[str, Any] | None = None,
    prior_artifacts: Iterable[
        ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any]
    ] = (),
) -> dict[str, Any]:
    wizard_stage = _validate_stage(stage)
    safe_intake = _coerce_intake(intake or {})
    contract = STAGE_CONTRACTS[wizard_stage]
    sources = _approved_sources_for_stage(contract, prior_artifacts)
    source_ids = tuple(source.id for source in sources)
    return {
        **contract.to_dict(),
        "source_artifact_ids": list(source_ids),
        "output_metadata": {
            "stage": wizard_stage,
            "title": contract.title,
            "owner_agent_id": contract.owner_agent_id,
            "source_artifact_ids": list(source_ids),
            "checks": [check_id for check_id, _ in COMMON_QUALITY_CHECKS],
            "next_decision": contract.next_decision,
        },
        "prompt": _safe_text(_prompt_for_contract(contract, safe_intake, sources)),
    }


def generate_wizard_artifact(
    stage: WizardStage | str,
    intake: ProductWizardIntake | Mapping[str, Any],
    prior_artifacts: Iterable[
        ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any]
    ] = (),
) -> ProductWizardArtifact:
    wizard_stage = _validate_stage(stage)
    safe_intake = _coerce_intake(intake)
    contract = STAGE_CONTRACTS[wizard_stage]
    sources = _approved_sources_for_stage(contract, prior_artifacts)
    artifact_id = f"product-wizard-{_slug(safe_intake.project_name)}-{wizard_stage}"
    title = f"{contract.title} for {safe_intake.project_name}"
    markdown = _safe_text(_render_artifact(contract, safe_intake, sources))
    return ProductWizardArtifact(
        id=artifact_id,
        stage=wizard_stage,
        title=title,
        owner_agent_id=contract.owner_agent_id,
        supporting_agent_ids=contract.supporting_agent_ids,
        markdown=markdown,
        source_artifact_ids=tuple(source.id for source in sources),
        checks=_quality_checks(contract, sources),
        next_decision=contract.next_decision,
    )


def generate_wizard_sequence(
    intake: ProductWizardIntake | Mapping[str, Any],
    *,
    stages: Iterable[WizardStage | str] = WIZARD_STAGES,
) -> list[ProductWizardArtifact]:
    safe_intake = _coerce_intake(intake)
    artifacts: list[ProductWizardArtifact] = []
    for stage in stages:
        artifacts.append(generate_wizard_artifact(stage, safe_intake, artifacts))
    return artifacts


def _render_artifact(
    contract: ProductWizardStageContract,
    intake: ProductWizardIntake,
    sources: tuple[ProductWizardSourceArtifact, ...],
) -> str:
    context = intake.to_context_dict()
    stage_lines = _stage_specific_lines(contract.stage, context)
    lines = [
        f"# {contract.title} for {context['project_name']}",
        "",
        f"- Stage: `{contract.stage}`",
        f"- Owner agent: `{contract.owner_agent_id}`",
    ]
    if contract.supporting_agent_ids:
        supporting_agents = ", ".join(f"`{agent}`" for agent in contract.supporting_agent_ids)
        lines.append(f"- Supporting agents: {supporting_agents}")
    lines.extend(
        [
            "- Generation mode: `local_fake_public_demo`",
            "",
            "## Approved Inputs Used",
            "",
            *_source_lines(sources),
            "",
            "## Target User",
            "",
            context["target_customer"],
            "",
            "## Problem",
            "",
            context["problem"],
            "",
            "## Scope",
            "",
            *stage_lines["scope"],
            "",
            "## Recommended Content",
            "",
            *stage_lines["content"],
            "",
            "## Risks",
            "",
            *stage_lines["risks"],
            "",
            "## Test Plan",
            "",
            *stage_lines["test_plan"],
            "",
            "## Acceptance Mapping",
            "",
            *stage_lines["acceptance"],
            "",
            "## Next Decision",
            "",
            contract.next_decision,
            "",
        ]
    )
    return "\n".join(lines)


def _stage_specific_lines(stage: WizardStage, context: Mapping[str, str]) -> dict[str, list[str]]:
    stage_renderers = {
        "research": _research_lines,
        "prd": _prd_lines,
        "architecture": _architecture_lines,
        "tasks": _task_lines,
        "code_plan": _code_plan_lines,
        "acceptance": _acceptance_lines,
    }
    return stage_renderers[stage](context)


def _research_lines(context: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "scope": [
            f"- Investigate the founder idea: {context['founder_idea']}",
            f"- Compare current alternatives: {context['current_alternatives']}",
            f"- Explain why now: {context['why_now']}",
        ],
        "content": [
            "- Form a falsifiable opportunity hypothesis for the target user.",
            "- Separate facts, assumptions, and founder intuition in the research notes.",
            "- Identify the smallest customer conversation that can disprove the idea.",
            f"- Track the first success metric candidate: {context['success_metric']}",
        ],
        "risks": [
            "- Evidence may be anecdotal until direct user interviews are captured.",
            "- The initial segment may be too broad for a useful first product.",
            "- Competitors or manual workflows may already satisfy the urgent use case.",
        ],
        "test_plan": [
            "- Run at least three target-user interviews or equivalent discovery reviews.",
            "- Validate that users can describe the problem without prompting.",
            "- Check whether the success metric can be measured in the first version.",
        ],
        "acceptance": [
            "- Research is accepted when target user, problem, alternatives, "
            "and risks are explicit.",
            "- Open questions must be carried into the PRD as assumptions or decisions.",
        ],
    }


def _prd_lines(context: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "scope": [
            "- Define the smallest useful workflow that proves the product direction.",
            f"- Desired outcome: {context['desired_outcome']}",
            "- Non-goal: avoid broad platform features until the workflow is proven.",
        ],
        "content": [
            "- User story: target user completes the core workflow with less manual effort.",
            "- Requirements: intake, primary action, review state, and completion state.",
            "- Founder approval is required before expanding beyond the first workflow.",
            f"- Go-to-market hunch to preserve: {context['go_to_market']}",
        ],
        "risks": [
            "- Requirements may grow beyond the first measurable proof point.",
            "- Missing constraints can cause architecture and task plans to overbuild.",
            "- Weak research evidence should be marked as an assumption.",
        ],
        "test_plan": [
            "- Review each requirement against the problem and target user.",
            "- Define happy-path, empty-state, and failure-state checks.",
            "- Confirm the success metric is visible from product behavior.",
        ],
        "acceptance": [
            "- PRD is accepted when each requirement maps to a user problem or explicit decision.",
            "- Scope is accepted when non-goals are strong enough to prevent overbuild.",
        ],
    }


def _architecture_lines(context: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "scope": [
            "- Use a modular local-first design that can later connect to live Hermes services.",
            f"- Technical preferences: {context['technical_preferences']}",
            f"- Constraints: {context['constraints']}",
        ],
        "content": [
            "- Define boundaries for UI, API, persistence, background work, and integrations.",
            "- Keep public-demo generation deterministic and independent from live credentials.",
            "- Capture observability points for user actions, failed jobs, "
            "and acceptance evidence.",
            "- Prefer simple data contracts before adding distributed workflow complexity.",
        ],
        "risks": [
            "- Live integration assumptions may leak into public-demo behavior.",
            "- Missing persistence contracts can make route wiring brittle.",
            "- Operational failures may be invisible without explicit evidence capture.",
        ],
        "test_plan": [
            "- Unit test pure contract generation and sanitization.",
            "- Add integration tests only when routes or repositories consume the contract.",
            "- Verify no generated artifact requires live credentials.",
        ],
        "acceptance": [
            "- Architecture is accepted when boundaries, data contracts, and risks are explicit.",
            "- Implementation may start only after owner agents and test evidence are mapped.",
        ],
    }


def _task_lines(context: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "scope": [
            "- Convert approved PRD and architecture into a small implementation backlog.",
            "- engineering-manager owns sequencing and dependency clarity.",
            "- chief-of-staff owns founder approval checkpoints and escalation wording.",
        ],
        "content": [
            "- Task 1: confirm contract shape and acceptance criteria before route wiring.",
            "- Task 2: implement backend data flow only after the contract is stable.",
            "- Task 3: implement UI review states with clear approve/revise decisions.",
            "- Task 4: capture QA evidence before a founder-facing launch decision.",
        ],
        "risks": [
            "- Parallel workers may edit adjacent files; keep task ownership explicit.",
            "- Backlog items can hide founder decisions unless approval gates are named.",
            "- Test work can lag implementation unless assigned in the first slice.",
        ],
        "test_plan": [
            "- Require focused tests for each new module and route contract.",
            "- Add regression tests for stage ordering and source artifact handling.",
            "- Track acceptance evidence as part of task completion, not after the fact.",
        ],
        "acceptance": [
            "- Tasks are accepted when each item has owner, dependency, and test evidence.",
            "- Founder approval gates are accepted when chief-of-staff handoff text is explicit.",
        ],
    }


def _code_plan_lines(context: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "scope": [
            "- backend-engineer owns API and persistence integration points.",
            "- frontend-engineer owns wizard review, approval, and revision states.",
            "- cloud-infra-agent owns deployment and runtime configuration boundaries.",
        ],
        "content": [
            "- Backend: expose deterministic artifact generation through a route-friendly service.",
            "- Frontend: render markdown and metadata without assuming live Hermes execution.",
            "- Cloud: keep public-demo mode free of external credential requirements.",
            "- Shared: preserve stage order, source artifact IDs, and quality checks in JSON.",
        ],
        "risks": [
            "- Code may couple route behavior to local fake generation too tightly.",
            "- UI may drop metadata needed for downstream acceptance and task creation.",
            "- Deployment config may accidentally imply live provider credentials are required.",
        ],
        "test_plan": [
            "- Unit test generator contracts, deterministic rendering, and sanitization.",
            "- Add route tests when parent integration wires the module.",
            "- Add browser or UI tests after the wizard flow is visible.",
        ],
        "acceptance": [
            "- Code plan is accepted when backend, frontend, and cloud responsibilities are named.",
            "- Implementation is accepted only when metadata survives the full route/UI path.",
        ],
    }


def _acceptance_lines(context: Mapping[str, str]) -> dict[str, list[str]]:
    return {
        "scope": [
            "- qa-critic owns launch-readiness critique and contradiction hunting.",
            "- test-automation-agent owns repeatable test coverage and regression evidence.",
            "- Founder approval depends on visible acceptance evidence, not generated prose alone.",
        ],
        "content": [
            "- Acceptance criterion 1: target user and problem remain visible in every artifact.",
            "- Acceptance criterion 2: scope, risks, and non-goals are explicit before build.",
            "- Acceptance criterion 3: implementation tasks map to tests and owner agents.",
            "- Acceptance criterion 4: launch recommendation includes blockers and next decision.",
        ],
        "risks": [
            "- Acceptance can become subjective if checks lack observable evidence.",
            "- Test coverage may miss workflow-level regressions across stage transitions.",
            "- Founder decisions may be hidden if critique is not separated from status.",
        ],
        "test_plan": [
            "- Run unit tests for contract generation and no-secret guarantees.",
            "- Run route and UI tests after parent integration wires this module.",
            "- Capture manual review notes for assumptions that automation cannot verify.",
        ],
        "acceptance": [
            "- Wizard output is accepted when all required checks are included and evidence-ready.",
            "- Public-demo mode is accepted when no output depends on live Hermes credentials.",
        ],
    }


def _source_lines(sources: tuple[ProductWizardSourceArtifact, ...]) -> list[str]:
    if not sources:
        return ["- No approved prior artifact supplied; this stage uses safe intake context only."]
    return [
        f"- `{source.id}` ({source.stage}): {source.title} - {_summary(source.content)}"
        for source in sources
    ]


def _quality_checks(
    contract: ProductWizardStageContract,
    sources: tuple[ProductWizardSourceArtifact, ...],
) -> tuple[dict[str, str], ...]:
    checks = []
    source_status = "included"
    source_evidence = "No prior artifact required for this stage."
    if contract.required_prior_stages:
        source_status = "included" if sources else "needs_review"
        source_evidence = (
            "Approved source artifacts are referenced."
            if sources
            else "Required prior artifacts were not supplied."
        )
    evidence_by_id = {
        "target_user": "Target User section is rendered from sanitized intake.",
        "problem": "Problem section is rendered from sanitized intake.",
        "scope": "Scope section names the current stage boundary.",
        "risks": "Risks section is present in markdown.",
        "test_plan": "Test Plan section is present in markdown.",
        "acceptance_mapping": "Acceptance Mapping section is present in markdown.",
        "prior_artifacts": source_evidence,
        "secret_safety": "Output is sanitized before the artifact is returned.",
    }
    for check_id, label in COMMON_QUALITY_CHECKS:
        checks.append(
            {
                "id": check_id,
                "label": label,
                "status": source_status if check_id == "prior_artifacts" else "included",
                "evidence": evidence_by_id[check_id],
            }
        )
    return tuple(checks)


def _prompt_for_contract(
    contract: ProductWizardStageContract,
    intake: ProductWizardIntake,
    sources: tuple[ProductWizardSourceArtifact, ...],
) -> str:
    context = intake.to_context_dict()
    return "\n".join(
        [
            f"You are `{contract.owner_agent_id}` generating the `{contract.stage}` artifact.",
            "Use local deterministic public-demo mode. Do not call live Hermes services.",
            f"Project: {context['project_name']}",
            f"Founder idea: {context['founder_idea']}",
            f"Target user: {context['target_customer']}",
            f"Problem: {context['problem']}",
            f"Approved source artifact IDs: {', '.join(source.id for source in sources) or 'none'}",
            f"Required output sections: {', '.join(contract.output_sections)}",
            "Required metadata fields: "
            f"{', '.join(product_wizard_contracts()['artifact_metadata_contract'])}",
            "Quality checks: target user, problem, scope, risks, test plan, acceptance mapping.",
            f"Next decision: {contract.next_decision}",
        ]
    )


def _approved_sources_for_stage(
    contract: ProductWizardStageContract,
    prior_artifacts: Iterable[
        ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any]
    ],
) -> tuple[ProductWizardSourceArtifact, ...]:
    if not contract.required_prior_stages:
        return ()
    required = set(contract.required_prior_stages)
    sources = []
    for item in prior_artifacts:
        source = _coerce_source_artifact(item)
        if source.approved and source.stage in required:
            sources.append(source)
    return tuple(sources)


def _coerce_source_artifact(
    item: ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any],
) -> ProductWizardSourceArtifact:
    if isinstance(item, ProductWizardSourceArtifact):
        return item
    if isinstance(item, ProductWizardArtifact):
        return ProductWizardSourceArtifact(
            id=item.id,
            stage=item.stage,
            title=item.title,
            content=item.markdown,
            approved=True,
        )

    metadata = item.get("metadata", {})
    status = str(item.get("status", metadata.get("status", ""))).lower()
    approved = bool(item.get("approved", True)) and (
        not status or status in APPROVED_SOURCE_STATUSES
    )
    artifact_id = _safe_text(item.get("id", metadata.get("id", ""))) or "source-artifact"
    return ProductWizardSourceArtifact(
        id=artifact_id,
        stage=_safe_text(item.get("stage", metadata.get("stage", ""))),
        title=_safe_text(item.get("title", metadata.get("title", artifact_id))),
        content=_safe_text(item.get("markdown", item.get("content", item.get("body", "")))),
        approved=approved,
    )


def _coerce_intake(intake: ProductWizardIntake | Mapping[str, Any]) -> ProductWizardIntake:
    if isinstance(intake, ProductWizardIntake):
        return ProductWizardIntake.from_mapping(intake.to_context_dict())
    return ProductWizardIntake.from_mapping(intake)


def _validate_stage(stage: WizardStage | str) -> WizardStage:
    if stage not in WIZARD_STAGES:
        raise ValueError(f"Unknown product wizard stage: {stage}")
    return stage  # type: ignore[return-value]


def _safe_text(value: Any) -> str:
    cleaned = str(value or "")
    for _, pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("REDACTED_SECRET", cleaned)
    return cleaned.strip()


def _summary(value: str, *, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", _safe_text(value)).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _safe_text(value).lower()).strip("-")
    return slug or "untitled-product"
