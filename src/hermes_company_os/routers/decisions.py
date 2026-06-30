from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from hermes_company_os.founder_decisions import (
    DECISION_TYPE_LABELS,
    RESOLVED_DECISION_STATUSES,
    founder_decisions_payload,
)
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.routers._helpers import (
    form_checkbox_checked,
    reject_secret_values,
    safe_return_path,
)

DECISION_STATUS_OPTIONS = ("needed", "blocked", "approved", "rejected", "deferred")


def register_decisions_routes(app: FastAPI) -> None:
    """Register the founder decision inbox routes."""

    @app.get("/decisions")
    def founder_decision_inbox(
        request: Request,
        status: str = "",
        urgency: str = "",
        decision_type: str = "",
        project_id: str = "",
        stage_id: str = "",
        owner_agent_id: str = "",
    ):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        try:
            decisions = repository.list_founder_decisions(
                status=status,
                urgency=urgency,
                decision_type=decision_type,
                project_id=project_id,
                stage_id=stage_id,
                owner_agent_id=owner_agent_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        all_decisions = repository.list_founder_decisions()
        return templates.TemplateResponse(
            request,
            "decisions.html",
            {
                "decisions": decisions,
                "selected_decision": decisions[0] if len(decisions) == 1 else None,
                "summary": founder_decisions_payload(all_decisions)["summary"],
                "agents": repository.list_agents(),
                "projects": repository.list_projects(),
                "decision_types": DECISION_TYPE_LABELS,
                "statuses": DECISION_STATUS_OPTIONS,
                "filters": {
                    "status": status,
                    "urgency": urgency,
                    "decision_type": decision_type,
                    "project_id": project_id,
                    "stage_id": stage_id,
                    "owner_agent_id": owner_agent_id,
                },
            },
        )

    @app.get("/decisions/{decision_id}")
    def founder_decision_detail(request: Request, decision_id: str):
        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        selected_decision = repository.get_founder_decision(decision_id)
        if selected_decision is None:
            raise HTTPException(status_code=404, detail="Founder decision not found")
        all_decisions = repository.list_founder_decisions()
        return templates.TemplateResponse(
            request,
            "decisions.html",
            {
                "decisions": [selected_decision],
                "selected_decision": selected_decision,
                "summary": founder_decisions_payload(all_decisions)["summary"],
                "agents": repository.list_agents(),
                "projects": repository.list_projects(),
                "decision_types": DECISION_TYPE_LABELS,
                "statuses": DECISION_STATUS_OPTIONS,
                "filters": {
                    "status": "",
                    "urgency": "",
                    "decision_type": "",
                    "project_id": selected_decision.get("project_id") or "",
                    "stage_id": selected_decision.get("stage_id") or "",
                    "owner_agent_id": selected_decision.get("owner_agent_id") or "",
                },
            },
        )

    @app.post("/decisions")
    def create_founder_decision(
        request: Request,
        title: str = Form(...),
        urgency: str = Form("routine"),
        decision_type: str = Form("operating_decision"),
        source: str = Form("manual"),
        owner_agent_id: str = Form("chief-of-staff"),
        project_id: str = Form(""),
        stage_id: str = Form(""),
        artifact_id: str = Form(""),
        slack_channel: str = Form("#decisions"),
        telegram_policy: str = Form("Telegram only if this blocks founder progress."),
        context: str = Form(""),
        evidence: str = Form(""),
        requires_founder_approval: str = Form(""),
        return_to: str = Form("/decisions"),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        allowed_urgencies = {"routine", "urgent"}
        if urgency not in allowed_urgencies:
            raise HTTPException(status_code=400, detail="Invalid decision urgency")
        if repository.get_agent(owner_agent_id) is None:
            raise HTTPException(status_code=404, detail="Decision owner profile not found")
        if not title.strip() or not context.strip() or not slack_channel.strip():
            raise HTTPException(
                status_code=400,
                detail="Title, context, and Slack channel are required",
            )
        reject_secret_values(
            {
                "title": title,
                "urgency": urgency,
                "decision_type": decision_type,
                "source": source,
                "owner_agent_id": owner_agent_id,
                "project_id": project_id,
                "stage_id": stage_id,
                "artifact_id": artifact_id,
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
                "context": context,
                "evidence": evidence,
            }
        )
        try:
            repository.create_founder_decision(
                title=title,
                urgency=urgency,
                decision_type=decision_type,
                source=source,
                owner_agent_id=owner_agent_id,
                project_id=project_id or None,
                stage_id=stage_id or None,
                artifact_id=artifact_id or None,
                slack_channel=slack_channel,
                telegram_policy=telegram_policy,
                context=context,
                evidence=evidence,
                requires_founder_approval=(
                    True if form_checkbox_checked(requires_founder_approval) else None
                ),
            )
        except (sqlite3.IntegrityError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(
            safe_return_path(return_to, "/decisions"),
            status_code=303,
        )

    @app.post("/decisions/{decision_id}")
    def update_founder_decision(
        request: Request,
        decision_id: str,
        status: str = Form(...),
        decision: str = Form(""),
        founder_confirmed: str = Form(""),
        return_to: str = Form("/decisions"),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        current = repository.get_founder_decision(decision_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Founder decision not found")
        allowed_statuses = set(DECISION_STATUS_OPTIONS)
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Invalid founder decision status")
        if status in RESOLVED_DECISION_STATUSES and not decision.strip():
            raise HTTPException(
                status_code=400,
                detail="A decision note is required before resolving a founder decision",
            )
        reject_secret_values({"status": status, "decision": decision})
        try:
            repository.update_founder_decision(
                decision_id=decision_id,
                status=status,
                decision=decision,
                founder_confirmed=form_checkbox_checked(founder_confirmed),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse(
            safe_return_path(return_to, "/decisions"),
            status_code=303,
        )
