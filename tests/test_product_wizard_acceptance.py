from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.kanban_client import KanbanResult
from hermes_company_os.main import create_app
from hermes_company_os.settings import Settings

PROJECT_INTAKE = {
    "wizard_version": "product-wizard-v1",
    "name": "Atlas Brief",
    "product_category": "saas",
    "founder_idea": "AI due-diligence workspace for acquisition teams.",
    "target_audience": "Corporate development teams reviewing small acquisitions.",
    "current_alternative": "Shared docs, spreadsheets, and ad hoc chat threads.",
    "problem_statement": "Teams lose the thread across diligence notes, risks, and asks.",
    "desired_outcome": "A reviewed risk brief with assigned follow-up questions.",
    "launch_tier": "t0_internal",
    "deadline_pressure": "normal",
    "constraints": "Use mock data only; no live customer files in the public demo.",
    "non_goals": "Do not build an enterprise data-room connector in V1.",
    "success_metrics": "Reduce first-pass diligence synthesis time by 40 percent.",
}

WIZARD_STAGE_IDS = ["research", "prd", "architecture", "tasks", "code_plan", "acceptance"]


class FakeKanbanClient:
    def __init__(self) -> None:
        self.created_tasks: list[dict] = []

    def diagnostics(self) -> KanbanResult:
        return KanbanResult(ok=True, output='{"ok": true}')

    def create_task(self, task: dict) -> KanbanResult:
        self.created_tasks.append(task)
        task_id = f"kb_{len(self.created_tasks)}"
        return KanbanResult(ok=True, output=f'{{"id": "{task_id}"}}', task_id=task_id)


