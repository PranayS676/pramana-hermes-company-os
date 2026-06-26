import json

from fastapi.testclient import TestClient

from hermes_company_os.company_manifest import company_manifest_json, company_manifest_markdown
from hermes_company_os.main import create_app
from hermes_company_os.profile_doctrine import PROFILE_DOCTRINES
from hermes_company_os.settings import Settings

EXPECTED_ACCEPTANCE_CASES = sum(
    len(doctrine["acceptance_cases"]) for doctrine in PROFILE_DOCTRINES.values()
)


def test_company_manifest_routes_export_no_secret_handoff(tmp_path):
    app = create_app(Settings(database_path=tmp_path / "company.db"))
    app.state.repository.update_setup_inputs(
        {
            "founder_name": "Masad",
            "slack_workspace_name": "Founder Lab",
            "founder_slack_member_id": "U123",
            "slack_channel_engineering": "C123",
            "llm_provider": "openrouter",
        }
    )
    client = TestClient(app)

    markdown = client.get("/setup/company-manifest.md")
    response = client.get("/setup/company-manifest.json")

    assert markdown.status_code == 200
    assert "Hermes Company OS Setup Manifest" in markdown.text
    assert "Next best action" in markdown.text
    assert "/setup/company-manifest.json" in markdown.text

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["title"] == "Hermes Company OS Setup Manifest"
    assert manifest["activation"]["summary"]["ready"] is False
    assert manifest["profiles"][0]["id"] == "chief-of-staff"
    assert manifest["profiles"][0]["artifacts"]["apply_script"] == (
        "/setup/profile-apply/chief-of-staff.ps1"
    )
    assert manifest["messaging"]["slack_is_main_workspace"] is True
    assert manifest["messaging"]["telegram_is_urgent_only"] is True
    assert manifest["llm"]["verification_last"] is True
    assert manifest["profile_installation"]["status"] == {"needed": 10}
    assert manifest["profile_acceptance"]["status"] == {"needed": EXPECTED_ACCEPTANCE_CASES}
    assert manifest["founder_decisions"]["status"] == {"needed": 2}
    assert manifest["founder_decisions"]["urgent_open"] == 1
    assert manifest["workflow"]["templates"]
    assert manifest["artifacts"]["activation_sequence"] == "/setup/activation-sequence.md"
    assert manifest["artifacts"]["company_manifest_json"] == "/setup/company-manifest.json"
    assert manifest["artifacts"]["company_launch_drill"] == (
        "/setup/company-launch-drill.md"
    )
    assert manifest["artifacts"]["founder_handoff"] == "/setup/founder-handoff.md"
    assert manifest["artifacts"]["founder_decisions"] == "/setup/founder-decisions.md"
    assert manifest["artifacts"]["founder_input_collector"] == (
        "/setup/founder-inputs.ps1"
    )
    assert manifest["artifacts"]["first_run_runner"] == "/setup/first-run.ps1"
    assert manifest["artifacts"]["progress_board"] == "/setup/progress-board.md"
    assert manifest["artifacts"]["input_ledger"] == "/setup/input-ledger.md"
    assert manifest["artifacts"]["credential_loading"] == "/setup/credential-loading.md"
    assert manifest["artifacts"]["founder_next_actions"] == "/setup/founder-next-actions.md"
    assert manifest["artifacts"]["slack_provisioning"] == (
        "/setup/slack-provisioning.md"
    )
    assert manifest["artifacts"]["slack_provisioning_runner"] == (
        "/setup/slack-provisioning.ps1"
    )
    assert manifest["artifacts"]["slack_channel_template"] == (
        "/setup/slack-channel-template.md"
    )
    assert manifest["artifacts"]["slack_bot_user_map"] == (
        "/setup/slack-bot-user-map.json"
    )
    assert manifest["artifacts"]["slack_bot_user_template"] == (
        "/setup/slack-bot-user-map-template.md"
    )
    assert manifest["artifacts"]["telegram_provisioning"] == (
        "/setup/telegram-provisioning.md"
    )
    assert manifest["artifacts"]["telegram_recipient_template"] == (
        "/setup/telegram-recipient-template.md"
    )
    assert manifest["artifacts"]["telegram_provisioning_runner"] == (
        "/setup/telegram-provisioning.ps1"
    )
    assert manifest["artifacts"]["llm_provisioning"] == "/setup/llm-provisioning.md"
    assert manifest["artifacts"]["llm_provisioning_runner"] == (
        "/setup/llm-provisioning.ps1"
    )
    assert manifest["artifacts"]["llm_smoke"] == "/setup/llm-smoke.md"
    assert manifest["artifacts"]["messaging_drill"] == "/setup/messaging-drill.md"
    assert manifest["artifacts"]["gateway_operations"] == "/setup/gateway-operations.md"
    assert manifest["artifacts"]["verification_evidence"] == (
        "/setup/verification-evidence.md"
    )
    assert manifest["artifacts"]["standup_preview"] == "/setup/standup-preview.md"
    assert manifest["artifacts"]["schedule_provisioning"] == (
        "/setup/schedule-provisioning.md"
    )
    assert manifest["artifacts"]["schedule_config_template"] == (
        "/setup/schedule-config-template.md"
    )
    assert manifest["artifacts"]["schedule_provisioning_runner"] == (
        "/setup/schedule-provisioning.ps1"
    )
    assert manifest["artifacts"]["idea_intake"] == "/setup/idea-intake.md"
    assert manifest["artifacts"]["project_workflow"] == "/setup/project-workflow.md"
    assert manifest["artifacts"]["kanban_provisioning"] == (
        "/setup/kanban-provisioning.md"
    )
    assert manifest["artifacts"]["kanban_provisioning_runner"] == (
        "/setup/kanban-provisioning.ps1"
    )
    assert manifest["artifacts"]["delegation_playbook"] == (
        "/setup/delegation-playbook.md"
    )
    assert manifest["artifacts"]["profile_installation"] == (
        "/setup/profile-installation.md"
    )
    assert manifest["artifacts"]["profile_installation_runner"] == (
        "/setup/profile-installation.ps1"
    )
    assert manifest["artifacts"]["hermes_runtime"] == "/setup/hermes-runtime.md"

    llm_input = next(
        item
        for item in manifest["setup_inputs"]["safe_dashboard_inputs"]
        if item["key"] == "llm_provider"
    )
    assert llm_input["status"] == "captured"
    assert llm_input["value"] == ""

    raw = json.dumps(manifest) + markdown.text
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "OPENAI_API_KEY=sk-" not in raw
    assert "BotFather token" not in raw


