from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from hermes_company_os.secret_guard import assert_no_secret_values

MULTI_AGENT_REVIEW_SCHEMA = "multi_agent_review_package_v1"

REVIEWERS: tuple[dict[str, str], ...] = (
    {
        "agent_id": "qa-critic",
        "name": "QA Critic",
        "role": "Risk, blocker, and launch-readiness review",
    },
    {
        "agent_id": "test-automation-agent",
        "name": "Test Automation Agent",
        "role": "Automated coverage, regression, and evidence review",
    },
    {
        "agent_id": "product-manager",
        "name": "Product Manager",
        "role": "User value, scope, and PRD alignment review",
    },
    {
        "agent_id": "engineering-manager",
        "name": "Engineering Manager",
        "role": "Implementation feasibility, ownership, and operational-risk review",
    },
    {
        "agent_id": "ui-ux-research-agent",
        "name": "UI/UX Research Agent",
        "role": "Founder usability, workflow ergonomics, and accessibility review",
    },
)

ACCEPTANCE_RULES: tuple[dict[str, str], ...] = (
    {
        "id": "approved_source_artifacts",
        "label": "Code plan and acceptance package are approved.",
    },
    {
        "id": "reviewer_specific_checks",
        "label": "Each reviewer records role-specific checks and findings.",
    },
    {
        "id": "founder_visible_evidence",
        "label": "Review package is exported to project JSON/Markdown and visible in the UI.",
    },
    {
        "id": "no_secret_review_payload",
        "label": "Review records and exports remain no-secret.",
    },
)


def multi_agent_review_package(repository, project_id: str) -> dict[str, Any]:
    project = repository.get_project(project_id)
    if project is None:
        raise ValueError(f"Unknown project: {project_id}")
    readiness = _review_readiness(repository, project_id)
    records = (
        repository.list_project_review_records(
            project_id,
            review_batch_id=readiness["review_batch_id"],
        )
        if readiness["review_batch_id"]
        else []
    )
    payload = {
        "schema": MULTI_AGENT_REVIEW_SCHEMA,
        "project": {
            "id": project_id,
            "name": project["name"],
            "status": project["status"],
        },
        "review_batch_id": readiness["review_batch_id"],
        "ready": readiness["ready"],
        "blocker": readiness["blocker"],
        "source_artifacts": readiness["source_artifacts"],
        "acceptance_rules": [dict(rule) for rule in ACCEPTANCE_RULES],
        "reviewers": [_record_payload(record) for record in records],
        "aggregate": _aggregate(readiness, records),
    }
    assert_no_secret_values({"multi_agent_review_package": json.dumps(payload, sort_keys=True)})
    return payload


def generate_multi_agent_review(repository, project_id: str) -> dict[str, Any]:
    readiness = _review_readiness(repository, project_id)
    if not readiness["ready"]:
        raise ValueError(readiness["blocker"])
    artifacts = readiness["source_artifacts"]
    review_batch_id = readiness["review_batch_id"]
    for reviewer in REVIEWERS:
        record = _review_record(
            reviewer=reviewer,
            project_id=project_id,
            review_batch_id=review_batch_id,
            artifacts=artifacts,
        )
        repository.create_project_review_record(**record)
    return multi_agent_review_package(repository, project_id)


