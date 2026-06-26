from __future__ import annotations

import re

SLACK_MEMBER_ID = re.compile(r"^[UW][A-Z0-9]{2,}$")
SLACK_CHANNEL_ID = re.compile(r"^[CGD][A-Z0-9]{2,}$")
TELEGRAM_ID = re.compile(r"^-?\d+$")

SLACK_CHANNEL_KEYS = [
    "slack_channel_founder_command",
    "slack_channel_agent_standup",
    "slack_channel_product",
    "slack_channel_research",
    "slack_channel_engineering",
    "slack_channel_marketing",
    "slack_channel_qa_review",
    "slack_channel_decisions",
    "slack_channel_alerts",
]


def activation_checks(
    setup_inputs: list[dict],
    schedules: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    secret_requirements: list[dict] | None = None,
    messaging_checks: list[dict] | None = None,
    schedule_checks: list[dict] | None = None,
    kanban_checks: list[dict] | None = None,
    profile_acceptance_checks: list[dict] | None = None,
    profile_installation_checks: list[dict] | None = None,
) -> list[dict]:
    values = {item["key"]: item["value"].strip() for item in setup_inputs}
    checks = [
        _required_inputs_check(setup_inputs),
        _slack_member_check(values),
        _slack_channel_check(values),
        _telegram_check(values),
        _schedule_check(schedules),
        _model_preference_check(model_preferences),
        _secret_requirement_check(secret_requirements or []),
    ]
    if messaging_checks is not None:
        checks.append(_messaging_verification_check(messaging_checks))
    if schedule_checks is not None:
        checks.append(_schedule_verification_check(schedule_checks))
    if kanban_checks is not None:
        checks.append(_kanban_verification_check(kanban_checks))
    if profile_installation_checks is not None:
        checks.append(_profile_installation_verification_check(profile_installation_checks))
    if profile_acceptance_checks is not None:
        checks.append(_profile_acceptance_verification_check(profile_acceptance_checks))
    checks.extend(
        [
            _integration_check("Slack integrations", integrations, "slack"),
            _integration_check("Telegram urgent alerts", integrations, "telegram"),
        ]
    )
    checks.extend(
        [
            _integration_check("Kanban integration", integrations, "kanban"),
            _integration_check("Standup cron", integrations, "schedule"),
            _integration_check("LLM provider", integrations, "runtime"),
        ]
    )
    return checks


def activation_summary(checks: list[dict]) -> dict:
    blocking = [item for item in checks if item["status"] in {"missing", "invalid"}]
    needs_setup = [item for item in checks if item["status"] == "needs_setup"]
    deferred = [item for item in checks if item["status"] == "deferred"]
    ready = [item for item in checks if item["status"] == "ready"]
    return {
        "ready": not blocking and not needs_setup,
        "blocking": len(blocking),
        "needs_setup": len(needs_setup),
        "deferred": len(deferred),
        "ready_checks": len(ready),
        "total": len(checks),
    }


def activation_report_markdown(checks: list[dict]) -> str:
    summary = activation_summary(checks)
    lines = [
        "# Activation Readiness Report",
        "",
        "This report validates no-secret setup state before live Hermes activation. "
        "It does not require or store Slack tokens, Telegram tokens, or LLM API keys.",
        "",
        "## Summary",
        "",
        f"- Ready for live activation: {'yes' if summary['ready'] else 'no'}",
        f"- Blocking checks: {summary['blocking']}",
        f"- Needs setup checks: {summary['needs_setup']}",
        f"- Deferred checks: {summary['deferred']}",
        f"- Ready checks: {summary['ready_checks']} of {summary['total']}",
        "",
        "## Checks",
        "",
    ]
    for item in checks:
        lines.extend(
            [
                f"### {item['label']}",
                "",
                f"- Status: `{item['status']}`",
                f"- Detail: {item['detail']}",
                "",
            ]
        )
    return "\n".join(lines)


def _required_inputs_check(setup_inputs: list[dict]) -> dict:
    missing = [
        item["label"]
        for item in setup_inputs
        if item["required"]
        and item["secret_policy"] == "non_secret"
        and not item["value"].strip()
    ]
    if missing:
        return _check(
            "required-inputs",
            "Required dashboard inputs",
            "missing",
            "Missing: " + ", ".join(missing),
        )
    return _check(
        "required-inputs",
        "Required dashboard inputs",
        "ready",
        "All required non-secret dashboard inputs are captured.",
    )


