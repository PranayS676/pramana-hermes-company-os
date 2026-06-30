from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.research_packages import (
    finding_severity_options,
    research_method_options,
    research_package_markdown,
    research_package_severity_counts,
    research_status_options,
)


def register_research_routes(app: FastAPI) -> None:
    """Register UI/UX research-package routes (M1A).

    Direct-decorator pattern (no APIRouter) per CLAUDE.md. Exposes JSON list/get,
    a markdown export, a founder-facing HTML page, and create/retire actions.
    """

    @app.get("/projects/{project_id}/research.json")
    def project_research_json(request: Request, project_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        packages = repository.list_research_packages(
            project_id=project_id,
            include_company_wide=True,
            include_retired=True,
        )
        return {
            "schema": "ui_ux_research_package_list_v1",
            "project_id": project_id,
            "count": len(packages),
            "packages": packages,
        }

    @app.get("/research/packages/{package_id}.json")
    def research_package_json(request: Request, package_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        package = repository.get_research_package(package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Research package not found")
        return package

    @app.get("/research/packages/{package_id}.md")
    def research_package_markdown_route(request: Request, package_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        package = repository.get_research_package(package_id)
        if package is None:
            raise HTTPException(status_code=404, detail="Research package not found")
        return PlainTextResponse(research_package_markdown(package))

    @app.get("/projects/{project_id}/research")
    def project_research_html(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        packages = repository.list_research_packages(
            project_id=project_id,
            include_company_wide=True,
            include_retired=True,
        )
        for package in packages:
            package["severity_counts"] = research_package_severity_counts(
                package.get("findings", [])
            )
        return templates.TemplateResponse(
            request,
            "research.html",
            {
                "project": project,
                "packages": packages,
                "method_options": research_method_options(),
                "severity_options": finding_severity_options(),
                "status_options": research_status_options(),
            },
        )

    @app.post("/projects/{project_id}/research")
    def create_research_package_route(
        request: Request,
        project_id: str,
        title: str = Form(...),
        research_thread: str = Form(...),
        research_question: str = Form(...),
        method: str = Form(...),
        owner_agent_id: str = Form("ui-ux-research-agent"),
        target_workflow: str = Form(""),
        summary: str = Form(""),
        finding_title: str = Form(""),
        finding_severity: str = Form("medium"),
        finding_detail: str = Form(""),
        finding_evidence: str = Form(""),
        finding_surface: str = Form(""),
        recommendation_behavior: str = Form(""),
        recommendation_surface: str = Form(""),
        recommendation_acceptance: str = Form(""),
        founder_decision: str = Form(""),
        founder_decision_default: str = Form(""),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        findings = []
        if finding_title.strip():
            findings.append(
                {
                    "title": finding_title,
                    "severity": finding_severity,
                    "detail": finding_detail,
                    "evidence": finding_evidence,
                    "surface": finding_surface,
                }
            )
        recommendations = []
        if recommendation_behavior.strip():
            recommendations.append(
                {
                    "behavior": recommendation_behavior,
                    "surface": recommendation_surface,
                    "acceptance_signal": recommendation_acceptance,
                }
            )
        decisions = []
        if founder_decision.strip():
            decisions.append(
                {
                    "decision": founder_decision,
                    "default_recommendation": founder_decision_default,
                }
            )
        try:
            repository.create_research_package(
                title=title,
                research_thread=research_thread,
                research_question=research_question,
                method=method,
                owner_agent_id=owner_agent_id,
                project_id=project_id,
                target_workflow=target_workflow,
                summary=summary,
                findings=findings,
                recommendations=recommendations,
                founder_decisions_needed=decisions,
                status="active",
            )
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}/research", status_code=303)

    @app.post("/projects/{project_id}/research/{package_id}")
    def update_research_package_route(
        request: Request,
        project_id: str,
        package_id: str,
        research_action: str = Form("retire"),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = repository.get_research_package(package_id)
        if package is None or (
            package.get("project_id") and package["project_id"] != project_id
        ):
            raise HTTPException(status_code=404, detail="Research package not found")
        try:
            if research_action == "retire":
                repository.retire_research_package(package_id)
            elif research_action == "reactivate":
                repository.update_research_package_status(package_id, "active")
            else:
                raise ValueError(f"Unsupported research action: {research_action}")
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}/research", status_code=303)