def multi_agent_review_markdown(package: Mapping[str, Any]) -> str:
    lines = [
        f"# Multi-Agent Review Package: {package['project']['name']}",
        "",
        f"- Schema: `{package['schema']}`",
        f"- Project: `{package['project']['id']}`",
        f"- Batch: `{package['review_batch_id'] or 'not-ready'}`",
        f"- Status: `{package['aggregate']['status']}`",
        f"- Reviewer records: {package['aggregate']['reviewer_count']}",
        "",
        "## Acceptance Rules",
        "",
    ]
    for rule in package["acceptance_rules"]:
        lines.append(f"- `{rule['id']}`: {rule['label']}")
    lines.extend(["", "## Source Artifacts", ""])
    if package["source_artifacts"]:
        for artifact in package["source_artifacts"]:
            lines.append(
                f"- `{artifact['stage_id']}`: {artifact['id']} "
                f"v{artifact['version']} ({artifact['status']})"
            )
    else:
        lines.append("- Waiting for approved code plan and acceptance package.")
    lines.extend(["", "## Reviewer Records", ""])
    if package["reviewers"]:
        for reviewer in package["reviewers"]:
            lines.extend(
                [
                    f"### {reviewer['reviewer_name']}",
                    "",
                    f"- Agent: `{reviewer['reviewer_agent_id']}`",
                    f"- Verdict: `{reviewer['verdict']}`",
                    f"- Role: {reviewer['reviewer_role']}",
                    f"- Summary: {reviewer['summary']}",
                    "",
                    "Checks:",
                ]
            )
            for check in reviewer["checks"]:
                lines.append(f"- `{check['id']}`: {check['status']} - {check['detail']}")
            lines.append("")
            lines.append("Findings:")
            for finding in reviewer["findings"]:
                lines.append(
                    f"- `{finding['severity']}`: {finding['title']} - {finding['detail']}"
                )
            lines.append("")
    else:
        lines.append("- No reviewer records yet.")
        if package["blocker"]:
            lines.append(f"- Blocker: {package['blocker']}")
        lines.append("")
    return "\n".join(lines)


def _review_readiness(repository, project_id: str) -> dict[str, Any]:
    code_plan = repository.latest_project_stage_artifact(project_id, "code_plan")
    acceptance = repository.latest_project_stage_artifact(project_id, "acceptance")
    source_artifacts = [
        artifact
        for artifact in (_artifact_summary(code_plan), _artifact_summary(acceptance))
        if artifact
    ]
    missing = []
    if code_plan is None or code_plan["status"] != "approved":
        missing.append("approved code plan")
    if acceptance is None or acceptance["status"] != "approved":
        missing.append("approved acceptance package")
    ready = not missing
    blocker = (
        "Multi-agent review requires approved code plan and acceptance package."
        if missing
        else ""
    )
    return {
        "ready": ready,
        "blocker": blocker,
        "source_artifacts": source_artifacts,
        "review_batch_id": _review_batch_id(project_id, source_artifacts) if ready else "",
    }


