from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from hermes_company_os.secret_guard import assert_no_secret_values

RESEARCH_PACKAGE_SCHEMA = "ui_ux_research_package_v1"

# Research methods mirror the doctrine's required research method
# (`docs/ui-ux-research/01-ui-ux-research-agent-doctrine.md`).
RESEARCH_METHODS: tuple[str, ...] = (
    "workflow_analysis",
    "state_analysis",
    "decision_analysis",
    "evidence_analysis",
    "failure_analysis",
    "accessibility_analysis",
    "implementation_analysis",
    "heuristic_review",
)

RESEARCH_METHOD_LABELS: dict[str, str] = {
    "workflow_analysis": "Workflow analysis",
    "state_analysis": "State analysis",
    "decision_analysis": "Decision analysis",
    "evidence_analysis": "Evidence analysis",
    "failure_analysis": "Failure analysis",
    "accessibility_analysis": "Accessibility analysis",
    "implementation_analysis": "Implementation analysis",
    "heuristic_review": "Heuristic review",
}

# Finding severity ordered from most to least urgent.
FINDING_SEVERITIES: tuple[str, ...] = ("critical", "high", "medium", "low", "info")

FINDING_SEVERITY_LABELS: dict[str, str] = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Info",
}

FINDING_SEVERITY_RANK: dict[str, int] = {
    severity: rank for rank, severity in enumerate(FINDING_SEVERITIES)
}

RESEARCH_PACKAGE_STATUSES: tuple[str, ...] = ("draft", "active", "retired")


def research_method_options() -> list[dict[str, str]]:
    return [
        {"id": method, "label": RESEARCH_METHOD_LABELS[method]}
        for method in RESEARCH_METHODS
    ]


def finding_severity_options() -> list[dict[str, str]]:
    return [
        {"id": severity, "label": FINDING_SEVERITY_LABELS[severity]}
        for severity in FINDING_SEVERITIES
    ]


def research_status_options() -> list[dict[str, str]]:
    return [
        {"id": status, "label": status.replace("_", " ").title()}
        for status in RESEARCH_PACKAGE_STATUSES
    ]


def normalize_research_method(method: str) -> str:
    normalized = method.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in RESEARCH_METHODS:
        raise ValueError(f"Unsupported research method: {method}")
    return normalized


def normalize_finding_severity(severity: str) -> str:
    normalized = severity.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in FINDING_SEVERITIES:
        raise ValueError(f"Unsupported finding severity: {severity}")
    return normalized


def normalize_research_status(status: str) -> str:
    normalized = status.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in RESEARCH_PACKAGE_STATUSES:
        raise ValueError(f"Unsupported research package status: {status}")
    return normalized


def build_finding(
    *,
    title: str,
    severity: str,
    detail: str = "",
    evidence: str = "",
    surface: str = "",
) -> dict[str, str]:
    """Normalize one research finding (severity + evidence)."""
    cleaned_title = title.strip()
    if not cleaned_title:
        raise ValueError("Finding title is required.")
    return {
        "title": cleaned_title,
        "severity": normalize_finding_severity(severity),
        "detail": detail.strip(),
        "evidence": evidence.strip(),
        "surface": surface.strip(),
    }


def build_recommendation(
    *,
    behavior: str,
    surface: str = "",
    data_needed: str = "",
    acceptance_signal: str = "",
) -> dict[str, str]:
    """Normalize one implementation recommendation."""
    cleaned_behavior = behavior.strip()
    if not cleaned_behavior:
        raise ValueError("Recommendation behavior is required.")
    return {
        "behavior": cleaned_behavior,
        "surface": surface.strip(),
        "data_needed": data_needed.strip(),
        "acceptance_signal": acceptance_signal.strip(),
    }


def build_founder_decision(
    *,
    decision: str,
    why_it_matters: str = "",
    default_recommendation: str = "",
    impact_if_deferred: str = "",
) -> dict[str, str]:
    """Normalize one founder-decision-needed entry."""
    cleaned_decision = decision.strip()
    if not cleaned_decision:
        raise ValueError("Founder decision question is required.")
    return {
        "decision": cleaned_decision,
        "why_it_matters": why_it_matters.strip(),
        "default_recommendation": default_recommendation.strip(),
        "impact_if_deferred": impact_if_deferred.strip(),
    }


