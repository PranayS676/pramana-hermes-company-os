from __future__ import annotations

from collections import defaultdict

from hermes_company_os.activation_report import activation_summary

BLOCKING_STATUSES = {"missing", "invalid"}
OPEN_STATUSES = {"missing", "invalid", "needs_setup", "deferred"}


def activation_sequence_markdown(
    checks: list[dict],
    setup_inputs: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
    profile_installation_checks: list[dict] | None = None,
) -> str:
    summary = activation_summary(checks)
    next_action = next_best_action(
        checks,
        secret_requirements,
        messaging_checks,
        schedule_checks,
        kanban_checks,
        model_preferences,
        integrations,
    )
    lines = [
        "# Founder Activation Sequence",
        "",
        "This is the single operating sequence for bringing Hermes Company OS live. "
        "It stores only non-secret setup state. Slack tokens, Telegram bot tokens, "
        "and provider credentials stay in the real Hermes profile runtime.",
        "",
        "## Current Gate",
        "",
        f"- Ready for live activation: {'yes' if summary['ready'] else 'no'}",
        f"- Blocking checks: {summary['blocking']}",
        f"- Needs setup checks: {summary['needs_setup']}",
        f"- Deferred checks: {summary['deferred']}",
        f"- Ready checks: {summary['ready_checks']} of {summary['total']}",
        "",
        "## Next Best Action",
        "",
        f"- {next_action}",
        "",
        "## Ordered Activation Path",
        "",
        "1. Run `/setup/first-run.md` for the guided local sequence, or capture "
        "non-secret founder and workspace IDs directly in `/setup#inputs`. Track "
        "stage progress in `/setup/progress-board.md`.",
        "2. Install or connect Hermes with `/setup/hermes-runtime.md` and "
        "`/setup/hermes-install.ps1`, then review local runtime state with "
        "`/setup/runtime-preflight.md`.",
        "3. Review `/setup/activation-runner.md` and decide which local phases to run.",
        "4. Create or review Hermes profiles with `/setup/bootstrap.ps1` and "
        "`/setup/profile-artifacts.md`, then verify them in "
        "`/setup#profile-installation-tracking`.",
        "5. Create Slack apps from `/setup/slack-plan.md`, `/setup/slack-manifests.json`, "
        "and `/setup/slack-provisioning.md`.",
        "6. Configure the Chief of Staff Telegram bot with `/setup/telegram-botfather.md`, "
        "`/setup/telegram-provisioning.md`, and `/setup/telegram-policy.md`.",
        "7. Audit loaded Slack and Telegram keys with `/setup/secret-audit.ps1`.",
        "8. Run Kanban setup with `/setup/kanban-provisioning.md`, "
        "`/setup/kanban-runbook.md`, and `/setup/kanban-diagnostics.ps1`.",
        "9. Verify manual standups, then install cron from "
        "`/setup/schedule-provisioning.md` and `/setup/standup-cron.ps1`.",
        "10. Configure LLM provider credentials last with `/setup/llm-provisioning.md`, "
        "`/setup/llm-credentials.md`, and `/setup/llm-finalize.md`.",
        "11. Audit LLM keys with `/setup/secret-audit.ps1 -AuditLlm`.",
        "12. Run profile smoke checks in `/setup#profile-smoke`.",
        "13. Run role-specific acceptance prompts from `/setup/profile-acceptance.md` "
        "and track them in `/setup#profile-acceptance-tracking`.",
        "14. Review `/setup/company-launch-drill.md`, then make the founder "
        "go/no-go decision before `/setup/idea-intake.md`.",
        "",
        "## Founder Inputs Needed Now",
        "",
    ]
    missing_inputs = [
        item for item in setup_inputs if item["required"] and not item["value"].strip()
    ]
    if missing_inputs:
        for item in missing_inputs:
            lines.append(f"- {item['label']} (`{item['key']}`): {item['help_text']}")
    else:
        lines.append("- None. Required non-secret setup inputs are captured.")
    lines.extend(
        [
            "",
            "## External Secrets To Load Outside This Dashboard",
            "",
        ]
    )
    lines.extend(_secret_lines(secret_requirements))
    lines.extend(
        [
            "",
            "## Verification Work Remaining",
            "",
            *_verification_lines("Messaging", messaging_checks),
            *_verification_lines("Schedule", schedule_checks),
            *_verification_lines("Kanban", kanban_checks),
            *_verification_lines(
                "Profile installation",
                profile_installation_checks or [],
            ),
            *_model_lines(model_preferences),
            "",
            "## Runbooks",
            "",
            "- `/setup/company-manifest.md`",
            "- `/setup/company-manifest.json`",
            "- `/setup/company-launch-drill.md`",
            "- `/setup/company-launch-drill.json`",
            "- `/setup/founder-handoff.md`",
            "- `/setup/founder-handoff.json`",
            "- `/setup/input-ledger.md`",
            "- `/setup/input-ledger.json`",
            "- `/setup/kickoff-readiness.md`",
            "- `/setup/kickoff-readiness.json`",
            "- `/setup/inputs-needed.md`",
            "- `/setup/credential-loading.md`",
            "- `/setup/credential-loading.json`",
            "- `/setup/credential-status-template.md`",
            "- `/setup/credential-status-template.json`",
            "- `/setup/founder-next-actions.md`",
            "- `/setup/founder-next-actions.json`",
            "- `/setup/first-run.md`",
            "- `/setup/first-run.json`",
            "- `/setup/first-run.ps1`",
            "- `/setup/progress-board.md`",
            "- `/setup/progress-board.json`",
            "- `/setup/slack-plan.md`",
            "- `/setup/slack-manifests.json`",
            "- `/setup/slack-provisioning.md`",
            "- `/setup/slack-provisioning.json`",
            "- `/setup/slack-provisioning.ps1`",
            "- `/setup/slack-bot-user-map.json`",
            "- `/setup/slack-workspace.md`",
            "- `/setup/slack-invite-matrix.json`",
            "- `/setup/slack-invite-matrix.csv`",
            "- `/setup/telegram-plan.md`",
            "- `/setup/telegram-botfather.md`",
            "- `/setup/telegram-provisioning.md`",
            "- `/setup/telegram-provisioning.json`",
            "- `/setup/telegram-provisioning.ps1`",
            "- `/setup/telegram-policy.md`",
            "- `/setup/telegram-policy.json`",
            "- `/setup/messaging-drill.md`",
            "- `/setup/messaging-drill.json`",
            "- `/setup/gateway-operations.md`",
            "- `/setup/gateway-operations.json`",
            "- `/setup/gateway-operations.ps1`",
            "- `/setup/secret-audit.md`",
            "- `/setup/secret-audit.ps1`",
            "- `/setup/hermes-runtime.md`",
            "- `/setup/hermes-runtime.json`",
            "- `/setup/hermes-install.ps1`",
            "- `/setup/runtime-preflight.md`",
            "- `/setup/activation-runner.md`",
            "- `/setup/activation-runner.ps1`",
            "- `/setup/schedule-provisioning.md`",
            "- `/setup/schedule-provisioning.json`",
            "- `/setup/schedule-provisioning.ps1`",
            "- `/setup/team-topology.md`",
            "- `/setup/team-topology.json`",
            "- `/setup/delegation-playbook.md`",
            "- `/setup/delegation-playbook.json`",
            "- `/setup/profile-installation.md`",
            "- `/setup/profile-installation.json`",
            "- `/setup/profile-installation.ps1`",
            "- `/setup/founder-decisions.md`",
            "- `/setup/founder-decisions.json`",
            "- `/setup/profile-acceptance.md`",
            "- `/setup/profile-acceptance.json`",
            "- `/setup/standup-preview.md`",
            "- `/setup/standup-preview.json`",
            "- `/setup/idea-intake.md`",
            "- `/setup/idea-intake.json`",
            "- `/setup/project-workflow.md`",
            "- `/setup/project-workflow.json`",
            "- `/setup/kanban-provisioning.md`",
            "- `/setup/kanban-provisioning.json`",
            "- `/setup/kanban-provisioning.ps1`",
            "- `/setup/kanban-runbook.md`",
            "- `/setup/standup-runbook.md`",
            "- `/setup/llm-credentials.md`",
            "- `/setup/llm-provisioning.md`",
            "- `/setup/llm-provisioning.json`",
            "- `/setup/llm-provisioning.ps1`",
            "- `/setup/llm-provider-presets.md`",
            "- `/setup/llm-provider-presets.json`",
            "- `/setup/llm-finalize.md`",
            "- `/setup/llm-finalize.ps1`",
            "- `/setup/llm-smoke.md`",
            "- `/setup/llm-smoke.json`",
            "- `/setup/verification-evidence.md`",
            "- `/setup/verification-evidence.json`",
            "- `/setup/readiness-report.md`",
            "- `/setup/activation-checklist.md`",
            "",
        ]
    )
    return "\n".join(lines)