def _slack_member_check(values: dict[str, str]) -> dict:
    member_id = values.get("founder_slack_member_id", "")
    if not member_id:
        return _check("slack-member-id", "Founder Slack member ID", "missing", "Value is blank.")
    if not SLACK_MEMBER_ID.match(member_id):
        return _check(
            "slack-member-id",
            "Founder Slack member ID",
            "invalid",
            "Expected a Slack member ID starting with U or W.",
        )
    return _check("slack-member-id", "Founder Slack member ID", "ready", member_id)


def _slack_channel_check(values: dict[str, str]) -> dict:
    invalid = []
    missing = []
    for key in SLACK_CHANNEL_KEYS:
        value = values.get(key, "")
        if not value:
            if key not in {"slack_channel_decisions", "slack_channel_alerts"}:
                missing.append(key)
            continue
        if not SLACK_CHANNEL_ID.match(value):
            invalid.append(key)
    if invalid:
        return _check(
            "slack-channel-ids",
            "Slack channel IDs",
            "invalid",
            "Expected channel IDs starting with C, G, or D for: " + ", ".join(invalid),
        )
    if missing:
        return _check(
            "slack-channel-ids",
            "Slack channel IDs",
            "missing",
            "Missing required Slack channel IDs: " + ", ".join(missing),
        )
    return _check("slack-channel-ids", "Slack channel IDs", "ready", "All provided IDs look valid.")


def _telegram_check(values: dict[str, str]) -> dict:
    user_id = values.get("founder_telegram_user_id", "")
    home_channel = values.get("telegram_home_channel", "")
    if not user_id:
        return _check(
            "telegram-ids",
            "Telegram IDs",
            "missing",
            "Founder Telegram user ID is blank.",
        )
    if not TELEGRAM_ID.match(user_id):
        return _check(
            "telegram-ids",
            "Telegram IDs",
            "invalid",
            "Founder Telegram user ID must be numeric.",
        )
    if home_channel and not TELEGRAM_ID.match(home_channel):
        return _check(
            "telegram-ids",
            "Telegram IDs",
            "invalid",
            "Telegram home channel/chat must be numeric.",
        )
    return _check("telegram-ids", "Telegram IDs", "ready", "Telegram numeric IDs look valid.")


def _schedule_check(schedules: list[dict]) -> dict:
    active = [schedule for schedule in schedules if schedule["active"]]
    if not active:
        return _check(
            "standup-schedules",
            "Standup schedules",
            "missing",
            "No active standup schedules.",
        )
    invalid = [
        schedule["id"]
        for schedule in active
        if not schedule["timezone"].strip() or not schedule["slack_channel"].strip()
    ]
    if invalid:
        return _check(
            "standup-schedules",
            "Standup schedules",
            "invalid",
            "Active schedules need timezone and Slack channel: " + ", ".join(invalid),
        )
    return _check(
        "standup-schedules",
        "Standup schedules",
        "ready",
        f"{len(active)} active schedule(s).",
    )


def _model_preference_check(model_preferences: list[dict]) -> dict:
    missing = [
        preference["agent_id"]
        for preference in model_preferences
        if not preference["provider"].strip() or not preference["model"].strip()
    ]
    if missing:
        return _check(
            "model-preferences",
            "LLM profile preferences",
            "missing",
            "Missing provider/model for: " + ", ".join(missing),
        )
    verified = [item for item in model_preferences if item["status"] == "verified"]
    if len(verified) == len(model_preferences):
        return _check(
            "model-preferences",
            "LLM profile preferences",
            "ready",
            "All profiles verified.",
        )
    return _check(
        "model-preferences",
        "LLM profile preferences",
        "deferred",
        (
            f"{len(verified)} of {len(model_preferences)} profiles verified. "
            "Live credentials are deferred."
        ),
    )


