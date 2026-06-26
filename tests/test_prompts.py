from hermes_company_os.prompts import build_agent_prompt, build_standup_prompt


def test_standup_prompt_routes_slack_and_telegram():
    prompt = build_standup_prompt(
        schedule={
            "name": "Morning Standup",
            "slack_channel": "#agent-standup",
        },
        agents=[
            {"name": "Chief of Staff", "id": "chief-of-staff", "slack_channel": "#founder-command"}
        ],
        tasks=[],
        documents=[],
        slack_founder_command="#founder-command",
        slack_alerts="#alerts",
        telegram_urgent_label="Founder Telegram urgent channel",
    )

    assert "#agent-standup" in prompt
    assert "#alerts" in prompt
    assert "Telegram only for urgent founder alerts" in prompt
    assert "Founder decisions needed" in prompt


def test_agent_prompt_keeps_v1_planning_only():
    prompt = build_agent_prompt(
        {
            "name": "Engineering Manager",
            "description": "Creates architecture plans.",
            "soul": "Think in AWS, tests, and distributed systems.",
        },
        "Plan a product architecture.",
    )

    assert "planning/documentation response only" in prompt
    assert "Do not make code changes" in prompt