def app_client_and_kanban(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    kanban_client = FakeKanbanClient()
    app.state.kanban_client = kanban_client
    return app, TestClient(app), kanban_client


def create_project(client: TestClient) -> str:
    response = client.post("/projects", data=PROJECT_INTAKE, follow_redirects=False)
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def generate_current_stage(app, client: TestClient, project_id: str) -> str:
    current = app.state.repository.next_actionable_stage(project_id)
    assert current is not None
    stage_id = current["stage_id"]
    response = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    artifact = app.state.repository.latest_project_stage_artifact(project_id, stage_id)
    assert artifact is not None
    assert artifact["status"] == "draft"
    assert artifact["version"] >= 1
    return stage_id


def approve_stage(app, client: TestClient, project_id: str, stage_id: str) -> None:
    response = client.post(
        f"/projects/{project_id}/stages/{stage_id}/approve",
        data={"approval_note": f"Approved {stage_id} in acceptance test."},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    stage = app.state.repository.get_project_wizard_stage(project_id, stage_id)
    assert stage["status"] == "approved"


def generate_and_approve_current_stage(app, client: TestClient, project_id: str) -> str:
    stage_id = generate_current_stage(app, client, project_id)
    approve_stage(app, client, project_id, stage_id)
    return stage_id


def mark_kanban_verified(repository) -> None:
    for check in repository.list_kanban_checks():
        repository.update_kanban_check(
            check_id=check["id"],
            status="verified",
            evidence="Verified before product wizard acceptance test.",
        )


def approve_until_stage(
    app,
    client: TestClient,
    project_id: str,
    target_stage_id: str,
) -> list[str]:
    approved_stage_ids = []
    for _ in range(len(WIZARD_STAGE_IDS)):
        approved_stage_id = generate_and_approve_current_stage(app, client, project_id)
        approved_stage_ids.append(approved_stage_id)
        if approved_stage_id == target_stage_id:
            return approved_stage_ids
    pytest.fail(f"Did not reach stage {target_stage_id}; approved {approved_stage_ids}")


def test_project_detail_initial_timeline_exposes_only_first_actionable_stage(tmp_path):
    app, client, _ = app_client_and_kanban(tmp_path)
    project_id = create_project(client)

    detail = client.get(f"/projects/{project_id}")
    stages = app.state.repository.list_project_wizard_stages(project_id)

    assert detail.status_code == 200
    assert [stage["stage_id"] for stage in stages] == WIZARD_STAGE_IDS
    assert app.state.repository.next_actionable_stage(project_id)["stage_id"] == "research"
    assert "Product wizard timeline" in detail.text
    for stage in stages:
        assert f'data-stage-id="{stage["stage_id"]}"' in detail.text
    assert detail.text.count(f"/projects/{project_id}/stages/current/generate") == 1
    assert f"/projects/{project_id}/stages/research/approve" not in detail.text
    assert f"/projects/{project_id}/stages/prd/generate" not in detail.text


def test_generate_then_approve_stage_saves_draft_and_unlocks_next_stage(tmp_path):
    app, client, _ = app_client_and_kanban(tmp_path)
    project_id = create_project(client)

    first_stage_id = generate_current_stage(app, client, project_id)
    first_artifact = app.state.repository.latest_project_stage_artifact(project_id, first_stage_id)

    assert first_stage_id == "research"
    assert first_artifact["status"] == "draft"
    assert first_artifact["version"] == 1
    assert "Opportunity Research" in first_artifact["markdown_content"]

    approve_stage(app, client, project_id, first_stage_id)
    research = app.state.repository.get_project_wizard_stage(project_id, "research")
    prd = app.state.repository.get_project_wizard_stage(project_id, "prd")

    assert research["status"] == "approved"
    assert prd["status"] == "ready"
    assert app.state.repository.next_actionable_stage(project_id)["stage_id"] == "prd"


def test_revision_and_regenerate_preserve_prior_artifact_history(tmp_path):
    app, client, _ = app_client_and_kanban(tmp_path)
    project_id = create_project(client)
    stage_id = generate_current_stage(app, client, project_id)

    revision = client.post(
        f"/projects/{project_id}/stages/{stage_id}/revision",
        data={
            "revision_reason": "evidence_gap",
            "revision_request": "Tighten the target-customer evidence.",
        },
        follow_redirects=False,
    )
    assert revision.status_code == 303, revision.text

    regenerate = client.post(
        f"/projects/{project_id}/stages/{stage_id}/regenerate",
        data={"revision_request": "Tighten the target-customer evidence."},
        follow_redirects=False,
    )
    assert regenerate.status_code == 303, regenerate.text

    artifacts = app.state.repository.list_project_stage_artifacts(project_id, stage_id)
    assert [artifact["version"] for artifact in artifacts] == [2, 1]
    assert artifacts[0]["status"] == "draft"
    assert artifacts[1]["status"] == "needs_revision"
    revision_notes = app.state.repository.get_project_wizard_stage(
        project_id,
        stage_id,
    )["revision_notes"]
    assert "Evidence gap" in revision_notes
    assert "Tighten the target-customer evidence." in revision_notes
    assert json.dumps(artifacts[0], sort_keys=True) != json.dumps(artifacts[1], sort_keys=True)

    detail = client.get(f"/projects/{project_id}")
    assert "Artifact history" in detail.text
    assert "Version 1" in detail.text
    assert "Version 2" in detail.text
    assert f"?artifact_id={artifacts[1]['id']}#artifact-preview" in detail.text

    selected = client.get(f"/projects/{project_id}?artifact_id={artifacts[1]['id']}")
    assert selected.status_code == 200
    assert "selected version" in selected.text
    assert "History inspection mode" in selected.text
    assert "Return to latest review" in selected.text
    assert "Version 1 - needs_revision" in selected.text


def test_happy_path_reaches_acceptance_checklist_one_stage_at_a_time(tmp_path):
    app, client, _ = app_client_and_kanban(tmp_path)
    project_id = create_project(client)
    approved_stage_ids = approve_until_stage(app, client, project_id, "code_plan")

    detail = client.get(f"/projects/{project_id}")
    acceptance = app.state.repository.get_project_wizard_stage(project_id, "acceptance")

    assert approved_stage_ids == ["research", "prd", "architecture", "tasks", "code_plan"]
    assert acceptance["status"] == "ready"
    assert app.state.repository.next_actionable_stage(project_id)["stage_id"] == "acceptance"
    assert detail.status_code == 200
    assert "Acceptance checklist" in detail.text
    assert 'data-stage-id="acceptance"' in detail.text
    assert detail.text.count(f"/projects/{project_id}/stages/current/generate") == 1


def test_project_kanban_push_waits_for_tasks_stage_even_when_kanban_verified(tmp_path):
    app, client, kanban_client = app_client_and_kanban(tmp_path)
    mark_kanban_verified(app.state.repository)
    project_id = create_project(client)

    blocked = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)

    assert blocked.status_code == 409
    assert "tasks" in blocked.text.lower()
    assert "approval" in blocked.text.lower()
    assert kanban_client.created_tasks == []

    approved_stage_ids = approve_until_stage(app, client, project_id, "tasks")
    allowed = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)

    assert approved_stage_ids[-1] == "tasks"
    assert allowed.status_code == 303, allowed.text
    assert kanban_client.created_tasks