def _secret_requirement_check(secret_requirements: list[dict]) -> dict:
    if not secret_requirements:
        return _check(
            "external-secret-status",
            "External secret status",
            "missing",
            "No external secret requirements are tracked.",
        )
    waiting = [item for item in secret_requirements if item["status"] == "needed"]
    loaded = [item for item in secret_requirements if item["status"] in {"loaded", "verified"}]
    deferred = [item for item in secret_requirements if item["status"] == "deferred"]
    if waiting:
        return _check(
            "external-secret-status",
            "External secret status",
            "needs_setup",
            f"{len(waiting)} needed, {len(loaded)} loaded or verified, {len(deferred)} deferred.",
        )
    if deferred:
        return _check(
            "external-secret-status",
            "External secret status",
            "deferred",
            f"{len(loaded)} loaded or verified, {len(deferred)} deferred.",
        )
    return _check(
        "external-secret-status",
        "External secret status",
        "ready",
        "All tracked external secrets are loaded or verified.",
    )


def _messaging_verification_check(messaging_checks: list[dict]) -> dict:
    if not messaging_checks:
        return _check(
            "messaging-verification",
            "Messaging verification",
            "missing",
            "No messaging verification checks are tracked.",
        )
    blocked = [item for item in messaging_checks if item["status"] == "blocked"]
    needed = [item for item in messaging_checks if item["status"] == "needed"]
    loaded = [item for item in messaging_checks if item["status"] == "loaded"]
    deferred = [item for item in messaging_checks if item["status"] == "deferred"]
    verified = [item for item in messaging_checks if item["status"] == "verified"]
    if blocked:
        return _check(
            "messaging-verification",
            "Messaging verification",
            "needs_setup",
            f"{len(blocked)} blocked check(s), {len(verified)} verified.",
        )
    if needed or loaded:
        return _check(
            "messaging-verification",
            "Messaging verification",
            "needs_setup",
            (
                f"{len(verified)} verified, {len(loaded)} loaded, "
                f"{len(needed)} needed, {len(deferred)} deferred."
            ),
        )
    if deferred:
        return _check(
            "messaging-verification",
            "Messaging verification",
            "deferred",
            f"{len(verified)} verified, {len(deferred)} deferred.",
        )
    return _check(
        "messaging-verification",
        "Messaging verification",
        "ready",
        "All messaging checks are verified.",
    )


def _schedule_verification_check(schedule_checks: list[dict]) -> dict:
    active_checks = [item for item in schedule_checks if item.get("schedule_active", 1)]
    if not active_checks:
        return _check(
            "schedule-verification",
            "Schedule verification",
            "missing",
            "No active schedule verification checks are tracked.",
        )
    blocked = [item for item in active_checks if item["status"] == "blocked"]
    needed = [item for item in active_checks if item["status"] == "needed"]
    deferred = [item for item in active_checks if item["status"] == "deferred"]
    verified = [item for item in active_checks if item["status"] == "verified"]
    if blocked:
        return _check(
            "schedule-verification",
            "Schedule verification",
            "needs_setup",
            f"{len(blocked)} blocked check(s), {len(verified)} verified.",
        )
    if needed:
        return _check(
            "schedule-verification",
            "Schedule verification",
            "needs_setup",
            f"{len(verified)} verified, {len(needed)} needed, {len(deferred)} deferred.",
        )
    if deferred:
        return _check(
            "schedule-verification",
            "Schedule verification",
            "deferred",
            f"{len(verified)} verified, {len(deferred)} deferred.",
        )
    return _check(
        "schedule-verification",
        "Schedule verification",
        "ready",
        "All active schedule checks are verified.",
    )


def _kanban_verification_check(kanban_checks: list[dict]) -> dict:
    if not kanban_checks:
        return _check(
            "kanban-verification",
            "Kanban verification",
            "missing",
            "No Kanban verification checks are tracked.",
        )
    blocked = [item for item in kanban_checks if item["status"] == "blocked"]
    needed = [item for item in kanban_checks if item["status"] == "needed"]
    deferred = [item for item in kanban_checks if item["status"] == "deferred"]
    verified = [item for item in kanban_checks if item["status"] == "verified"]
    if blocked:
        return _check(
            "kanban-verification",
            "Kanban verification",
            "needs_setup",
            f"{len(blocked)} blocked check(s), {len(verified)} verified.",
        )
    if needed:
        return _check(
            "kanban-verification",
            "Kanban verification",
            "needs_setup",
            f"{len(verified)} verified, {len(needed)} needed, {len(deferred)} deferred.",
        )
    if deferred:
        return _check(
            "kanban-verification",
            "Kanban verification",
            "deferred",
            f"{len(verified)} verified, {len(deferred)} deferred.",
        )
    return _check(
        "kanban-verification",
        "Kanban verification",
        "ready",
        "All Kanban checks are verified.",
    )


