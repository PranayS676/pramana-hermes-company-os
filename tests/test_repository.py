from hermes_company_os.database import initialize_database
from hermes_company_os.profile_doctrine import PROFILE_DOCTRINES
from hermes_company_os.repository import CompanyRepository

EXPECTED_ACCEPTANCE_CASES = sum(
    len(doctrine["acceptance_cases"]) for doctrine in PROFILE_DOCTRINES.values()
)


def test_database_seeds_profiles_and_standups(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)

    repository = CompanyRepository(database_path)

    agents = repository.list_agents()
    schedules = repository.list_schedules()

    assert {agent["id"] for agent in agents} == {
        "chief-of-staff",
        "product-manager",
        "research-agent",
        "engineering-manager",
        "backend-engineer",
        "frontend-engineer",
        "cloud-infra-agent",
        "test-automation-agent",
        "marketing-agent",
        "qa-critic",
    }
    by_id = {agent["id"]: agent for agent in agents}
    assert "Protect Pranay's attention" in by_id["chief-of-staff"]["soul"]
    assert "React frontend architecture" in by_id["frontend-engineer"]["capabilities"]
    assert "launch-readiness critique" in by_id["qa-critic"]["capabilities"]
    assert [(schedule["hour"], schedule["minute"]) for schedule in schedules] == [(9, 0), (15, 0)]


