from hermes_company_os.live_verification import live_verification_markdown


def test_live_verification_markdown_counts_checks_and_preserves_no_secret_rule():
    markdown = live_verification_markdown(
        secret_requirements=[
            {"status": "loaded"},
            {"status": "needed"},
        ],
        messaging_checks=[
            {"status": "verified"},
            {"status": "needed"},
        ],
        schedule_checks=[
            {"status": "verified", "schedule_active": 1},
            {"status": "needed", "schedule_active": 1},
            {"status": "blocked", "schedule_active": 0},
        ],
        kanban_checks=[
            {"status": "verified"},
            {"status": "needed"},
        ],
        model_preferences=[
            {"status": "verified"},
            {"status": "planned"},
        ],
        integrations=[
            {"status": "configured"},
            {"status": "needs_setup"},
        ],
        profile_installation_checks=[
            {"status": "verified"},
            {"status": "needed"},
        ],
        profile_acceptance_checks=[
            {"status": "verified"},
            {"status": "blocked"},
        ],
    )

    assert "Live Verification Runbook" in markdown
    assert "Profile installation verified" in markdown
    assert "Profile installation checks: 1 verified" in markdown
    assert "Profile acceptance passes" in markdown
    assert "Profile acceptance checks: 1 verified" in markdown
    assert "External credential statuses: 0 verified, 1 loaded" in markdown
    assert "Messaging checks: 1 verified" in markdown
    assert "Active schedule checks: 1 verified" in markdown
    assert "Kanban checks: 1 verified" in markdown
    assert "Profile smoke checks: 1 verified, 1 open" in markdown
    assert "/setup#profile-acceptance-tracking" in markdown
    assert "/setup#profile-smoke" in markdown
    assert "Do not paste bot tokens" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
    assert "TELEGRAM_BOT_TOKEN" not in markdown
