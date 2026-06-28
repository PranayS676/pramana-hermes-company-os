import json
from collections.abc import Mapping
from typing import Any

from hermes_company_os.product_wizard import STAGE_CONTRACTS
from hermes_company_os.secret_guard import assert_no_secret_values

HANDOFF_SCHEMA = "profile_handoff_contract_v1"


def profile_handoff_contract(repository, work_item: Mapping[str, Any]) -> dict[str, Any]:
    owner_agent_id = str(work_item["owner_agent_id"])
    work_item_id = str(work_item["id"])
    contract_id = f"profile-handoff:{work_item_id}"
    stage_id = str(work_item.get("stage_id") or "")
    stage_contract = STAGE_CONTRACTS.get(stage_id)
    supporting_agent_ids = (
        list(stage_contract.supporting_agent_ids) if stage_contract else []
    )
    artifact = _linked_artifact(repository, work_item)
    payload = {
        "schema": HANDOFF_SCHEMA,
        "contract_id": contract_id,
        "work_item": {
            "id": work_item_id,
            "title": str(work_item["title"]),
            "status": str(work_item["status"]),
            "priority": str(work_item["priority"]),
            "summary": str(work_item["summary"]),
            "source": str(work_item["source"]),
        },
        "delegation": {
            "from_agent_id": str(work_item.get("created_by_agent_id") or "chief-of-staff"),
            "from_agent_name": str(work_item.get("creator_name") or "Chief of Staff"),
            "to_agent_id": owner_agent_id,
            "to_agent_name": str(work_item.get("owner_name") or owner_agent_id),
            "supporting_agent_ids": supporting_agent_ids,
        },
        "inputs": {
            "project_id": str(work_item.get("project_id") or ""),
            "project_name": str(work_item.get("project_name") or ""),
            "stage_id": stage_id,
            "stage_name": str(work_item.get("stage_name") or stage_id),
            "artifact": artifact,
            "decision_id": str(work_item.get("decision_id") or ""),
            "decision_status": str(work_item.get("decision_status") or ""),
        },
        "execution": {
            "mode": "manual_profile_handoff",
            "external_execution_enabled": False,
            "source_of_truth": "dashboard",
            "command_preview": [
                "hermes",
                "profiles",
                "run",
                owner_agent_id,
                "--handoff-contract",
                contract_id,
                "--output",
                "agent-handoff-result-json",
            ],
        },
        "acceptance": _acceptance_contract(stage_contract, artifact),
        "review_gates": {
            "founder_action_required": bool(work_item.get("founder_action_required")),
            "decision_id": str(work_item.get("decision_id") or ""),
            "decision_status": str(work_item.get("decision_status") or ""),
            "status_policy": (
                "Queue approval, rejection, launch, external execution, and accepted "
                "risk remain founder-gated."
            ),
        },
    }
    payload["prompt"] = _handoff_prompt(payload)
    assert_no_secret_values({"profile_handoff_contract": json.dumps(payload, sort_keys=True)})
    return payload


def profile_handoff_contract_markdown(contract: Mapping[str, Any]) -> str:
    command = " ".join(str(part) for part in contract["execution"]["command_preview"])
    acceptance_checks = "\n".join(
        f"- `{check['id']}`: {check['label']}"
        for check in contract["acceptance"]["checks"]
    )
    supporting_agents = ", ".join(contract["delegation"]["supporting_agent_ids"]) or "none"
    return "\n".join(
        [
            f"# Profile Handoff Contract: {contract['work_item']['title']}",
            "",
            f"- Schema: `{contract['schema']}`",
            f"- Contract ID: `{contract['contract_id']}`",
            f"- From: `{contract['delegation']['from_agent_id']}`",
            f"- To: `{contract['delegation']['to_agent_id']}`",
            f"- Supporting agents: `{supporting_agents}`",
            f"- Work item: `{contract['work_item']['id']}`",
            f"- Project: `{contract['inputs']['project_id']}`",
            f"- Stage: `{contract['inputs']['stage_id']}`",
            "",
            "## Runnable Command Preview",
            "",
            f"`{command}`",
            "",
            "No external execution is started by this contract.",
            "",
            "## Acceptance Checks",
            "",
            acceptance_checks or "- No stage-specific checks are available.",
            "",
            "## Review Gates",
            "",
            (
                "- Founder action required: "
                f"`{str(contract['review_gates']['founder_action_required']).lower()}`"
            ),
            f"- Decision: `{contract['review_gates']['decision_id'] or 'not linked'}`",
            f"- Policy: {contract['review_gates']['status_policy']}",
            "",
            "## Prompt",
            "",
            contract["prompt"],
            "",
        ]
    )


def _linked_artifact(repository, work_item: Mapping[str, Any]) -> dict[str, Any]:
    project_id = str(work_item.get("project_id") or "")
    artifact_id = str(work_item.get("artifact_id") or "")
    if not project_id or not artifact_id:
        return {}
    artifact = repository.get_project_wizard_artifact(project_id, artifact_id)
    if artifact is None:
        return {}
    return {
        "id": artifact["id"],
        "stage_id": artifact["stage_id"],
        "status": artifact["status"],
        "version": artifact["version"],
        "title": artifact.get("json", {}).get("title", artifact["stage_id"]),
    }


def _acceptance_contract(stage_contract, artifact: Mapping[str, Any]) -> dict[str, Any]:
    if artifact:
        checks = artifact.get("json", {}).get("checks", [])
        if isinstance(checks, list):
            return {
                "source": "linked_artifact",
                "checks": [
                    {
                        "id": str(check.get("id", "check")),
                        "label": str(check.get("label", check.get("description", "Check"))),
                    }
                    for check in checks
                    if isinstance(check, dict)
                ],
            }
    if stage_contract:
        return {
            "source": "stage_contract",
            "output_sections": list(stage_contract.output_sections),
            "checks": [
                {"id": check_id, "label": check_id.replace("_", " ").title()}
                for check_id in stage_contract.quality_check_ids
            ],
        }
    return {
        "source": "queue_item",
        "output_sections": [],
        "checks": [{"id": "expected_output", "label": "Produce the expected output."}],
    }


def _handoff_prompt(contract: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            (
                f"You are `{contract['delegation']['to_agent_id']}` receiving a "
                f"profile-to-profile handoff from `{contract['delegation']['from_agent_id']}`."
            ),
            f"Work item: {contract['work_item']['title']}.",
            f"Summary: {contract['work_item']['summary']}",
            f"Project: {contract['inputs']['project_name'] or contract['inputs']['project_id']}.",
            f"Stage: {contract['inputs']['stage_name'] or contract['inputs']['stage_id']}.",
            "Use the linked artifact and acceptance checks as the source of truth.",
            "Return an agent-handoff-result-json payload with status, evidence, "
            "risks, and next action.",
            "No external execution is started by this contract.",
        ]
    )
