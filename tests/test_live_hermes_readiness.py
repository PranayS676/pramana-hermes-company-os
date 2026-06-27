from hermes_company_os.database import initialize_database
from hermes_company_os.live_hermes_readiness import (
    LIVE_HERMES_DECISION_SOURCE,
    LIVE_HERMES_DECISION_TYPE,
    LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
    LIVE_HERMES_RUN_CONFIRMATION_TYPE,
    evaluate_live_hermes_readiness,
    evaluate_live_hermes_run_confirmation,
)
from hermes_company_os.repository import CompanyRepository


def initialized_repository(tmp_path) -> CompanyRepository:
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    return CompanyRepository(database_path)


def mark_agent_runtime_ready(repository: CompanyRepository, agent_id: str) -> None:
    repository.update_profile_installation_check(
        check_id=f"{agent_id}-profile-installation",
        status="verified",
        evidence="Verified in readiness test.",
    )
    preference = repository.get_model_preference(agent_id)
    repository.update_model_preference(
        agent_id=agent_id,
        provider=preference["provider"],
        model=preference["model"],
        fallback_provider=preference["fallback_provider"],
        fallback_model=preference["fallback_model"],
        auth_method=preference["auth_method"],
        status="verified",
        notes="Verified in readiness test.",
    )
    for check in repository.list_profile_acceptance_checks():
        if check["agent_id"] == agent_id:
            repository.update_profile_acceptance_check(
                check_id=check["id"],
                status="verified",
                evidence="Verified in readiness test.",
            )


def test_live_hermes_readiness_reports_runtime_and_founder_gates(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI due-diligence workspace.",
    )

    initial = evaluate_live_hermes_readiness(repository, project_id, "research")
    by_id = {check["id"]: check for check in initial.checks}

    assert initial.ready is False
    assert initial.runtime_ready is False
    assert initial.founder_approved is False
    assert by_id["profile_installation"]["status"] == "blocked"
    assert by_id["founder_approval"]["status"] == "needed"
    assert "Profile installation" in initial.blocker

    mark_agent_runtime_ready(repository, "research-agent")
    runtime_ready = evaluate_live_hermes_readiness(repository, project_id, "research")

    assert runtime_ready.runtime_ready is True
    assert runtime_ready.ready is False
    assert "Founder live-mode approval" in runtime_ready.blocker

    decision_id = repository.create_founder_decision(
        title="Approve live Hermes generation for research",
        urgency="urgent",
        decision_type=LIVE_HERMES_DECISION_TYPE,
        source=LIVE_HERMES_DECISION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id="research",
        slack_channel="#founder-command",
        telegram_policy="Telegram only if live generation blocks launch.",
        context="Approve live Hermes generation for this project stage.",
        evidence="Runtime gates are verified.",
        requires_founder_approval=True,
    )
    repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Approved for one live Hermes research generation attempt.",
        founder_confirmed=True,
    )

    approved = evaluate_live_hermes_readiness(repository, project_id, "research")

    assert approved.ready is True
    assert approved.gate.enabled is True
    assert approved.gate.founder_approved is True
    assert approved.gate.runtime_ready is True
    assert approved.to_dict()["founder_approval_decision_id"] == decision_id


def test_live_hermes_run_confirmation_is_fresh_until_next_live_run(tmp_path):
    repository = initialized_repository(tmp_path)
    project_id = repository.create_structured_project(
        name="Atlas Brief",
        founder_idea="AI due-diligence workspace.",
    )

    missing = evaluate_live_hermes_run_confirmation(repository, project_id, "research")

    assert missing.fresh is False
    assert missing.request_allowed is True
    assert "fresh founder-confirmed run token" in missing.blocker

    decision_id = repository.create_founder_decision(
        title="Confirm one live Hermes run for research",
        urgency="urgent",
        decision_type=LIVE_HERMES_RUN_CONFIRMATION_TYPE,
        source=LIVE_HERMES_RUN_CONFIRMATION_SOURCE,
        owner_agent_id="chief-of-staff",
        project_id=project_id,
        stage_id="research",
        slack_channel="#founder-command",
        telegram_policy="Telegram only if live generation blocks launch.",
        context="Confirm one live Hermes run.",
        evidence="Command preview was reviewed.",
        requires_founder_approval=True,
    )
    repository.update_founder_decision(
        decision_id,
        status="approved",
        decision="Approved for one live Hermes research run.",
        founder_confirmed=True,
    )

    fresh = evaluate_live_hermes_run_confirmation(repository, project_id, "research")

    assert fresh.fresh is True
    assert fresh.decision_id == decision_id
    assert fresh.to_dict()["fresh"] is True

    run_id = repository.create_generation_run(
        project_id=project_id,
        stage_id="research",
        generation_mode="live_hermes",
    )
    repository.fail_generation_run(run_id, "Simulated live run failure.")
    consumed = evaluate_live_hermes_run_confirmation(repository, project_id, "research")

    assert consumed.fresh is False
    assert consumed.decision_id == decision_id
    assert consumed.latest_live_run_id == run_id
    assert consumed.request_allowed is True
