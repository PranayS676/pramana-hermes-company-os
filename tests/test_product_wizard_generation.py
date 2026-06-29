import json

import pytest

from hermes_company_os.product_wizard import (
    WIZARD_STAGES,
    ProductWizardIntake,
    ProductWizardMemoryPolicy,
    build_wizard_prompt_contract,
    generate_wizard_artifact,
    generate_wizard_sequence,
    product_wizard_contracts,
)
from hermes_company_os.secret_guard import secret_violations

FAKE_OPENAI_SECRET = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
FAKE_SLACK_SECRET = "xoxb-" + "123456789012-abcdefABCDEF"
FAKE_AWS_SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"


def _intake() -> ProductWizardIntake:
    return ProductWizardIntake(
        project_name="Ops Copilot",
        founder_idea="A dashboard that turns messy operations requests into approved tasks.",
        target_customer="Seed-stage founders with a small AI operations team.",
        problem="Founders lose implementation clarity between research, planning, and build.",
        current_alternatives="Docs, spreadsheets, and ad hoc chat threads.",
        why_now="Small teams can now coordinate specialized AI workers cheaply.",
        desired_outcome="A reviewed implementation plan with visible acceptance evidence.",
        constraints="Public-demo mode must not require live Hermes services.",
        technical_preferences="FastAPI, SQLite, deterministic local generation, and route tests.",
        go_to_market="Start with founder operators who already coordinate work in Slack.",
        success_metric="First useful project reaches accepted code plan in one sitting.",
        open_questions="Which artifact should gate build approval?",
    )


def _memory_context() -> list[dict[str, object]]:
    return [
        {
            "id": "memory-founder-demo-standard",
            "category": "founder_preference",
            "title": "Keep public demo data synthetic",
            "summary": "Founder prefers generated examples over customer files.",
            "body": "Use synthetic companies, fixture risks, and demo-safe evidence.",
            "status": "active",
            "reusable": True,
            "owner_agent_id": "chief-of-staff",
            "source": "founder-memory-form",
            "scope_label": "project",
            "confidence": "high",
        },
        {
            "id": "memory-customer-evidence",
            "category": "customer_evidence",
            "title": "Customer interview detail",
            "summary": "This category requires explicit artifact approval.",
            "body": "Do not auto-inject customer evidence through project memory.",
            "status": "active",
            "reusable": True,
            "owner_agent_id": "research-agent",
            "source": "research-notes",
            "scope_label": "project",
            "confidence": "medium",
        },
        {
            "id": "memory-retired-standard",
            "category": "technical_standard",
            "title": "Retired stack choice",
            "summary": "This retired memory must not be reused.",
            "body": "Use the retired stack.",
            "status": "retired",
            "reusable": False,
            "owner_agent_id": "engineering-manager",
            "source": "old-decision",
            "scope_label": "company-wide",
            "confidence": "low",
        },
    ]


def test_product_wizard_sequence_exports_canonical_contract_and_metadata():
    artifacts = generate_wizard_sequence(_intake())

    assert [artifact.stage for artifact in artifacts] == list(WIZARD_STAGES)

    by_stage = {artifact.stage: artifact for artifact in artifacts}
    assert by_stage["research"].owner_agent_id == "research-agent"
    assert by_stage["prd"].owner_agent_id == "product-manager"
    assert by_stage["architecture"].owner_agent_id == "engineering-manager"
    assert by_stage["tasks"].owner_agent_id == "engineering-manager"
    assert by_stage["code_plan"].owner_agent_id == "backend-engineer"
    assert by_stage["code_plan"].supporting_agent_ids == (
        "frontend-engineer",
        "cloud-infra-agent",
    )
    assert by_stage["acceptance"].owner_agent_id == "qa-critic"
    assert by_stage["acceptance"].supporting_agent_ids == ("test-automation-agent",)

    assert by_stage["prd"].source_artifact_ids == (by_stage["research"].id,)
    assert by_stage["architecture"].source_artifact_ids == (
        by_stage["research"].id,
        by_stage["prd"].id,
    )
    assert by_stage["tasks"].source_artifact_ids == (
        by_stage["prd"].id,
        by_stage["architecture"].id,
    )
    assert by_stage["code_plan"].source_artifact_ids == (
        by_stage["architecture"].id,
        by_stage["tasks"].id,
    )
    assert by_stage["acceptance"].source_artifact_ids == (
        by_stage["prd"].id,
        by_stage["tasks"].id,
        by_stage["code_plan"].id,
    )

    for artifact in artifacts:
        payload = artifact.to_dict()
        metadata = payload["metadata"]
        assert payload["markdown"].startswith("# ")
        assert metadata["stage"] == artifact.stage
        assert metadata["title"] == artifact.title
        assert metadata["owner_agent_id"] == artifact.owner_agent_id
        assert metadata["next_decision"]
        assert metadata["generation_mode"] == "local_fake_public_demo"
        assert {"target_user", "problem", "scope", "risks", "test_plan"} <= {
            check["id"] for check in metadata["checks"]
        }
        assert "## Target User" in artifact.markdown
        assert "## Problem" in artifact.markdown
        assert "## Risks" in artifact.markdown
        assert "## Test Plan" in artifact.markdown
        assert "## Acceptance Mapping" in artifact.markdown


