from __future__ import annotations


def build_standup_prompt(
    *,
    schedule: dict,
    agents: list[dict],
    tasks: list[dict],
    documents: list[dict],
    slack_founder_command: str,
    slack_alerts: str,
    telegram_urgent_label: str,
) -> str:
    agent_lines = "\n".join(
        f"- {agent['name']} ({agent['id']}): {agent['slack_channel']}" for agent in agents
    )
    task_lines = "\n".join(
        f"- [{task['status']}/{task['priority']}] {task['title']} -> {task['owner_name']}"
        for task in tasks
    ) or "- No dashboard tasks recorded yet."
    document_lines = "\n".join(
        f"- [{document['status']}] {document['title']} ({document['doc_type']})"
        for document in documents
    ) or "- No dashboard documents recorded yet."

    return f"""
You are the Chief of Staff profile for Hermes Company OS.

Run the {schedule['name']} for the founder's AI company.

Operating rules:
- Slack is the main workspace.
- Post the full standup summary to {schedule['slack_channel']}.
- Use {slack_founder_command} for decisions requiring founder input.
- Use {slack_alerts} for blockers or failed runs.
- Send Telegram only for urgent founder alerts through: {telegram_urgent_label}.
- Do not message Telegram for routine progress.
- Keep the standup concise and action-oriented.

Current agent map:
{agent_lines}

Current dashboard tasks:
{task_lines}

Current dashboard documents:
{document_lines}

Return these sections:
1. Completed since last standup
2. Active work
3. Blockers
4. Founder decisions needed
5. Next-cycle focus
6. Telegram escalation, either "None" or the exact urgent alert text
""".strip()


def build_agent_prompt(agent: dict, founder_request: str) -> str:
    return f"""
You are the {agent['name']} Hermes profile.

Role:
{agent['description']}

Identity:
{agent['soul']}

Founder request:
{founder_request}

Produce a planning/documentation response only. Do not make code changes, deploy systems,
or modify external state unless the founder explicitly approved that action.
""".strip()
