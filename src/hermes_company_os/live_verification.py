from __future__ import annotations

PHASES = [
    (
        "Profile installation verified",
        "Profile Installation Tracking",
        "/setup#profile-installation-tracking",
    ),
    ("External credentials loaded", "Secret Status", "/setup#secret-status"),
    ("Messaging works", "Messaging Verification", "/setup#messaging-verification"),
    ("Kanban works", "Kanban Verification", "/setup#kanban-verification"),
    ("Standups work", "Schedule Verification", "/setup#schedule-verification"),
    ("Profiles answer", "Profile Smoke Checks", "/setup#profile-smoke"),
    (
        "Profile acceptance passes",
        "Profile Acceptance Tracking",
        "/setup#profile-acceptance-tracking",
    ),
]


def live_verification_markdown(
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    profile_installation_checks: list[dict] | None = None,
    profile_acceptance_checks: list[dict] | None = None,
) -> str:
    lines = [
        "# Live Verification Runbook",
        "",
        "Use this only after external credentials are loaded into the real Hermes "
        "profile runtime. Do not paste tokens, API keys, OAuth values, or private "
        "endpoint credentials into this dashboard.",
        "",
        "## Phase Order",
        "",
    ]
    for index, (phase, section, anchor) in enumerate(PHASES, start=1):
        lines.append(f"{index}. {phase}: `{section}` at `{anchor}`")
    lines.extend(
        [
            "",
            "## Current Verification Counts",
            "",
            _status_line(
                "Profile installation checks",
                profile_installation_checks or [],
            ),
            _status_line("External credential statuses", secret_requirements),
            _status_line("Messaging checks", messaging_checks),
            _status_line(
                "Active schedule checks",
                [item for item in schedule_checks if item.get("schedule_active", 1)],
            ),
            _status_line("Kanban checks", kanban_checks),
            _model_line(model_preferences),
            _status_line(
                "Profile acceptance checks",
                profile_acceptance_checks or [],
            ),
            _integration_line(integrations),
            "",
            "## Exact Final Steps",
            "",
            "1. Verify each installed Hermes profile at `/setup#profile-installation-tracking`.",
            "2. Mark each externally loaded credential as `loaded` in `/setup#secret-status`.",
            "3. Start every Hermes profile gateway and complete Slack DM/channel checks.",
            "4. Trigger the Chief of Staff urgent Telegram check and record non-secret evidence.",
            "5. Run Kanban diagnostics from the dashboard and push one dashboard task.",
            "6. Run each active standup manually, then install cron and confirm the cron list.",
            "7. Configure provider/model credentials in each profile runtime.",
            "8. Run every profile smoke check from `/setup#profile-smoke`.",
            "9. Run profile acceptance prompts and record outcomes at "
            "`/setup#profile-acceptance-tracking`.",
            "10. Open `/setup/activation-sequence.md` and confirm the next action is "
            "complete.",
            "",
            "## Evidence Rules",
            "",
            "- Evidence should be short, observable, and non-secret.",
            "- Good examples: `Founder DM reply observed`, `cron list shows morning job`, "
            "`Kanban diagnostics passed`.",
            "- Do not paste bot tokens, provider keys, OAuth payloads, request headers, "
            "private endpoint URLs, or full logs.",
            "",
            "## Completion Gate",
            "",
            "- Messaging verification is fully verified.",
            "- Schedule verification is fully verified for active schedules.",
            "- Kanban verification is fully verified.",
            "- Every Hermes profile installation check is `verified`.",
            "- Every model preference is `verified` from a profile smoke check.",
            "- Every profile acceptance check is `verified`.",
            "- Relevant integration statuses are `configured` or `ready`.",
            "",
        ]
    )
    return "\n".join(lines)


def _status_line(label: str, items: list[dict]) -> str:
    if not items:
        return f"- {label}: none tracked."
    verified = len([item for item in items if item["status"] == "verified"])
    loaded = len([item for item in items if item["status"] == "loaded"])
    configured = len([item for item in items if item["status"] == "configured"])
    open_count = len(items) - verified - loaded - configured
    return (
        f"- {label}: {verified} verified, {loaded} loaded, "
        f"{configured} configured, {open_count} open."
    )


def _model_line(model_preferences: list[dict]) -> str:
    verified = len([item for item in model_preferences if item["status"] == "verified"])
    return (
        f"- Profile smoke checks: {verified} verified, "
        f"{len(model_preferences) - verified} open."
    )


def _integration_line(integrations: list[dict]) -> str:
    ready = len(
        [item for item in integrations if item["status"] in {"configured", "ready"}]
    )
    return f"- Integrations: {ready} ready/configured, {len(integrations) - ready} open."
