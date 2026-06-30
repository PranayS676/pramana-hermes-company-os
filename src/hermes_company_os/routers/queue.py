from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from hermes_company_os.agent_work_queue import (
    QUEUE_PRIORITIES,
    QUEUE_PRIORITY_LABELS,
    QUEUE_STATE_LABELS,
    QUEUE_STATES,
)
from hermes_company_os.profile_handoff_contracts import (
    profile_handoff_contract,
    profile_handoff_contract_markdown,
)
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.routers._helpers import (
    form_checkbox_checked,
    reject_secret_values,
    safe_return_path,
)


def register_queue_routes(app: FastAPI) -> None:
    """Register the agent work queue routes."""

    @app.get("/queue")
    def agent_work_queue(
        request: Request,
        status: str = "",
        project_id: str = "",
        owner_agent_id: str = "",
    ):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        try:
            items = repository.list_agent_work_items(
                project_id=project_id,
                owner_agent_id=owner_agent_id,
                status=status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return templates.TemplateResponse(
            request,
            "queue.html",
            {
                "items": items,
                "summary": repository.agent_work_queue_summary(),
                "agents": repository.list_agents(),
                "projects": repository.list_projects(),
                "states": QUEUE_STATES,
                "state_labels": QUEUE_STATE_LABELS,
                "priorities": QUEUE_PRIORITIES,
                "priority_labels": QUEUE_PRIORITY_LABELS,
                "filters": {
                    "status": status,
                    "project_id": project_id,
                    "owner_agent_id": owner_agent_id,
                },
            },
        )

    @app.post("/queue")
    def create_agent_work_item(
        request: Request,
        title: str = Form(...),
        owner_agent_id: str = Form("chief-of-staff"),
        status: str = Form("planned"),
        priority: str = Form("medium"),
        project_id: str = Form(""),
        summary: str = Form(""),
        blocked_reason: str = Form(""),
        blocked_owner: str = Form(""),
        founder_action_required: str = Form(""),
        return_to: str = Form("/queue"),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        reject_secret_values(
            {
                "title": title,
                "owner_agent_id": owner_agent_id,
                "status": status,
                "priority": priority,
                "project_id": project_id,
                "summary": summary,
                "blocked_reason": blocked_reason,
                "blocked_owner": blocked_owner,
            }
        )
        try:
            repository.create_agent_work_item(
                title=title,
                owner_agent_id=owner_agent_id,
                summary=summary,
                status=status,
                priority=priority,
                project_id=project_id or None,
                blocked_reason=blocked_reason,
                blocked_owner=blocked_owner,
                founder_action_required=form_checkbox_checked(founder_action_required),
                source="manual",
                external_handoff_status="dashboard_source_of_truth",
                slack_channel="#decisions",
                telegram_policy="Telegram only if this blocks founder progress.",
            )
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(safe_return_path(return_to, "/queue"), status_code=303)

    @app.post("/queue/{work_item_id}")
    def update_agent_work_item(
        request: Request,
        work_item_id: str,
        status: str = Form(...),
        priority: str = Form(""),
        owner_agent_id: str = Form(""),
        blocked_reason: str = Form(""),
        blocked_owner: str = Form(""),
        founder_action_required: str = Form(""),
        founder_confirmed: str = Form(""),
        return_to: str = Form("/queue"),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        if repository.get_agent_work_item(work_item_id) is None:
            raise HTTPException(status_code=404, detail="Agent work item not found")
        reject_secret_values(
            {
                "status": status,
                "priority": priority,
                "owner_agent_id": owner_agent_id,
                "blocked_reason": blocked_reason,
                "blocked_owner": blocked_owner,
            }
        )
        try:
            repository.update_agent_work_item(
                work_item_id,
                status=status,
                priority=priority or None,
                owner_agent_id=owner_agent_id or None,
                blocked_reason=blocked_reason,
                blocked_owner=blocked_owner,
                founder_action_required=form_checkbox_checked(founder_action_required),
                founder_confirmed=form_checkbox_checked(founder_confirmed),
            )
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(safe_return_path(return_to, "/queue"), status_code=303)

    @app.get("/queue/{work_item_id}/handoff.json")
    def agent_work_item_handoff_json(request: Request, work_item_id: str) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        work_item = repository.get_agent_work_item(work_item_id)
        if work_item is None:
            raise HTTPException(status_code=404, detail="Agent work item not found")
        return profile_handoff_contract(repository, work_item)

    @app.get("/queue/{work_item_id}/handoff.md")
    def agent_work_item_handoff_markdown(request: Request, work_item_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        work_item = repository.get_agent_work_item(work_item_id)
        if work_item is None:
            raise HTTPException(status_code=404, detail="Agent work item not found")
        contract = profile_handoff_contract(repository, work_item)
        return PlainTextResponse(profile_handoff_contract_markdown(contract))
