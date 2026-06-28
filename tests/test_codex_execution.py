from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hermes_company_os.codex_execution import (
    CODEX_EXECUTION_DECISION_SOURCE,
    CODEX_EXECUTION_DECISION_TYPE,
)
from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

STRUCTURED_INTAKE = {
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


def app_and_client(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    return app, TestClient(app)


def create_structured_project(client: TestClient) -> str:
    response = client.post(
        "/projects",
        data=STRUCTURED_INTAKE,
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return response.headers["location"].rsplit("/", 1)[-1]


def generate_and_approve_current_stage(app, client: TestClient, project_id: str) -> str:
    current = app.state.repository.next_actionable_stage(project_id)
    assert current is not None
    stage_id = current["stage_id"]
    generated = client.post(
        f"/projects/{project_id}/stages/current/generate",
        follow_redirects=False,
    )
    assert generated.status_code == 303, generated.text
    approved = client.post(
        f"/projects/{project_id}/stages/{stage_id}/approve",
        data={"approval_note": f"Approve {stage_id} for Codex execution test."},
        follow_redirects=False,
    )
    assert approved.status_code == 303, approved.text
    return stage_id


def approve_until_stage(
    app,
    client: TestClient,
    project_id: str,
    target_stage_id: str,
) -> list[str]:
    approved = []
    for _ in range(len(WIZARD_STAGE_IDS)):
        stage_id = generate_and_approve_current_stage(app, client, project_id)
        approved.append(stage_id)
        if stage_id == target_stage_id:
            return approved
    pytest.fail(f"Did not reach {target_stage_id}; approved {approved}")


def test_codex_execution_package_locked_until_plan_and_acceptance_are_approved(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    json_response = client.get(f"/projects/{project_id}/codex-execution.json")
    markdown_response = client.get(f"/projects/{project_id}/codex-execution.md")
    project_page = client.get(f"/projects/{project_id}")
    payload = json_response.json()

    assert json_response.status_code == 200
    assert payload["schema"] == "codex_project_execution_package_v1"
    assert payload["execution"]["external_execution_enabled"] is False
    assert payload["execution"]["ready_for_founder_approval"] is False
    assert payload["execution"]["ready_for_execution"] is False
    assert payload["approval_gates"]["code_plan"]["status"] == "missing"
    assert payload["approval_gates"]["acceptance"]["status"] == "missing"
    assert "code_plan" in payload["missing_gates"]
    assert "acceptance" in payload["missing_gates"]
    assert payload["branch_plan"]["branch_name"] == (
        "codex/atlas-brief/implementation-v1"
    )
    assert payload["branch_plan"]["create_branch"] is False
    assert payload["branch_plan"]["create_worktree"] is False
    assert markdown_response.status_code == 200
    assert "No branch or worktree is created by this export." in markdown_response.text
    assert project_page.status_code == 200
    assert "Codex package locked" in project_page.text
    assert "Codex package JSON" in project_page.text
    assert "Request Codex execution approval" not in project_page.text
    assert secret_violations(
        {
            "codex_execution_json": json.dumps(payload, sort_keys=True),
            "codex_execution_markdown": markdown_response.text,
            "project_page": project_page.text,
        }
    ) == []


def test_codex_execution_package_requests_founder_approval_once_after_acceptance(
    tmp_path,
):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    approved_stage_ids = approve_until_stage(app, client, project_id, "acceptance")
    json_response = client.get(f"/projects/{project_id}/codex-execution.json")
    markdown_response = client.get(f"/projects/{project_id}/codex-execution.md")
    project_page = client.get(f"/projects/{project_id}")
    payload = json_response.json()
    acceptance = app.state.repository.latest_project_stage_artifact(
        project_id,
        "acceptance",
    )

    assert approved_stage_ids == WIZARD_STAGE_IDS
    assert json_response.status_code == 200
    assert payload["execution"]["ready_for_founder_approval"] is True
    assert payload["execution"]["approval_request_allowed"] is True
    assert payload["execution"]["ready_for_execution"] is False
    assert payload["approval_gates"]["code_plan"]["status"] == "approved"
    assert payload["approval_gates"]["acceptance"]["status"] == "approved"
    assert payload["approval_gates"]["founder_execution_approval"]["status"] == (
        "requestable"
    )
    assert payload["source_artifacts"][0]["stage_id"] == "code_plan"
    assert payload["source_artifacts"][1]["stage_id"] == "acceptance"
    assert payload["workstreams"][0]["owner_agent_id"] == "backend-engineer"
    assert payload["workstreams"][1]["owner_agent_id"] == "frontend-engineer"
    assert payload["workstreams"][2]["owner_agent_id"] == "cloud-infra-agent"
    assert payload["workstreams"][3]["owner_agent_id"] == "qa-critic"
    assert payload["command_preview"][0]["command"] == (
        "git switch -c codex/atlas-brief/implementation-v1"
    )
    assert all(command["runs_automatically"] is False for command in payload["command_preview"])
    assert markdown_response.status_code == 200
    assert "Codex Project Execution Package" in markdown_response.text
    assert "codex/atlas-brief/implementation-v1" in markdown_response.text
    assert "py -3.11 -m poetry run pytest" in markdown_response.text
    assert project_page.status_code == 200
    assert "Codex package is ready for founder approval" in project_page.text
    assert "Request Codex execution approval" in project_page.text

    first = client.post(
        f"/projects/{project_id}/codex-execution-approval",
        follow_redirects=False,
    )
    second = client.post(
        f"/projects/{project_id}/codex-execution-approval",
        follow_redirects=False,
    )
    decisions = app.state.repository.list_founder_decisions(
        project_id=project_id,
        stage_id="acceptance",
        decision_type=CODEX_EXECUTION_DECISION_TYPE,
        include_resolved=False,
    )
    codex_decisions = [
        decision
        for decision in decisions
        if decision["source"] == CODEX_EXECUTION_DECISION_SOURCE
    ]
    updated_payload = client.get(f"/projects/{project_id}/codex-execution.json").json()
    updated_page = client.get(f"/projects/{project_id}")

    assert first.status_code == 303
    assert second.status_code == 303
    assert len(codex_decisions) == 1
    assert codex_decisions[0]["requires_founder_approval"] == 1
    assert codex_decisions[0]["status"] == "needed"
    assert codex_decisions[0]["artifact_id"] == acceptance["id"]
    assert "does not create branches" in codex_decisions[0]["context"]
    assert updated_payload["execution"]["approval_request_open"] is True
    assert updated_payload["execution"]["approval_request_allowed"] is False
    assert updated_payload["execution"]["decision_id"] == codex_decisions[0]["id"]
    assert updated_page.status_code == 200
    assert "Open Codex execution approval" in updated_page.text
    assert codex_decisions[0]["id"] in updated_page.text
    assert secret_violations(
        {
            "codex_execution_json": json.dumps(updated_payload, sort_keys=True),
            "codex_execution_markdown": markdown_response.text,
            "project_page": updated_page.text,
            "decision": json.dumps(codex_decisions[0], sort_keys=True),
        }
    ) == []


def test_codex_execution_runner_queue_requires_approved_founder_decision(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    approve_until_stage(app, client, project_id, "acceptance")

    response = client.post(
        f"/projects/{project_id}/codex-execution-run",
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Founder approval is required" in response.json()["detail"]
    assert app.state.repository.list_codex_execution_runs(project_id) == []


def test_codex_execution_runner_consumes_approval_into_source_only_audit(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    approve_until_stage(app, client, project_id, "acceptance")
    client.post(
        f"/projects/{project_id}/codex-execution-approval",
        follow_redirects=False,
    )
    decision = next(
        item
        for item in app.state.repository.list_founder_decisions(
            project_id=project_id,
            stage_id="acceptance",
            decision_type=CODEX_EXECUTION_DECISION_TYPE,
        )
        if item["source"] == CODEX_EXECUTION_DECISION_SOURCE
    )
    app.state.repository.update_founder_decision(
        decision["id"],
        status="approved",
        decision="Founder approves queuing the source-only Codex runner.",
        founder_confirmed=True,
    )

    response = client.post(
        f"/projects/{project_id}/codex-execution-run",
        follow_redirects=False,
    )
    second_response = client.post(
        f"/projects/{project_id}/codex-execution-run",
        follow_redirects=False,
    )
    runs = app.state.repository.list_codex_execution_runs(project_id)
    package = client.get(f"/projects/{project_id}/codex-execution.json").json()
    project_page = client.get(f"/projects/{project_id}")
    run = runs[0]
    audit = run["audit"]

    assert response.status_code == 303
    assert second_response.status_code == 409
    assert "already queued" in second_response.json()["detail"]
    assert len(runs) == 1
    assert run["status"] == "queued"
    assert run["runner_mode"] == "source_only_disabled"
    assert run["external_execution_enabled"] is False
    assert run["decision_id"] == decision["id"]
    assert run["branch_name"] == "codex/atlas-brief/implementation-v1"
    assert run["source_artifact_ids"]
    assert run["command_preview"][0]["command"] == (
        "git switch -c codex/atlas-brief/implementation-v1"
    )
    assert audit["schema"] == "codex_execution_run_audit_v1"
    assert audit["immutable"] is True
    assert audit["run_id"] == run["id"]
    assert audit["approval_consumption"]["decision_id"] == decision["id"]
    assert audit["approval_consumption"]["status"] == "consumed"
    assert audit["approval_consumption"]["consumed_by_run_id"] == run["id"]
    assert audit["package_fingerprint"]["sha256"]
    assert audit["command_fingerprints"][0]["sha256"]
    assert package["runner"]["latest_run"]["id"] == run["id"]
    assert package["runner"]["latest_run"]["status"] == "queued"
    assert package["runner"]["queue_open"] is True
    assert package["runner"]["queue_request_allowed"] is False
    assert project_page.status_code == 200
    assert "Codex runner queued" in project_page.text
    assert "Approval consumed" in project_page.text
    assert run["id"] in project_page.text
    assert "External execution disabled" in project_page.text
    assert secret_violations(
        {
            "codex_execution_package": json.dumps(package, sort_keys=True),
            "codex_execution_run": json.dumps(run, sort_keys=True),
            "project_page": project_page.text,
        }
    ) == []
