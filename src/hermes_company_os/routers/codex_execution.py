from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from hermes_company_os.codex_execution import (
    CODEX_EXECUTION_DECISION_SOURCE,
    CODEX_EXECUTION_DECISION_TYPE,
    CODEX_EXECUTION_STAGE_ID,
    codex_execution_markdown,
    codex_execution_package,
    queue_codex_execution_run,
    start_codex_execution_git_worktree,
)
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.settings import Settings


def register_codex_execution_routes(app: FastAPI) -> None:
    """Register the Codex execution routes (read, approval, and gated runs)."""

    @app.get("/projects/{project_id}/codex-execution.json")
    def project_codex_execution_json(request: Request, project_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return codex_execution_package(repository, project_id)

    @app.get("/projects/{project_id}/codex-execution.md")
    def project_codex_execution_markdown(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = codex_execution_package(repository, project_id)
        return PlainTextResponse(codex_execution_markdown(package))

    @app.post("/projects/{project_id}/codex-execution-approval")
    def request_project_codex_execution_approval(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = codex_execution_package(repository, project_id)
        if package["execution"]["approval_request_allowed"]:
            source_artifacts = ", ".join(
                f"{artifact['stage_id']}={artifact['id']}@v{artifact['version']}"
                for artifact in package["source_artifacts"]
            )
            command_preview = "; ".join(
                command["command"] for command in package["command_preview"]
            )
            acceptance_artifact = next(
                (
                    artifact
                    for artifact in package["source_artifacts"]
                    if artifact["stage_id"] == CODEX_EXECUTION_STAGE_ID
                ),
                {},
            )
            repository.create_founder_decision(
                title=f"Approve Codex execution for {project['name']}",
                urgency="urgent",
                decision_type=CODEX_EXECUTION_DECISION_TYPE,
                source=CODEX_EXECUTION_DECISION_SOURCE,
                owner_agent_id="chief-of-staff",
                project_id=project_id,
                stage_id=CODEX_EXECUTION_STAGE_ID,
                artifact_id=acceptance_artifact.get("id") or None,
                slack_channel="#founder-command",
                telegram_policy="Telegram only if Codex execution blocks launch.",
                context=(
                    f"Approve Codex implementation start for {project['name']}. "
                    "This dashboard action does not create branches, create "
                    "worktrees, spawn chats, or run commands."
                ),
                evidence=(
                    f"Source artifacts: {source_artifacts}. Branch preview: "
                    f"{package['branch_plan']['branch_name']}. Commands previewed: "
                    f"{command_preview}."
                ),
                requires_founder_approval=True,
            )
        return RedirectResponse(
            f"/projects/{project_id}#codex-execution",
            status_code=303,
        )

    @app.post("/projects/{project_id}/codex-execution-run")
    def queue_project_codex_execution_run(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            queue_codex_execution_run(repository, project_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#codex-execution",
            status_code=303,
        )

    @app.post("/projects/{project_id}/codex-execution-real-run")
    def start_project_codex_execution_real_run(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        settings: Settings = request.app.state.settings
        try:
            start_codex_execution_git_worktree(
                repository,
                project_id,
                enabled=settings.codex_execution_enabled,
                workspace_root=settings.codex_workspace_root,
                worktree_root=settings.codex_worktree_root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}#codex-execution",
            status_code=303,
        )
