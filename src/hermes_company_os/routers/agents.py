from __future__ import annotations

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from hermes_company_os.prompts import build_agent_prompt
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.routers._helpers import (
    get_agent_or_404,
    reject_secret_values,
)


def register_agents_routes(app: FastAPI) -> None:
    """Register the agent detail / profile / routing / run routes."""

    @app.get("/agents/{agent_id}")
    def agent_detail(request: Request, agent_id: str):
        # Imported lazily to avoid a circular import with main during module load.
        from hermes_company_os.main import profile_live_run_blocker

        repository: RepositoryProtocol = request.app.state.repository
        templates = request.app.state.templates
        agent = get_agent_or_404(repository, agent_id)
        return templates.TemplateResponse(
            request,
            "agent.html",
            {
                "agent": agent,
                "live_run_blocker": profile_live_run_blocker(repository, agent_id),
                "agent_work_items": repository.list_agent_work_items(
                    owner_agent_id=agent_id,
                    limit=8,
                    include_done=False,
                ),
                "settings": request.app.state.settings,
            },
        )

    @app.post("/agents/{agent_id}/profile")
    def update_agent_profile(
        request: Request,
        agent_id: str,
        description: str = Form(...),
        soul: str = Form(...),
        capabilities: str = Form(...),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        get_agent_or_404(repository, agent_id)
        parsed_capabilities = [
            line.strip()
            for line in capabilities.replace(",", "\n").splitlines()
            if line.strip()
        ]
        if not description.strip() or not soul.strip() or not parsed_capabilities:
            raise HTTPException(
                status_code=400,
                detail="Description, soul, and at least one capability are required",
            )
        reject_secret_values(
            {
                "description": description,
                "soul": soul,
                "capabilities": "\n".join(parsed_capabilities),
            }
        )
        repository.update_agent_profile(
            agent_id=agent_id,
            description=description,
            soul=soul,
            capabilities=parsed_capabilities,
        )
        return RedirectResponse(f"/agents/{agent_id}", status_code=303)

    @app.post("/agents/{agent_id}/routing")
    def update_agent_routing(
        request: Request,
        agent_id: str,
        slack_channel: str = Form(...),
        telegram_policy: str = Form(...),
        hermes_command: str = Form(...),
    ):
        repository: RepositoryProtocol = request.app.state.repository
        get_agent_or_404(repository, agent_id)
        if not slack_channel.strip() or not telegram_policy.strip() or not hermes_command.strip():
            raise HTTPException(
                status_code=400,
                detail="Slack channel, Telegram policy, and Hermes command are required",
            )
        reject_secret_values(
            {
                "slack_channel": slack_channel,
                "telegram_policy": telegram_policy,
                "hermes_command": hermes_command,
            }
        )
        repository.update_agent_routing(
            agent_id=agent_id,
            slack_channel=slack_channel,
            telegram_policy=telegram_policy,
            hermes_command=hermes_command,
        )
        return RedirectResponse(f"/agents/{agent_id}", status_code=303)

    @app.post("/agents/{agent_id}/run")
    def run_agent(request: Request, agent_id: str, founder_request: str = Form(...)):
        # Imported lazily to avoid a circular import with main during module load.
        from hermes_company_os.main import profile_live_run_blocker

        reject_secret_values({"founder_request": founder_request})
        repository: RepositoryProtocol = request.app.state.repository
        agent = get_agent_or_404(repository, agent_id)
        live_run_blocker = profile_live_run_blocker(repository, agent_id)
        if live_run_blocker:
            raise HTTPException(status_code=409, detail=live_run_blocker)
        prompt = build_agent_prompt(agent, founder_request.strip())
        run_id = repository.create_run(agent_id=agent_id, run_type="agent", prompt=prompt)
        result = request.app.state.hermes_client.run_prompt(agent, prompt)
        repository.complete_run(run_id, output=result.output, error=result.error)
        return RedirectResponse("/", status_code=303)
