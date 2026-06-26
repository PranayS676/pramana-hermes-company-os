from hermes_company_os.activation_report import (
    activation_checks,
    activation_report_markdown,
    activation_summary,
)


def test_activation_checks_report_missing_and_invalid_inputs():
    checks = activation_checks(
        setup_inputs=[
            {
                "key": "founder_slack_member_id",
                "label": "Founder Slack member ID",
                "value": "bad",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_founder_command",
                "label": "#founder-command channel ID",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "founder_telegram_user_id",
                "label": "Founder Telegram user ID",
                "value": "abc",
                "required": 1,
                "secret_policy": "non_secret",
            },
        ],
        schedules=[],
        model_preferences=[],
        integrations=[],
        secret_requirements=[],
    )

    by_id = {check["id"]: check for check in checks}
    assert by_id["required-inputs"]["status"] == "missing"
    assert by_id["slack-member-id"]["status"] == "invalid"
    assert by_id["telegram-ids"]["status"] == "invalid"
    assert by_id["standup-schedules"]["status"] == "missing"
    assert by_id["external-secret-status"]["status"] == "missing"
    assert activation_summary(checks)["ready"] is False


def test_activation_report_marks_deferred_llm_as_non_blocking():
    checks = activation_checks(
        setup_inputs=[
            {
                "key": "founder_slack_member_id",
                "label": "Founder Slack member ID",
                "value": "U12345",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_founder_command",
                "label": "#founder-command channel ID",
                "value": "C12345",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_agent_standup",
                "label": "#agent-standup channel ID",
                "value": "C23456",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_product",
                "label": "#product channel ID",
                "value": "C34567",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_research",
                "label": "#research channel ID",
                "value": "C45678",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_engineering",
                "label": "#engineering channel ID",
                "value": "C56789",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_marketing",
                "label": "#marketing channel ID",
                "value": "C67890",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_channel_qa_review",
                "label": "#qa-review channel ID",
                "value": "C78901",
                "required": 1,
                "secret_policy": "non_secret",
            },
            {
                "key": "founder_telegram_user_id",
                "label": "Founder Telegram user ID",
                "value": "123456",
                "required": 1,
                "secret_policy": "non_secret",
            },
        ],
        schedules=[
            {
                "id": "morning-standup",
                "active": 1,
                "timezone": "America/New_York",
                "slack_channel": "#agent-standup",
            }
        ],
        model_preferences=[
            {
                "agent_id": "chief-of-staff",
                "provider": "openai-codex",
                "model": "gpt-5-codex",
                "status": "planned",
            }
        ],
        integrations=[
            {"category": "runtime", "status": "deferred"},
            {"category": "slack", "status": "configured"},
            {"category": "telegram", "status": "configured"},
            {"category": "kanban", "status": "configured"},
            {"category": "schedule", "status": "configured"},
        ],
        secret_requirements=[
            {"category": "slack", "status": "loaded"},
            {"category": "telegram", "status": "verified"},
            {"category": "llm", "status": "deferred"},
        ],
    )

    by_id = {check["id"]: check for check in checks}
    assert by_id["model-preferences"]["status"] == "deferred"
    assert by_id["integration-runtime"]["status"] == "deferred"
    assert by_id["external-secret-status"]["status"] == "deferred"
    summary = activation_summary(checks)
    assert summary["blocking"] == 0
    assert summary["needs_setup"] == 0
    assert summary["ready"] is True
    markdown = activation_report_markdown(checks)
    assert "Activation Readiness Report" in markdown
    assert "Ready for live activation: yes" in markdown


def test_activation_checks_include_messaging_verification_when_provided():
    checks = activation_checks(
        setup_inputs=[],
        schedules=[],
        model_preferences=[],
        integrations=[],
        secret_requirements=[],
        messaging_checks=[
            {"status": "verified"},
            {"status": "needed"},
            {"status": "blocked"},
        ],
    )

    by_id = {item["id"]: item for item in checks}

    assert by_id["messaging-verification"]["status"] == "needs_setup"
    assert "blocked" in by_id["messaging-verification"]["detail"]


def test_activation_checks_include_schedule_verification_for_active_schedules():
    checks = activation_checks(
        setup_inputs=[],
        schedules=[],
        model_preferences=[],
        integrations=[],
        secret_requirements=[],
        schedule_checks=[
            {"status": "verified", "schedule_active": 1},
            {"status": "needed", "schedule_active": 1},
            {"status": "blocked", "schedule_active": 0},
        ],
    )

    by_id = {item["id"]: item for item in checks}

    assert by_id["schedule-verification"]["status"] == "needs_setup"
    assert "1 verified" in by_id["schedule-verification"]["detail"]


def test_activation_checks_include_kanban_verification_when_provided():
    checks = activation_checks(
        setup_inputs=[],
        schedules=[],
        model_preferences=[],
        integrations=[],
        secret_requirements=[],
        kanban_checks=[
            {"status": "verified"},
            {"status": "needed"},
        ],
    )

    by_id = {item["id"]: item for item in checks}

    assert by_id["kanban-verification"]["status"] == "needs_setup"
    assert "1 verified" in by_id["kanban-verification"]["detail"]


def test_activation_checks_include_profile_acceptance_when_provided():
    checks = activation_checks(
        setup_inputs=[],
        schedules=[],
        model_preferences=[],
        integrations=[],
        secret_requirements=[],
        profile_acceptance_checks=[
            {"status": "verified"},
            {"status": "failed"},
        ],
    )

    by_id = {item["id"]: item for item in checks}

    assert by_id["profile-acceptance"]["status"] == "needs_setup"
    assert "1 verified, 1 failed" in by_id["profile-acceptance"]["detail"]


def test_activation_checks_include_profile_installation_when_provided():
    checks = activation_checks(
        setup_inputs=[],
        schedules=[],
        model_preferences=[],
        integrations=[],
        secret_requirements=[],
        profile_installation_checks=[
            {"status": "verified"},
            {"status": "needed"},
        ],
    )

    by_id = {item["id"]: item for item in checks}

    assert by_id["profile-installation"]["status"] == "needs_setup"
    assert "1 verified, 1 needed" in by_id["profile-installation"]["detail"]
