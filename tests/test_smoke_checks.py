from hermes_company_os.smoke_checks import append_smoke_note, profile_smoke_prompt


def test_profile_smoke_prompt_uses_agent_and_model_context():
    prompt = profile_smoke_prompt(
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "role": "Engineering",
            "capabilities": ["architecture", "testing"],
        },
        {"provider": "openai-codex", "model": "gpt-5-codex"},
    )

    assert "Engineering Manager (engineering-manager)" in prompt
    assert "openai-codex / gpt-5-codex" in prompt
    assert "Respond without using Slack, Telegram" in prompt
    assert "- profile_ready: yes/no" in prompt


def test_append_smoke_note_is_idempotent():
    notes = append_smoke_note("Configured in profile .env.", "passed")

    assert notes == "Configured in profile .env. Smoke check passed via dashboard."
    assert append_smoke_note(notes, "passed") == notes