def next_best_action(
    checks: list[dict],
    secret_requirements: list[dict],
    messaging_checks: list[dict],
    schedule_checks: list[dict],
    kanban_checks: list[dict],
    model_preferences: list[dict],
    integrations: list[dict],
) -> str:
    blocking = [item for item in checks if item["status"] in BLOCKING_STATUSES]
    if blocking:
        return f"Resolve `{blocking[0]['label']}`: {blocking[0]['detail']}"

    profile_installation = next(
        (item for item in checks if item["id"] == "profile-installation"),
        None,
    )
    if profile_installation and profile_installation["status"] == "needs_setup":
        return (
            "Run `/setup/profile-installation.ps1`, then complete "
            "`/setup#profile-installation-tracking`."
        )

    if _category_has_status(secret_requirements, "slack", {"needed"}):
        return (
            "Create Slack apps, load Slack tokens into Hermes profiles externally, "
            "then mark Slack secret status loaded."
        )
    if _category_has_status(secret_requirements, "telegram", {"needed"}):
        return (
            "Create the Chief of Staff Telegram bot, load its token externally, "
            "then mark Telegram secret status loaded."
        )
    if _checks_have_open_work(messaging_checks):
        return (
            "Complete `/setup#messaging-verification` for Slack DMs, channel "
            "mentions, and Telegram urgent alerts."
        )
    if _checks_have_open_work(kanban_checks):
        return (
            "Run Kanban initialization, diagnostics, and one dashboard task push "
            "using `/setup/kanban-runbook.md`."
        )
    if _checks_have_open_work(schedule_checks):
        return "Run manual standups, install cron, and complete `/setup#schedule-verification`."
    if _category_has_status(secret_requirements, "llm", {"needed", "deferred"}):
        return (
            "Load LLM provider credentials into each Hermes profile externally, "
            "then run `/setup#profile-smoke`."
        )
    if any(preference["status"] != "verified" for preference in model_preferences):
        return "Run `/setup#profile-smoke` until every Hermes profile is verified."
    if not _integration_ready(integrations, "runtime"):
        return (
            "Mark the LLM provider integration configured after every profile smoke "
            "check passes."
        )
    needs_setup = [item for item in checks if item["status"] == "needs_setup"]
    if needs_setup:
        return f"Resolve `{needs_setup[0]['label']}`: {needs_setup[0]['detail']}"
    return (
        "All local setup gates are complete. Continue with the first founder "
        "idea/project workflow."
    )


