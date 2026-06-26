from __future__ import annotations

from hermes_company_os.activation import cron_commands


def standup_runbook_markdown(
    setup_values: dict[str, str],
    schedules: list[dict],
    schedule_checks: list[dict] | None = None,
) -> str:
    active = [schedule for schedule in schedules if schedule.get("active", 1)]
    paused = [schedule for schedule in schedules if not schedule.get("active", 1)]
    lines = [
        "# Standup Scheduling Runbook",
        "",
        "The Chief of Staff profile owns scheduled company standups. Slack is the "
        "main delivery surface; Telegram is urgent-only for founder approvals, blockers, "
        "failed runs, or broken schedules.",
        "",
        "## Current Cadence",
        "",
        f"- Cadence: `{setup_values.get('standup_cadence') or 'every day'}`",
        f"- Active schedules: {len(active)}",
        f"- Paused schedules: {len(paused)}",
        "",
        "## Active Schedules",
        "",
    ]
    if active:
        for schedule in active:
            lines.extend(_schedule_lines(schedule))
    else:
        lines.append("- None. Enable at least one schedule before creating cron jobs.")
    if paused:
        lines.extend(["", "## Paused Schedules", ""])
        for schedule in paused:
            lines.extend(_schedule_lines(schedule))
    lines.extend(
        [
            "",
            "## Manual Verification First",
            "",
            "1. Confirm Slack and Telegram gateways are configured.",
            "2. Use the dashboard standup run button for each active schedule.",
            "3. Confirm the full summary appears in the schedule Slack channel.",
            "4. Confirm Telegram stays quiet unless the standup contains an urgent founder alert.",
            "5. Record non-secret evidence in `/setup#schedule-verification`.",
            "",
            "## Cron Install Commands",
            "",
            "Use `/setup/standup-cron.ps1` for a PowerShell script version.",
            "",
            "```powershell",
            *cron_commands(setup_values, schedules),
            "chief-of-staff cron list",
            "```",
            "",
            "## Verification Matrix",
            "",
        ]
    )
    active_check_rows = [
        check for check in (schedule_checks or []) if check.get("schedule_active", 1)
    ]
    if active_check_rows:
        for check in active_check_rows:
            lines.extend(
                [
                    f"- `{check['id']}`: {check['label']}",
                    f"  Status: `{check['status']}`",
                    f"  Evidence: {check['evidence'] or 'not recorded'}",
                ]
            )
    else:
        lines.append("- Use `/setup#schedule-verification` to track manual and cron checks.")
    lines.extend(
        [
            "",
            "## Completion Criteria",
            "",
            "- Every active schedule has one successful manual run.",
            "- `chief-of-staff cron list` shows every active schedule.",
            "- `/setup#schedule-verification` checks are verified with non-secret evidence.",
            "- `standup-cron` integration status is `configured`.",
            "",
        ]
    )
    return "\n".join(lines)


def standup_cron_powershell(setup_values: dict[str, str], schedules: list[dict]) -> str:
    commands = cron_commands(setup_values, schedules)
    command_block = "\n".join(commands) if commands else "# No active schedules to install."
    return "\n".join(
        [
            "# Hermes Company OS standup cron installer",
            "# Run after Slack and Telegram gateways are configured.",
            "# This script contains no tokens or provider credentials.",
            "",
            command_block,
            "chief-of-staff cron list",
            "",
        ]
    )


def _schedule_lines(schedule: dict) -> list[str]:
    return [
        f"### {schedule['name']}",
        "",
        f"- Time: `{int(schedule['hour']):02d}:{int(schedule['minute']):02d}`",
        f"- Timezone: `{schedule['timezone']}`",
        f"- Slack channel: `{schedule['slack_channel']}`",
        f"- Telegram policy: {schedule['telegram_policy']}",
        "",
    ]
