import pytest

from hermes_company_os.database import initialize_database
from hermes_company_os.repository import CompanyRepository
from hermes_company_os.secret_guard import secret_violations

FAKE_OPENAI_SECRET = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def test_product_wizard_stage_definitions_are_seeded_in_canonical_order(tmp_path):
    repository = initialized_repository(tmp_path)

    stages = repository.list_product_wizard_stage_definitions()

    assert [stage["id"] for stage in stages] == [
        "research",
        "prd",
        "architecture",
        "tasks",
        "code_plan",
        "acceptance",
    ]
    assert stages[0]["owner_agent_id"] == "research-agent"
    assert stages[-1]["owner_agent_id"] == "qa-critic"


def test_create_structured_project_initializes_one_ready_stage(tmp_path):
    repository = initialized_repository(tmp_path)

    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    project = repository.get_project(project_id)
    stages = repository.list_project_wizard_stages(project_id)

    assert project["status"] == "wizard_active"
    assert [stage["stage_id"] for stage in stages] == [
        "research",
        "prd",
        "architecture",
        "tasks",
        "code_plan",
        "acceptance",
    ]
    assert [stage["status"] for stage in stages] == [
        "ready",
        "waiting",
        "waiting",
        "waiting",
        "waiting",
        "waiting",
    ]
    assert repository.next_actionable_stage(project_id)["stage_id"] == "research"


def test_stage_artifacts_version_and_advance_one_stage_at_a_time(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    artifact_id = repository.save_stage_artifact_draft(
        project_id=project_id,
        stage_id="research",
        markdown_content="# Research\n\nEvidence-backed opportunity.",
        json_content={"open_questions": ["pricing"]},
    )
    repository.approve_stage(project_id, "research")

    research = repository.get_project_wizard_stage(project_id, "research")
    prd = repository.get_project_wizard_stage(project_id, "prd")
    artifact = repository.latest_project_stage_artifact(project_id, "research")

    assert artifact["id"] == artifact_id
    assert artifact["version"] == 1
    assert artifact["status"] == "approved"
    assert artifact["json"] == {"open_questions": ["pricing"]}
    assert research["status"] == "approved"
    assert prd["status"] == "ready"
    assert repository.next_actionable_stage(project_id)["stage_id"] == "prd"


def test_revision_request_allows_new_draft_version(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )
    repository.save_stage_artifact_draft(
        project_id=project_id,
        stage_id="research",
        markdown_content="# Research\n\nInitial evidence.",
        json_content={"confidence": "medium"},
    )
    repository.approve_stage(project_id, "research")

    repository.request_stage_revision(
        project_id=project_id,
        stage_id="research",
        notes="Add primary-source evidence before continuing.",
    )
    repository.save_stage_artifact_draft(
        project_id=project_id,
        stage_id="research",
        markdown_content="# Research\n\nRevised evidence.",
        json_content={"confidence": "high"},
    )

    research = repository.get_project_wizard_stage(project_id, "research")
    artifacts = repository.list_project_stage_artifacts(project_id, "research")

    assert research["status"] == "draft"
    assert research["revision_notes"] == "Add primary-source evidence before continuing."
    assert [artifact["version"] for artifact in artifacts] == [2, 1]
    assert artifacts[0]["json"] == {"confidence": "high"}
    assert artifacts[1]["status"] == "needs_revision"


def test_waiting_stage_cannot_accept_draft_until_previous_stage_approved(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    with pytest.raises(ValueError, match="waiting"):
        repository.save_stage_artifact_draft(
            project_id=project_id,
            stage_id="prd",
            markdown_content="# PRD",
            json_content={"scope": "narrow"},
        )


def test_blocked_stage_is_reported_as_next_actionable(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    repository.block_stage(project_id, "research", "Need founder answer on ICP.")

    stage = repository.next_actionable_stage(project_id)

    assert stage["stage_id"] == "research"
    assert stage["status"] == "blocked"
    assert stage["revision_notes"] == "Need founder answer on ICP."


def test_wizard_artifacts_reject_secret_like_values(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    with pytest.raises(ValueError, match="Do not paste secret values"):
        repository.save_stage_artifact_draft(
            project_id=project_id,
            stage_id="research",
            markdown_content="OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456",
            json_content={"safe": True},
        )


def test_generation_runs_track_success_and_redact_secret_shaped_errors(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    run_id = repository.create_generation_run(
        project_id=project_id,
        stage_id="research",
        generation_mode="local_fake_public_demo",
        source_artifact_ids=["research-input"],
        memory_ids=["memory-founder-preference"],
    )
    running_run = repository.get_generation_run(run_id)

    assert running_run["status"] == "running"
    assert running_run["source_artifact_ids"] == ["research-input"]
    assert running_run["memory_ids"] == ["memory-founder-preference"]
    assert running_run["artifact_id"] is None

    artifact_id = repository.save_stage_artifact_draft(
        project_id=project_id,
        stage_id="research",
        markdown_content="# Research\n\nEvidence-backed opportunity.",
        json_content={"generation_mode": "local_fake_public_demo"},
    )
    repository.complete_generation_run(
        run_id,
        artifact_id,
        source_artifact_ids=[],
        memory_ids=["memory-founder-preference", "memory-technical-standard"],
    )
    succeeded_run = repository.get_generation_run(run_id)

    assert succeeded_run["status"] == "succeeded"
    assert succeeded_run["artifact_id"] == artifact_id
    assert succeeded_run["source_artifact_ids"] == []
    assert succeeded_run["memory_ids"] == [
        "memory-founder-preference",
        "memory-technical-standard",
    ]
    assert succeeded_run["completed_at"]

    failed_run_id = repository.create_generation_run(
        project_id=project_id,
        stage_id="research",
        generation_mode="local_fake_public_demo",
    )
    repository.fail_generation_run(
        failed_run_id,
        "Provider returned pasted key " + FAKE_OPENAI_SECRET,
    )
    failed_run = repository.get_generation_run(failed_run_id)

    assert failed_run["status"] == "failed"
    assert "secret-looking content" in failed_run["error"]
    assert FAKE_OPENAI_SECRET not in failed_run["error"]
    assert secret_violations({"generation_run": str(failed_run)}) == []
    assert repository.latest_generation_run(project_id, "research")["id"] == failed_run_id


def test_legacy_project_workflow_behavior_is_unchanged(tmp_path):
    repository = initialized_repository(tmp_path)

    project_id = repository.create_project_with_workflow(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    project = repository.get_project(project_id)
    items = repository.list_project_workflow_items(project_id)
    stages = repository.list_project_wizard_stages(project_id)

    assert project["status"] == "planning"
    assert len(items) == len(repository.list_workflow_templates())
    assert stages == []
