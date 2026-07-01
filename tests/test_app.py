import json

from fastapi.testclient import TestClient

from hermes_company_os.hermes_client import HermesResult
from hermes_company_os.kanban_client import KanbanResult
from hermes_company_os.main import create_app
from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.settings import Settings

FAKE_OPENAI_SECRET = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
FAKE_OPENAI_ENV_SECRET = "OPENAI_API_KEY=" + FAKE_OPENAI_SECRET
FAKE_SLACK_BOT_SECRET = "xoxb-" + "123456789012-abcdefABCDEF"
FAKE_SLACK_APP_SECRET = "xapp-" + "1-ABCDEFabcdef123456"
FAKE_SHORT_SLACK_BOT_SECRET = "xoxb-" + "123456789012-abc"
FAKE_ALPHA_SLACK_BOT_SECRET = "xoxb-" + "abcdefghijklmnopqrstuvwxyz123456"
FAKE_TELEGRAM_BOT_SECRET = "123456789:" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"
FAKE_LOWER_TELEGRAM_BOT_SECRET = "123456789:" + "abcdefghijklmnopqrstuvwxyzABCDEF"
FAKE_TELEGRAM_ENV_SECRET = "TELEGRAM_BOT_TOKEN=" + FAKE_TELEGRAM_BOT_SECRET
FAKE_LOWER_TELEGRAM_ENV_SECRET = "TELEGRAM_BOT_TOKEN=" + FAKE_LOWER_TELEGRAM_BOT_SECRET


class FakeHermesClient:
    def run_prompt(self, agent, prompt):
        return HermesResult(output=f"ran {agent['id']}: {prompt[:20]}")


class FakeKanbanClient:
    def diagnostics(self):
        return KanbanResult(ok=True, output='{"ok": true}')

    def create_task(self, task):
        return KanbanResult(ok=True, output='{"id": "t_123"}', task_id="t_123")


def mark_profile_llm_verified(repository, agent_id):
    preference = repository.get_model_preference(agent_id)
    repository.update_model_preference(
        agent_id=agent_id,
        provider=preference["provider"],
        model=preference["model"],
        fallback_provider=preference["fallback_provider"],
        fallback_model=preference["fallback_model"],
        auth_method=preference["auth_method"],
        status="verified",
        notes="Verified in test.",
    )
    repository.update_agent_secret_requirements(
        agent_id=agent_id,
        category="llm",
        status="verified",
        notes="Verified in test.",
    )


def mark_profile_installation_verified(repository, agent_id):
    repository.update_profile_installation_check(
        check_id=f"{agent_id}-profile-installation",
        status="verified",
        evidence="Verified in test.",
    )


def mark_all_profile_installations_verified(repository):
    for check in repository.list_profile_installation_checks():
        repository.update_profile_installation_check(
            check_id=check["id"],
            status="verified",
            evidence="Verified in test.",
        )


def mark_messaging_credentials_loaded(repository, platform, agent_id=None):
    for requirement in repository.list_secret_requirements():
        if requirement["category"] != platform:
            continue
        if agent_id is not None and requirement["owner_agent_id"] != agent_id:
            continue
        repository.update_secret_requirement(
            requirement_id=requirement["id"],
            status="loaded",
            notes="Loaded in test.",
        )


def mark_all_messaging_verified(repository):
    mark_messaging_credentials_loaded(repository, "slack")
    mark_messaging_credentials_loaded(repository, "telegram")
    for check in repository.list_messaging_checks():
        repository.update_messaging_check(
            check_id=check["id"],
            status="verified",
            evidence="Verified in test.",
        )