def build_research_package(
    *,
    title: str,
    research_thread: str,
    research_question: str,
    method: str,
    owner_agent_id: str = "ui-ux-research-agent",
    target_workflow: str = "",
    summary: str = "",
    findings: Sequence[Mapping[str, Any]] = (),
    recommendations: Sequence[Mapping[str, Any]] = (),
    founder_decisions_needed: Sequence[Mapping[str, Any]] = (),
    status: str = "active",
) -> dict[str, Any]:
    """Assemble a normalized, secret-scanned research-package payload.

    Findings/recommendations/founder-decisions may be raw mappings (they are
    re-normalized through the ``build_*`` helpers) so callers can pass plain
    dicts from a form or fixture.
    """
    cleaned_title = title.strip()
    if not cleaned_title:
        raise ValueError("Research package title is required.")
    cleaned_thread = research_thread.strip()
    if not cleaned_thread:
        raise ValueError("Research thread is required.")
    cleaned_question = research_question.strip()
    if not cleaned_question:
        raise ValueError("Research question is required.")
    cleaned_owner = owner_agent_id.strip()
    if not cleaned_owner:
        raise ValueError("Owner agent id is required.")

    normalized_findings = [
        build_finding(
            title=str(item.get("title", "")),
            severity=str(item.get("severity", "")),
            detail=str(item.get("detail", "")),
            evidence=str(item.get("evidence", "")),
            surface=str(item.get("surface", "")),
        )
        for item in findings
    ]
    normalized_findings.sort(key=lambda finding: FINDING_SEVERITY_RANK[finding["severity"]])
    normalized_recommendations = [
        build_recommendation(
            behavior=str(item.get("behavior", "")),
            surface=str(item.get("surface", "")),
            data_needed=str(item.get("data_needed", "")),
            acceptance_signal=str(item.get("acceptance_signal", "")),
        )
        for item in recommendations
    ]
    normalized_decisions = [
        build_founder_decision(
            decision=str(item.get("decision", "")),
            why_it_matters=str(item.get("why_it_matters", "")),
            default_recommendation=str(item.get("default_recommendation", "")),
            impact_if_deferred=str(item.get("impact_if_deferred", "")),
        )
        for item in founder_decisions_needed
    ]

    package = {
        "schema": RESEARCH_PACKAGE_SCHEMA,
        "title": cleaned_title,
        "research_thread": cleaned_thread,
        "research_question": cleaned_question,
        "method": normalize_research_method(method),
        "owner_agent_id": cleaned_owner,
        "target_workflow": target_workflow.strip(),
        "summary": summary.strip(),
        "status": normalize_research_status(status),
        "findings": normalized_findings,
        "recommendations": normalized_recommendations,
        "founder_decisions_needed": normalized_decisions,
    }
    assert_no_secret_values({"research_package": json.dumps(package, sort_keys=True)})
    return package


def research_package_severity_counts(
    findings: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    counts = {severity: 0 for severity in FINDING_SEVERITIES}
    for finding in findings:
        severity = str(finding.get("severity", ""))
        if severity in counts:
            counts[severity] += 1
    return counts


def research_package_markdown(package: Mapping[str, Any]) -> str:
    """Render a stored research package as founder-readable markdown."""
    findings = list(package.get("findings", []))
    recommendations = list(package.get("recommendations", []))
    decisions = list(package.get("founder_decisions_needed", []))
    method = str(package.get("method", ""))
    method_label = RESEARCH_METHOD_LABELS.get(method, method.replace("_", " ").title())

    lines = [
        f"# UI/UX Research Package: {package['title']}",
        "",
        f"- Schema: `{package.get('schema', RESEARCH_PACKAGE_SCHEMA)}`",
        f"- Research thread: {package.get('research_thread', '')}",
        f"- Method: {method_label}",
        f"- Owner: `{package.get('owner_agent_id', '')}`",
        f"- Status: `{package.get('status', '')}`",
    ]
    if package.get("project_id"):
        lines.append(f"- Project: `{package['project_id']}`")
    lines.extend(
        [
            "",
            "## Research Question",
            "",
            str(package.get("research_question", "")),
            "",
        ]
    )
    if package.get("target_workflow"):
        lines.extend(["## Target Workflow", "", str(package["target_workflow"]), ""])
    if package.get("summary"):
        lines.extend(["## Summary", "", str(package["summary"]), ""])

    lines.extend(["## Findings", ""])
    if findings:
        for finding in findings:
            severity = str(finding.get("severity", ""))
            severity_label = FINDING_SEVERITY_LABELS.get(severity, severity.title())
            lines.append(f"### [{severity_label}] {finding.get('title', '')}")
            lines.append("")
            if finding.get("surface"):
                lines.append(f"- Surface: {finding['surface']}")
            if finding.get("detail"):
                lines.append(f"- Detail: {finding['detail']}")
            if finding.get("evidence"):
                lines.append(f"- Evidence: {finding['evidence']}")
            lines.append("")
    else:
        lines.extend(["- No findings recorded.", ""])

    lines.extend(["## Implementation Recommendations", ""])
    if recommendations:
        for rec in recommendations:
            lines.append(f"### {rec.get('behavior', '')}")
            lines.append("")
            if rec.get("surface"):
                lines.append(f"- Affected surface: {rec['surface']}")
            if rec.get("data_needed"):
                lines.append(f"- Data needed: {rec['data_needed']}")
            if rec.get("acceptance_signal"):
                lines.append(f"- Acceptance signal: {rec['acceptance_signal']}")
            lines.append("")
    else:
        lines.extend(["- No recommendations recorded.", ""])

    lines.extend(["## Founder Decisions Needed", ""])
    if decisions:
        for decision in decisions:
            lines.append(f"### {decision.get('decision', '')}")
            lines.append("")
            if decision.get("why_it_matters"):
                lines.append(f"- Why it matters: {decision['why_it_matters']}")
            if decision.get("default_recommendation"):
                lines.append(
                    f"- Default recommendation: {decision['default_recommendation']}"
                )
            if decision.get("impact_if_deferred"):
                lines.append(f"- Impact if deferred: {decision['impact_if_deferred']}")
            lines.append("")
    else:
        lines.extend(["- No founder decisions outstanding.", ""])

    markdown = "\n".join(lines)
    assert_no_secret_values({"research_package_markdown": markdown})
    return markdown
