from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.rollback_plan import (
    rollback_plan_markdown,
    rollback_plan_package,
)


def register_launch_routes(app: FastAPI) -> None:
    """Register the founder-facing launch/release artifact routes on ``app``.

    Uses direct ``@app`` decorators (not ``APIRouter``) so the routes register
    identically to the rest of the dashboard. Currently exposes the Milestone 9
    rollback-plan artifact as project-scoped JSON and Markdown.
    """

    @app.get("/projects/{project_id}/rollback-plan.json")
    def project_rollback_plan_json(request: Request, project_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return rollback_plan_package(repository, project_id)

    @app.get("/projects/{project_id}/rollback-plan.md")
    def project_rollback_plan_markdown(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = rollback_plan_package(repository, project_id)
        return PlainTextResponse(rollback_plan_markdown(package))
