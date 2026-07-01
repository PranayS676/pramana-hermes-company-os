from __future__ import annotations

from fastapi.testclient import TestClient

from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

STRUCTURED_INTAKE = {
    "wizard_version": "product-wizard-v1",
    "name": "Accessible Atlas",
    "product_category": "saas",
    "founder_idea": "AI due-diligence workspace for acquisition teams.",
    "target_audience": "Corporate development teams.",
    "current_alternative": "Shared docs and ad hoc chat threads.",
    "problem_statement": "Teams lose the thread across diligence notes.",
    "desired_outcome": "A reviewed risk brief with assigned questions.",
    "launch_tier": "t0_internal",
    "deadline_pressure": "normal",
    "constraints": "Use mock data only.",
    "non_goals": "Do not build a data-room connector in V1.",
    "success_metrics": "Reduce first-pass synthesis time by 40 percent.",
}


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


def test_product_wizard_steps_are_semantic_and_keyboard_ready(tmp_path):
    _, client = app_and_client(tmp_path)

    response = client.get("/projects/new")

    assert response.status_code == 200
    assert 'role="tablist"' in response.text
    assert 'aria-orientation="vertical"' in response.text
    for step in ("basics", "audience", "constraints", "review"):
        assert f'id="wizard-tab-{step}"' in response.text
        assert 'role="tab"' in response.text
        assert f'aria-controls="wizard-panel-{step}"' in response.text
        assert f'id="wizard-panel-{step}"' in response.text
        assert f'aria-labelledby="wizard-tab-{step}"' in response.text
    assert 'aria-current="step"' in response.text
    assert 'id="wizard-step-status"' in response.text
    assert 'aria-live="polite"' in response.text
    assert "ArrowDown" in response.text
    assert "focusTarget" in response.text
    assert secret_violations({"project_new": response.text}) == []


def test_disabled_project_gates_have_reachable_reasons(tmp_path):
    _, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    assert 'id="kanban-gate-reason"' in response.text
    assert 'aria-describedby="kanban-gate-reason"' in response.text
    assert response.text.index('id="kanban-gate-reason"') < response.text.index(
        'aria-describedby="kanban-gate-reason"'
    )
    assert 'id="codex-gate-reason"' in response.text
    assert 'aria-describedby="codex-gate-reason"' in response.text
    assert response.text.index('id="codex-gate-reason"') < response.text.index(
        'aria-describedby="codex-gate-reason"'
    )
    assert "approved code plan, approved acceptance package" in response.text


def test_setup_repeated_rows_have_accessible_control_names(tmp_path):
    _, client = app_and_client(tmp_path)

    # Setup is split into section pages; each repeated-row control lives on the
    # page that owns that section.
    section_fragments = {
        "/setup/profiles": [
            "Installation status for",
            "Installation evidence for",
            "Save installation status for",
            "Acceptance status for",
            "Acceptance evidence for",
            "Save acceptance status for",
            'aria-describedby="profile-smoke-blocker-',
        ],
        "/setup/messaging": [
            "Messaging status for",
            "Messaging evidence for",
            "Save messaging verification for",
            "Secret requirement status for",
            "Secret requirement notes for",
            "Save secret requirement status for",
        ],
        "/setup/verification": [
            "Schedule verification status for",
            "Schedule verification evidence for",
            "Save schedule verification for",
            "Kanban verification status for",
            "Kanban verification evidence for",
            "Save Kanban verification for",
        ],
        "/setup/integrations": [
            "Integration status for",
            "Save integration status for",
        ],
    }
    for path, fragments in section_fragments.items():
        response = client.get(path)
        assert response.status_code == 200, path
        for fragment in fragments:
            assert fragment in response.text, f"{fragment!r} missing from {path}"


def test_status_labels_are_not_color_only_on_decision_project_and_queue_pages(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    app.state.repository.create_agent_work_item(
        title="Review accessibility baseline",
        owner_agent_id="qa-critic",
        status="blocked",
        priority="urgent",
        project_id=project_id,
        summary="Accessibility review cannot proceed until blocker copy is visible.",
        blocked_reason="Missing visible blocker copy near a disabled action.",
        blocked_owner="Frontend Engineer",
    )

    client.post(f"/projects/{project_id}/stages/current/generate", follow_redirects=False)
    decisions = client.get(f"/decisions?project_id={project_id}")
    project = client.get(f"/projects/{project_id}")
    queue = client.get(f"/queue?project_id={project_id}")
    dashboard = client.get("/")

    assert 'aria-label="Decision status:' in decisions.text
    assert 'aria-label="Artifact status:' in project.text
    assert 'aria-label="Queue state:' in queue.text
    assert 'aria-label="Decision status:' in dashboard.text
    assert "Blocked" in queue.text
    assert "Missing visible blocker copy" in queue.text
    assert secret_violations(
        {
            "decisions": decisions.text,
            "project": project.text,
            "queue": queue.text,
            "dashboard": dashboard.text,
        }
    ) == []


def test_long_generated_text_has_rendering_and_css_overflow_safeguards(tmp_path):
    app, client = app_and_client(tmp_path)
    project_id = create_structured_project(client)
    long_token = "evidence_" + ("verylongsegment" * 20)
    long_body = (
        "# Research\n\n"
        "## Evidence\n\n"
        f"{long_token}\n\n"
        "- Long generated finding with enough prose to force wrapping.\n"
        "- Another finding that should remain readable near the approval controls."
    )
    app.state.repository.save_stage_artifact_draft(
        project_id=project_id,
        stage_id="research",
        markdown_content=long_body,
        json_content={"title": "Long Accessibility Research", "checks": []},
        owner_agent_id="research-agent",
    )

    project = client.get(f"/projects/{project_id}")
    css = client.get("/static/styles.css")

    assert project.status_code == 200
    assert long_token in project.text
    assert 'id="artifact-preview"' in project.text
    assert 'aria-describedby="artifact-status-summary"' in project.text
    assert css.status_code == 200
    assert "overflow-wrap: anywhere" in css.text
    assert "white-space: pre-wrap" in css.text
    assert "overflow-x: hidden" in css.text
    assert "@media (prefers-reduced-motion: reduce)" in css.text
    assert "@media (max-width: 560px)" in css.text
    assert secret_violations({"project": project.text, "css": css.text}) == []
