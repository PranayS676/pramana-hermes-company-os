from __future__ import annotations

from dataclasses import dataclass

from hermes_company_os.founder_decisions import RESOLVED_DECISION_STATUSES
from hermes_company_os.generation_service import LiveHermesGenerationGate
from hermes_company_os.product_wizard import STAGE_CONTRACTS

LIVE_HERMES_DECISION_SOURCE = "live_hermes_generation"
LIVE_HERMES_DECISION_TYPE = "external_action_approval"


@dataclass(frozen=True)
class LiveHermesReadiness:
    project_id: str
    stage_id: str
    owner_agent_ids: tuple[str, ...]
    checks: tuple[dict[str, str], ...]
    founder_approval_decision_id: str = ""
    founder_approval_status: str = ""

    @property
    def founder_approved(self) -> bool:
        return self.founder_approval_status == "approved"

    @property
    def runtime_ready(self) -> bool:
        return all(
            check["status"] == "ready"
            for check in self.checks
            if check["id"] != "founder_approval"
        )

    @property
    def ready(self) -> bool:
        return self.runtime_ready and self.founder_approved

    @property
    def approval_request_open(self) -> bool:
        return bool(
            self.founder_approval_decision_id
            and self.founder_approval_status not in RESOLVED_DECISION_STATUSES
        )

    @property
    def approval_request_allowed(self) -> bool:
        return not self.founder_approved and not self.approval_request_open

    @property
    def blocker(self) -> str:
        for check in self.checks:
            if check["status"] != "ready":
                return f"Live Hermes readiness blocked: {check['label']}. {check['detail']}"
        return ""

    @property
    def gate(self) -> LiveHermesGenerationGate:
        return LiveHermesGenerationGate(
            enabled=True,
            founder_approved=self.founder_approved,
            runtime_ready=self.runtime_ready,
        )

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "stage_id": self.stage_id,
            "owner_agent_ids": list(self.owner_agent_ids),
            "checks": [dict(check) for check in self.checks],
            "ready": self.ready,
            "runtime_ready": self.runtime_ready,
            "founder_approved": self.founder_approved,
            "founder_approval_decision_id": self.founder_approval_decision_id,
            "founder_approval_status": self.founder_approval_status,
            "approval_request_open": self.approval_request_open,
            "approval_request_allowed": self.approval_request_allowed,
            "blocker": self.blocker,
        }


def evaluate_live_hermes_readiness(repository, project_id: str, stage_id: str):
    stage = repository.get_project_wizard_stage(project_id, stage_id)
    if stage is None:
        raise ValueError(f"Unknown product wizard stage: {project_id}/{stage_id}")
    contract = STAGE_CONTRACTS.get(stage_id)
    supporting_agent_ids = contract.supporting_agent_ids if contract else ()
    owner_agent_ids = tuple(
        dict.fromkeys([stage["owner_agent_id"], *supporting_agent_ids])
    )
    checks = (
        _profile_installation_check(repository, owner_agent_ids),
        _llm_verification_check(repository, owner_agent_ids),
        _profile_acceptance_check(repository, owner_agent_ids),
        _prior_artifacts_check(repository, project_id, stage_id),
        _founder_approval_check(repository, project_id, stage_id),
    )
    approval = _live_hermes_approval(repository, project_id, stage_id)
    return LiveHermesReadiness(
        project_id=project_id,
        stage_id=stage_id,
        owner_agent_ids=owner_agent_ids,
        checks=checks,
        founder_approval_decision_id=approval["id"],
        founder_approval_status=approval["status"],
    )


def _profile_installation_check(repository, agent_ids: tuple[str, ...]) -> dict[str, str]:
    missing = [
        agent_id
        for agent_id in agent_ids
        if not repository.agent_profile_installation_verified(agent_id)
    ]
    if not missing:
        return _check(
            "profile_installation",
            "Profile installation",
            "ready",
            "All stage owner profiles are marked installed.",
        )
    return _check(
        "profile_installation",
        "Profile installation",
        "blocked",
        "Verify profile installation for: " + ", ".join(missing) + ".",
    )


