from hermes_company_os.setup_artifacts import (
    activation_checklist_markdown,
    inputs_needed_markdown,
    llm_setup_plan_markdown,
    slack_setup_plan_markdown,
    telegram_setup_plan_markdown,
)


def test_slack_setup_plan_includes_each_profile_and_scopes():
    plan = slack_setup_plan_markdown(
        [
            {
                "id": "engineering-manager",
                "name": "Engineering Manager",
                "slack_channel": "#engineering",
                "hermes_command": "engineering-manager",
            }
        ],
        {
            "slack_workspace_name": "Founder Lab",
            "founder_slack_member_id": "U123",
            "slack_channel_engineering": "C123",
        },
    )

    assert "Hermes Engineering Manager" in plan
    assert "`engineering-manager slack manifest --write`" in plan
    assert "`chat:write`" in plan
    assert "`message.channels`" in plan
    assert "`/invite @Hermes Engineering Manager`" in plan


def test_inputs_needed_splits_dashboard_values_from_external_secrets():
    plan = inputs_needed_markdown(
        [
            {
                "key": "founder_slack_member_id",
                "label": "Founder Slack member ID",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
                "help_text": "Slack member IDs start with U.",
            },
            {
                "key": "llm_provider",
                "label": "LLM provider",
                "value": "",
                "required": 0,
                "secret_policy": "secret_external",
                "help_text": "Deferred until last.",
            },
        ],
        [{"name": "Chief of Staff"}],
    )

    assert "Missing Required Dashboard Inputs" in plan
    assert "Founder Slack member ID" in plan
    assert "External Secrets Never Stored Here" in plan
    assert "Slack bot credential loaded externally" in plan
    assert "Telegram BotFather credential loaded externally" in plan
    assert "Provider credential" in plan
    assert "Focused Reply Templates" in plan
    assert "/setup/slack-channel-template.md" in plan
    assert "/setup/slack-bot-user-map-template.md" in plan
    assert "/setup/telegram-recipient-template.md" in plan
    assert "/setup/schedule-config-template.md" in plan
    assert "/setup/profile-acceptance-template.md" in plan
    assert "SLACK_BOT_TOKEN" not in plan
    assert "TELEGRAM_BOT_TOKEN" not in plan
    assert "xoxb-" not in plan
    assert "xapp-" not in plan
    assert "API_KEY=" not in plan


def test_telegram_setup_plan_is_chief_urgent_only():
    plan = telegram_setup_plan_markdown({"founder_telegram_user_id": "98765"})

    assert "urgent-only" in plan
    assert "Allowed users metadata: `98765`" in plan
    assert "Chief of Staff" in plan
    assert "TELEGRAM_BOT_TOKEN" not in plan
    assert "xoxb-" not in plan
    assert "xapp-" not in plan


def test_llm_setup_plan_lists_profile_preferences_without_keys():
    plan = llm_setup_plan_markdown(
        [
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
                "notes": "Starter preference.",
            }
        ]
    )

    assert "LLM Provider Setup Plan" in plan
    assert "`engineering-manager`" in plan
    assert "`openai-codex`" in plan
    assert "`gpt-5-codex`" in plan
    assert "Provider credential" in plan
    assert "API key" not in plan
    assert "sk-" not in plan


def test_activation_checklist_includes_model_gateway_kanban_and_cron():
    plan = activation_checklist_markdown(
        [
            {
                "id": "chief-of-staff",
                "name": "Chief of Staff",
                "hermes_command": "chief-of-staff",
            }
        ],
        {"standup_cadence": "weekdays"},
    )

    assert "`chief-of-staff model`" in plan
    assert "`chief-of-staff gateway setup`" in plan
    assert "/setup/profile-installation.ps1" in plan
    assert "/setup#profile-installation-tracking" in plan
    assert "/setup/llm-finalize.ps1" in plan
    assert "/setup/profile-acceptance.md" in plan
    assert "/setup#profile-acceptance-tracking" in plan
    assert "hermes kanban diagnostics --json" in plan
    assert '"every weekday at 9am"' in plan
    assert plan.index("## 3. Configure Slack And Telegram Gateways") < plan.index(
        "## 6. Load And Verify LLM Provider Last"
    )
    assert plan.index("## 5. Verify Standups And Create Cron") < plan.index(
        "`chief-of-staff model`"
    )
    assert "API keys" not in plan
