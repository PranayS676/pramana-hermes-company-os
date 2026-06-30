from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from hermes_company_os.external_dispatch import (
    HermesExternalDispatchCommandAdapter,
    operating_loop_package,
)
from hermes_company_os.project_operating_loop import (
    consume_external_dispatch_preview_approval,
    project_external_dispatch_preview_package,
    request_external_dispatch_approval,
    run_external_dispatch_runner,
)
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.settings import Settings


def register_external_dispatch_routes(app: FastAPI) -> None:
    """Register the founder-gated external-dispatch action routes on ``app``.

    Uses direct ``@app`` decorators so these routes register identically to the
    rest of the dashboard. Behaviour is unchanged from the previous inline
    definitions in ``main.py``; this only moves them into a focused module.
    """

    @app.get("/operating-loop")
    def company_operating_loop_html(request: Request):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        package = operating_loop_package(repository)
        return templates.TemplateResponse(
            request,
            "operating_loop.html",
            {
                "package": package,
                "projects": repository.list_projects(),
            },
        )

    @app.get("/projects/{project_id}/operating-loop")
    def project_operating_loop_html(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = operating_loop_package(repository, project_id)
        return templates.TemplateResponse(
            request,
            "operating_loop.html",
            {
                "package": package,
                "projects": [],
            },
        )

    @app.get("/projects/{project_id}/external-dispatch-preview.json")
    def project_external_dispatch_preview_json(
        request: Request, project_id: str
    ) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project_external_dispatch_preview_package(
            repository,
            project_id,
            external_dispatch_enabled=request.app.state.settings.external_dispatch_enabled,
        )

    @app.post("/projects/{project_id}/external-dispatch-approval")
    def request_project_external_dispatch_approval(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            request_external_dispatch_approval(repository, project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#external-dispatch-preview",
            status_code=303,
        )

    @app.post("/projects/{project_id}/external-dispatch-audit")
    def consume_project_external_dispatch_audit(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            consume_external_dispatch_preview_approval(repository, project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#external-dispatch-preview",
            status_code=303,
        )

    @app.post("/projects/{project_id}/external-dispatch-run")
    def run_project_external_dispatch(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        settings: Settings = request.app.state.settings
        runner = getattr(request.app.state, "external_dispatch_runner", None)
        runner_label = getattr(
            request.app.state,
            "external_dispatch_runner_label",
            "external_dispatch_runner",
        )
        if runner is None and settings.external_dispatch_enabled:
            runner = HermesExternalDispatchCommandAdapter(
                enabled=True,
                runner_label="subprocess",
            )
            runner_label = runner.runner_label
        try:
            run_external_dispatch_runner(
                repository,
                project_id,
                enabled=settings.external_dispatch_enabled,
                runner=runner,
                runner_label=runner_label,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#external-dispatch-preview",
            status_code=303,
        )
