from hermes_company_os.bootstrap import powershell_bootstrap, profile_setup_commands


def test_profile_setup_commands_include_gateway_commands():
    agents = [
        {
            "id": "chief-of-staff",
            "name": "Chief of Staff",
            "description": "Coordinates work.",
            "hermes_command": "chief-of-staff",
        }
    ]

    commands = profile_setup_commands(agents)

    assert commands[0]["create"] == (
        'hermes profile create chief-of-staff --description "Coordinates work."'
    )
    assert commands[0]["gateway_setup"] == "chief-of-staff gateway setup"


def test_powershell_bootstrap_writes_soul_and_kanban():
    agents = [
        {
            "id": "product-manager",
            "name": "Product Manager",
            "description": "Less is more.",
            "slack_channel": "#product",
            "soul": "Prefer fewer concepts and clear workflows.",
        }
    ]

    script = powershell_bootstrap(
        agents,
        {
            "founder_slack_member_id": "U123",
            "slack_channel_product": "C123",
            "llm_provider": "openai-codex",
            "llm_model": "gpt-5-codex",
            "standup_cadence": "weekdays",
        },
    )

    assert "hermes profile create product-manager" in script
    assert "HERMES_HOME" in script
    assert "LOCALAPPDATA" in script
    assert "Join-Path $ProfileRoot 'product-manager'" in script
    assert "$soulPath = Join-Path $profilePath 'SOUL.md'" in script
    assert ".env.example" in script
    assert "SLACK_ALLOWED_USERS=U123" in script
    assert "SLACK_HOME_CHANNEL=C123" in script
    assert "config.yaml.example" in script
    assert 'provider: "openai-codex"' in script
    assert 'model: "gpt-5-codex"' in script
    assert "hermes kanban diagnostics --json" in script
    assert 'chief-of-staff cron create "every weekday at 9am"' in script
