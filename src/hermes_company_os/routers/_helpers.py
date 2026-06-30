from __future__ import annotations

from fastapi import HTTPException


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
