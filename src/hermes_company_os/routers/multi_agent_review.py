from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from hermes_company_os.multi_agent_review import (
    generate_multi_agent_review,
    multi_agent_review_markdown,
    multi_agent_review_package,
)
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.review_policy import stage_review_requirements


def register_multi_agent_review_routes(app: FastAPI) -> None:
    """Register the multi-agent review routes (read + founder-triggered run)."""

    @app.get("/projects/{project_id}/multi-agent-review.json")
    def project_multi_agent_review_json(request: Request, project_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return multi_agent_review_package(repository, project_id)

    @app.get("/projects/{project_id}/stages/{stage_id}/review-requirements.json")
    def project_stage_review_requirements_json(
        request: Request, project_id: str, stage_id: str
    ) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return stage_review_requirements(repository, project_id, stage_id)

    @app.get("/projects/{project_id}/multi-agent-review.md")
    def project_multi_agent_review_markdown(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        package = multi_agent_review_package(repository, project_id)
        return PlainTextResponse(multi_agent_review_markdown(package))

    @app.post("/projects/{project_id}/multi-agent-review")
    def generate_project_multi_agent_review(request: Request, project_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            package = generate_multi_agent_review(repository, project_id)
        except ValueError as exc:
            repository.create_audit_event(
                project_id=project_id,
                event_type="multi_agent_review_blocked",
                status="blocked",
                actor_agent_id="qa-critic",
                source_table="company_projects",
                source_id=project_id,
                summary=f"Multi-agent review blocked: {exc}",
                payload={"blocker": str(exc)},
            )
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        repository.create_audit_event(
            project_id=project_id,
            event_type="multi_agent_review_completed",
            status=package["aggregate"]["status"],
            actor_agent_id="qa-critic",
            source_table="project_review_records",
            source_id=package["review_batch_id"],
            summary=(
                "Multi-agent review completed with "
                f"{package['aggregate']['reviewer_count']} reviewer records."
            ),
            payload={
                "review_batch_id": package["review_batch_id"],
                "reviewer_count": package["aggregate"]["reviewer_count"],
                "required_reviewer_count": package["aggregate"]["required_reviewer_count"],
                "status": package["aggregate"]["status"],
            },
        )
        return RedirectResponse(
            f"/projects/{project_id}#multi-agent-review",
            status_code=303,
        )
