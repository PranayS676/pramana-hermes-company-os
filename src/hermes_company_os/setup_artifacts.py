from __future__ import annotations

from hermes_company_os.activation import cron_commands
from hermes_company_os.focused_setup_imports import (
    focused_setup_imports,
    focused_setup_markdown_lines,
)

CHANNEL_INPUT_BY_AGENT = {
    "chief-of-staff": "slack_channel_founder_command",
    "product-manager": "slack_channel_product",
    "research-agent": "slack_channel_research",
    "engineering-manager": "slack_channel_engineering",
    "backend-engineer": "slack_channel_engineering",
    "frontend-engineer": "slack_channel_engineering",
    "cloud-infra-agent": "slack_channel_engineering",
    "test-automation-agent": "slack_channel_engineering",
    "marketing-agent": "slack_channel_marketing",
    "qa-critic": "slack_channel_qa_review",
}

SLACK_SCOPES = [
    "chat:write",
    "app_mentions:read",
    "channels:history",
    "channels:read",
    "groups:history",
    "groups:read",
    "im:history",
    "im:read",
    "im:write",
    "users:read",
    "files:read",
    "files:write",
]

SLACK_EVENTS = [
    "message.im",
    "message.channels",
    "message.groups",
    "app_mention",
]


def inputs_needed_markdown(setup_inputs: list[dict], agents: list[dict]) -> str:
    dashboard_inputs = [
        item for item in setup_inputs if item["secret_policy"] == "non_secret"
    ]
    deferred_config = [
        item for item in setup_inputs if item["secret_policy"] != "non_secret"
    ]
    missing_required = [
        item
        for item in dashboard_inputs
        if item["required"] and not item["value"].strip()
    ]
    lines = [
        "# Inputs Needed",
        "",
        "Use this as the founder checklist before live Hermes activation. Dashboard "
        "inputs are non-secret. Secret credentials stay outside this repo.",
        "",
        "## Missing Required Dashboard Inputs",
        "",
    ]
    if missing_required:
        lines.extend(_setup_input_lines(missing_required, show_status=False))
    else:
        lines.append("- None. Required non-secret dashboard inputs are captured.")
    lines.extend(
        [
            "",
            "## Dashboard Inputs Safe To Store",
            "",
            *_setup_input_lines(dashboard_inputs, show_status=True),
            "",
            "## Deferred Provider And Model Choices",
            "",
        ]
    )
    if deferred_config:
        lines.extend(_setup_input_lines(deferred_config, show_status=True))
    else:
        lines.append("- None configured.")
    lines.extend(
        [
            "",
            "## External Secrets Never Stored Here",
            "",
            "### Slack",
            "",
        ]
    )
    for agent in agents:
        lines.extend(
            [
                f"- {agent['name']}: Slack bot credential loaded externally",
                f"- {agent['name']}: Slack Socket Mode app credential loaded externally",
            ]
        )
    lines.extend(
        [
            "",
            "### Telegram",
            "",
            "- Chief of Staff: Telegram BotFather credential loaded externally",
            "",
            "### LLM Provider",
            "",
            "- Provider credential, OAuth login, or local endpoint access for each profile",
            "- Optional fallback provider/model credential",
            "",
            "## Where Each Value Goes",
            "",
            "- Non-secret IDs and preferences: `/setup` dashboard form",
            "- Slack and Telegram credentials: real Hermes profile runtime",
            "- Provider model routing: Hermes profile `config.yaml` or `<profile> model`",
            "- Provider credentials: Hermes profile runtime or provider OAuth flow",
            "- Secret readiness status only: `/setup/messaging#secret-status`",
            "",
            "## Focused Reply Templates",
            "",
            *focused_setup_markdown_lines(focused_setup_imports()),
            "",
        ]
    )
    return "\n".join(lines)


