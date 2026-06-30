from __future__ import annotations

from fastapi import HTTPException

from hermes_company_os.secret_guard import assert_no_secret_values


def reject_secret_values(values: dict[str, str]) -> None:
    try:
        assert_no_secret_values(values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def safe_return_path(return_to: str, fallback: str) -> str:
    if return_to.startswith("/") and not return_to.startswith("//"):
        return return_to
    return fallback


def form_checkbox_checked(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on", "confirmed"}


def get_project_or_404(repository, project_id):
    """Return the project for ``project_id`` or raise a 404 HTTPException."""
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_agent_or_404(repository, agent_id):
    """Return the agent for ``agent_id`` or raise a 404 HTTPException."""
    agent = repository.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