def test_update_agent_profile_changes_starter_values(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_agent_profile(
        agent_id="engineering-manager",
        description="Designs ambitious but testable systems.",
        soul="Think big, prove every tradeoff, and protect delivery quality.",
        capabilities=["distributed architecture", "aws planning", "test strategy"],
    )

    agent = repository.get_agent("engineering-manager")
    assert agent["description"] == "Designs ambitious but testable systems."
    assert agent["soul"] == "Think big, prove every tradeoff, and protect delivery quality."
    assert agent["capabilities"] == [
        "distributed architecture",
        "aws planning",
        "test strategy",
    ]


def test_update_agent_routing_changes_runtime_values(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_agent_routing(
        agent_id="research-agent",
        slack_channel="#deep-research",
        telegram_policy="Telegram only for founder-blocking evidence gaps",
        hermes_command="research-director",
    )

    agent = repository.get_agent("research-agent")
    assert agent["slack_channel"] == "#deep-research"
    assert agent["telegram_policy"] == "Telegram only for founder-blocking evidence gaps"
    assert agent["hermes_command"] == "research-director"


def test_database_seeds_agent_relationships(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    relationships = repository.list_agent_relationships()

    assert [item["member_agent_id"] for item in relationships] == [
        "backend-engineer",
        "frontend-engineer",
        "cloud-infra-agent",
        "test-automation-agent",
    ]
    assert all(item["manager_agent_id"] == "engineering-manager" for item in relationships)
    assert relationships[0]["manager_name"] == "Engineering Manager"
    assert relationships[0]["member_name"] == "Backend Engineer"


def test_update_schedule_changes_standup_settings(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_schedule(
        schedule_id="afternoon-standup",
        name="Late founder sync",
        hour=18,
        minute=30,
        timezone="America/New_York",
        slack_channel="#agent-standup",
        telegram_policy="urgent only",
        active=False,
    )

    schedule = repository.get_schedule("afternoon-standup")
    assert schedule["name"] == "Late founder sync"
    assert schedule["hour"] == 18
    assert schedule["minute"] == 30
    assert schedule["telegram_policy"] == "urgent only"
    assert schedule["active"] == 0


def test_database_seeds_integrations_and_setup_steps(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)

    repository = CompanyRepository(database_path)

    integrations = repository.list_integrations()
    setup_steps = repository.list_setup_steps()

    assert {integration["id"] for integration in integrations} >= {
        "llm-provider",
        "telegram-founder-alerts",
        "hermes-kanban",
        "standup-cron",
    }
    assert any(
        "bot token starting with xoxb-" in item for item in integrations[1]["required_inputs"]
    )
    assert [step["id"] for step in setup_steps][:2] == ["install-hermes", "create-profiles"]


def test_database_seeds_setup_inputs(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    setup_inputs = repository.list_setup_inputs()
    keys = {item["key"] for item in setup_inputs}

    assert "founder_slack_member_id" in keys
    assert "slack_bot_user_id_chief_of_staff" in keys
    assert "slack_bot_user_id_engineering_manager" in keys
    assert "founder_telegram_user_id" in keys
    assert "llm_provider" in keys
    assert repository.setup_input_completion()["ready"] is False


def test_model_preferences_seeded_for_profiles(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    preferences = repository.list_model_preferences()

    assert {preference["agent_id"] for preference in preferences} == {
        "chief-of-staff",
        "product-manager",
        "research-agent",
        "engineering-manager",
        "backend-engineer",
        "frontend-engineer",
        "cloud-infra-agent",
        "test-automation-agent",
        "marketing-agent",
        "qa-critic",
    }
    assert all(preference["provider"] == "openai-codex" for preference in preferences)
    assert all(preference["model"] == "gpt-5-codex" for preference in preferences)


def test_secret_requirements_seeded_without_values(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    requirements = repository.list_secret_requirements()

    assert {item["category"] for item in requirements} == {"slack", "telegram", "llm"}
    assert any(item["environment_key"] == "SLACK_BOT_TOKEN" for item in requirements)
    assert any(item["environment_key"] == "TELEGRAM_BOT_TOKEN" for item in requirements)
    assert all("REPLACE" not in item["notes"] for item in requirements)
    assert all("sk-" not in item["notes"] for item in requirements)


def test_messaging_checks_seeded_for_profiles(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    checks = repository.list_messaging_checks()

    assert len(checks) == 31
    assert {item["platform"] for item in checks} == {"slack", "telegram"}
    assert any(item["id"] == "chief-of-staff-telegram-urgent-alert" for item in checks)
    assert all(item["status"] == "needed" for item in checks)
    assert repository.messaging_platform_verified("slack") is False


def test_schedule_checks_seeded_for_standups(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    checks = repository.list_schedule_checks()

    assert len(checks) == 4
    assert {item["schedule_id"] for item in checks} == {
        "morning-standup",
        "afternoon-standup",
    }
    assert {item["check_type"] for item in checks} == {"manual_run", "cron_installed"}
    assert repository.active_schedule_verification_ready() is False


def test_kanban_checks_seeded_for_board_verification(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    checks = repository.list_kanban_checks()

    assert [item["id"] for item in checks] == [
        "kanban-board-initialized",
        "kanban-diagnostics-pass",
        "kanban-task-create",
    ]
    assert all(item["status"] == "needed" for item in checks)
    assert repository.kanban_verification_ready() is False


def test_profile_acceptance_checks_seeded_for_role_quality(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    checks = repository.list_profile_acceptance_checks()

    assert len(checks) == EXPECTED_ACCEPTANCE_CASES
    assert checks[0]["id"] == "chief-of-staff-acceptance-1"
    assert checks[0]["agent_name"] == "Chief of Staff"
    assert any(item["id"] == "engineering-manager-acceptance-1" for item in checks)
    assert all(item["status"] == "needed" for item in checks)
    assert repository.profile_acceptance_verified() is False


def test_profile_installation_checks_seeded_for_profile_runtime(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    checks = repository.list_profile_installation_checks()

    assert len(checks) == 10
    assert checks[0]["id"] == "chief-of-staff-profile-installation"
    assert checks[0]["agent_name"] == "Chief of Staff"
    assert any(item["id"] == "engineering-manager-profile-installation" for item in checks)
    assert all(item["status"] == "needed" for item in checks)
    assert repository.profile_installation_verified() is False
    assert repository.agent_profile_installation_verified("chief-of-staff") is False


def test_founder_decisions_seeded_for_steering_queue(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    decisions = repository.list_founder_decisions()

    assert [item["id"] for item in decisions] == [
        "decision-first-idea-start",
        "decision-company-operating-model",
    ]
    assert decisions[0]["urgency"] == "urgent"
    assert decisions[0]["owner_name"] == "Chief of Staff"
    assert all(item["status"] == "needed" for item in decisions)
    assert repository.founder_decision_queue_ready() is False


def test_create_and_update_founder_decision_tracks_resolution(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    decision_id = repository.create_founder_decision(
        title="Approve research direction",
        urgency="routine",
        source="manual",
        owner_agent_id="research-agent",
        slack_channel="#decisions",
        telegram_policy="Slack first.",
        context="Choose whether to research healthcare or legal AI first.",
    )
    repository.update_founder_decision(
        decision_id=decision_id,
        status="approved",
        decision="Start with legal AI research.",
    )

    decision = repository.get_founder_decision(decision_id)
    assert decision["status"] == "approved"
    assert decision["decision"] == "Start with legal AI research."
    assert decision["owner_name"] == "Research Agent"


def test_update_secret_requirement_status(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_secret_requirement(
        requirement_id="chief-of-staff-slack-bot-token",
        status="loaded",
        notes="Loaded in profile .env.",
    )

    requirement = repository.get_secret_requirement("chief-of-staff-slack-bot-token")
    assert requirement["status"] == "loaded"
    assert requirement["notes"] == "Loaded in profile .env."


def test_update_agent_secret_requirements_changes_matching_category(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_agent_secret_requirements(
        agent_id="research-agent",
        category="llm",
        status="verified",
        notes="Smoke check passed.",
    )

    requirements = repository.list_secret_requirements()
    research_llm = next(
        item
        for item in requirements
        if item["owner_agent_id"] == "research-agent" and item["category"] == "llm"
    )
    research_slack = next(
        item
        for item in requirements
        if item["owner_agent_id"] == "research-agent" and item["category"] == "slack"
    )
    assert research_llm["status"] == "verified"
    assert research_llm["notes"] == "Smoke check passed."
    assert research_slack["status"] == "needed"


def test_update_messaging_check_tracks_non_secret_evidence(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_messaging_check(
        check_id="research-agent-slack-dm",
        status="verified",
        evidence="Reply observed in founder DM at 9:12 AM.",
    )

    check = repository.get_messaging_check("research-agent-slack-dm")
    assert check["status"] == "verified"
    assert check["evidence"] == "Reply observed in founder DM at 9:12 AM."
    assert check["owner_name"] == "Research Agent"


def test_update_schedule_check_tracks_non_secret_evidence(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_schedule_check(
        check_id="morning-standup-manual-run",
        status="verified",
        evidence="Manual standup run posted summary to Slack.",
    )

    check = repository.get_schedule_check("morning-standup-manual-run")
    assert check["status"] == "verified"
    assert check["evidence"] == "Manual standup run posted summary to Slack."
    assert check["schedule_name"] == "Morning Standup"


def test_update_kanban_check_tracks_non_secret_evidence(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_kanban_check(
        check_id="kanban-board-initialized",
        status="verified",
        evidence="Initialized with hermes kanban init.",
    )

    check = repository.get_kanban_check("kanban-board-initialized")
    assert check["status"] == "verified"
    assert check["evidence"] == "Initialized with hermes kanban init."


def test_update_profile_acceptance_check_tracks_non_secret_evidence(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_profile_acceptance_check(
        check_id="engineering-manager-acceptance-1",
        status="failed",
        evidence="Response missed integration test coverage.",
    )

    check = repository.get_profile_acceptance_check("engineering-manager-acceptance-1")
    assert check["status"] == "failed"
    assert check["evidence"] == "Response missed integration test coverage."
    assert check["agent_name"] == "Engineering Manager"


def test_update_profile_installation_check_tracks_non_secret_evidence(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_profile_installation_check(
        check_id="engineering-manager-profile-installation",
        status="verified",
        evidence="Profile directory and command alias verified locally.",
    )

    check = repository.get_profile_installation_check(
        "engineering-manager-profile-installation"
    )
    assert check["status"] == "verified"
    assert check["evidence"] == "Profile directory and command alias verified locally."
    assert check["agent_name"] == "Engineering Manager"
    assert repository.agent_profile_installation_verified("engineering-manager") is True


def test_update_model_preference(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_model_preference(
        agent_id="research-agent",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        fallback_provider="openai-codex",
        fallback_model="gpt-5-codex",
        auth_method="profile_env",
        status="needs_secret",
        notes="Use for broad market research.",
    )

    preference = repository.get_model_preference("research-agent")
    assert preference["provider"] == "openrouter"
    assert preference["fallback_model"] == "gpt-5-codex"
    assert preference["status"] == "needs_secret"


def test_latest_runs_by_type_returns_newest_per_agent(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    first = repository.create_run("research-agent", "profile-smoke", "first")
    repository.complete_run(first, output="first output")
    second = repository.create_run("research-agent", "profile-smoke", "second")
    repository.complete_run(second, output="second output")
    other = repository.create_run("product-manager", "profile-smoke", "product")
    repository.complete_run(other, output="product output")

    latest = repository.latest_runs_by_type("profile-smoke")

    assert latest["research-agent"]["id"] == second
    assert latest["research-agent"]["output"] == "second output"
    assert latest["product-manager"]["id"] == other


def test_update_setup_inputs(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_setup_inputs(
        {
            "founder_name": "Masad",
            "founder_slack_member_id": "U123",
            "unknown": "ignored",
        }
    )

    values = repository.setup_input_map()
    assert values["founder_name"] == "Masad"
    assert values["founder_slack_member_id"] == "U123"
    assert "unknown" not in values


def test_workflow_templates_seeded(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    templates = repository.list_workflow_templates()

    assert {template["id"] for template in templates} >= {
        "idea-opportunity-research",
        "product-concept-prd",
        "architecture-plan",
        "backend-implementation-plan",
        "frontend-implementation-plan",
        "testing-strategy",
        "founder-decision-memo",
    }
    assert templates[0]["owner_name"] == "Research Agent"
    by_id = {template["id"]: template for template in templates}
    assert by_id["aws-operating-plan"]["owner_agent_id"] == "cloud-infra-agent"
    assert by_id["testing-strategy"]["owner_agent_id"] == "test-automation-agent"


def test_create_project_with_workflow_generates_tasks_and_docs(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    project_id = repository.create_project_with_workflow(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )

    project = repository.get_project(project_id)
    items = repository.list_project_workflow_items(project_id)
    tasks = repository.list_tasks()
    documents = repository.list_documents()

    assert project["name"] == "Acme AI"
    assert len(items) == len(repository.list_workflow_templates())
    assert len(tasks) == len(items)
    assert len(documents) == len(items)
    assert any("Acme AI" in item["title"] for item in items)


def test_task_creation_links_to_agent(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    task_id = repository.create_task(
        title="Create founder brief",
        owner_agent_id="chief-of-staff",
        priority="high",
        summary="Synthesize the current idea pipeline.",
    )

    tasks = repository.list_tasks()
    assert tasks[0]["id"] == task_id
    assert tasks[0]["owner_name"] == "Chief of Staff"


def test_update_integration_status(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    repository = CompanyRepository(database_path)

    repository.update_integration_status("telegram-founder-alerts", "configured")

    integration = next(
        item for item in repository.list_integrations() if item["id"] == "telegram-founder-alerts"
    )
    assert integration["status"] == "configured"