def slack_setup_plan_markdown(agents: list[dict], setup_values: dict[str, str]) -> str:
    lines = [
        "# Slack Setup Plan",
        "",
        "Slack is the main workspace. Keep one Slack app and one bot token per Hermes "
        "profile unless you later decide to consolidate.",
        "",
        "## Workspace Inputs",
        "",
        f"- Workspace: {setup_values.get('slack_workspace_name') or 'REPLACE_WITH_WORKSPACE'}",
        (
            "- Founder member ID: "
            f"{setup_values.get('founder_slack_member_id') or 'U_REPLACE_WITH_FOUNDER'}"
        ),
        "",
        "## Required Hermes Slack App Shape",
        "",
        "Generate the official Hermes manifest from each profile, then paste it into "
        "Slack when creating the app. The dashboard also exports no-secret starter "
        "JSON manifests for review and import.",
        "",
        "- Combined manifest review bundle: `/setup/slack-manifests.json`",
        "- Slack channel provisioning pack: `/setup/slack-provisioning.md`",
        "",
    ]
    for agent in agents:
        channel_id = setup_values.get(CHANNEL_INPUT_BY_AGENT[agent["id"]], "")
        lines.extend(
            [
                f"### {agent['name']}",
                "",
                f"- Suggested Slack app name: Hermes {agent['name']}",
                f"- Hermes profile command: `{agent['hermes_command']}`",
                f"- Home channel name: `{agent['slack_channel']}`",
                f"- Home channel ID: `{channel_id or 'C_REPLACE_WITH_CHANNEL_ID'}`",
                f"- Dashboard manifest starter: `/setup/slack-manifest/{agent['id']}.json`",
                f"- Manifest command: `{agent['hermes_command']} slack manifest --write`",
                f"- Gateway setup: `{agent['hermes_command']} gateway setup`",
                f"- Gateway start: `{agent['hermes_command']} gateway start`",
                f"- Service install: `{agent['hermes_command']} gateway install`",
                (
                    "- Invite command after app install: "
                    f"`/invite @Hermes {agent['name']}` in {agent['slack_channel']}"
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Bot Token Scopes",
            "",
            *_bullet_list(SLACK_SCOPES),
            "",
            "## Bot Events",
            "",
            *_bullet_list(SLACK_EVENTS),
            "",
            "## Channel Plan",
            "",
            "- `#founder-command`: founder approvals and Chief of Staff coordination",
            "- `#agent-standup`: 9 AM and 3 PM ET operating summaries",
            "- `#product`: product decisions, PRDs, scope tradeoffs",
            "- `#research`: market, customer, competitor, and technical research",
            "- `#engineering`: architecture, AWS, implementation planning",
            "- `#marketing`: positioning, messaging, launch work",
            "- `#qa-review`: critic reviews, risk checks, test strategy",
            "- `#decisions`: optional durable decision log",
            "- `#alerts`: optional blockers and failed-run notices",
            "",
            "## Verification",
            "",
            "- Each app has Socket Mode enabled and its app credential is loaded externally.",
            "- Each app is installed to the workspace and its bot credential is loaded externally.",
            "- Each bot is invited to its home channel.",
            "- `SLACK_ALLOWED_USERS` includes the founder Slack member ID.",
            "- `SLACK_HOME_CHANNEL` is the channel ID, not the channel name.",
            "- In channels, start conversations by mentioning the bot.",
            "- Use `/setup/messaging#messaging-verification` to record Slack gateway, DM, and "
            "channel-mention checks after external tokens are loaded.",
            "",
        ]
    )
    return "\n".join(lines)


def telegram_setup_plan_markdown(setup_values: dict[str, str]) -> str:
    founder_user = setup_values.get("founder_telegram_user_id") or "REPLACE_WITH_USER_ID"
    home_channel = setup_values.get("telegram_home_channel") or founder_user
    return "\n".join(
        [
            "# Telegram Urgent Alert Setup",
            "",
            "Telegram is urgent-only and should be wired to the Chief of Staff profile, "
            "not every agent.",
            "",
            "## Bot Plan",
            "",
            "- Bot owner: Chief of Staff profile",
            "- Bot name: Hermes Chief of Staff",
            "- BotFather setup sheet: `/setup/telegram-botfather.md`",
            "- Telegram provisioning runner: `/setup/telegram-provisioning.ps1`",
            "- Allowed user: founder only at first",
            f"- Founder Telegram user ID: `{founder_user}`",
            f"- Telegram home channel/chat: `{home_channel}`",
            "",
            "## Hermes Profile .env Values",
            "",
            "- BotFather credential: load only in the Chief of Staff Hermes profile runtime.",
            f"- Allowed users metadata: `{founder_user}`",
            f"- Home channel/chat metadata: `{home_channel}`",
            "",
            "## Commands",
            "",
            "```powershell",
            "chief-of-staff gateway setup",
            "chief-of-staff gateway start",
            "chief-of-staff gateway install",
            "```",
            "",
            "## Alert Policy",
            "",
            "- Send Telegram only for founder approval requests.",
            "- Send Telegram for blocked work that needs founder action.",
            "- Send Telegram for failed Hermes runs or broken scheduled operations.",
            "- Keep routine updates in Slack `#agent-standup`.",
            "",
            "## Verification",
            "",
            "- The founder can DM the bot.",
            "- `/sethome` is run if using a group/channel instead of the founder DM.",
            "- Chief of Staff standup prompts mention Telegram only for urgent alerts.",
            "- Use `/setup/messaging#messaging-verification` to record the Chief of Staff "
            "Telegram urgent-alert check after the bot token is loaded externally.",
            "",
        ]
    )


def llm_setup_plan_markdown(model_preferences: list[dict]) -> str:
    lines = [
        "# LLM Provider Setup Plan",
        "",
        "Each Hermes profile has its own model configuration. This plan stores "
        "provider and model preferences only; provider credentials and OAuth sessions stay "
        "inside the Hermes profile runtime.",
        "",
        "Review `/setup/llm-credentials.md` for the provider credential matrix and "
        "per-profile LLM-only `.env` starters.",
        "",
        "## Profile Preferences",
        "",
    ]
    for preference in model_preferences:
        lines.extend(
            [
                f"### {preference['agent_name']}",
                "",
                f"- Profile command: `{preference['hermes_command']}`",
                f"- Provider: `{preference['provider']}`",
                f"- Model: `{preference['model']}`",
                f"- Fallback provider: `{preference['fallback_provider'] or 'not set'}`",
                f"- Fallback model: `{preference['fallback_model'] or 'not set'}`",
                f"- Auth method: `{preference['auth_method']}`",
                f"- Status: `{preference['status']}`",
                f"- Notes: {preference['notes'] or 'none'}",
                f"- LLM-only env starter: `/setup/profile-llm-env/{preference['agent_id']}.env`",
                f"- Config starter: `/setup/profile-config/{preference['agent_id']}.yaml`",
                "",
            ]
        )
    lines.extend(
        [
            "## Secrets Needed Later",
            "",
            "- Provider credential, OAuth login, or local endpoint access per profile.",
            "- Fallback provider credential only if fallback provider differs from primary.",
            "- Any provider-specific base URL for local or self-hosted endpoints.",
            "",
            "## Verification",
            "",
            "- Run `<profile> model` for each profile after credentials exist.",
            "- Use `/setup/profiles#profile-smoke` to run one dashboard smoke test per profile.",
            "- Mark a profile `ready_for_verification` only after secrets are loaded.",
            "- A successful dashboard smoke test marks that profile `verified` and updates "
            "the matching LLM credential status without storing the credential value.",
            "",
        ]
    )
    return "\n".join(lines)


def activation_checklist_markdown(
    agents: list[dict],
    setup_values: dict[str, str],
    schedules: list[dict] | None = None,
) -> str:
    lines = [
        "# Hermes Activation Checklist",
        "",
        "Use this after installing Hermes and before switching on scheduled operations.",
        "",
        "## 1. Create Profiles And Starter Souls",
        "",
        "Run `/setup/bootstrap.ps1`, then review `/setup/profile-artifacts.md`.",
        "",
        "## 2. Verify Profile Installation",
        "",
        "Run `/setup/profile-installation.ps1`, then import the no-secret audit "
        "output at `/setup/profiles#profile-installation-tracking`.",
        "",
        "Do not run profile smoke checks until the matching profile installation "
        "check is verified.",
        "",
        "## 3. Configure Slack And Telegram Gateways",
        "",
    ]
    for agent in agents:
        lines.extend(
            [
                f"### {agent['name']}",
                "",
                f"- Review env template: `/setup/profile-env/{agent['id']}.env`",
                f"- Review Slack manifest starter: `/setup/slack-manifest/{agent['id']}.json`",
                f"- Run gateway setup: `{agent['hermes_command']} gateway setup`",
                f"- Start gateway: `{agent['hermes_command']} gateway start`",
                f"- Optional service install: `{agent['hermes_command']} gateway install`",
                "",
            ]
        )
    lines.extend(
        [
            "Complete `/setup/messaging#messaging-verification` for Slack gateway, Slack DM, "
            "Slack channel mention, and Chief of Staff urgent Telegram checks.",
            "",
            "## 4. Initialize Kanban",
            "",
            "Review `/setup/kanban-runbook.md`, then run `/setup/kanban-diagnostics.ps1`.",
            "",
            "```powershell",
            "hermes kanban init",
            "hermes kanban diagnostics --json",
            "```",
            "",
            "Then complete `/setup/verification#kanban-verification` for board initialization, "
            "diagnostics, and dashboard task creation.",
            "",
            "## 5. Verify Standups And Create Cron",
            "",
            "Review `/setup/standup-runbook.md`, then run `/setup/standup-cron.ps1` "
            "after manual standup verification passes.",
            "",
        ]
    )
    lines.extend(
        [
            "```powershell",
            *cron_commands(setup_values, schedules),
            "chief-of-staff cron list",
            "```",
            "",
            "Complete `/setup/verification#schedule-verification` "
            "for manual standup and cron checks.",
            "",
            "## 6. Load And Verify LLM Provider Last",
            "",
            "Review `/setup/llm-provisioning.md`, load provider credentials into the "
            "real Hermes profile runtime, then run `/setup/llm-finalize.ps1`.",
            "",
            "Use `/setup/profile-config/<profile>.yaml` as a starter review artifact. "
            "Use `/setup/profile-llm-env/<profile>.env` for profile-local credential "
            "placeholders. Keep provider credentials in the Hermes profile runtime.",
            "",
        ]
    )
    for agent in agents:
        lines.append(f"- `{agent['hermes_command']} model`")
    lines.extend(
        [
            "",
            "Run `/setup/profiles#profile-smoke` once for each profile after model credentials "
            "are loaded.",
            "",
            "## 7. Founder Smoke And Acceptance",
            "",
            "- Complete `/setup/verification#kanban-verification` for Kanban board readiness.",
            "- Run `/setup/profile-acceptance.md` after all profile smoke checks pass.",
            "- Import acceptance outcomes at `/setup/profiles#profile-acceptance-tracking`.",
            "- Send a Slack DM to each profile bot.",
            "- Mention each profile bot in its home channel.",
            "- Create one dashboard task and push it to Hermes Kanban.",
            "- Run one manual standup from the dashboard.",
            "- Confirm Telegram stays quiet unless the prompt contains an urgent founder alert.",
            "",
        ]
    )
    return "\n".join(lines)


def _bullet_list(values: list[str]) -> list[str]:
    return [f"- `{value}`" for value in values]


def _setup_input_lines(items: list[dict], show_status: bool) -> list[str]:
    lines = []
    for item in items:
        status = "captured" if item["value"].strip() else "missing"
        required = "required" if item["required"] else "optional"
        prefix = f"- {item['label']} (`{item['key']}`)"
        prefix = f"{prefix}: {status}, {required}" if show_status else f"{prefix}: {required}"
        lines.append(f"{prefix}. {item['help_text']}")
    return lines