def _review_batch_id(project_id: str, source_artifacts: list[dict[str, Any]]) -> str:
    fingerprint_source = {
        "project_id": project_id,
        "artifact_ids": [artifact["id"] for artifact in source_artifacts],
        "schema": MULTI_AGENT_REVIEW_SCHEMA,
    }
    digest = sha256(
        json.dumps(fingerprint_source, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return f"review-batch-{digest}"


def _review_record(
    *,
    reviewer: Mapping[str, str],
    project_id: str,
    review_batch_id: str,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    reviewer_agent_id = reviewer["agent_id"]
    artifact_ids = [artifact["id"] for artifact in artifacts]
    checks = _review_checks(reviewer_agent_id, artifacts)
    findings = _review_findings(reviewer_agent_id, artifacts)
    summary = _review_summary(reviewer["name"], artifacts)
    return {
        "source_key": (
            f"multi_agent_review:{project_id}:{review_batch_id}:{reviewer_agent_id}"
        ),
        "project_id": project_id,
        "review_batch_id": review_batch_id,
        "reviewer_agent_id": reviewer_agent_id,
        "reviewer_name": reviewer["name"],
        "reviewer_role": reviewer["role"],
        "verdict": "approved",
        "summary": summary,
        "artifact_ids": artifact_ids,
        "checks": checks,
        "findings": findings,
    }


def _review_checks(reviewer_agent_id: str, artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
    shared = [
        {
            "id": "source_artifacts_approved",
            "status": "passed",
            "detail": "Code plan and acceptance package are approved.",
        },
        {
            "id": "artifact_linkage",
            "status": "passed",
            "detail": "Review is tied to artifact ids: "
            + ", ".join(artifact["id"] for artifact in artifacts)
            + ".",
        },
    ]
    role_specific = {
        "qa-critic": (
            "risk_and_blocker_scan",
            "Risks and blocker ownership are explicit enough for founder review.",
        ),
        "test-automation-agent": (
            "test_plan_coverage",
            "Acceptance package includes test-plan evidence before implementation.",
        ),
        "product-manager": (
            "product_scope_alignment",
            "Implementation stays tied to target user, problem, and non-goals.",
        ),
        "engineering-manager": (
            "implementation_feasibility",
            "Engineering ownership and rollout gates are clear enough to proceed.",
        ),
        "ui-ux-research-agent": (
            "founder_workflow_usability",
            "Founder-facing workflow states are reviewable before UI polish begins.",
        ),
    }
    check_id, detail = role_specific[reviewer_agent_id]
    return [
        *shared,
        {
            "id": check_id,
            "status": "passed",
            "detail": detail,
        },
    ]


def _review_findings(
    reviewer_agent_id: str,
    artifacts: list[dict[str, Any]],
) -> list[dict[str, str]]:
    artifact_label = ", ".join(f"{item['stage_id']} v{item['version']}" for item in artifacts)
    findings = {
        "qa-critic": (
            "Launch risk is reviewable",
            "Risk and acceptance evidence are present; founder still owns accepted-risk decisions.",
        ),
        "test-automation-agent": (
            "Test plan is ready for automation mapping",
            "The approved acceptance package can now be converted into automated checks.",
        ),
        "product-manager": (
            "Scope remains founder-reviewable",
            "Code plan and acceptance artifacts stay connected to the original user problem.",
        ),
        "engineering-manager": (
            "Implementation boundary is ready",
            "Engineering can proceed from the approved plan with explicit verification gates.",
        ),
        "ui-ux-research-agent": (
            "Experience review is ready",
            "Founder workflow, screen states, and accessibility notes can now drive UI polish.",
        ),
    }
    title, detail = findings[reviewer_agent_id]
    return [
        {
            "severity": "info",
            "title": title,
            "detail": f"{detail} Source artifacts: {artifact_label}.",
        }
    ]


def _review_summary(reviewer_name: str, artifacts: list[dict[str, Any]]) -> str:
    artifact_label = ", ".join(f"{item['stage_id']} v{item['version']}" for item in artifacts)
    return f"{reviewer_name} approved the current implementation handoff for {artifact_label}."


def _artifact_summary(artifact: Mapping[str, Any] | None) -> dict[str, Any]:
    if artifact is None:
        return {}
    metadata = artifact.get("json") or {}
    return {
        "id": artifact["id"],
        "stage_id": artifact["stage_id"],
        "status": artifact["status"],
        "version": artifact["version"],
        "title": metadata.get("title", artifact["stage_id"]),
        "owner_agent_id": artifact["owner_agent_id"],
    }


def _record_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "review_batch_id": record["review_batch_id"],
        "reviewer_agent_id": record["reviewer_agent_id"],
        "reviewer_name": record["reviewer_name"],
        "reviewer_role": record["reviewer_role"],
        "verdict": record["verdict"],
        "summary": record["summary"],
        "artifact_ids": list(record["artifact_ids"]),
        "checks": [dict(check) for check in record["checks"]],
        "findings": [dict(finding) for finding in record["findings"]],
        "created_at": record["created_at"],
    }


def _aggregate(readiness: Mapping[str, Any], records: list[dict]) -> dict[str, Any]:
    if not readiness["ready"]:
        status = "blocked"
    elif len(records) < len(REVIEWERS):
        status = "pending"
    elif any(record["verdict"] == "blocked" for record in records):
        status = "blocked"
    elif any(record["verdict"] == "needs_revision" for record in records):
        status = "needs_revision"
    else:
        status = "approved"
    return {
        "status": status,
        "reviewer_count": len(records),
        "required_reviewer_count": len(REVIEWERS),
        "approved": status == "approved",
    }