def _profile_installation_verification_check(
    profile_installation_checks: list[dict],
) -> dict:
    if not profile_installation_checks:
        return _check(
            "profile-installation",
            "Profile installation",
            "missing",
            "No profile installation checks are tracked.",
        )
    blocked = [
        item for item in profile_installation_checks if item["status"] == "blocked"
    ]
    needed = [item for item in profile_installation_checks if item["status"] == "needed"]
    deferred = [
        item for item in profile_installation_checks if item["status"] == "deferred"
    ]
    verified = [
        item for item in profile_installation_checks if item["status"] == "verified"
    ]
    if blocked:
        return _check(
            "profile-installation",
            "Profile installation",
            "needs_setup",
            f"{len(blocked)} blocked check(s), {len(verified)} verified.",
        )
    if needed:
        return _check(
            "profile-installation",
            "Profile installation",
            "needs_setup",
            f"{len(verified)} verified, {len(needed)} needed, {len(deferred)} deferred.",
        )
    if deferred:
        return _check(
            "profile-installation",
            "Profile installation",
            "deferred",
            f"{len(verified)} verified, {len(deferred)} deferred.",
        )
    return _check(
        "profile-installation",
        "Profile installation",
        "ready",
        "All Hermes profile installation checks are verified.",
    )


def _profile_acceptance_verification_check(acceptance_checks: list[dict]) -> dict:
    if not acceptance_checks:
        return _check(
            "profile-acceptance",
            "Profile acceptance",
            "missing",
            "No profile acceptance checks are tracked.",
        )
    blocked = [item for item in acceptance_checks if item["status"] == "blocked"]
    failed = [item for item in acceptance_checks if item["status"] == "failed"]
    needed = [item for item in acceptance_checks if item["status"] == "needed"]
    deferred = [item for item in acceptance_checks if item["status"] == "deferred"]
    verified = [item for item in acceptance_checks if item["status"] == "verified"]
    if blocked or failed:
        return _check(
            "profile-acceptance",
            "Profile acceptance",
            "needs_setup",
            (
                f"{len(verified)} verified, {len(failed)} failed, "
                f"{len(blocked)} blocked."
            ),
        )
    if needed:
        return _check(
            "profile-acceptance",
            "Profile acceptance",
            "needs_setup",
            f"{len(verified)} verified, {len(needed)} needed, {len(deferred)} deferred.",
        )
    if deferred:
        return _check(
            "profile-acceptance",
            "Profile acceptance",
            "deferred",
            f"{len(verified)} verified, {len(deferred)} deferred.",
        )
    return _check(
        "profile-acceptance",
        "Profile acceptance",
        "ready",
        "All role acceptance checks are verified.",
    )


def _integration_check(label: str, integrations: list[dict], category: str) -> dict:
    relevant = [item for item in integrations if item["category"] == category]
    configured = [item for item in relevant if item["status"] in {"configured", "ready"}]
    if not relevant:
        return _check(f"integration-{category}", label, "missing", "No integration records found.")
    if category == "runtime" and relevant[0]["status"] == "deferred":
        return _check(
            f"integration-{category}",
            label,
            "deferred",
            "Provider credentials and live verification are intentionally last.",
        )
    if len(configured) == len(relevant):
        return _check(
            f"integration-{category}",
            label,
            "ready",
            f"{len(configured)} of {len(relevant)} ready.",
        )
    return _check(
        f"integration-{category}",
        label,
        "needs_setup",
        f"{len(configured)} of {len(relevant)} ready.",
    )


def _check(check_id: str, label: str, status: str, detail: str) -> dict:
    return {"id": check_id, "label": label, "status": status, "detail": detail}
