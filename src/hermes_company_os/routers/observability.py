from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from hermes_company_os.observability import (
    run_observability_markdown,
    run_observability_package,
)
from hermes_company_os.repository_protocol import RepositoryProtocol


def register_observability_routes(app: FastAPI) -> None:
    """Register the read-only run-observability routes (M8)."""

    @app.get("/observability.json")
    def company_observability_json(request: Request) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        return run_observability_package(repository)

    @app.get("/observability")
    def company_observability_html(request: Request):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        package = run_observability_package(repository)
        return templates.TemplateResponse(
            request,
            "observability.html",
            {
                "package": package,
                "projects": repository.list_projects(),
            },
        )

    @app.get("/projects/{project_id}/observability")
    def project_observability_html(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = run_observability_package(repository, project_id)
        return templates.TemplateResponse(
            request,
            "observability.html",
            {
                "package": package,
                "projects": [],
            },
        )

    @app.get("/projects/{project_id}/observability.json")
    def project_observability_json(request: Request, project_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return run_observability_package(repository, project_id)

    @app.get("/projects/{project_id}/observability.md")
    def project_observability_markdown(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = run_observability_package(repository, project_id)
        return PlainTextResponse(run_observability_markdown(package))