def test_product_wizard_artifacts_are_deterministic_and_use_only_approved_sources():
    intake = _intake()
    prior_artifacts = [
        {
            "id": "research-approved",
            "stage": "research",
            "title": "Approved research",
            "content": "Target user evidence includes " + FAKE_SLACK_SECRET,
            "status": "approved",
        },
        {
            "id": "research-draft",
            "stage": "research",
            "title": "Draft research",
            "content": "This draft should not be referenced.",
            "status": "draft",
        },
    ]

    first = generate_wizard_artifact("prd", intake, prior_artifacts)
    second = generate_wizard_artifact("prd", intake, prior_artifacts)

    assert first.to_dict() == second.to_dict()
    assert first.source_artifact_ids == ("research-approved",)
    assert "research-approved" in first.markdown
    assert "research-draft" not in first.markdown
    assert FAKE_SLACK_SECRET not in json.dumps(first.to_dict())
    assert secret_violations({"artifact": json.dumps(first.to_dict())}) == []


def test_product_wizard_sanitizes_intake_and_generated_sequence():
    intake = {
        "project_name": "Credential Demo",
        "founder_idea": "Use pasted provider value " + FAKE_OPENAI_SECRET,
        "target_customer": "Ops team with leaked Slack value " + FAKE_SLACK_SECRET,
        "problem": "Someone pasted cloud access value " + FAKE_AWS_SECRET,
        "technical_preferences": "Keep public-demo mode local.",
    }

    artifacts = generate_wizard_sequence(intake)
    raw = json.dumps([artifact.to_dict() for artifact in artifacts])

    assert FAKE_OPENAI_SECRET not in raw
    assert FAKE_SLACK_SECRET not in raw
    assert FAKE_AWS_SECRET not in raw
    assert "REDACTED_SECRET" in raw
    assert secret_violations({"wizard": raw}) == []


def test_product_wizard_prompt_contract_is_json_ready_and_route_friendly():
    research = generate_wizard_artifact("research", _intake())
    contract = build_wizard_prompt_contract("code_plan", _intake(), [research])
    full_contract = product_wizard_contracts()

    assert full_contract["artifact_metadata_contract"] == [
        "stage",
        "title",
        "owner_agent_id",
        "source_artifact_ids",
        "memory_ids",
        "checks",
        "next_decision",
    ]
    assert contract["stage"] == "code_plan"
    assert contract["owner_agent_id"] == "backend-engineer"
    assert contract["supporting_agent_ids"] == ["frontend-engineer", "cloud-infra-agent"]
    assert "Do not call live Hermes services" in contract["prompt"]
    assert "Required metadata fields" in contract["prompt"]
    assert json.loads(json.dumps(contract)) == contract


def test_product_wizard_uses_only_policy_approved_memory_context():
    policy = ProductWizardMemoryPolicy(
        enabled=True,
        allowed_categories=("founder_preference", "technical_standard"),
        source="test-founder-approved-policy",
    )

    contract = build_wizard_prompt_contract(
        "research",
        _intake(),
        memory_context=_memory_context(),
        memory_policy=policy,
    )
    artifact = generate_wizard_artifact(
        "research",
        _intake(),
        memory_context=_memory_context(),
        memory_policy=policy,
    )
    raw = json.dumps({"contract": contract, "artifact": artifact.to_dict()})

    assert contract["memory_ids"] == ["memory-founder-demo-standard"]
    assert contract["output_metadata"]["memory_ids"] == [
        "memory-founder-demo-standard"
    ]
    assert contract["memory_policy"]["enabled"] is True
    assert "Approved memory IDs: memory-founder-demo-standard" in contract["prompt"]
    assert "Keep public demo data synthetic" in contract["prompt"]
    assert "memory-customer-evidence" not in raw
    assert "memory-retired-standard" not in raw
    assert "## Approved Memory Used" in artifact.markdown
    assert artifact.memory_ids == ("memory-founder-demo-standard",)
    assert artifact.metadata["memory_ids"] == ["memory-founder-demo-standard"]
    assert secret_violations({"memory_artifact": raw}) == []


def test_product_wizard_rejects_unknown_stage():
    with pytest.raises(ValueError, match="Unknown product wizard stage"):
        generate_wizard_artifact("fundraising", _intake())
