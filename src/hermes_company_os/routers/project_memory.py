from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from hermes_company_os.project_memory import (
    company_memory_search_package,
    project_memory_markdown,
    project_memory_package,
)
from hermes_company_os.repository_protocol import RepositoryProtocol


def register_project_memory_routes(app: FastAPI) -> None:
    """Register the project-memory routes (read, create, and entry actions)."""

    @app.get("/memory/search.json")
    def company_memory_search_json(
        request: Request,
        q: str = "",
        category: str = "",
        status: str = "active",
        confidence: str = "",
    ) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        return company_memory_search_package(
            repository,
            query=q,
            category=category,
            status=status,
            confidence=confidence,
        )

    @app.get("/memory/search")
    def company_memory_search_html(
        request: Request,
        q: str = "",
        category: str = "",
        status: str = "active",
        confidence: str = "",
    ):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        package = company_memory_search_package(
            repository,
            query=q,
            category=category,
            status=status,
            confidence=confidence,
        )
        return templates.TemplateResponse(
            request,
            "memory_search.html",
            {"package": package},
        )

    @app.get("/projects/{project_id}/memory.json")
    def project_memory_json(request: Request, project_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_memory_package(repository, project_id)

    @app.get("/projects/{project_id}/memory.md")
    def project_memory_markdown_route(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = project_memory_package(repository, project_id)
        return PlainTextResponse(project_memory_markdown(package))

    @app.post("/projects/{project_id}/memory")
    def create_project_memory(
        request: Request,
        project_id: str,
        category: str = Form(...),
        memory_type: str = Form("context"),
        owner_agent_id: str = Form("chief-of-staff"),
        source: str = Form("founder-memory-form"),
        title: str = Form(...),
        summary: str = Form(...),
        body: str = Form(...),
        confidence: str = Form("medium"),
        pinned: str | None = Form(None),
        review_after: str = Form(""),
        expires_at: str = Form(""),
        source_artifact_id: str = Form(""),
        source_decision_id: str = Form(""),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            repository.create_project_memory_entry(
                project_id=project_id,
                category=category,
                memory_type=memory_type,
                owner_agent_id=owner_agent_id,
                source=source,
                title=title,
                summary=summary,
                body=body,
                confidence=confidence,
                status="active",
                pinned=bool(pinned),
                review_after=review_after,
                expires_at=expires_at,
                source_artifact_id=source_artifact_id,
                source_decision_id=source_decision_id,
            )
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}#project-memory", status_code=303)

    @app.post("/projects/{project_id}/memory/{memory_id}")
    def update_project_memory(
        request: Request,
        project_id: str,
        memory_id: str,
        memory_action: str = Form("pin"),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        entry = repository.get_project_memory_entry(memory_id)
        if entry is None or (entry["project_id"] and entry["project_id"] != project_id):
            raise HTTPException(status_code=404, detail="Project memory entry not found")
        try:
            if memory_action == "retire":
                repository.update_project_memory_entry(memory_id, status="retired")
            elif memory_action == "pin":
                repository.update_project_memory_entry(memory_id, pinned=True)
            elif memory_action == "unpin":
                repository.update_project_memory_entry(memory_id, pinned=False)
            elif memory_action == "reactivate":
                repository.update_project_memory_entry(memory_id, status="active")
            else:
                raise ValueError(f"Unsupported memory action: {memory_action}")
        except (ValueError, sqlite3.IntegrityError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(f"/projects/{project_id}#project-memory", status_code=303)