def _secret_lines(secret_requirements: list[dict]) -> list[str]:
    if not secret_requirements:
        return ["- None tracked."]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in secret_requirements:
        grouped[item["category"]].append(item)
    lines: list[str] = []
    for category in sorted(grouped):
        lines.append(f"### {category.title()}")
        lines.append("")
        for item in grouped[category]:
            lines.append(
                f"- `{item['status']}` {item['label']} -> "
                f"{item['destination']} (`{item['environment_key']}`)"
            )
        lines.append("")
    return lines


def _verification_lines(label: str, checks: list[dict]) -> list[str]:
    if not checks:
        return [f"- {label}: no checks tracked."]
    open_count = len([item for item in checks if item["status"] != "verified"])
    verified_count = len(checks) - open_count
    return [f"- {label}: {verified_count} verified, {open_count} open."]


def _model_lines(model_preferences: list[dict]) -> list[str]:
    verified = len([item for item in model_preferences if item["status"] == "verified"])
    open_count = len(model_preferences) - verified
    return [f"- LLM profile smoke checks: {verified} verified, {open_count} open."]


def _category_has_status(
    secret_requirements: list[dict],
    category: str,
    statuses: set[str],
) -> bool:
    return any(
        item["category"] == category and item["status"] in statuses
        for item in secret_requirements
    )


def _checks_have_open_work(checks: list[dict]) -> bool:
    return any(item["status"] != "verified" for item in checks)


def _integration_ready(integrations: list[dict], category: str) -> bool:
    relevant = [item for item in integrations if item["category"] == category]
    return bool(relevant) and all(
        item["status"] in {"configured", "ready"} for item in relevant
    )