def test_dashboard_loads(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Engineering Manager" in response.text
    assert "09:00" in response.text
    assert "Activation gate" in response.text
    assert "setup needed" in response.text
    assert "Input ledger" in response.text
    assert "/setup/input-ledger.md" in response.text
    assert "Next actions" in response.text
    assert "/setup/founder-next-actions.md" in response.text
    assert "/setup/kickoff-readiness.md" in response.text
    assert "Founder Decision Queue" in response.text
    assert "/setup/founder-decisions.md" in response.text


def test_setup_page_loads(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    # The setup surface is split into a hub plus one page per section; each page
    # is asserted against the content it now owns.
    page_expectations = {
        "/setup": [
            "Company infrastructure readiness",
            "Founder return packet",
            "Founder input request",
            "Input collector",
            "Founder next actions",
            "Founder decision queue",
            "Team topology",
            "Delegation playbook",
            "Profile installation audit",
            "Profile acceptance",
            "Standup cron",
        ],
        "/setup/inputs": [
            "Deferred Setup Inputs",
            "Founder Reply Import",
            "Import safe inputs",
            "Slack Bot User ID Import",
            "/setup/slack-bot-user-map-template.md",
            "slack-bot-user-map-reply",
            "Telegram Recipient ID Import",
            "/setup/telegram-recipient-template.md",
            "telegram-recipient-reply",
            "Slack Channel ID Import",
            "/setup/slack-channel-template.md",
            "slack-channel-reply",
            "Profile Personalization Import",
            "/setup/profile-personalization-reply",
            "Import profile personalization",
        ],
        "/setup/schedules": [
            "Schedule Configuration Import",
            "/setup/schedule-config-template.md",
            "schedule-config-reply",
        ],
        "/setup/models": [
            "LLM Profile Preferences",
            "LLM Preference Import",
            "/setup/llm-preference-reply",
            "Import LLM preferences",
            "LLM Provider Presets",
            "Apply preset",
        ],
        "/setup/profiles": [
            "Profile Installation Tracking",
            "Import audit output",
            "Profile Acceptance Tracking",
            "Reply template",
            "/setup/profile-acceptance-reply",
            "Import acceptance checks",
            "Profile Smoke Checks",
        ],
        "/setup/messaging": [
            "Credential Status Import",
            "Import credential statuses",
            "Messaging Verification",
            "External Secret Status",
        ],
        "/setup/commands": [
            "Profile apply script",
            "Standup Cron",
        ],
        "/setup/verification": [
            "Schedule Verification",
            "/setup/schedule-verification-reply",
            "Import schedule checks",
            "Kanban Verification",
            "/setup/kanban-verification-reply",
            "Import Kanban checks",
        ],
        "/setup/integrations": [
            "Chief of Staff Slack bot",
            "Founder Telegram urgent alerts",
        ],
    }

    for path, fragments in page_expectations.items():
        response = client.get(path)
        assert response.status_code == 200, path
        for fragment in fragments:
            assert fragment in response.text, f"{fragment!r} missing from {path}"


def test_projects_page_loads(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/projects")

    assert response.status_code == 200
    assert "Company kickoff workflows" in response.text
    assert "Kickoff readiness" in response.text
    assert "Idea intake" in response.text
    assert "/setup/idea-intake.md" in response.text
    assert "draft_only" in response.text
    assert "Opportunity research" in response.text


def test_create_project_route_generates_workflow(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/projects",
        data={
            "name": "Acme AI",
            "founder_idea": "AI operating company for small businesses.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    projects = app.state.repository.list_projects()
    assert projects[0]["name"] == "Acme AI"
    assert projects[0]["workflow_count"] == len(app.state.repository.list_workflow_templates())


def test_bootstrap_script_includes_profiles_and_cron(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.repository.update_setup_inputs(
        {
            "founder_slack_member_id": "U123",
            "slack_channel_founder_command": "C123",
            "llm_provider": "openai-codex",
            "llm_model": "gpt-5-codex",
            "standup_cadence": "weekdays",
        }
    )
    client = TestClient(app)

    response = client.get("/setup/bootstrap.ps1")

    assert response.status_code == 200
    assert "hermes profile create chief-of-staff" in response.text
    assert ".env.example" in response.text
    assert "SLACK_ALLOWED_USERS=U123" in response.text
    assert "config.yaml.example" in response.text
    assert 'provider: "openai-codex"' in response.text
    assert "hermes kanban init" in response.text
    assert 'chief-of-staff cron create "every weekday at 9am"' in response.text


def test_profile_env_template_route(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/setup/profile-env/chief-of-staff.env")

    assert response.status_code == 200
    assert "SLACK_BOT_TOKEN=TODO" in response.text
    assert "SLACK_APP_TOKEN=TODO" in response.text
    assert "TELEGRAM_BOT_TOKEN=TODO" in response.text
    assert "xoxb-" not in response.text
    assert "xapp-" not in response.text


def test_profile_config_template_route(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.repository.update_model_preference(
        agent_id="engineering-manager",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        fallback_provider="openai-codex",
        fallback_model="gpt-5-codex",
        auth_method="profile_env",
        status="needs_secret",
        notes="Use for architecture review.",
    )
    client = TestClient(app)

    response = client.get("/setup/profile-config/engineering-manager.yaml")

    assert response.status_code == 200
    assert "Hermes config.yaml starter for Engineering Manager" in response.text
    assert 'provider: "openrouter"' in response.text
    assert 'model: "anthropic/claude-sonnet-4"' in response.text
    assert "fallback_providers:" in response.text


def test_profile_llm_env_template_route(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.repository.update_model_preference(
        agent_id="engineering-manager",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        fallback_provider="openai-codex",
        fallback_model="gpt-5-codex",
        auth_method="profile_env",
        status="needs_secret",
        notes="Use for architecture review.",
    )
    client = TestClient(app)

    response = client.get("/setup/profile-llm-env/engineering-manager.env")

    assert response.status_code == 200
    assert "OPENROUTER_API_KEY=REPLACE_WITH_OPENROUTER_API_KEY" in response.text
    assert "OPENAI_API_KEY=REPLACE_WITH_OPENAI_API_KEY" in response.text
    assert "SLACK_BOT_TOKEN" not in response.text
    assert "TELEGRAM_BOT_TOKEN" not in response.text
    assert "xoxb-" not in response.text
    assert "xapp-" not in response.text
    assert "sk-" not in response.text


def test_profile_artifacts_route(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/setup/profile-artifacts.md")
    template = client.get("/setup/profile-personalization-template.md")
    template_json = client.get("/setup/profile-personalization-template.json")

    assert response.status_code == 200
    assert "Hermes Company OS Profile Artifacts" in response.text
    assert "Engineering Manager" in response.text
    assert template.status_code == 200
    assert "Profile Personalization Reply Template" in template.text
    assert "engineering-manager" in template.text
    assert "xoxb-" not in template.text
    assert "xapp-" not in template.text
    assert "sk-" not in template.text
    assert template_json.status_code == 200
    assert template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/inputs#profile-personalization-import"
    )


def test_profile_specific_artifact_routes(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    soul = client.get("/setup/profile-soul/engineering-manager.md")
    manifest = client.get("/setup/profile-manifest/engineering-manager.json")
    apply_script = client.get("/setup/profile-apply/engineering-manager.ps1")
    live_config = client.get("/setup/profile-live-config/engineering-manager.yaml")
    live_context = client.get("/setup/profile-live-context/engineering-manager.md")
    live_prompts = client.get("/setup/profile-live-prompts/engineering-manager.md")
    live_rules = client.get("/setup/profile-live-rules/engineering-manager.md")
    live_assets = client.get("/setup/profile-live-assets.md")
    live_assets_json = client.get("/setup/profile-live-assets.json")
    live_assets_script = client.get("/setup/profile-live-assets.ps1")

    assert soul.status_code == 200
    assert "smallest safe version" in soul.text
    assert "engineering safety floor" in soul.text
    assert manifest.status_code == 200
    assert manifest.json()["id"] == "engineering-manager"
    assert manifest.json()["setup_exports"]["profile_apply_script"] == (
        "/setup/profile-apply/engineering-manager.ps1"
    )
    assert apply_script.status_code == 200
    assert "hermes profile create engineering-manager" in apply_script.text
    assert "profile-manifest.json" in apply_script.text
    assert "SLACK_BOT_TOKEN" not in apply_script.text
    assert "TELEGRAM_BOT_TOKEN" not in apply_script.text
    assert "xoxb-" not in apply_script.text
    assert "xapp-" not in apply_script.text
    assert "sk-" not in apply_script.text
    assert live_config.status_code == 200
    assert 'provider: "openai-codex"' in live_config.text
    assert 'default: "gpt-5-codex"' in live_config.text
    assert "REPLACE_WITH" not in live_config.text
    assert live_context.status_code == 200
    assert "Company Context" in live_context.text
    assert "Slack is the main company workspace." in live_context.text
    assert live_prompts.status_code == 200
    assert "Profile Prompt Pack" in live_prompts.text
    assert live_rules.status_code == 200
    assert "Credential Boundary" in live_rules.text
    assert live_assets.status_code == 200
    assert "Hermes Live Starter Profile Assets" in live_assets.text
    assert live_assets_json.status_code == 200
    assert live_assets_json.json()["entry_points"]["script"] == ("/setup/profile-live-assets.ps1")
    assert live_assets_script.status_code == 200
    assert "Credential files were not touched" in live_assets_script.text
    raw_live_assets = (
        live_config.text
        + live_context.text
        + live_prompts.text
        + live_rules.text
        + live_assets.text
        + json.dumps(live_assets_json.json())
        + live_assets_script.text
    )
    assert secret_violations({"raw": raw_live_assets}) == []


def test_profile_specific_artifact_routes_return_404_for_unknown_profile(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    assert client.get("/setup/profile-soul/missing-agent.md").status_code == 404
    assert client.get("/setup/profile-manifest/missing-agent.json").status_code == 404
    assert client.get("/setup/profile-apply/missing-agent.ps1").status_code == 404
    assert client.get("/setup/profile-live-config/missing-agent.yaml").status_code == 404
    assert client.get("/setup/profile-live-context/missing-agent.md").status_code == 404
    assert client.get("/setup/profile-live-prompts/missing-agent.md").status_code == 404
    assert client.get("/setup/profile-live-rules/missing-agent.md").status_code == 404


def test_update_agent_profile_route_updates_artifacts(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/agents/engineering-manager/profile",
        data={
            "description": "Builds ambitious systems with proof.",
            "soul": "Think big. Demand clean architecture and serious tests.",
            "capabilities": "distributed systems\naws planning\ne2e testing",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    agent = app.state.repository.get_agent("engineering-manager")
    assert agent["description"] == "Builds ambitious systems with proof."
    assert agent["capabilities"] == [
        "distributed systems",
        "aws planning",
        "e2e testing",
    ]
    artifacts = client.get("/setup/profile-artifacts.md")
    assert "Think big. Demand clean architecture and serious tests." in artifacts.text


def test_update_agent_routing_route_updates_artifacts(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/agents/research-agent/routing",
        data={
            "slack_channel": "#deep-research",
            "telegram_policy": "Telegram only for founder-blocking evidence gaps",
            "hermes_command": "research-director",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    agent = app.state.repository.get_agent("research-agent")
    assert agent["slack_channel"] == "#deep-research"
    assert agent["telegram_policy"] == "Telegram only for founder-blocking evidence gaps"
    assert agent["hermes_command"] == "research-director"
    slack_plan = client.get("/setup/slack-plan.md")
    assert "Hermes profile command: `research-director`" in slack_plan.text
    assert "Home channel name: `#deep-research`" in slack_plan.text
    assert "Gateway setup: `research-director gateway setup`" in slack_plan.text
    profile_artifacts = client.get("/setup/profile-artifacts.md")
    assert "- Hermes command: `research-director`" in profile_artifacts.text


def test_profile_personalization_reply_import_updates_artifacts(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-personalization-reply",
        data={
            "reply_text": json.dumps(
                {
                    "profiles": [
                        {
                            "id": "engineering-manager",
                            "description": "Builds ambitious systems with proof.",
                            "soul": "Think big. Demand architecture and tests.",
                            "capabilities": [
                                "distributed systems",
                                "aws architecture",
                                "integration testing",
                            ],
                            "slack_channel": "#eng-leadership",
                            "telegram_policy": "Telegram only for founder-blocking risks.",
                            "hermes_command": "engineering-lead",
                        }
                    ]
                }
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/inputs?profile_personalization_imported=1"
        "&profile_personalization_unknown=0"
        "&profile_personalization_invalid=0"
        "&profile_personalization_ignored=0"
        "#profile-personalization-import"
    )
    agent = app.state.repository.get_agent("engineering-manager")
    assert agent["description"] == "Builds ambitious systems with proof."
    assert agent["soul"] == "Think big. Demand architecture and tests."
    assert agent["capabilities"] == [
        "distributed systems",
        "aws architecture",
        "integration testing",
    ]
    assert agent["slack_channel"] == "#eng-leadership"
    assert agent["telegram_policy"] == "Telegram only for founder-blocking risks."
    assert agent["hermes_command"] == "engineering-lead"
    artifacts = client.get("/setup/profile-artifacts.md")
    assert "Think big. Demand architecture and tests." in artifacts.text
    assert "- Hermes command: `engineering-lead`" in artifacts.text


def test_profile_personalization_reply_import_rejects_invalid_profile(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-personalization-reply",
        data={
            "reply_text": json.dumps(
                {"profiles": [{"id": "engineering-manager", "description": ""}]}
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    agent = app.state.repository.get_agent("engineering-manager")
    assert agent["description"] != ""


def test_profile_personalization_reply_import_rejects_secret_text(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-personalization-reply",
        data={
            "reply_text": json.dumps(
                {
                    "profiles": [
                        {
                            "id": "engineering-manager",
                            "description": FAKE_OPENAI_ENV_SECRET,
                        }
                    ]
                }
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    agent = app.state.repository.get_agent("engineering-manager")
    assert "OPENAI_API_KEY" not in agent["description"]


def test_profile_personalization_reply_import_rejects_invalid_json(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-personalization-reply",
        data={"reply_text": "not json"},
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_external_setup_plan_routes(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    inputs = client.get("/setup/inputs-needed.md")
    founder_handoff = client.get("/setup/founder-handoff.md")
    founder_handoff_json = client.get("/setup/founder-handoff.json")
    founder_input_request = client.get("/setup/founder-input-request.md")
    founder_input_json = client.get("/setup/founder-input-request.json")
    founder_input_collector = client.get("/setup/founder-inputs.ps1")
    first_run = client.get("/setup/first-run.md")
    first_run_json = client.get("/setup/first-run.json")
    first_run_script = client.get("/setup/first-run.ps1")
    progress_board = client.get("/setup/progress-board.md")
    progress_board_json = client.get("/setup/progress-board.json")
    input_ledger = client.get("/setup/input-ledger.md")
    input_ledger_json = client.get("/setup/input-ledger.json")
    credential_loading = client.get("/setup/credential-loading.md")
    credential_loading_json = client.get("/setup/credential-loading.json")
    credential_status_template = client.get("/setup/credential-status-template.md")
    credential_status_json = client.get("/setup/credential-status-template.json")
    founder_next_actions = client.get("/setup/founder-next-actions.md")
    founder_next_actions_json = client.get("/setup/founder-next-actions.json")
    founder_decisions = client.get("/setup/founder-decisions.md")
    founder_decisions_json = client.get("/setup/founder-decisions.json")
    readiness = client.get("/setup/readiness-report.md")
    company_manifest = client.get("/setup/company-manifest.md")
    company_manifest_json = client.get("/setup/company-manifest.json")
    company_launch_drill = client.get("/setup/company-launch-drill.md")
    company_launch_drill_json = client.get("/setup/company-launch-drill.json")
    kickoff_readiness = client.get("/setup/kickoff-readiness.md")
    kickoff_readiness_json = client.get("/setup/kickoff-readiness.json")
    team_topology = client.get("/setup/team-topology.md")
    team_topology_json = client.get("/setup/team-topology.json")
    delegation_playbook = client.get("/setup/delegation-playbook.md")
    delegation_playbook_json = client.get("/setup/delegation-playbook.json")
    profile_installation = client.get("/setup/profile-installation.md")
    profile_installation_json = client.get("/setup/profile-installation.json")
    profile_installation_script = client.get("/setup/profile-installation.ps1")
    profile_personalization = client.get("/setup/profile-personalization-template.md")
    profile_personalization_json = client.get("/setup/profile-personalization-template.json")
    profile_acceptance = client.get("/setup/profile-acceptance.md")
    profile_acceptance_json = client.get("/setup/profile-acceptance.json")
    profile_acceptance_template = client.get("/setup/profile-acceptance-template.md")
    profile_acceptance_template_json = client.get("/setup/profile-acceptance-template.json")
    slack = client.get("/setup/slack-plan.md")
    slack_provisioning = client.get("/setup/slack-provisioning.md")
    slack_provisioning_json = client.get("/setup/slack-provisioning.json")
    slack_provisioning_script = client.get("/setup/slack-provisioning.ps1")
    slack_channel_template = client.get("/setup/slack-channel-template.md")
    slack_channel_template_json = client.get("/setup/slack-channel-template.json")
    slack_bot_user_map = client.get("/setup/slack-bot-user-map.json")
    slack_bot_user_template = client.get("/setup/slack-bot-user-map-template.md")
    slack_bot_user_template_json = client.get("/setup/slack-bot-user-map-template.json")
    slack_workspace = client.get("/setup/slack-workspace.md")
    slack_invite_json = client.get("/setup/slack-invite-matrix.json")
    slack_invite_csv = client.get("/setup/slack-invite-matrix.csv")
    telegram = client.get("/setup/telegram-plan.md")
    telegram_botfather = client.get("/setup/telegram-botfather.md")
    telegram_recipient_template = client.get("/setup/telegram-recipient-template.md")
    telegram_recipient_template_json = client.get("/setup/telegram-recipient-template.json")
    telegram_provisioning = client.get("/setup/telegram-provisioning.md")
    telegram_provisioning_json = client.get("/setup/telegram-provisioning.json")
    telegram_provisioning_script = client.get("/setup/telegram-provisioning.ps1")
    telegram_policy = client.get("/setup/telegram-policy.md")
    telegram_policy_json = client.get("/setup/telegram-policy.json")
    messaging_drill = client.get("/setup/messaging-drill.md")
    messaging_drill_json = client.get("/setup/messaging-drill.json")
    messaging_template = client.get("/setup/messaging-verification-template.md")
    messaging_template_json = client.get("/setup/messaging-verification-template.json")
    gateway_operations = client.get("/setup/gateway-operations.md")
    gateway_operations_json = client.get("/setup/gateway-operations.json")
    gateway_operations_script = client.get("/setup/gateway-operations.ps1")
    llm = client.get("/setup/llm-plan.md")
    llm_credentials = client.get("/setup/llm-credentials.md")
    llm_provisioning = client.get("/setup/llm-provisioning.md")
    llm_provisioning_json = client.get("/setup/llm-provisioning.json")
    llm_provisioning_script = client.get("/setup/llm-provisioning.ps1")
    llm_provider_presets = client.get("/setup/llm-provider-presets.md")
    llm_provider_presets_json = client.get("/setup/llm-provider-presets.json")
    llm_preference_template = client.get("/setup/llm-preference-template.md")
    llm_preference_template_json = client.get("/setup/llm-preference-template.json")
    llm_finalization = client.get("/setup/llm-finalize.md")
    llm_finalization_script = client.get("/setup/llm-finalize.ps1")
    llm_smoke = client.get("/setup/llm-smoke.md")
    llm_smoke_json = client.get("/setup/llm-smoke.json")
    secret_audit = client.get("/setup/secret-audit.md")
    secret_audit_script = client.get("/setup/secret-audit.ps1")
    hermes_runtime = client.get("/setup/hermes-runtime.md")
    hermes_runtime_json = client.get("/setup/hermes-runtime.json")
    hermes_install_script = client.get("/setup/hermes-install.ps1")
    runtime_preflight = client.get("/setup/runtime-preflight.md")
    runtime_preflight_json = client.get("/setup/runtime-preflight.json")
    runtime_preflight_script = client.get("/setup/runtime-preflight.ps1")
    schedule_provisioning = client.get("/setup/schedule-provisioning.md")
    schedule_provisioning_json = client.get("/setup/schedule-provisioning.json")
    schedule_provisioning_script = client.get("/setup/schedule-provisioning.ps1")
    schedule_config_template = client.get("/setup/schedule-config-template.md")
    schedule_config_template_json = client.get("/setup/schedule-config-template.json")
    schedule_template = client.get("/setup/schedule-verification-template.md")
    schedule_template_json = client.get("/setup/schedule-verification-template.json")
    standup_preview = client.get("/setup/standup-preview.md")
    standup_preview_json = client.get("/setup/standup-preview.json")
    standup_runbook = client.get("/setup/standup-runbook.md")
    standup_cron = client.get("/setup/standup-cron.ps1")
    idea_intake = client.get("/setup/idea-intake.md")
    idea_intake_json = client.get("/setup/idea-intake.json")
    project_workflow = client.get("/setup/project-workflow.md")
    project_workflow_json = client.get("/setup/project-workflow.json")
    kanban_provisioning = client.get("/setup/kanban-provisioning.md")
    kanban_provisioning_json = client.get("/setup/kanban-provisioning.json")
    kanban_provisioning_script = client.get("/setup/kanban-provisioning.ps1")
    kanban_template = client.get("/setup/kanban-verification-template.md")
    kanban_template_json = client.get("/setup/kanban-verification-template.json")
    kanban_runbook = client.get("/setup/kanban-runbook.md")
    kanban_diagnostics = client.get("/setup/kanban-diagnostics.ps1")
    activation_sequence = client.get("/setup/activation-sequence.md")
    activation_runner = client.get("/setup/activation-runner.md")
    activation_runner_script = client.get("/setup/activation-runner.ps1")
    live_verification = client.get("/setup/live-verification.md")
    verification_evidence = client.get("/setup/verification-evidence.md")
    verification_evidence_json = client.get("/setup/verification-evidence.json")
    activation = client.get("/setup/activation-checklist.md")

    assert inputs.status_code == 200
    assert "Inputs Needed" in inputs.text
    assert "External Secrets Never Stored Here" in inputs.text
    assert "Slack bot credential loaded externally" in inputs.text
    assert "Telegram BotFather credential loaded externally" in inputs.text
    assert "xoxb-" not in inputs.text
    assert "xapp-" not in inputs.text
    assert "TELEGRAM_BOT_TOKEN=" not in inputs.text
    assert "API_KEY=" not in inputs.text
    assert founder_handoff.status_code == 200
    assert "Founder Return Packet" in founder_handoff.text
    assert "Safe Dashboard Reply Template" in founder_handoff.text
    assert "Credential Status Reply Template" in founder_handoff.text
    assert "/setup/gateway-operations.md" in founder_handoff.text
    assert "xoxb-" not in founder_handoff.text
    assert "xapp-" not in founder_handoff.text
    assert "sk-" not in founder_handoff.text
    assert founder_handoff_json.status_code == 200
    assert founder_handoff_json.json()["title"] == "Founder Return Packet"
    assert founder_handoff_json.json()["entry_points"]["input_import"] == (
        "/setup/inputs#input-import"
    )
    assert founder_input_request.status_code == 200
    assert "Founder Input Request" in founder_input_request.text
    assert "Reply Template" in founder_input_request.text
    assert "External Secrets To Load Later" in founder_input_request.text
    assert "xoxb-" not in founder_input_request.text
    assert "xapp-" not in founder_input_request.text
    assert "sk-" not in founder_input_request.text
    assert founder_input_json.status_code == 200
    assert founder_input_json.json()["entry_points"]["safe_inputs"] == "/setup/inputs#inputs"
    assert founder_input_json.json()["entry_points"]["collector_script"] == (
        "/setup/founder-inputs.ps1"
    )
    assert "safe_dashboard_inputs" in founder_input_json.json()
    assert founder_input_collector.status_code == 200
    assert "Hermes Company OS founder input collector" in founder_input_collector.text
    assert "PostDashboardInputs" in founder_input_collector.text
    assert "/setup/founder-input-reply" in founder_input_collector.text
    assert "xoxb-" not in founder_input_collector.text
    assert "xapp-" not in founder_input_collector.text
    assert "sk-" not in founder_input_collector.text
    assert "API_KEY=" not in founder_input_collector.text
    assert first_run.status_code == 200
    assert "First Run Helper" in first_run.text
    assert "/setup/first-run.ps1" in first_run.text
    assert first_run_json.status_code == 200
    assert first_run_json.json()["entry_points"]["script"] == "/setup/first-run.ps1"
    assert first_run_script.status_code == 200
    assert "Hermes Company OS first-run helper" in first_run_script.text
    assert "InstallHermes" in first_run_script.text
    assert "RunActivation" in first_run_script.text
    assert "/setup/runtime-preflight.ps1" in first_run_script.text
    assert "xoxb-" not in first_run_script.text
    assert "xapp-" not in first_run_script.text
    assert "sk-" not in first_run_script.text
    assert progress_board.status_code == 200
    assert "Founder Setup Progress Board" in progress_board.text
    assert "Do after Hermes install" in progress_board.text
    assert progress_board_json.status_code == 200
    assert progress_board_json.json()["entry_points"]["first_run"] == ("/setup/first-run.ps1")
    assert [column["id"] for column in progress_board_json.json()["columns"]] == [
        "do-now",
        "after-hermes-install",
        "after-credentials",
        "final-verification",
    ]
    assert "xoxb-" not in progress_board.text
    assert "xapp-" not in progress_board.text
    assert "sk-" not in progress_board.text
    assert input_ledger.status_code == 200
    assert "Founder Input Ledger" in input_ledger.text
    assert "Questions For You" in input_ledger.text
    assert "Credential Status Reply Template" in input_ledger.text
    assert "xoxb-" not in input_ledger.text
    assert "xapp-" not in input_ledger.text
    assert "sk-" not in input_ledger.text
    assert input_ledger_json.status_code == 200
    assert input_ledger_json.json()["title"] == "Founder Input Ledger"
    assert input_ledger_json.json()["entry_points"]["founder_handoff"] == (
        "/setup/founder-handoff.md"
    )
    assert credential_loading.status_code == 200
    assert "External Credential Loading Sequence" in credential_loading.text
    assert "Profile Installation Precheck" in credential_loading.text
    assert "LLM Credentials Last" in credential_loading.text
    assert "Profile Acceptance Last" in credential_loading.text
    assert ".\\secret-audit.ps1 -AuditLlm -PostDashboardStatus" in credential_loading.text
    assert "xoxb-" not in credential_loading.text
    assert "xapp-" not in credential_loading.text
    assert "sk-" not in credential_loading.text
    assert credential_loading_json.status_code == 200
    credential_loading_payload = credential_loading_json.json()
    assert credential_loading_payload["verification_last"] is True
    assert [phase["id"] for phase in credential_loading_payload["phase_order"]] == [
        "profile_installation_precheck",
        "messaging_credentials",
        "messaging_verification",
        "kanban_and_scheduling",
        "llm_credentials_last",
        "profile_acceptance_final",
    ]
    assert credential_loading_payload["entry_points"]["profile_installation"] == (
        "/setup/profiles#profile-installation-tracking"
    )
    assert credential_loading_payload["entry_points"]["profile_acceptance"] == (
        "/setup/profiles#profile-acceptance-tracking"
    )
    assert credential_loading_payload["entry_points"]["live_verification"] == (
        "/setup/live-verification.md"
    )
    assert credential_status_template.status_code == 200
    assert "External Credential Status Template" in credential_status_template.text
    assert "/setup/messaging#credential-status-import" in credential_status_template.text
    assert "xoxb-" not in credential_status_template.text
    assert "xapp-" not in credential_status_template.text
    assert "sk-" not in credential_status_template.text
    assert credential_status_json.status_code == 200
    assert credential_status_json.json()["entry_points"]["bulk_import"] == (
        "/setup/messaging#credential-status-import"
    )
    assert founder_next_actions.status_code == 200
    assert "Founder Next Actions" in founder_next_actions.text
    assert "Next best action" in founder_next_actions.text
    assert founder_next_actions_json.status_code == 200
    assert founder_next_actions_json.json()["title"] == "Founder Next Actions"
    assert founder_next_actions_json.json()["entry_points"]["input_ledger"] == (
        "/setup/input-ledger.md"
    )
    assert founder_next_actions_json.json()["entry_points"]["founder_decisions"] == (
        "/setup/founder-decisions.md"
    )
    assert founder_next_actions_json.json()["entry_points"]["first_run"] == ("/setup/first-run.md")
    assert founder_next_actions_json.json()["entry_points"]["first_run_runner"] == (
        "/setup/first-run.ps1"
    )
    assert founder_next_actions_json.json()["entry_points"]["progress_board"] == (
        "/setup/progress-board.md"
    )
    assert founder_next_actions_json.json()["entry_points"]["progress_board_json"] == (
        "/setup/progress-board.json"
    )
    assert founder_next_actions_json.json()["entry_points"]["hermes_runtime"] == (
        "/setup/hermes-runtime.md"
    )
    assert founder_next_actions_json.json()["entry_points"]["hermes_install_runner"] == (
        "/setup/hermes-install.ps1"
    )
    assert "local_runtime" in founder_next_actions_json.json()
    assert founder_next_actions_json.json()["entry_points"]["profile_installation"] == (
        "/setup/profiles#profile-installation-tracking"
    )
    assert founder_decisions.status_code == 200
    assert "Founder Decision Queue" in founder_decisions.text
    assert "Urgent open decisions" in founder_decisions.text
    assert founder_decisions_json.status_code == 200
    assert founder_decisions_json.json()["title"] == "Founder Decision Queue"
    assert founder_decisions_json.json()["summary"]["open"] == 2
    assert readiness.status_code == 200
    assert "Activation Readiness Report" in readiness.text
    assert company_manifest.status_code == 200
    assert "Hermes Company OS Setup Manifest" in company_manifest.text
    assert "Credential Boundary" in company_manifest.text
    assert company_manifest_json.status_code == 200
    assert company_manifest_json.json()["title"] == "Hermes Company OS Setup Manifest"
    assert company_manifest_json.json()["artifacts"]["company_manifest_markdown"] == (
        "/setup/company-manifest.md"
    )
    assert company_manifest_json.json()["artifacts"]["company_launch_drill"] == (
        "/setup/company-launch-drill.md"
    )
    assert company_manifest_json.json()["artifacts"]["founder_handoff"] == (
        "/setup/founder-handoff.md"
    )
    assert company_manifest_json.json()["artifacts"]["first_run_runner"] == ("/setup/first-run.ps1")
    assert company_manifest_json.json()["artifacts"]["progress_board"] == (
        "/setup/progress-board.md"
    )
    assert company_manifest_json.json()["artifacts"]["founder_decisions"] == (
        "/setup/founder-decisions.md"
    )
    assert company_manifest_json.json()["artifacts"]["input_ledger"] == ("/setup/input-ledger.md")
    assert company_manifest_json.json()["artifacts"]["kickoff_readiness"] == (
        "/setup/kickoff-readiness.md"
    )
    assert company_manifest_json.json()["artifacts"]["credential_status_template"] == (
        "/setup/credential-status-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["credential_loading"] == (
        "/setup/credential-loading.md"
    )
    assert company_manifest_json.json()["artifacts"]["llm_provisioning"] == (
        "/setup/llm-provisioning.md"
    )
    assert company_manifest_json.json()["artifacts"]["llm_provisioning_runner"] == (
        "/setup/llm-provisioning.ps1"
    )
    assert company_manifest_json.json()["artifacts"]["llm_provider_presets"] == (
        "/setup/llm-provider-presets.md"
    )
    assert company_manifest_json.json()["artifacts"]["llm_preference_template"] == (
        "/setup/llm-preference-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["slack_provisioning"] == (
        "/setup/slack-provisioning.md"
    )
    assert company_manifest_json.json()["artifacts"]["slack_channel_template"] == (
        "/setup/slack-channel-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["slack_bot_user_template"] == (
        "/setup/slack-bot-user-map-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["telegram_provisioning"] == (
        "/setup/telegram-provisioning.md"
    )
    assert (
        company_manifest_json.json()["artifacts"]["telegram_recipient_template"]
        == "/setup/telegram-recipient-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["team_topology"] == ("/setup/team-topology.md")
    assert company_manifest_json.json()["artifacts"]["delegation_playbook"] == (
        "/setup/delegation-playbook.md"
    )
    assert company_manifest_json.json()["artifacts"]["gateway_operations"] == (
        "/setup/gateway-operations.md"
    )
    assert company_manifest_json.json()["artifacts"]["profile_installation"] == (
        "/setup/profile-installation.md"
    )
    assert (
        company_manifest_json.json()["artifacts"]["profile_personalization_template"]
        == "/setup/profile-personalization-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["profile_acceptance_template"] == (
        "/setup/profile-acceptance-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["verification_evidence"] == (
        "/setup/verification-evidence.md"
    )
    assert company_manifest_json.json()["artifacts"]["schedule_provisioning"] == (
        "/setup/schedule-provisioning.md"
    )
    assert company_manifest_json.json()["artifacts"]["schedule_config_template"] == (
        "/setup/schedule-config-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["schedule_verification_template"] == (
        "/setup/schedule-verification-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["kanban_provisioning"] == (
        "/setup/kanban-provisioning.md"
    )
    assert company_manifest_json.json()["artifacts"]["kanban_verification_template"] == (
        "/setup/kanban-verification-template.md"
    )
    assert company_manifest_json.json()["artifacts"]["hermes_runtime"] == (
        "/setup/hermes-runtime.md"
    )
    assert company_manifest_json.json()["artifacts"]["hermes_install_runner"] == (
        "/setup/hermes-install.ps1"
    )
    assert company_manifest_json.json()["profile_installation"]["status"] == ({"needed": 10})
    assert company_launch_drill.status_code == 200
    assert "Company Launch Drill" in company_launch_drill.text
    assert "Founder Go / No-Go Rule" in company_launch_drill.text
    assert company_launch_drill_json.status_code == 200
    assert company_launch_drill_json.json()["title"] == "Company Launch Drill"
    assert company_launch_drill_json.json()["entry_points"]["input_collector"] == (
        "/setup/founder-inputs.ps1"
    )
    assert company_launch_drill_json.json()["entry_points"]["first_run_runner"] == (
        "/setup/first-run.ps1"
    )
    assert company_launch_drill_json.json()["entry_points"]["progress_board"] == (
        "/setup/progress-board.md"
    )
    assert company_launch_drill_json.json()["entry_points"]["hermes_runtime"] == (
        "/setup/hermes-runtime.md"
    )
    assert (
        company_launch_drill_json.json()["entry_points"]["hermes_install_runner"]
        == "/setup/hermes-install.ps1"
    )
    assert company_launch_drill_json.json()["entry_points"]["idea_intake"] == (
        "/setup/idea-intake.md"
    )
    assert company_launch_drill_json.json()["entry_points"]["founder_decisions"] == (
        "/setup/founder-decisions.md"
    )
    assert company_launch_drill_json.json()["entry_points"]["profile_installation"] == (
        "/setup/profile-installation.md"
    )
    assert kickoff_readiness.status_code == 200
    assert "First Project Kickoff Readiness" in kickoff_readiness.text
    assert "Live kickoff ready" in kickoff_readiness.text
    assert kickoff_readiness_json.status_code == 200
    assert kickoff_readiness_json.json()["title"] == "First Project Kickoff Readiness"
    assert kickoff_readiness_json.json()["draft_workflow_allowed"] is True
    kickoff_gate_ids = {gate["id"] for gate in kickoff_readiness_json.json()["gates"]}
    assert "profile_installation" in kickoff_gate_ids
    assert "profile_acceptance" in kickoff_gate_ids
    assert team_topology.status_code == 200
    assert "Hermes Team Topology" in team_topology.text
    assert "Backend Engineer (`backend-engineer`)" in team_topology.text
    assert team_topology_json.status_code == 200
    assert team_topology_json.json()["summary"]["relationships"] == 4
    assert team_topology_json.json()["managers"][0]["manager"]["id"] == ("engineering-manager")
    assert delegation_playbook.status_code == 200
    assert "Hermes Delegation Playbook" in delegation_playbook.text
    assert "Chief of Staff" in delegation_playbook.text
    assert "Backend implementation plan" in delegation_playbook.text
    assert delegation_playbook_json.status_code == 200
    delegation_payload = delegation_playbook_json.json()
    assert delegation_payload["title"] == "Hermes Delegation Playbook"
    assert delegation_payload["manager_groups"][0]["manager"]["id"] == ("engineering-manager")
    assert delegation_payload["entry_points"]["team_topology"] == ("/setup/team-topology.md")
    assert delegation_payload["standups"][0]["time"] == "09:00"
    assert "xoxb-" not in delegation_playbook.text
    assert "xapp-" not in delegation_playbook.text
    assert "sk-" not in delegation_playbook.text
    assert profile_installation.status_code == 200
    assert "Hermes Profile Installation Audit" in profile_installation.text
    assert "Credential Boundary" in profile_installation.text
    assert "/setup/profile-apply/chief-of-staff.ps1" in profile_installation.text
    assert "xoxb-" not in profile_installation.text
    assert "xapp-" not in profile_installation.text
    assert "sk-" not in profile_installation.text
    assert profile_installation_json.status_code == 200
    assert profile_installation_json.json()["title"] == ("Hermes Profile Installation Audit")
    assert profile_installation_json.json()["profiles"][0]["apply_script"] == (
        "/setup/profile-apply/chief-of-staff.ps1"
    )
    assert profile_installation_json.json()["tracking"]["status"] == {"needed": 10}
    assert profile_installation_script.status_code == 200
    assert "Hermes Company OS profile installation audit" in (profile_installation_script.text)
    assert "File contents were not printed" in profile_installation_script.text
    assert "xoxb-" not in profile_installation_script.text
    assert "xapp-" not in profile_installation_script.text
    assert "sk-" not in profile_installation_script.text
    assert profile_personalization.status_code == 200
    assert "Profile Personalization Reply Template" in profile_personalization.text
    assert "/setup/inputs#profile-personalization-import" in profile_personalization.text
    assert "xoxb-" not in profile_personalization.text
    assert "xapp-" not in profile_personalization.text
    assert "sk-" not in profile_personalization.text
    assert profile_personalization_json.status_code == 200
    assert profile_personalization_json.json()["entry_points"]["bulk_import"] == (
        "/setup/inputs#profile-personalization-import"
    )
    assert profile_acceptance.status_code == 200
    assert "Profile Acceptance Suite" in profile_acceptance.text
    assert "T0 fast path" in profile_acceptance.text
    assert "Status: `needed`" in profile_acceptance.text
    assert profile_acceptance_json.status_code == 200
    assert profile_acceptance_json.json()["title"] == "Profile Acceptance Suite"
    assert profile_acceptance_json.json()["cases"]
    assert profile_acceptance_json.json()["cases"][0]["status"] == "needed"
    assert profile_acceptance_template.status_code == 200
    assert "Profile Acceptance Reply Template" in profile_acceptance_template.text
    assert "/setup/profiles#profile-acceptance-tracking" in profile_acceptance_template.text
    assert "xoxb-" not in profile_acceptance_template.text
    assert "xapp-" not in profile_acceptance_template.text
    assert "sk-" not in profile_acceptance_template.text
    assert profile_acceptance_template_json.status_code == 200
    assert profile_acceptance_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/profiles#profile-acceptance-tracking"
    )
    assert slack.status_code == 200
    assert "Slack Setup Plan" in slack.text
    assert "chief-of-staff slack manifest --write" in slack.text
    assert "/setup/slack-manifest/chief-of-staff.json" in slack.text
    assert "xoxb-" not in slack.text
    assert "xapp-" not in slack.text
    assert "TELEGRAM_BOT_TOKEN=" not in slack.text
    assert "API_KEY=" not in slack.text
    assert slack_provisioning.status_code == 200
    assert "Slack Provisioning Pack" in slack_provisioning.text
    assert "conversations.create" in slack_provisioning.text
    assert "xoxb-" not in slack_provisioning.text
    assert "xapp-" not in slack_provisioning.text
    assert "sk-" not in slack_provisioning.text
    assert slack_provisioning_json.status_code == 200
    assert slack_provisioning_json.json()["title"] == "Slack Provisioning Pack"
    assert slack_provisioning_json.json()["runner"]["default_mode"] == "dry_run"
    assert slack_provisioning_script.status_code == 200
    assert "Hermes Company OS Slack provisioning runner" in slack_provisioning_script.text
    assert "conversations.invite" in slack_provisioning_script.text
    assert "DASHBOARD skipped input ${Key}:" in slack_provisioning_script.text
    assert "DASHBOARD skipped input $Key:" not in slack_provisioning_script.text
    assert "xoxb-" not in slack_provisioning_script.text
    assert "xapp-" not in slack_provisioning_script.text
    assert "sk-" not in slack_provisioning_script.text
    assert slack_channel_template.status_code == 200
    assert "Slack Channel ID Reply Template" in slack_channel_template.text
    assert "/setup/inputs#slack-channel-import" in slack_channel_template.text
    assert slack_channel_template_json.status_code == 200
    assert slack_channel_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/inputs#slack-channel-import"
    )
    assert (
        secret_violations(
            {
                "slack_channel_template": slack_channel_template.text,
                "slack_channel_template_json": slack_channel_template_json.text,
            }
        )
        == []
    )
    assert slack_bot_user_map.status_code == 200
    assert slack_bot_user_map.json()["chief-of-staff"] == (
        "U_REPLACE_WITH_CHIEF_OF_STAFF_BOT_USER_ID"
    )
    assert slack_bot_user_template.status_code == 200
    assert "Slack Bot User ID Reply Template" in slack_bot_user_template.text
    assert "/setup/inputs#slack-bot-user-import" in slack_bot_user_template.text
    assert slack_bot_user_template_json.status_code == 200
    assert slack_bot_user_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/inputs#slack-bot-user-import"
    )
    assert (
        secret_violations(
            {
                "slack_bot_user_template": slack_bot_user_template.text,
                "slack_bot_user_template_json": slack_bot_user_template_json.text,
            }
        )
        == []
    )
    assert slack_workspace.status_code == 200
    assert "Slack Workspace Matrix" in slack_workspace.text
    assert "/invite @Hermes Chief of Staff" in slack_workspace.text
    assert slack_invite_json.status_code == 200
    assert slack_invite_json.json()["title"] == "Slack Workspace Matrix"
    assert slack_invite_csv.status_code == 200
    assert "channel_name,channel_id,required" in slack_invite_csv.text
    assert telegram.status_code == 200
    assert "Telegram Urgent Alert Setup" in telegram.text
    assert "/setup/telegram-botfather.md" in telegram.text
    assert "Allowed users metadata" in telegram.text
    assert "xoxb-" not in telegram.text
    assert "xapp-" not in telegram.text
    assert "TELEGRAM_BOT_TOKEN=" not in telegram.text
    assert "API_KEY=" not in telegram.text
    assert telegram_botfather.status_code == 200
    assert "Telegram BotFather Setup Sheet" in telegram_botfather.text
    assert "Hermes Chief of Staff" in telegram_botfather.text
    assert "Should Trigger Telegram" in telegram_botfather.text
    assert "Should Stay In Slack Only" in telegram_botfather.text
    assert "xoxb-" not in telegram_botfather.text
    assert "xapp-" not in telegram_botfather.text
    assert "sk-" not in telegram_botfather.text
    assert telegram_recipient_template.status_code == 200
    assert "Telegram Recipient ID Reply Template" in telegram_recipient_template.text
    assert "/setup/inputs#telegram-recipient-import" in telegram_recipient_template.text
    assert telegram_recipient_template_json.status_code == 200
    assert telegram_recipient_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/inputs#telegram-recipient-import"
    )
    assert (
        secret_violations(
            {
                "telegram_recipient_template": telegram_recipient_template.text,
                "telegram_recipient_template_json": telegram_recipient_template_json.text,
            }
        )
        == []
    )
    assert telegram_provisioning.status_code == 200
    assert "Telegram Provisioning Pack" in telegram_provisioning.text
    assert "setMyCommands" in telegram_provisioning.text
    assert "xoxb-" not in telegram_provisioning.text
    assert "xapp-" not in telegram_provisioning.text
    assert "sk-" not in telegram_provisioning.text
    assert telegram_provisioning_json.status_code == 200
    assert telegram_provisioning_json.json()["title"] == "Telegram Provisioning Pack"
    assert telegram_provisioning_json.json()["runner"]["default_mode"] == "dry_run"
    assert telegram_provisioning_script.status_code == 200
    assert "Hermes Company OS Telegram provisioning runner" in (telegram_provisioning_script.text)
    assert "sendMessage" in telegram_provisioning_script.text
    assert "xoxb-" not in telegram_provisioning_script.text
    assert "xapp-" not in telegram_provisioning_script.text
    assert "sk-" not in telegram_provisioning_script.text
    assert telegram_policy.status_code == 200
    assert "Telegram Urgent Policy" in telegram_policy.text
    assert "Keep In Slack Only" in telegram_policy.text
    assert telegram_policy_json.status_code == 200
    assert telegram_policy_json.json()["title"] == "Telegram Urgent Policy"
    assert telegram_policy_json.json()["owner_profile"] == "chief-of-staff"
    assert messaging_drill.status_code == 200
    assert "Messaging Drill Pack" in messaging_drill.text
    assert "Slack Profile Drills" in messaging_drill.text
    assert messaging_drill_json.status_code == 200
    assert messaging_drill_json.json()["title"] == "Messaging Drill Pack"
    assert messaging_drill_json.json()["policy"]["telegram_owner"] == "chief-of-staff"
    assert messaging_template.status_code == 200
    assert "Messaging Verification Reply Template" in messaging_template.text
    assert "research-agent-slack-dm" in messaging_template.text
    assert "xoxb-" not in messaging_template.text
    assert "xapp-" not in messaging_template.text
    assert "sk-" not in messaging_template.text
    assert messaging_template_json.status_code == 200
    assert messaging_template_json.json()["title"] == ("Messaging Verification Reply Template")
    assert gateway_operations.status_code == 200
    assert "Hermes Gateway Operations" in gateway_operations.text
    assert ".\\gateway-operations.ps1 -CheckCommands" in gateway_operations.text
    assert "xoxb-" not in gateway_operations.text
    assert "xapp-" not in gateway_operations.text
    assert "sk-" not in gateway_operations.text
    assert gateway_operations_json.status_code == 200
    assert gateway_operations_json.json()["title"] == "Hermes Gateway Operations"
    assert gateway_operations_json.json()["profiles"][0]["commands"]["setup"] == (
        "chief-of-staff gateway setup"
    )
    assert gateway_operations_script.status_code == 200
    assert "Hermes Company OS gateway operations" in gateway_operations_script.text
    assert "Invoke-GatewayAction" in gateway_operations_script.text
    assert "Post-MessagingGatewayStatus" in gateway_operations_script.text
    assert "/setup/messaging-checks/$checkId" in gateway_operations_script.text
    assert "xoxb-" not in gateway_operations_script.text
    assert "xapp-" not in gateway_operations_script.text
    assert "sk-" not in gateway_operations_script.text
    assert llm.status_code == 200
    assert "LLM Provider Setup Plan" in llm.text
    assert "gpt-5-codex" in llm.text
    assert "/setup/llm-credentials.md" in llm.text
    assert "Provider credential" in llm.text
    assert "xoxb-" not in llm.text
    assert "xapp-" not in llm.text
    assert "TELEGRAM_BOT_TOKEN=" not in llm.text
    assert "API_KEY=" not in llm.text
    assert llm_credentials.status_code == 200
    assert "LLM Credential Setup Matrix" in llm_credentials.text
    assert "/setup/profile-llm-env/chief-of-staff.env" in llm_credentials.text
    assert "OPENAI_API_KEY" in llm_credentials.text
    assert llm_provisioning.status_code == 200
    assert "LLM Provisioning Pack" in llm_provisioning.text
    assert "/setup/llm-finalize.ps1" in llm_provisioning.text
    assert llm_provisioning_json.status_code == 200
    assert llm_provisioning_json.json()["title"] == "LLM Provisioning Pack"
    assert llm_provisioning_json.json()["runner"]["route"] == ("/setup/llm-provisioning.ps1")
    assert llm_provisioning_json.json()["verification_last"] is True
    assert llm_provisioning_script.status_code == 200
    assert "Hermes Company OS LLM provisioning runner" in llm_provisioning_script.text
    assert "Dry run only" in llm_provisioning_script.text
    assert "llm.env.example" in llm_provisioning_script.text
    assert "xoxb-" not in llm_provisioning_script.text
    assert "xapp-" not in llm_provisioning_script.text
    assert "sk-" not in llm_provisioning_script.text
    assert llm_provider_presets.status_code == 200
    assert "LLM Provider Presets" in llm_provider_presets.text
    assert "/setup/llm-provider-presets/codex-company-default" in llm_provider_presets.text
    assert "sk-" not in llm_provider_presets.text
    assert llm_provider_presets_json.status_code == 200
    assert llm_provider_presets_json.json()["verification_last"] is True
    assert llm_provider_presets_json.json()["entry_points"]["manual_preferences"] == (
        "/setup/models#models"
    )
    assert llm_preference_template.status_code == 200
    assert "LLM Preference Reply Template" in llm_preference_template.text
    assert "/setup/models#llm-preference-import" in llm_preference_template.text
    assert "xoxb-" not in llm_preference_template.text
    assert "xapp-" not in llm_preference_template.text
    assert "sk-" not in llm_preference_template.text
    assert llm_preference_template_json.status_code == 200
    assert llm_preference_template_json.json()["verification_last"] is True
    assert llm_preference_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/models#llm-preference-import"
    )
    assert llm_finalization.status_code == 200
    assert "LLM Finalization Runner" in llm_finalization.text
    assert "/setup/profile-smoke/chief-of-staff" in llm_finalization.text
    assert llm_finalization_script.status_code == 200
    assert "Hermes Company OS LLM finalization runner" in llm_finalization_script.text
    assert "-AuditLlm" in llm_finalization_script.text
    assert "RunSmokeChecks" in llm_finalization_script.text
    assert "xoxb-" not in llm_finalization_script.text
    assert "xapp-" not in llm_finalization_script.text
    assert "sk-" not in llm_finalization_script.text
    assert llm_smoke.status_code == 200
    assert "LLM Smoke Drill Pack" in llm_smoke.text
    assert "Expected Response Schema" in llm_smoke.text
    assert llm_smoke_json.status_code == 200
    assert llm_smoke_json.json()["title"] == "LLM Smoke Drill Pack"
    assert llm_smoke_json.json()["verification_last"] is True
    assert secret_audit.status_code == 200
    assert "External Secret Audit" in secret_audit.text
    assert "-AuditLlm" in secret_audit.text
    assert secret_audit_script.status_code == 200
    assert "Hermes Company OS external secret audit" in secret_audit_script.text
    assert "PostDashboardStatus" in secret_audit_script.text
    assert "xoxb-" not in secret_audit_script.text
    assert "xapp-" not in secret_audit_script.text
    assert "sk-" not in secret_audit_script.text
    assert hermes_runtime.status_code == 200
    assert "Hermes Runtime Connect" in hermes_runtime.text
    assert "Why We Do Not Clone By Default" in hermes_runtime.text
    assert "hermes doctor" in hermes_runtime.text
    assert "/setup/hermes-install.ps1" in hermes_runtime.text
    assert "xoxb-" not in hermes_runtime.text
    assert "xapp-" not in hermes_runtime.text
    assert "sk-" not in hermes_runtime.text
    assert hermes_runtime_json.status_code == 200
    assert hermes_runtime_json.json()["title"] == "Hermes Runtime Connect"
    assert hermes_runtime_json.json()["decision"]["do_not_vendor_into_dashboard"] is True
    assert hermes_runtime_json.json()["entry_points"]["installer_runner"] == (
        "/setup/hermes-install.ps1"
    )
    assert hermes_install_script.status_code == 200
    assert "Hermes runtime installer helper" in hermes_install_script.text
    assert "RunInstall" in hermes_install_script.text
    assert "Dry run only" in hermes_install_script.text
    assert "xoxb-" not in hermes_install_script.text
    assert "xapp-" not in hermes_install_script.text
    assert "sk-" not in hermes_install_script.text
    assert runtime_preflight.status_code == 200
    assert "Runtime Preflight" in runtime_preflight.text
    assert "Credential Boundary" in runtime_preflight.text
    assert "xoxb-" not in runtime_preflight.text
    assert "xapp-" not in runtime_preflight.text
    assert "sk-" not in runtime_preflight.text
    assert runtime_preflight_json.status_code == 200
    assert runtime_preflight_json.json()["title"] == "Runtime Preflight"
    assert "checks" in runtime_preflight_json.json()
    assert runtime_preflight_script.status_code == 200
    assert "Hermes Company OS runtime preflight runner" in runtime_preflight_script.text
    assert "FailOnMissing" in runtime_preflight_script.text
    assert "SLACK_BOT_TOKEN" not in runtime_preflight_script.text
    assert "TELEGRAM_BOT_TOKEN" not in runtime_preflight_script.text
    assert "sk-" not in runtime_preflight_script.text
    assert schedule_provisioning.status_code == 200
    assert "Schedule Provisioning Pack" in schedule_provisioning.text
    assert "Morning Standup" in schedule_provisioning.text
    assert "xoxb-" not in schedule_provisioning.text
    assert "xapp-" not in schedule_provisioning.text
    assert "sk-" not in schedule_provisioning.text
    assert schedule_provisioning_json.status_code == 200
    assert schedule_provisioning_json.json()["title"] == "Schedule Provisioning Pack"
    assert schedule_provisioning_json.json()["runner"]["default_mode"] == "dry_run"
    assert schedule_provisioning_script.status_code == 200
    assert "Hermes Company OS schedule provisioning runner" in (schedule_provisioning_script.text)
    assert '"cron" "create"' in schedule_provisioning_script.text
    assert "xoxb-" not in schedule_provisioning_script.text
    assert "xapp-" not in schedule_provisioning_script.text
    assert "sk-" not in schedule_provisioning_script.text
    assert schedule_config_template.status_code == 200
    assert "Schedule Configuration Reply Template" in schedule_config_template.text
    assert "/setup/schedules#schedule-config-import" in schedule_config_template.text
    assert schedule_config_template_json.status_code == 200
    assert schedule_config_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/schedules#schedule-config-import"
    )
    assert (
        secret_violations(
            {
                "schedule_config_template": schedule_config_template.text,
                "schedule_config_template_json": schedule_config_template_json.text,
            }
        )
        == []
    )
    assert schedule_template.status_code == 200
    assert "Schedule Verification Reply Template" in schedule_template.text
    assert "morning-standup-manual-run" in schedule_template.text
    assert "xoxb-" not in schedule_template.text
    assert "xapp-" not in schedule_template.text
    assert "sk-" not in schedule_template.text
    assert schedule_template_json.status_code == 200
    assert schedule_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/verification#schedule-verification"
    )
    assert standup_preview.status_code == 200
    assert "Standup Preview And Drill Pack" in standup_preview.text
    assert "Founder approval needed" in standup_preview.text
    assert standup_preview_json.status_code == 200
    assert standup_preview_json.json()["title"] == "Standup Preview And Drill Pack"
    assert standup_preview_json.json()["delivery_policy"]["primary_workspace"] == "slack"
    assert standup_runbook.status_code == 200
    assert "Standup Scheduling Runbook" in standup_runbook.text
    assert "Morning Standup" in standup_runbook.text
    assert "chief-of-staff cron create" in standup_runbook.text
    assert "TELEGRAM_BOT_TOKEN" not in standup_runbook.text
    assert standup_cron.status_code == 200
    assert "Hermes Company OS standup cron installer" in standup_cron.text
    assert 'chief-of-staff cron create "every day at 9am"' in standup_cron.text
    assert "xoxb-" not in standup_cron.text
    assert idea_intake.status_code == 200
    assert "Founder Idea Intake Packet" in idea_intake.text
    assert "project_name=" in idea_intake.text
    assert "founder_idea=" in idea_intake.text
    assert "xoxb-" not in idea_intake.text
    assert "xapp-" not in idea_intake.text
    assert "TELEGRAM_BOT_TOKEN=" not in idea_intake.text
    assert "API_KEY=" not in idea_intake.text
    assert idea_intake_json.status_code == 200
    assert idea_intake_json.json()["title"] == "Founder Idea Intake Packet"
    assert idea_intake_json.json()["entry_points"]["projects"] == "/projects"
    assert project_workflow.status_code == 200
    assert "Project Workflow And Kanban Handoff" in project_workflow.text
    assert "Kanban Create Shape" in project_workflow.text
    assert project_workflow_json.status_code == 200
    assert project_workflow_json.json()["title"] == "Project Workflow And Kanban Handoff"
    assert project_workflow_json.json()["kanban_create_shape"]["remote_id_storage"] == (
        "tasks.kanban_task_id"
    )
    assert kanban_provisioning.status_code == 200
    assert "Kanban Provisioning Pack" in kanban_provisioning.text
    assert "Board Lanes" in kanban_provisioning.text
    assert "xoxb-" not in kanban_provisioning.text
    assert "xapp-" not in kanban_provisioning.text
    assert "sk-" not in kanban_provisioning.text
    assert kanban_provisioning_json.status_code == 200
    assert kanban_provisioning_json.json()["title"] == "Kanban Provisioning Pack"
    assert kanban_provisioning_json.json()["runner"]["default_mode"] == "dry_run"
    assert kanban_provisioning_script.status_code == 200
    assert "Hermes Company OS Kanban provisioning runner" in kanban_provisioning_script.text
    assert "hermes kanban diagnostics --json" in kanban_provisioning_script.text
    assert "xoxb-" not in kanban_provisioning_script.text
    assert "xapp-" not in kanban_provisioning_script.text
    assert "sk-" not in kanban_provisioning_script.text
    assert kanban_template.status_code == 200
    assert "Kanban Verification Reply Template" in kanban_template.text
    assert "kanban-board-initialized" in kanban_template.text
    assert "xoxb-" not in kanban_template.text
    assert "xapp-" not in kanban_template.text
    assert secret_violations({"kanban_template": kanban_template.text}) == []
    assert kanban_template_json.status_code == 200
    assert kanban_template_json.json()["entry_points"]["bulk_import"] == (
        "/setup/verification#kanban-verification"
    )
    assert kanban_runbook.status_code == 200
    assert "Hermes Kanban Setup Runbook" in kanban_runbook.text
    assert "Workflow Templates That Push To Kanban" in kanban_runbook.text
    assert "hermes kanban diagnostics --json" in kanban_runbook.text
    assert "TELEGRAM_BOT_TOKEN" not in kanban_runbook.text
    assert kanban_diagnostics.status_code == 200
    assert "Hermes Company OS Kanban diagnostics" in kanban_diagnostics.text
    assert "hermes kanban init" in kanban_diagnostics.text
    assert "hermes kanban diagnostics --json" in kanban_diagnostics.text
    assert "sk-" not in kanban_diagnostics.text
    assert activation_sequence.status_code == 200
    assert "Founder Activation Sequence" in activation_sequence.text
    assert "Next Best Action" in activation_sequence.text
    assert "/setup/hermes-install.ps1" in activation_sequence.text
    assert "/setup/llm-provisioning.md" in activation_sequence.text
    assert "/setup/llm-provisioning.ps1" in activation_sequence.text
    assert "/setup/llm-credentials.md" in activation_sequence.text
    assert "/setup/llm-finalize.md" in activation_sequence.text
    assert "/setup/llm-smoke.md" in activation_sequence.text
    assert "/setup/llm-smoke.json" in activation_sequence.text
    assert "/setup/verification-evidence.md" in activation_sequence.text
    assert "/setup/verification-evidence.json" in activation_sequence.text
    assert "/setup/slack-workspace.md" in activation_sequence.text
    assert "/setup/slack-provisioning.md" in activation_sequence.text
    assert "/setup/slack-provisioning.ps1" in activation_sequence.text
    assert "/setup/slack-bot-user-map.json" in activation_sequence.text
    assert "/setup/telegram-policy.md" in activation_sequence.text
    assert "/setup/telegram-provisioning.md" in activation_sequence.text
    assert "/setup/telegram-provisioning.ps1" in activation_sequence.text
    assert "/setup/messaging-drill.md" in activation_sequence.text
    assert "/setup/messaging-drill.json" in activation_sequence.text
    assert "/setup/gateway-operations.md" in activation_sequence.text
    assert "/setup/gateway-operations.json" in activation_sequence.text
    assert "/setup/gateway-operations.ps1" in activation_sequence.text
    assert "/setup/secret-audit.ps1" in activation_sequence.text
    assert "/setup/activation-runner.md" in activation_sequence.text
    assert "/setup/company-manifest.md" in activation_sequence.text
    assert "/setup/company-manifest.json" in activation_sequence.text
    assert "/setup/founder-handoff.md" in activation_sequence.text
    assert "/setup/founder-handoff.json" in activation_sequence.text
    assert "/setup/input-ledger.md" in activation_sequence.text
    assert "/setup/input-ledger.json" in activation_sequence.text
    assert "/setup/credential-loading.md" in activation_sequence.text
    assert "/setup/credential-loading.json" in activation_sequence.text
    assert "/setup/founder-next-actions.md" in activation_sequence.text
    assert "/setup/founder-next-actions.json" in activation_sequence.text
    assert "/setup/kickoff-readiness.md" in activation_sequence.text
    assert "/setup/kickoff-readiness.json" in activation_sequence.text
    assert "/setup/delegation-playbook.md" in activation_sequence.text
    assert "/setup/delegation-playbook.json" in activation_sequence.text
    assert "/setup/profile-installation.md" in activation_sequence.text
    assert "/setup/profile-installation.json" in activation_sequence.text
    assert "/setup/profile-installation.ps1" in activation_sequence.text
    assert "/setup/schedule-provisioning.md" in activation_sequence.text
    assert "/setup/schedule-provisioning.ps1" in activation_sequence.text
    assert "/setup/standup-preview.md" in activation_sequence.text
    assert "/setup/standup-preview.json" in activation_sequence.text
    assert "/setup/idea-intake.md" in activation_sequence.text
    assert "/setup/idea-intake.json" in activation_sequence.text
    assert "/setup/project-workflow.md" in activation_sequence.text
    assert "/setup/project-workflow.json" in activation_sequence.text
    assert "/setup/kanban-provisioning.md" in activation_sequence.text
    assert "/setup/kanban-provisioning.ps1" in activation_sequence.text
    assert "/setup/profile-acceptance.md" in activation_sequence.text
    assert "xoxb-" not in activation_sequence.text
    assert "xapp-" not in activation_sequence.text
    assert "sk-" not in activation_sequence.text
    assert activation_runner.status_code == 200
    assert "Local Activation Runner" in activation_runner.text
    assert "/setup/activation-runner.ps1" in activation_runner.text
    assert "- `-InstallHermes`" in activation_runner.text
    assert "/setup/hermes-install.ps1" in activation_runner.text
    assert activation_runner_script.status_code == 200
    assert "Hermes Company OS local activation runner" in activation_runner_script.text
    assert "InstallHermes" in activation_runner_script.text
    assert "/setup/hermes-install.ps1" in activation_runner_script.text
    assert "/setup/profile-apply/chief-of-staff.ps1" in activation_runner_script.text
    assert "/setup/slack-provisioning.ps1" in activation_runner_script.text
    assert "/setup/telegram-provisioning.ps1" in activation_runner_script.text
    assert "/setup/schedule-provisioning.ps1" in activation_runner_script.text
    assert "/setup/llm-provisioning.ps1" in activation_runner_script.text
    assert "ExecuteProvisioning" in activation_runner_script.text
    assert "RunSmokeChecks" in activation_runner_script.text
    assert "xoxb-" not in activation_runner_script.text
    assert "xapp-" not in activation_runner_script.text
    assert "sk-" not in activation_runner_script.text
    assert live_verification.status_code == 200
    assert "Live Verification Runbook" in live_verification.text
    assert "Current Verification Counts" in live_verification.text
    assert "Profile installation checks: 0 verified" in live_verification.text
    assert "Profile installation checks: none tracked." not in live_verification.text
    assert "Profile acceptance checks: 0 verified" in live_verification.text
    assert "Profile acceptance checks: none tracked." not in live_verification.text
    assert "/setup/profiles#profile-acceptance-tracking" in live_verification.text
    assert "/setup/profiles#profile-smoke" in live_verification.text
    assert "xoxb-" not in live_verification.text
    assert "xapp-" not in live_verification.text
    assert "sk-" not in live_verification.text
    assert verification_evidence.status_code == 200
    assert "Verification Evidence Pack" in verification_evidence.text
    assert "Verified items missing evidence" in verification_evidence.text
    assert "Private reply observed" not in verification_evidence.text
    assert "xoxb-" not in verification_evidence.text
    assert "xapp-" not in verification_evidence.text
    assert "sk-" not in verification_evidence.text
    assert verification_evidence_json.status_code == 200
    verification_payload = verification_evidence_json.json()
    assert verification_payload["title"] == "Verification Evidence Pack"
    assert any(phase["id"] == "profile_installation" for phase in verification_payload["phases"])
    assert verification_payload["entry_points"]["live_verification"] == (
        "/setup/live-verification.md"
    )
    assert "phases" in verification_payload
    assert activation.status_code == 200
    assert "Hermes Activation Checklist" in activation.text
    assert "/setup/slack-manifest/chief-of-staff.json" in activation.text
    assert "/setup/profile-llm-env/<profile>.env" in activation.text
    assert "xoxb-" not in activation.text
    assert "xapp-" not in activation.text
    assert "TELEGRAM_BOT_TOKEN=" not in activation.text
    assert "API_KEY=" not in activation.text
    assert "/setup/standup-runbook.md" in activation.text
    assert "/setup/kanban-runbook.md" in activation.text


def test_profile_llm_env_route_returns_404_for_unknown_profile(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/setup/profile-llm-env/missing-agent.env")

    assert response.status_code == 404


def test_slack_manifest_routes_export_no_secret_json(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.repository.update_setup_inputs({"slack_channel_engineering": "C123"})
    client = TestClient(app)

    response = client.get("/setup/slack-manifest/engineering-manager.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    manifest = response.json()
    assert manifest["display_information"]["name"] == "Hermes Engineering Manager"
    assert manifest["features"]["bot_user"]["display_name"] == ("Hermes Engineering Manager")
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert "chat:write" in manifest["oauth_config"]["scopes"]["bot"]
    assert "message.im" in manifest["settings"]["event_subscriptions"]["bot_events"]
    raw = json.dumps(manifest)
    assert "C123" in raw
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "SLACK_BOT_TOKEN" not in raw


def test_slack_manifest_bundle_route_exports_all_profiles(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/setup/slack-manifests.json")

    assert response.status_code == 200
    bundle = response.json()
    assert set(bundle) == {
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
    assert bundle["chief-of-staff"]["profile"]["hermes_command"] == "chief-of-staff"
    assert bundle["chief-of-staff"]["manifest"]["settings"]["socket_mode_enabled"] is True


def test_slack_manifest_route_returns_404_for_unknown_profile(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.get("/setup/slack-manifest/missing-agent.json")

    assert response.status_code == 404


def test_setup_integration_status_update(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/integrations/telegram-founder-alerts",
        data={"status": "configured"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    integration = next(
        item
        for item in app.state.repository.list_integrations()
        if item["id"] == "telegram-founder-alerts"
    )
    assert integration["status"] == "configured"


def test_setup_inputs_update_route(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/inputs",
        data={
            "founder_name": "Masad",
            "founder_slack_member_id": "U123",
            "founder_telegram_user_id": "123456",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    values = app.state.repository.setup_input_map()
    assert values["founder_name"] == "Masad"
    assert values["founder_slack_member_id"] == "U123"
    assert values["founder_telegram_user_id"] == "123456"


def test_founder_input_reply_import_route_updates_safe_inputs_only(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/founder-input-reply",
        data={
            "reply_text": """
            founder_name=Masad
            slack_workspace_name=Hermes Lab
            founder_slack_member_id=U123
            llm_provider=openai
            unknown_key=value
            not a key value line
            """,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/inputs?input_imported=3&input_unknown=1&input_deferred=1&input_ignored=1#inputs"
    )
    values = app.state.repository.setup_input_map()
    assert values["founder_name"] == "Masad"
    assert values["slack_workspace_name"] == "Hermes Lab"
    assert values["founder_slack_member_id"] == "U123"
    assert values["llm_provider"] == ""


def test_founder_input_reply_import_route_rejects_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/founder-input-reply",
        data={
            "reply_text": ("founder_name=Masad\nslack_bot_token=" + FAKE_SLACK_BOT_SECRET),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["founder_name"] == ""


def test_slack_channel_reply_import_route_updates_safe_channel_ids(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/slack-channel-reply",
        data={
            "reply_text": """
            slack_channel_founder_command=CFOUNDER123
            #engineering=CENGINEER123
            missing-channel=CUNKNOWN123
            not a key value line
            """,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/inputs?slack_channel_imported=2&slack_channel_unknown=1"
        "&slack_channel_invalid=0&slack_channel_ignored=1"
        "#slack-channel-import"
    )
    values = app.state.repository.setup_input_map()
    assert values["slack_channel_founder_command"] == "CFOUNDER123"
    assert values["slack_channel_engineering"] == "CENGINEER123"
    workspace = client.get("/setup/slack-workspace.md")
    assert "CENGINEER123" in workspace.text


def test_slack_channel_reply_import_route_rejects_invalid_ids(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/slack-channel-reply",
        data={"reply_text": '{"channel_ids":{"slack_channel_engineering":"bad-id"}}'},
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["slack_channel_engineering"] == ""


def test_slack_channel_reply_import_route_rejects_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/slack-channel-reply",
        data={
            "reply_text": (
                "slack_channel_engineering=CENGINEER123\nslack_bot_token=" + FAKE_SLACK_BOT_SECRET
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["slack_channel_engineering"] == ""


def test_slack_bot_user_reply_import_route_updates_safe_bot_ids(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/slack-bot-user-map-reply",
        data={
            "reply_text": """
            chief-of-staff=U012ABCDEF
            engineering-manager=U045GHIJKL
            missing-profile=U999AAAAAA
            not a key value line
            """,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/inputs?slack_bot_user_imported=2&slack_bot_user_unknown=1"
        "&slack_bot_user_invalid=0&slack_bot_user_ignored=1"
        "#slack-bot-user-import"
    )
    values = app.state.repository.setup_input_map()
    assert values["slack_bot_user_id_chief_of_staff"] == "U012ABCDEF"
    assert values["slack_bot_user_id_engineering_manager"] == "U045GHIJKL"
    assert client.get("/setup/slack-bot-user-map.json").json()["chief-of-staff"] == ("U012ABCDEF")


def test_slack_bot_user_reply_import_route_rejects_invalid_ids(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/slack-bot-user-map-reply",
        data={"reply_text": '{"bot_user_ids":{"chief-of-staff":"not-a-slack-id"}}'},
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["slack_bot_user_id_chief_of_staff"] == ""


def test_slack_bot_user_reply_import_route_rejects_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/slack-bot-user-map-reply",
        data={
            "reply_text": ("chief-of-staff=U012ABCDEF\nslack_bot_token=" + FAKE_SLACK_BOT_SECRET),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["slack_bot_user_id_chief_of_staff"] == ""


def test_telegram_recipient_reply_import_route_updates_safe_ids(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/telegram-recipient-reply",
        data={
            "reply_text": """
            founder_telegram_user_id=123456789
            telegram_home_channel=-100987654321
            unknown_key=123
            ignored line
            """,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/inputs?telegram_recipient_imported=2&telegram_recipient_unknown=1"
        "&telegram_recipient_invalid=0&telegram_recipient_ignored=1"
        "#telegram-recipient-import"
    )
    values = app.state.repository.setup_input_map()
    assert values["founder_telegram_user_id"] == "123456789"
    assert values["telegram_home_channel"] == "-100987654321"
    policy = client.get("/setup/telegram-policy.json").json()
    assert policy["founder_telegram_user_id"] == "123456789"
    assert policy["telegram_home_channel"] == "-100987654321"


def test_telegram_recipient_reply_import_route_rejects_invalid_ids(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/telegram-recipient-reply",
        data={"reply_text": '{"founder_telegram_user_id":"not-a-number"}'},
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["founder_telegram_user_id"] == ""


def test_telegram_recipient_reply_import_route_rejects_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/telegram-recipient-reply",
        data={
            "reply_text": ("founder_telegram_user_id=123456789\n" + FAKE_LOWER_TELEGRAM_ENV_SECRET),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    values = app.state.repository.setup_input_map()
    assert values["founder_telegram_user_id"] == ""


def test_credential_status_reply_import_route_updates_secret_statuses(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/credential-status-reply",
        data={
            "reply_text": (
                "chief-of-staff-slack-bot-token=loaded | Loaded in profile env.\n"
                "chief-of-staff-llm-provider-credential=deferred\n"
                "missing-requirement=loaded\n"
                "not a status line"
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/messaging?credential_imported=2&credential_unknown=1"
        "&credential_invalid=0&credential_ignored=1#secret-status"
    )
    slack_requirement = app.state.repository.get_secret_requirement(
        "chief-of-staff-slack-bot-token"
    )
    llm_requirement = app.state.repository.get_secret_requirement(
        "chief-of-staff-llm-provider-credential"
    )
    assert slack_requirement["status"] == "loaded"
    assert slack_requirement["notes"] == "Loaded in profile env."
    assert llm_requirement["status"] == "deferred"
    assert llm_requirement["notes"] == (
        "Final provider credentials are configured after messaging is ready."
    )


def test_credential_status_reply_import_route_rejects_invalid_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/credential-status-reply",
        data={"reply_text": "chief-of-staff-slack-bot-token=done"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    requirement = app.state.repository.get_secret_requirement("chief-of-staff-slack-bot-token")
    assert requirement["status"] == "needed"


def test_credential_status_reply_import_route_rejects_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/credential-status-reply",
        data={
            "reply_text": ("chief-of-staff-slack-bot-token=loaded | " + FAKE_SLACK_BOT_SECRET),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    requirement = app.state.repository.get_secret_requirement("chief-of-staff-slack-bot-token")
    assert requirement["status"] == "needed"


def test_setup_inputs_reject_secret_like_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/inputs",
        data={
            "founder_name": "Masad",
            "llm_provider": FAKE_OPENAI_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Do not paste secret values" in response.text
    values = app.state.repository.setup_input_map()
    assert values["founder_name"] == ""
    assert values["llm_provider"] == ""


def test_schedule_config_reply_import_route_updates_schedule_metadata(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-config-reply",
        data={
            "reply_text": """
            morning-standup.hour=10
            morning-standup.minute=30
            morning-standup.slack_channel=CSTANDUP123
            afternoon-standup.name=Founder sync
            missing-standup.hour=8
            ignored line
            """,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/schedules?schedule_config_imported=2&schedule_config_unknown=1"
        "&schedule_config_invalid=0&schedule_config_ignored=1"
        "#schedule-config-import"
    )
    morning = app.state.repository.get_schedule("morning-standup")
    afternoon = app.state.repository.get_schedule("afternoon-standup")
    assert morning["hour"] == 10
    assert morning["minute"] == 30
    assert morning["slack_channel"] == "CSTANDUP123"
    assert morning["timezone"] == "America/New_York"
    assert afternoon["name"] == "Founder sync"
    assert (
        client.get("/setup/schedule-provisioning.json").json()["active_schedules"][0][
            "slack_channel"
        ]
        == "CSTANDUP123"
    )


def test_schedule_config_reply_import_route_rejects_invalid_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-config-reply",
        data={"reply_text": "morning-standup.hour=26"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    schedule = app.state.repository.get_schedule("morning-standup")
    assert schedule["hour"] == 9


def test_schedule_config_reply_import_route_rejects_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-config-reply",
        data={
            "reply_text": (
                "morning-standup.hour=10\nmorning-standup.telegram_policy=Use " + FAKE_OPENAI_SECRET
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    schedule = app.state.repository.get_schedule("morning-standup")
    assert schedule["hour"] == 9


def test_model_preference_update_route_changes_config_export(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/model-preferences/research-agent",
        data={
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "openai-codex",
            "fallback_model": "gpt-5-codex",
            "auth_method": "profile_env",
            "status": "needs_secret",
            "notes": "Use for research-heavy work.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["provider"] == "openrouter"
    config = client.get("/setup/profile-config/research-agent.yaml")
    assert 'provider: "openrouter"' in config.text
    assert 'model: "anthropic/claude-sonnet-4"' in config.text


def test_model_preference_update_route_rejects_manual_verified_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/model-preferences/research-agent",
        data={
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "",
            "fallback_model": "",
            "auth_method": "profile_env",
            "status": "verified",
            "notes": "Trying to bypass smoke.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "profile smoke check" in response.text
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["status"] == "planned"


def test_llm_preference_reply_import_updates_config_export(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/llm-preference-reply",
        data={
            "reply_text": json.dumps(
                {
                    "preferences": [
                        {
                            "agent_id": "research-agent",
                            "provider": "openrouter",
                            "model": "anthropic/claude-sonnet-4",
                            "fallback_provider": "openai-codex",
                            "fallback_model": "gpt-5-codex",
                            "auth_method": "profile_env",
                            "status": "needs_secret",
                            "notes": "Use for research-heavy work.",
                        }
                    ]
                }
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/models?llm_preference_imported=1"
        "&llm_preference_unknown=0"
        "&llm_preference_invalid=0"
        "&llm_preference_ignored=0#llm-preference-import"
    )
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["provider"] == "openrouter"
    assert preference["status"] == "needs_secret"
    config = client.get("/setup/profile-config/research-agent.yaml")
    assert 'provider: "openrouter"' in config.text
    assert 'model: "anthropic/claude-sonnet-4"' in config.text


def test_llm_preference_reply_import_rejects_verified_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/llm-preference-reply",
        data={
            "reply_text": json.dumps(
                {"preferences": [{"agent_id": "research-agent", "status": "verified"}]}
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["status"] == "planned"


def test_llm_preference_reply_import_rejects_secret_text(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/llm-preference-reply",
        data={
            "reply_text": json.dumps(
                {
                    "preferences": [
                        {
                            "agent_id": "research-agent",
                            "notes": FAKE_OPENAI_ENV_SECRET,
                        }
                    ]
                }
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    preference = app.state.repository.get_model_preference("research-agent")
    assert "OPENAI_API_KEY" not in preference["notes"]


def test_llm_preference_reply_import_downgrades_previous_verified_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_profile_llm_verified(app.state.repository, "research-agent")
    client = TestClient(app)

    response = client.post(
        "/setup/llm-preference-reply",
        data={
            "reply_text": json.dumps(
                {
                    "preferences": [
                        {
                            "agent_id": "research-agent",
                            "provider": "openrouter",
                            "model": "anthropic/claude-sonnet-4",
                        }
                    ]
                }
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["provider"] == "openrouter"
    assert preference["status"] == "ready_for_verification"


def test_llm_preference_reply_import_rejects_invalid_json(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/llm-preference-reply",
        data={"reply_text": "not json"},
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_apply_llm_provider_preset_updates_all_profile_preferences(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/llm-provider-presets/openrouter-research-heavy",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/setup/models#models"
    research = app.state.repository.get_model_preference("research-agent")
    engineering = app.state.repository.get_model_preference("engineering-manager")
    product = app.state.repository.get_model_preference("product-manager")
    assert research["provider"] == "openrouter"
    assert research["model"] == "anthropic/claude-sonnet-4"
    assert research["fallback_provider"] == "openai-codex"
    assert engineering["provider"] == "openrouter"
    assert product["provider"] == "openai-codex"
    assert product["status"] == "needs_secret"
    assert "Credentials remain external" in research["notes"]


def test_apply_llm_provider_preset_returns_404_for_unknown_preset(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/llm-provider-presets/missing-preset",
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert app.state.repository.get_model_preference("research-agent")["provider"] == (
        "openai-codex"
    )


def test_model_preference_update_route_rejects_secret_notes(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/model-preferences/research-agent",
        data={
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
            "fallback_provider": "",
            "fallback_model": "",
            "auth_method": "profile_env",
            "status": "needs_secret",
            "notes": FAKE_OPENAI_ENV_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["provider"] == "openai-codex"
    assert "OPENAI_API_KEY" not in preference["notes"]


def test_secret_requirement_update_route_changes_readiness_report(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/secret-requirements/chief-of-staff-slack-bot-token",
        data={"status": "loaded", "notes": "Loaded in Hermes profile .env."},
        follow_redirects=False,
    )

    assert response.status_code == 303
    requirement = app.state.repository.get_secret_requirement("chief-of-staff-slack-bot-token")
    assert requirement["status"] == "loaded"
    assert "Loaded in Hermes profile" in requirement["notes"]
    report = client.get("/setup/readiness-report.md")
    assert "External secret status" in report.text


def test_secret_requirement_update_route_rejects_manual_llm_verified_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/secret-requirements/chief-of-staff-llm-provider-credential",
        data={"status": "verified", "notes": "Trying to bypass smoke."},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "successful profile smoke check" in response.text
    requirement = app.state.repository.get_secret_requirement(
        "chief-of-staff-llm-provider-credential"
    )
    assert requirement["status"] == "deferred"


def test_credential_status_reply_import_route_rejects_manual_llm_verified_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/credential-status-reply",
        data={"reply_text": "chief-of-staff-llm-provider-credential=verified"},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "successful profile smoke check" in response.text
    requirement = app.state.repository.get_secret_requirement(
        "chief-of-staff-llm-provider-credential"
    )
    assert requirement["status"] == "deferred"


def test_secret_requirement_update_route_rejects_secret_notes(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/secret-requirements/chief-of-staff-slack-bot-token",
        data={
            "status": "loaded",
            "notes": FAKE_SLACK_BOT_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    requirement = app.state.repository.get_secret_requirement("chief-of-staff-slack-bot-token")
    assert requirement["status"] == "needed"
    assert "abcdefABCDEF" not in requirement["notes"]


def test_messaging_check_update_route_changes_readiness_report(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_messaging_credentials_loaded(app.state.repository, "slack", "research-agent")
    client = TestClient(app)

    response = client.post(
        "/setup/messaging-checks/research-agent-slack-dm",
        data={
            "status": "verified",
            "evidence": "Founder DM reply observed at 9:12 AM.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    check = app.state.repository.get_messaging_check("research-agent-slack-dm")
    assert check["status"] == "verified"
    assert check["evidence"] == "Founder DM reply observed at 9:12 AM."
    report = client.get("/setup/readiness-report.md")
    assert "Messaging verification" in report.text


def test_messaging_verification_reply_import_updates_loaded_and_verified_checks(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_messaging_credentials_loaded(app.state.repository, "slack", "research-agent")
    client = TestClient(app)

    response = client.post(
        "/setup/messaging-verification-reply",
        data={
            "reply_text": (
                "research-agent-slack-gateway=loaded | Gateway setup completed.\n"
                "research-agent-slack-dm=verified | Founder DM reply observed."
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "messaging_imported=2" in response.headers["location"]
    gateway = app.state.repository.get_messaging_check("research-agent-slack-gateway")
    dm = app.state.repository.get_messaging_check("research-agent-slack-dm")
    assert gateway["status"] == "loaded"
    assert gateway["evidence"] == "Gateway setup completed."
    assert dm["status"] == "verified"
    assert dm["evidence"] == "Founder DM reply observed."


def test_messaging_verification_reply_import_requires_credentials_for_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/messaging-verification-reply",
        data={"reply_text": ("research-agent-slack-dm=verified | Founder DM reply observed.")},
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Mark external slack credential status loaded" in response.text
    check = app.state.repository.get_messaging_check("research-agent-slack-dm")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_messaging_verification_reply_import_rejects_invalid_and_secret_values(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    invalid = client.post(
        "/setup/messaging-verification-reply",
        data={"reply_text": "research-agent-slack-dm=done"},
        follow_redirects=False,
    )
    secret = client.post(
        "/setup/messaging-verification-reply",
        data={"reply_text": ("research-agent-slack-dm=loaded | " + FAKE_SHORT_SLACK_BOT_SECRET)},
        follow_redirects=False,
    )

    assert invalid.status_code == 400
    assert "Invalid messaging status" in invalid.text
    assert secret.status_code == 400
    check = app.state.repository.get_messaging_check("research-agent-slack-dm")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_messaging_check_update_requires_loaded_platform_credentials(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    setup = client.get("/setup/messaging")
    response = client.post(
        "/setup/messaging-checks/research-agent-slack-dm",
        data={
            "status": "verified",
            "evidence": "Founder DM reply observed at 9:12 AM.",
        },
        follow_redirects=False,
    )

    assert setup.status_code == 200
    assert "Mark external slack credential status loaded" in setup.text
    assert response.status_code == 409
    assert "Mark external slack credential status loaded" in response.text
    check = app.state.repository.get_messaging_check("research-agent-slack-dm")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_messaging_check_update_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/messaging-checks/research-agent-slack-dm",
        data={
            "status": "verified",
            "evidence": FAKE_SLACK_APP_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_messaging_check("research-agent-slack-dm")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_messaging_checks_configure_slack_integrations_when_all_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_messaging_credentials_loaded(app.state.repository, "slack")
    client = TestClient(app)

    slack_checks = [
        check
        for check in app.state.repository.list_messaging_checks()
        if check["platform"] == "slack"
    ]
    for check in slack_checks:
        response = client.post(
            f"/setup/messaging-checks/{check['id']}",
            data={"status": "verified", "evidence": "Verified externally."},
            follow_redirects=False,
        )
        assert response.status_code == 303

    slack_integrations = [
        item for item in app.state.repository.list_integrations() if item["category"] == "slack"
    ]
    assert slack_integrations
    assert all(item["status"] == "configured" for item in slack_integrations)


def test_schedule_update_route_changes_generated_cron(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedules/afternoon-standup",
        data={
            "name": "Late founder sync",
            "hour": "18",
            "minute": "30",
            "timezone": "America/New_York",
            "slack_channel": "#agent-standup",
            "telegram_policy": "urgent only",
            "active": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    schedule = app.state.repository.get_schedule("afternoon-standup")
    assert schedule["name"] == "Late founder sync"
    assert "Late founder sync" in client.get("/setup/schedules").text
    assert "every day at 6:30pm" in client.get("/setup/commands").text


def test_schedule_check_update_route_changes_readiness_report(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    mark_all_messaging_verified(app.state.repository)
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-checks/morning-standup-manual-run",
        data={
            "status": "verified",
            "evidence": "Manual standup run posted summary to Slack.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    check = app.state.repository.get_schedule_check("morning-standup-manual-run")
    assert check["status"] == "verified"
    assert check["evidence"] == "Manual standup run posted summary to Slack."
    report = client.get("/setup/readiness-report.md")
    assert "Schedule verification" in report.text


def test_schedule_check_update_requires_chief_llm_and_messaging_first(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    setup = client.get("/setup/verification")
    blocked_by_llm = client.post(
        "/setup/schedule-checks/morning-standup-manual-run",
        data={
            "status": "verified",
            "evidence": "Manual standup run posted summary to Slack.",
        },
        follow_redirects=False,
    )
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    blocked_by_messaging = client.post(
        "/setup/schedule-checks/morning-standup-manual-run",
        data={
            "status": "verified",
            "evidence": "Manual standup run posted summary to Slack.",
        },
        follow_redirects=False,
    )

    assert setup.status_code == 200
    assert "Complete Chief of Staff LLM verification" in setup.text
    assert blocked_by_llm.status_code == 409
    assert "Complete Chief of Staff LLM verification" in blocked_by_llm.text
    assert blocked_by_messaging.status_code == 409
    assert "Complete Slack messaging verification" in blocked_by_messaging.text
    check = app.state.repository.get_schedule_check("morning-standup-manual-run")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_cron_schedule_check_requires_manual_run_first(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    mark_all_messaging_verified(app.state.repository)
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-checks/morning-standup-cron-installed",
        data={
            "status": "verified",
            "evidence": "cron list shows morning job",
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Verify the manual dashboard run for Morning Standup" in response.text
    check = app.state.repository.get_schedule_check("morning-standup-cron-installed")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_schedule_check_update_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-checks/morning-standup-manual-run",
        data={
            "status": "verified",
            "evidence": FAKE_TELEGRAM_ENV_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_schedule_check("morning-standup-manual-run")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_schedule_verification_reply_import_requires_prerequisites(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-verification-reply",
        data={
            "reply_text": (
                "morning-standup-manual-run=verified | Manual run posted.\n"
                "morning-standup-cron-installed=verified | Cron list showed job."
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert "Complete Chief of Staff LLM verification" in response.text
    manual = app.state.repository.get_schedule_check("morning-standup-manual-run")
    cron = app.state.repository.get_schedule_check("morning-standup-cron-installed")
    assert manual["status"] == "needed"
    assert cron["status"] == "needed"


def test_schedule_verification_reply_import_updates_with_staged_manual_run(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    mark_all_messaging_verified(app.state.repository)
    client = TestClient(app)

    lines = []
    for check in app.state.repository.list_schedule_checks():
        lines.append(f"{check['id']}=verified | {check['label']} verified externally.")
    response = client.post(
        "/setup/schedule-verification-reply",
        data={"reply_text": "\n".join(reversed(lines))},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/verification?schedule_imported=4&schedule_unknown=0"
        "&schedule_invalid=0&schedule_ignored=0#schedule-verification"
    )
    for check in app.state.repository.list_schedule_checks():
        assert check["status"] == "verified"
        assert check["evidence"].endswith("verified externally.")
    integration = next(
        item for item in app.state.repository.list_integrations() if item["id"] == "standup-cron"
    )
    assert integration["status"] == "configured"


def test_schedule_verification_reply_import_rejects_invalid_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-verification-reply",
        data={"reply_text": "morning-standup-manual-run=done"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_schedule_check("morning-standup-manual-run")
    assert check["status"] == "needed"


def test_schedule_verification_reply_import_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    mark_all_messaging_verified(app.state.repository)
    client = TestClient(app)

    response = client.post(
        "/setup/schedule-verification-reply",
        data={"reply_text": ("morning-standup-manual-run=verified | " + FAKE_TELEGRAM_ENV_SECRET)},
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_schedule_check("morning-standup-manual-run")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_schedule_checks_configure_standup_cron_when_active_checks_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    mark_all_messaging_verified(app.state.repository)
    client = TestClient(app)

    for check in app.state.repository.list_schedule_checks():
        response = client.post(
            f"/setup/schedule-checks/{check['id']}",
            data={"status": "verified", "evidence": "Verified externally."},
            follow_redirects=False,
        )
        assert response.status_code == 303

    integration = next(
        item for item in app.state.repository.list_integrations() if item["id"] == "standup-cron"
    )
    assert integration["status"] == "configured"


def test_kanban_check_update_route_changes_readiness_report(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/kanban-checks/kanban-board-initialized",
        data={
            "status": "verified",
            "evidence": "Initialized with hermes kanban init.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    check = app.state.repository.get_kanban_check("kanban-board-initialized")
    assert check["status"] == "verified"
    assert check["evidence"] == "Initialized with hermes kanban init."
    report = client.get("/setup/readiness-report.md")
    assert "Kanban verification" in report.text


def test_kanban_check_update_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/kanban-checks/kanban-board-initialized",
        data={
            "status": "verified",
            "evidence": FAKE_OPENAI_ENV_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_kanban_check("kanban-board-initialized")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_kanban_verification_reply_import_updates_and_configures_integration(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/kanban-verification-reply",
        data={
            "reply_text": "\n".join(
                f"{check['id']}=verified | {check['label']} verified externally."
                for check in app.state.repository.list_kanban_checks()
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/verification?kanban_imported=3&kanban_unknown=0"
        "&kanban_invalid=0&kanban_ignored=0#kanban-verification"
    )
    for check in app.state.repository.list_kanban_checks():
        assert check["status"] == "verified"
        assert check["evidence"].endswith("verified externally.")
    integration = next(
        item for item in app.state.repository.list_integrations() if item["id"] == "hermes-kanban"
    )
    assert integration["status"] == "configured"


def test_kanban_verification_reply_import_rejects_invalid_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/kanban-verification-reply",
        data={"reply_text": "kanban-board-initialized=done"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_kanban_check("kanban-board-initialized")
    assert check["status"] == "needed"


def test_kanban_verification_reply_import_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/kanban-verification-reply",
        data={"reply_text": ("kanban-board-initialized=verified | " + FAKE_OPENAI_ENV_SECRET)},
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_kanban_check("kanban-board-initialized")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_kanban_diagnostics_records_run_and_marks_diagnostics_check(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    client = TestClient(app)

    response = client.post("/setup/kanban/diagnostics", follow_redirects=False)

    assert response.status_code == 303
    runs = app.state.repository.list_runs()
    assert runs[0]["run_type"] == "kanban-diagnostics"
    check = app.state.repository.get_kanban_check("kanban-diagnostics-pass")
    assert check["status"] == "verified"
    integration = next(
        item for item in app.state.repository.list_integrations() if item["id"] == "hermes-kanban"
    )
    assert integration["status"] == "needs_setup"


def test_kanban_checks_configure_integration_when_all_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    for check in app.state.repository.list_kanban_checks():
        response = client.post(
            f"/setup/kanban-checks/{check['id']}",
            data={"status": "verified", "evidence": "Verified externally."},
            follow_redirects=False,
        )
        assert response.status_code == 303

    integration = next(
        item for item in app.state.repository.list_integrations() if item["id"] == "hermes-kanban"
    )
    assert integration["status"] == "configured"


def test_profile_installation_check_update_tracks_non_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-installation-checks/engineering-manager-profile-installation",
        data={
            "status": "verified",
            "evidence": "Profile directory and alias verified.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    check = app.state.repository.get_profile_installation_check(
        "engineering-manager-profile-installation"
    )
    assert check["status"] == "verified"
    assert check["evidence"] == "Profile directory and alias verified."
    report = client.get("/setup/readiness-report.md")
    assert "Profile installation" in report.text


def test_profile_installation_check_update_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-installation-checks/engineering-manager-profile-installation",
        data={
            "status": "verified",
            "evidence": FAKE_OPENAI_ENV_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_profile_installation_check(
        "engineering-manager-profile-installation"
    )
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_profile_installation_audit_import_updates_checks(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-installation-audit",
        data={
            "audit_text": """
            FOUND chief-of-staff profile directory
            FOUND chief-of-staff command alias
            FOUND chief-of-staff SOUL.md
            FOUND chief-of-staff capabilities.json
            FOUND chief-of-staff profile-manifest.json
            FOUND chief-of-staff .env.example
            FOUND chief-of-staff config.yaml.example
            DEFER chief-of-staff .env presence
            DEFER chief-of-staff config.yaml presence
            FOUND engineering-manager profile directory
            MISSING engineering-manager command alias
            FOUND engineering-manager SOUL.md
            FOUND engineering-manager capabilities.json
            FOUND engineering-manager profile-manifest.json
            FOUND engineering-manager .env.example
            FOUND engineering-manager config.yaml.example
            """,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/profiles?profile_installation_imported=2"
        "&profile_installation_unknown=0"
        "&profile_installation_incomplete=0"
        "&profile_installation_ignored=0"
        "#profile-installation-tracking"
    )
    chief = app.state.repository.get_profile_installation_check(
        "chief-of-staff-profile-installation"
    )
    engineering = app.state.repository.get_profile_installation_check(
        "engineering-manager-profile-installation"
    )
    assert chief["status"] == "verified"
    assert chief["evidence"].startswith("Profile installation audit passed.")
    assert engineering["status"] == "blocked"
    assert engineering["evidence"] == ("Profile installation audit missing: command alias.")


def test_profile_installation_audit_import_rejects_secret_text(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-installation-audit",
        data={
            "audit_text": ("FOUND chief-of-staff profile directory\n" + FAKE_OPENAI_ENV_SECRET),
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_profile_installation_check(
        "chief-of-staff-profile-installation"
    )
    assert check["status"] == "needed"


def test_profile_acceptance_check_update_requires_smoke_first(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-acceptance-checks/engineering-manager-acceptance-1",
        data={
            "status": "verified",
            "evidence": "Founder accepted architecture judgment.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    check = app.state.repository.get_profile_acceptance_check("engineering-manager-acceptance-1")
    assert check["status"] == "needed"


def test_profile_acceptance_check_update_tracks_after_smoke(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)
    mark_profile_llm_verified(app.state.repository, "engineering-manager")

    response = client.post(
        "/setup/profile-acceptance-checks/engineering-manager-acceptance-1",
        data={
            "status": "verified",
            "evidence": "Founder accepted architecture and test plan answer.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    check = app.state.repository.get_profile_acceptance_check("engineering-manager-acceptance-1")
    assert check["status"] == "verified"
    assert check["evidence"] == "Founder accepted architecture and test plan answer."
    report = client.get("/setup/readiness-report.md")
    assert "Profile acceptance" in report.text


def test_profile_acceptance_check_update_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)
    mark_profile_llm_verified(app.state.repository, "engineering-manager")

    response = client.post(
        "/setup/profile-acceptance-checks/engineering-manager-acceptance-1",
        data={
            "status": "verified",
            "evidence": FAKE_OPENAI_ENV_SECRET,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_profile_acceptance_check("engineering-manager-acceptance-1")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_profile_acceptance_reply_import_requires_smoke_before_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-acceptance-reply",
        data={
            "reply_text": (
                "engineering-manager-acceptance-1=verified | "
                "Founder accepted architecture judgment.\n"
                "product-manager-acceptance-1=failed | Too many controls."
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 409
    engineering = app.state.repository.get_profile_acceptance_check(
        "engineering-manager-acceptance-1"
    )
    product = app.state.repository.get_profile_acceptance_check("product-manager-acceptance-1")
    assert engineering["status"] == "needed"
    assert product["status"] == "needed"


def test_profile_acceptance_reply_import_updates_after_smoke(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)
    mark_profile_llm_verified(app.state.repository, "engineering-manager")

    response = client.post(
        "/setup/profile-acceptance-reply",
        data={
            "reply_text": (
                "engineering-manager-acceptance-1=verified | "
                "Architecture and testing answer accepted.\n"
                "product-manager-acceptance-1=failed | Added too many buttons."
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/setup/profiles?profile_acceptance_imported=2"
        "&profile_acceptance_unknown=0"
        "&profile_acceptance_invalid=0"
        "&profile_acceptance_ignored=0"
        "#profile-acceptance-tracking"
    )
    engineering = app.state.repository.get_profile_acceptance_check(
        "engineering-manager-acceptance-1"
    )
    product = app.state.repository.get_profile_acceptance_check("product-manager-acceptance-1")
    assert engineering["status"] == "verified"
    assert engineering["evidence"] == "Architecture and testing answer accepted."
    assert product["status"] == "failed"
    assert product["evidence"] == "Added too many buttons."


def test_profile_acceptance_reply_import_rejects_invalid_status(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/setup/profile-acceptance-reply",
        data={"reply_text": "engineering-manager-acceptance-1=done"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_profile_acceptance_check("engineering-manager-acceptance-1")
    assert check["status"] == "needed"


def test_profile_acceptance_reply_import_rejects_secret_evidence(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)
    mark_profile_llm_verified(app.state.repository, "engineering-manager")

    response = client.post(
        "/setup/profile-acceptance-reply",
        data={
            "reply_text": ("engineering-manager-acceptance-1=verified | " + FAKE_OPENAI_ENV_SECRET)
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    check = app.state.repository.get_profile_acceptance_check("engineering-manager-acceptance-1")
    assert check["status"] == "needed"
    assert check["evidence"] == ""


def test_profile_smoke_check_records_run_and_marks_profile_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    mark_profile_installation_verified(app.state.repository, "research-agent")
    client = TestClient(app)

    response = client.post("/setup/profile-smoke/research-agent", follow_redirects=False)

    assert response.status_code == 303
    runs = app.state.repository.list_runs()
    assert runs[0]["run_type"] == "profile-smoke"
    assert runs[0]["status"] == "completed"
    assert "ran research-agent" in runs[0]["output"]
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["status"] == "verified"
    assert "Smoke check passed via dashboard." in preference["notes"]
    requirement = app.state.repository.get_secret_requirement(
        "research-agent-llm-provider-credential"
    )
    assert requirement["status"] == "verified"


def test_profile_smoke_check_requires_verified_profile_installation(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    client = TestClient(app)

    response = client.post("/setup/profile-smoke/research-agent", follow_redirects=False)

    assert response.status_code == 409
    assert app.state.repository.list_runs() == []
    preference = app.state.repository.get_model_preference("research-agent")
    assert preference["status"] == "planned"


def test_profile_smoke_checks_mark_llm_integration_configured_when_all_pass(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    mark_all_profile_installations_verified(app.state.repository)
    client = TestClient(app)

    for agent in app.state.repository.list_agents():
        response = client.post(
            f"/setup/profile-smoke/{agent['id']}",
            follow_redirects=False,
        )
        assert response.status_code == 303

    integration = next(
        item for item in app.state.repository.list_integrations() if item["id"] == "llm-provider"
    )
    assert integration["status"] == "configured"
    report = client.get("/setup/readiness-report.md")
    assert "LLM profile preferences" in report.text
    assert "All profiles verified." in report.text


def test_push_task_to_kanban_attaches_remote_task_id(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    for check in app.state.repository.list_kanban_checks():
        if check["check_type"] != "task_create":
            app.state.repository.update_kanban_check(
                check_id=check["id"],
                status="verified",
                evidence="Verified before task-create drill.",
            )
    task_id = app.state.repository.create_task(
        title="Research startup markets",
        owner_agent_id="research-agent",
        priority="high",
        summary="Find three promising areas.",
    )
    client = TestClient(app)

    response = client.post(f"/tasks/{task_id}/kanban", follow_redirects=False)

    assert response.status_code == 303
    task = app.state.repository.get_task(task_id)
    assert task["kanban_task_id"] == "t_123"
    check = app.state.repository.get_kanban_check("kanban-task-create")
    assert check["status"] == "verified"


def test_founder_decision_routes_create_and_update_queue_items(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)

    response = client.post(
        "/decisions",
        data={
            "title": "Approve research focus",
            "urgency": "routine",
            "source": "manual",
            "owner_agent_id": "research-agent",
            "slack_channel": "#decisions",
            "telegram_policy": "Slack first.",
            "context": "Choose which market the research agent should inspect first.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    decision = next(
        item
        for item in app.state.repository.list_founder_decisions()
        if item["title"] == "Approve research focus"
    )
    update = client.post(
        f"/decisions/{decision['id']}",
        data={"status": "approved", "decision": "Research legal AI first."},
        follow_redirects=False,
    )

    assert update.status_code == 303
    saved = app.state.repository.get_founder_decision(decision["id"])
    assert saved["status"] == "approved"
    assert saved["decision"] == "Research legal AI first."


def test_founder_decision_routes_reject_secret_values_and_empty_resolution(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    client = TestClient(app)
    decision_id = app.state.repository.list_founder_decisions()[0]["id"]

    empty_resolution = client.post(
        f"/decisions/{decision_id}",
        data={"status": "approved", "decision": ""},
        follow_redirects=False,
    )
    secret_create = client.post(
        "/decisions",
        data={
            "title": "Secret check",
            "urgency": "urgent",
            "source": "manual",
            "owner_agent_id": "chief-of-staff",
            "slack_channel": "#decisions",
            "telegram_policy": "Use " + FAKE_OPENAI_ENV_SECRET,
            "context": "Should be rejected.",
        },
        follow_redirects=False,
    )
    secret_update = client.post(
        f"/decisions/{decision_id}",
        data={
            "status": "blocked",
            "decision": "Use " + FAKE_ALPHA_SLACK_BOT_SECRET,
        },
        follow_redirects=False,
    )

    assert empty_resolution.status_code == 400
    assert secret_create.status_code == 400
    assert secret_update.status_code == 400


def test_push_task_to_kanban_requires_board_and_diagnostics_first(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    task_id = app.state.repository.create_task(
        title="Research startup markets",
        owner_agent_id="research-agent",
        priority="high",
        summary="Find three promising areas.",
    )
    client = TestClient(app)

    dashboard = client.get("/")
    response = client.post(f"/tasks/{task_id}/kanban", follow_redirects=False)

    assert dashboard.status_code == 200
    assert "Kanban prerequisites needed" in dashboard.text
    assert response.status_code == 409
    assert "Complete Kanban initialization and diagnostics" in response.text
    assert app.state.repository.get_task(task_id)["kanban_task_id"] is None
    assert app.state.repository.list_runs() == []


def test_push_project_workflow_to_kanban_is_idempotent(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    project_id = app.state.repository.create_project_with_workflow(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )
    for check in app.state.repository.list_kanban_checks():
        app.state.repository.update_kanban_check(
            check_id=check["id"],
            status="verified",
            evidence="Verified before project handoff.",
        )
    client = TestClient(app)

    response = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)

    assert response.status_code == 303
    tasks = app.state.repository.list_tasks()
    assert all(task["kanban_task_id"] == "t_123" for task in tasks)
    first_run_count = len(app.state.repository.list_runs())
    assert first_run_count == len(app.state.repository.list_workflow_templates())

    second_response = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)

    assert second_response.status_code == 303
    assert len(app.state.repository.list_runs()) == first_run_count


def test_push_project_workflow_to_kanban_requires_verified_kanban_gate(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.kanban_client = FakeKanbanClient()
    project_id = app.state.repository.create_project_with_workflow(
        name="Acme AI",
        founder_idea="AI operating company for small businesses.",
    )
    client = TestClient(app)

    project = client.get(f"/projects/{project_id}")
    response = client.post(f"/projects/{project_id}/kanban", follow_redirects=False)

    assert project.status_code == 200
    assert "Kanban verification needed" in project.text
    assert "Complete Kanban verification before pushing a full project workflow" in (project.text)
    assert response.status_code == 409
    assert "Complete Kanban verification before pushing a full project workflow" in (response.text)
    assert app.state.repository.list_runs() == []
    assert all(not task["kanban_task_id"] for task in app.state.repository.list_tasks())


def test_run_agent_records_fake_result(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    mark_profile_llm_verified(app.state.repository, "product-manager")
    client = TestClient(app)

    response = client.post(
        "/agents/product-manager/run",
        data={"founder_request": "Draft product principles."},
        follow_redirects=False,
    )

    assert response.status_code == 303
    runs = app.state.repository.list_runs()
    assert runs[0]["status"] == "completed"
    assert "ran product-manager" in runs[0]["output"]


def test_run_agent_requires_verified_llm_before_live_profile_run(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    client = TestClient(app)

    page = client.get("/agents/product-manager")
    response = client.post(
        "/agents/product-manager/run",
        data={"founder_request": "Draft product principles."},
        follow_redirects=False,
    )

    assert page.status_code == 200
    assert "Open profile smoke checks" in page.text
    assert response.status_code == 409
    assert "Run the profile smoke check for Product Manager" in response.text
    assert app.state.repository.list_runs() == []


def test_run_agent_rejects_secret_like_prompt(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    client = TestClient(app)

    response = client.post(
        "/agents/product-manager/run",
        data={"founder_request": "Use " + FAKE_OPENAI_ENV_SECRET},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert app.state.repository.list_runs() == []


def test_run_standup_requires_chief_of_staff_llm_verification(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    client = TestClient(app)

    dashboard = client.get("/")
    response = client.post("/standups/morning-standup/run", follow_redirects=False)

    assert dashboard.status_code == 200
    assert "Chief of Staff profile passes final LLM verification" in dashboard.text
    assert response.status_code == 409
    assert "Run the profile smoke check for Chief of Staff" in response.text
    assert app.state.repository.list_runs() == []


def test_run_standup_records_fake_result_after_chief_of_staff_llm_verified(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.hermes_client = FakeHermesClient()
    mark_profile_llm_verified(app.state.repository, "chief-of-staff")
    client = TestClient(app)

    response = client.post("/standups/morning-standup/run", follow_redirects=False)

    assert response.status_code == 303
    runs = app.state.repository.list_runs()
    assert runs[0]["run_type"] == "standup"
    assert runs[0]["status"] == "completed"
    assert "ran chief-of-staff" in runs[0]["output"]