def _llm_verification_check(repository, agent_ids: tuple[str, ...]) -> dict[str, str]:
    missing = []
    for agent_id in agent_ids:
        preference = repository.get_model_preference(agent_id)
        if preference is None or preference["status"] != "verified":
            missing.append(agent_id)
    if not missing:
        return _check(
            "llm_verification",
            "LLM smoke verification",
            "ready",
            "All stage owner profiles have verified model smoke checks.",
        )
    return _check(
        "llm_verification",
        "LLM smoke verification",
        "blocked",
        "Run successful profile smoke checks for: " + ", ".join(missing) + ".",
    )


def _profile_acceptance_check(repository, agent_ids: tuple[str, ...]) -> dict[str, str]:
    checks = repository.list_profile_acceptance_checks()
    missing = []
    for agent_id in agent_ids:
        agent_checks = [item for item in checks if item["agent_id"] == agent_id]
        if not agent_checks or any(item["status"] != "verified" for item in agent_checks):
            missing.append(agent_id)
    if not missing:
        return _check(
            "profile_acceptance",
            "Profile acceptance",
            "ready",
            "All stage owner profile acceptance checks are verified.",
        )
    return _check(
        "profile_acceptance",
        "Profile acceptance",
        "blocked",
        "Verify profile acceptance checks for: " + ", ".join(missing) + ".",
    )


def _prior_artifacts_check(repository, project_id: str, stage_id: str) -> dict[str, str]:
    contract = STAGE_CONTRACTS.get(stage_id)
    required_prior_stages = contract.required_prior_stages if contract else ()
    if not required_prior_stages:
        return _check(
            "required_prior_artifacts",
            "Required prior artifacts",
            "ready",
            "No prior artifact is required for this stage.",
        )
    missing = []
    for prior_stage in required_prior_stages:
        artifact = repository.latest_project_stage_artifact(project_id, prior_stage)
        if artifact is None or artifact["status"] != "approved":
            missing.append(prior_stage)
    if not missing:
        return _check(
            "required_prior_artifacts",
            "Required prior artifacts",
            "ready",
            "Required prior stages are approved: "
            + ", ".join(required_prior_stages)
            + ".",
        )
    return _check(
        "required_prior_artifacts",
        "Required prior artifacts",
        "blocked",
        "Approve prior stages first: " + ", ".join(missing) + ".",
    )


def _founder_approval_check(repository, project_id: str, stage_id: str) -> dict[str, str]:
    approval = _live_hermes_approval(repository, project_id, stage_id)
    if approval["status"] == "approved":
        return _check(
            "founder_approval",
            "Founder live-mode approval",
            "ready",
            f"Founder approved live Hermes generation in {approval['id']}.",
        )
    if approval["id"]:
        return _check(
            "founder_approval",
            "Founder live-mode approval",
            "needed",
            f"Founder approval is pending in {approval['id']}.",
        )
    return _check(
        "founder_approval",
        "Founder live-mode approval",
        "needed",
        "Request founder approval before live Hermes generation.",
    )


def _live_hermes_approval(repository, project_id: str, stage_id: str) -> dict[str, str]:
    decisions = [
        decision
        for decision in repository.list_founder_decisions(
            project_id=project_id,
            stage_id=stage_id,
            decision_type=LIVE_HERMES_DECISION_TYPE,
        )
        if decision["source"] == LIVE_HERMES_DECISION_SOURCE
    ]
    approved = next(
        (decision for decision in decisions if decision["status"] == "approved"),
        None,
    )
    if approved:
        return {"id": approved["id"], "status": approved["status"]}
    open_decision = next(
        (
            decision
            for decision in decisions
            if decision["status"] not in RESOLVED_DECISION_STATUSES
        ),
        None,
    )
    if open_decision:
        return {"id": open_decision["id"], "status": open_decision["status"]}
    return {"id": "", "status": ""}


def _check(check_id: str, label: str, status: str, detail: str) -> dict[str, str]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "detail": detail,
    }
