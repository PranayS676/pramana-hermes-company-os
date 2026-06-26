from hermes_company_os.activation_sequence import (
    activation_sequence_markdown,
    next_best_action,
)


def test_next_best_action_prioritizes_blocking_inputs():
    action = next_best_action(
        checks=[
            {
                "label": "Required dashboard inputs",
                "status": "missing",
                "detail": "Missing: Founder Slack member ID",
            }
        ],
        secret_requirements=[],
        messaging_checks=[],
        schedule_checks=[],
        kanban_checks=[],
        model_preferences=[],
        integrations=[],
    )

    assert "Required dashboard inputs" in action
    assert "Founder Slack member ID" in action


def test_next_best_action_keeps_llm_credentials_last():
    action = next_best_action(
        checks=[],
        secret_requirements=[
            {"category": "llm", "status": "deferred"},
        ],
        messaging_checks=[{"status": "verified"}],
        schedule_checks=[{"status": "verified"}],
        kanban_checks=[{"status": "verified"}],
        model_preferences=[
            {"status": "planned"},
        ],
        integrations=[
            {"category": "runtime", "status": "deferred"},
        ],
    )

    assert "LLM provider credentials" in action
    assert "profile-smoke" in action


def test_next_best_action_prioritizes_profile_installation_gate():
    action = next_best_action(
        checks=[
            {
                "id": "profile-installation",
                "label": "Profile installation",
                "status": "needs_setup",
                "detail": "0 verified, 10 needed.",
            }
        ],
        secret_requirements=[
            {"category": "slack", "status": "needed"},
            {"category": "telegram", "status": "needed"},
        ],
        messaging_checks=[],
        schedule_checks=[],
        kanban_checks=[],
        model_preferences=[],
        integrations=[],
    )

    assert "profile-installation.ps1" in action
    assert "profile-installation-tracking" in action


def test_activation_sequence_lists_inputs_runbooks_and_no_secret_values():
    markdown = activation_sequence_markdown(
        checks=[
            {
                "label": "Required dashboard inputs",
                "status": "missing",
                "detail": "Missing: Founder Slack member ID",
            }
        ],
        setup_inputs=[
            {
                "key": "founder_slack_member_id",
                "label": "Founder Slack member ID",
                "value": "",
                "required": 1,
                "help_text": "Slack member IDs start with U.",
            }
        ],
        secret_requirements=[
            {
                "category": "slack",
                "status": "needed",
                "label": "Chief of Staff Slack bot token",
                "destination": "chief-of-staff Hermes profile .env",
                "environment_key": "SLACK_BOT_TOKEN",
            }
        ],
        messaging_checks=[{"status": "needed"}],
        schedule_checks=[{"status": "needed"}],
        kanban_checks=[{"status": "needed"}],
        model_preferences=[{"status": "planned"}],
        integrations=[{"category": "runtime", "status": "deferred"}],
    )

    assert "Founder Activation Sequence" in markdown
    assert "Founder Slack member ID (`founder_slack_member_id`)" in markdown
    assert "External Secrets To Load Outside This Dashboard" in markdown
    assert "/setup/company-manifest.md" in markdown
    assert "/setup/company-manifest.json" in markdown
    assert "/setup/company-launch-drill.md" in markdown
    assert "/setup/company-launch-drill.json" in markdown
    assert "/setup/founder-handoff.md" in markdown
    assert "/setup/founder-handoff.json" in markdown
    assert "/setup/input-ledger.md" in markdown
    assert "/setup/input-ledger.json" in markdown
    assert "/setup/credential-loading.md" in markdown
    assert "/setup/credential-loading.json" in markdown
    assert "/setup/founder-next-actions.md" in markdown
    assert "/setup/founder-next-actions.json" in markdown
    assert "/setup/first-run.md" in markdown
    assert "/setup/first-run.json" in markdown
    assert "/setup/first-run.ps1" in markdown
    assert "/setup/progress-board.md" in markdown
    assert "/setup/progress-board.json" in markdown
    assert "/setup/kickoff-readiness.md" in markdown
    assert "/setup/kickoff-readiness.json" in markdown
    assert "/setup/slack-manifests.json" in markdown
    assert "/setup/slack-provisioning.md" in markdown
    assert "/setup/slack-provisioning.json" in markdown
    assert "/setup/slack-provisioning.ps1" in markdown
    assert "/setup/slack-bot-user-map.json" in markdown
    assert "/setup/slack-workspace.md" in markdown
    assert "/setup/slack-invite-matrix.json" in markdown
    assert "/setup/slack-invite-matrix.csv" in markdown
    assert "/setup/secret-audit.md" in markdown
    assert "/setup/secret-audit.ps1" in markdown
    assert "/setup/hermes-runtime.md" in markdown
    assert "/setup/hermes-runtime.json" in markdown
    assert "/setup/hermes-install.ps1" in markdown
    assert "/setup/telegram-provisioning.md" in markdown
    assert "/setup/telegram-provisioning.json" in markdown
    assert "/setup/telegram-provisioning.ps1" in markdown
    assert "/setup/telegram-policy.md" in markdown
    assert "/setup/telegram-policy.json" in markdown
    assert "/setup/messaging-drill.md" in markdown
    assert "/setup/messaging-drill.json" in markdown
    assert "/setup/gateway-operations.md" in markdown
    assert "/setup/gateway-operations.json" in markdown
    assert "/setup/gateway-operations.ps1" in markdown
    assert "/setup/runtime-preflight.md" in markdown
    assert "/setup/activation-runner.md" in markdown
    assert "/setup/activation-runner.ps1" in markdown
    assert "/setup/schedule-provisioning.md" in markdown
    assert "/setup/schedule-provisioning.json" in markdown
    assert "/setup/schedule-provisioning.ps1" in markdown
    assert "/setup/standup-preview.md" in markdown
    assert "/setup/standup-preview.json" in markdown
    assert "/setup/delegation-playbook.md" in markdown
    assert "/setup/delegation-playbook.json" in markdown
    assert "/setup/profile-installation.md" in markdown
    assert "/setup/profile-installation.json" in markdown
    assert "/setup/profile-installation.ps1" in markdown
    assert "/setup/founder-decisions.md" in markdown
    assert "/setup/founder-decisions.json" in markdown
    assert "/setup/idea-intake.md" in markdown
    assert "/setup/idea-intake.json" in markdown
    assert "/setup/project-workflow.md" in markdown
    assert "/setup/project-workflow.json" in markdown
    assert "/setup/kanban-provisioning.md" in markdown
    assert "/setup/kanban-provisioning.json" in markdown
    assert "/setup/kanban-provisioning.ps1" in markdown
    assert "/setup/profile-acceptance.md" in markdown
    assert "/setup/profile-acceptance.json" in markdown
    assert "/setup/kanban-runbook.md" in markdown
    assert "/setup/llm-credentials.md" in markdown
    assert "/setup/llm-provisioning.md" in markdown
    assert "/setup/llm-provisioning.json" in markdown
    assert "/setup/llm-provisioning.ps1" in markdown
    assert "/setup/llm-finalize.md" in markdown
    assert "/setup/llm-finalize.ps1" in markdown
    assert "/setup/llm-smoke.md" in markdown
    assert "/setup/llm-smoke.json" in markdown
    assert "/setup/verification-evidence.md" in markdown
    assert "/setup/verification-evidence.json" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
