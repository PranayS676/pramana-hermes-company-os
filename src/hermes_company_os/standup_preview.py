from __future__ import annotations

import json

from hermes_company_os.prompts import build_standup_prompt

DRILL_CASES = [
    {
        "id": "routine-progress",
        "label": "Routine progress summary",
        "prompt": "Summarize routine completed work and next focus with no blockers.",
        "expected_slack": "Post the full standup summary to the standup Slack channel.",
        "expected_telegram": "none",
    },
    {
        "id": "founder-approval",
        "label": "Founder approval needed",
        "prompt": "Include one decision that requires founder approval before agents continue.",
        "expected_slack": "Post summary and decision context to Slack.",
        "expected_telegram": "urgent founder approval alert",
    },
    {
        "id": "blocked-work",
        "label": "Blocked work",
        "prompt": "Include one blocker that requires founder action.",
        "expected_slack": "Post blocker details to Slack and alerts channel.",
        "expected_telegram": "urgent blocker alert",
    },
    {
        "id": "failed-run",
        "label": "Failed scheduled operation",
        "prompt": "Report a failed run or broken scheduled operation.",
        "expected_slack": "Post failure details to Slack and alerts channel.",
        "expected_telegram": "urgent failed-run alert",
    },
]


def standup_preview_payload(
    *,
    schedules: list[dict],
    agents: list[dict],
    tasks: list[dict],
    documents: list[dict],
    slack_founder_command: str,
    slack_alerts: str,
    telegram_urgent_label: str,
) -> dict:
    active_schedules = [schedule for schedule in schedules if schedule.get("active", 1)]
    return {
        "title": "Standup Preview And Drill Pack",
        "credential_boundary": (
            "This preview contains generated prompts and expected routing only. "
            "It does not include Slack tokens, Telegram bot tokens, or provider API keys."
        ),
        "owner_profile": "chief-of-staff",
        "delivery_policy": {
            "primary_workspace": "slack",
            "routine_channel": "schedule.slack_channel",
            "founder_decisions": slack_founder_command,
            "alerts": slack_alerts,
            "telegram": "urgent founder alerts only",
            "telegram_target_label": telegram_urgent_label,
        },
        "schedules": [
            _schedule_preview(
                schedule=schedule,
                agents=agents,
                tasks=tasks,
                documents=documents,
                slack_founder_command=slack_founder_command,
                slack_alerts=slack_alerts,
                telegram_urgent_label=telegram_urgent_label,
            )
            for schedule in active_schedules
        ],
        "drill_cases": DRILL_CASES,
        "verification": {
            "manual_run": "/setup#schedule-verification",
            "cron_install": "/setup/standup-cron.ps1",
            "runbook": "/setup/standup-runbook.md",
            "live_verification": "/setup/live-verification.md",
        },
    }


def standup_preview_json(**kwargs) -> str:
    return json.dumps(standup_preview_payload(**kwargs), indent=2, sort_keys=True)


def standup_preview_markdown(**kwargs) -> str:
    payload = standup_preview_payload(**kwargs)
    lines = [
        "# Standup Preview And Drill Pack",
        "",
        "Use this before installing Chief of Staff cron. It shows the exact prompt "
        "shape the dashboard will send for each active schedule.",
        "",
        "## Credential Boundary",
        "",
        payload["credential_boundary"],
        "",
        "## Delivery Policy",
        "",
        f"- Owner profile: `{payload['owner_profile']}`",
        "- Primary workspace: Slack",
        f"- Founder decisions: `{payload['delivery_policy']['founder_decisions']}`",
        f"- Alerts: `{payload['delivery_policy']['alerts']}`",
        f"- Telegram: {payload['delivery_policy']['telegram']}",
        f"- Telegram target label: `{payload['delivery_policy']['telegram_target_label']}`",
        "",
        "## Active Schedule Prompts",
        "",
    ]
    if payload["schedules"]:
        for schedule in payload["schedules"]:
            lines.extend(
                [
                    f"### {schedule['name']}",
                    "",
                    f"- Time: `{schedule['time']}`",
                    f"- Timezone: `{schedule['timezone']}`",
                    f"- Slack channel: `{schedule['slack_channel']}`",
                    f"- Telegram policy: {schedule['telegram_policy']}",
                    "",
                    "```text",
                    schedule["prompt"],
                    "```",
                    "",
                ]
            )
    else:
        lines.append("- No active standup schedules.")
        lines.append("")
    lines.extend(["## Drill Cases", ""])
    for case in payload["drill_cases"]:
        lines.extend(
            [
                f"### {case['label']}",
                "",
                f"- Prompt: {case['prompt']}",
                f"- Expected Slack: {case['expected_slack']}",
                f"- Expected Telegram: `{case['expected_telegram']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Verification",
            "",
            "- Run each active standup manually from the dashboard first.",
            "- Record non-secret evidence in `/setup#schedule-verification`.",
            "- Install cron only after manual runs and messaging verification pass.",
            "",
        ]
    )
    return "\n".join(lines)


def _schedule_preview(
    *,
    schedule: dict,
    agents: list[dict],
    tasks: list[dict],
    documents: list[dict],
    slack_founder_command: str,
    slack_alerts: str,
    telegram_urgent_label: str,
) -> dict:
    return {
        "id": schedule["id"],
        "name": schedule["name"],
        "time": f"{int(schedule['hour']):02d}:{int(schedule['minute']):02d}",
        "timezone": schedule["timezone"],
        "slack_channel": schedule["slack_channel"],
        "telegram_policy": schedule["telegram_policy"],
        "prompt": build_standup_prompt(
            schedule=schedule,
            agents=agents,
            tasks=tasks,
            documents=documents,
            slack_founder_command=slack_founder_command,
            slack_alerts=slack_alerts,
            telegram_urgent_label=telegram_urgent_label,
        ),
    }