def test_company_manifest_helpers_summarize_open_work_without_evidence_text():
    kwargs = {
        "agents": [
            {
                "id": "engineering-manager",
                "name": "Engineering Manager",
                "role": "Engineering",
                "hermes_command": "engineering-manager",
                "slack_channel": "#engineering",
                "telegram_policy": "Chief escalation only",
                "description": "Builds ambitious systems.",
                "capabilities": ["architecture", "testing"],
            }
        ],
        "setup_inputs": [
            {
                "key": "founder_name",
                "group_name": "founder",
                "label": "Founder name",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
                "help_text": "Founder display name.",
            }
        ],
        "schedules": [
            {
                "id": "morning",
                "name": "Morning",
                "hour": 9,
                "minute": 0,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
                "telegram_policy": "urgent only",
                "active": 1,
            }
        ],
        "model_preferences": [
            {
                "agent_id": "engineering-manager",
                "agent_name": "Engineering Manager",
                "hermes_command": "engineering-manager",
                "provider": "openai-codex",
                "model": "gpt-5-codex",
                "fallback_provider": "",
                "fallback_model": "",
                "auth_method": "deferred_profile_secret",
                "status": "planned",
            }
        ],
        "integrations": [
            {
                "id": "llm-provider",
                "name": "LLM provider",
                "category": "runtime",
                "owner_agent_id": None,
                "owner_name": None,
                "status": "deferred",
                "validation_command": "engineering-manager doctor",
                "docs_url": "https://example.com",
            }
        ],
        "secret_requirements": [
            {
                "id": "engineering-manager-llm-provider-credential",
                "owner_agent_id": "engineering-manager",
                "owner_name": "Engineering Manager",
                "category": "llm",
                "label": "Engineering Manager LLM provider credential",
                "environment_key": "PROVIDER_API_KEY_OR_OAUTH",
                "destination": "engineering-manager Hermes profile .env",
                "status": "deferred",
                "notes": "would contain private handling notes",
            }
        ],
        "messaging_checks": [
            {
                "id": "engineering-manager-slack-dm",
                "owner_agent_id": "engineering-manager",
                "platform": "slack",
                "label": "Engineering Manager Slack DM response",
                "status": "needed",
                "instructions": "Send a DM.",
                "evidence": "Founder saw private response text.",
            }
        ],
        "schedule_checks": [],
        "kanban_checks": [],
        "workflow_templates": [
            {
                "id": "architecture-plan",
                "name": "Architecture plan",
                "phase": "engineering",
                "owner_agent_id": "engineering-manager",
                "owner_name": "Engineering Manager",
                "doc_type": "architecture",
                "priority": "high",
                "sort_order": 10,
            }
        ],
        "activation_checks": [
            {
                "id": "required-inputs",
                "label": "Required dashboard inputs",
                "status": "missing",
                "detail": "Missing: Founder name",
            }
        ],
        "profile_acceptance_checks": [
            {
                "id": "engineering-manager-acceptance-1",
                "agent_id": "engineering-manager",
                "agent_name": "Engineering Manager",
                "title": "Architecture and test plan",
                "status": "verified",
                "evidence": "Private notes stay out.",
            }
        ],
        "profile_installation_checks": [
            {
                "id": "engineering-manager-profile-installation",
                "agent_id": "engineering-manager",
                "agent_name": "Engineering Manager",
                "label": "Engineering Manager profile installation verified",
                "status": "verified",
                "evidence": "Private local path stays out.",
            }
        ],
        "founder_decisions": [
            {
                "id": "decision-architecture",
                "title": "Approve architecture direction",
                "status": "blocked",
                "urgency": "urgent",
                "source": "manual",
                "owner_agent_id": "engineering-manager",
                "owner_name": "Engineering Manager",
                "slack_channel": "#founder-command",
                "telegram_policy": "Urgent founder approval only.",
                "context": "Choose one architecture path.",
                "decision": "Private decision note stays out.",
            }
        ],
    }

    manifest = json.loads(company_manifest_json(**kwargs))
    markdown = company_manifest_markdown(**kwargs)

    assert manifest["external_secrets"]["requirements"][0]["environment_key"] == (
        "PROVIDER_API_KEY_OR_OAUTH"
    )
    assert "notes" not in manifest["external_secrets"]["requirements"][0]
    assert manifest["messaging"]["verification"]["checks"][0]["has_evidence"] is True
    assert manifest["profile_installation"]["checks"][0]["has_evidence"] is True
    assert manifest["profile_acceptance"]["checks"][0]["has_evidence"] is True
    assert manifest["founder_decisions"]["open"][0]["has_decision"] is True
    assert "Founder saw private response text" not in json.dumps(manifest)
    assert "Private local path stays out" not in json.dumps(manifest)
    assert "Private notes stay out" not in json.dumps(manifest)
    assert "Private decision note stays out" not in json.dumps(manifest)
    assert "Missing required dashboard inputs: 1" in markdown
    assert "Profile installation: verified=1" in markdown
    assert "Founder decisions: blocked=1; 1 urgent open" in markdown
