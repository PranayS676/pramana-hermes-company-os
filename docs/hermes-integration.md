# Hermes Integration

## Boundary

Hermes Company OS is not a fork of `NousResearch/hermes-agent`. It is an operating dashboard that calls real Hermes profiles.

Use the upstream Hermes project for:

- profile runtime
- Slack and Telegram gateways
- cron jobs
- profile memory
- skills
- Kanban task execution
- provider and model configuration

Use this project for:

- founder-facing dashboard
- role definitions
- schedule visibility
- planning tasks and documents
- founder decision queue
- project workflow Kanban handoff
- run history
- prompts that route work to Hermes profiles

## Invocation Model

Each profile has a configured command. Defaults assume Hermes profile aliases:

- `chief-of-staff`
- `product-manager`
- `research-agent`
- `engineering-manager`
- `marketing-agent`
- `qa-critic`

The dashboard pipes a prompt into that command and records the output. If your Hermes install uses a different command shape, set an override:

```powershell
$env:HERMES_COMMAND_CHIEF_OF_STAFF = "hermes -p chief-of-staff"
```

## Provider And Model Setup

Hermes model selection belongs in each profile's `config.yaml`; provider secrets belong in that profile's `.env` file. The setup page stores editable per-profile provider/model preferences with no API keys. Use the generated starter at:

```text
/setup/profile-config/<profile>.yaml
```

Use the LLM credential matrix and LLM-only env starter routes to prepare the final
credential handoff without mixing provider keys into Slack or Telegram setup:

```text
/setup/llm-credentials.md
/setup/profile-llm-env/<profile>.env
```

Use `/setup/llm-provisioning.md` and `/setup/llm-provisioning.ps1` for the
last-phase provider matrix, expected env keys, starter route downloads,
model-picker commands, and prior setup gates. API-key values stay in the real
Hermes profile runtime and are not stored in this dashboard.
Use `/setup/llm-preference-template.md` to paste no-secret provider/model
preference updates in bulk before the final credential-loaded smoke checks.

Then run the profile alias model picker, for example:

```powershell
engineering-manager model
```

After the real profile credential is loaded, use `/setup#profile-smoke` to run a one-message smoke check. A successful check records the run, marks that profile's model preference as verified, and marks the matching LLM credential status verified without storing the credential itself.

## When To Clone Upstream Hermes

Clone `NousResearch/hermes-agent` only if you need to:

- modify Hermes core behavior
- debug a Hermes bug from source
- contribute a PR upstream
- build a Hermes profile distribution or plugin that needs repo-local tooling

For normal operation, install Hermes and configure profiles; do not vendor it into this dashboard repo.

Use `/setup/hermes-runtime.md` when the local `hermes` command is missing. It
captures the official runtime install/connect choices, `hermes doctor`
verification, `/setup/hermes-install.ps1`, and the dashboard post-install
sequence without asking for tokens or provider keys. The install helper prints
the official installer by default and only runs it when `-RunInstall` is passed.

## Project Workflow Kanban Handoff

Project kickoff workflows create local tasks and draft documents first. The project detail page can then batch-create missing Hermes Kanban tasks for that workflow. The batch action skips tasks that already have a `kanban_task_id`, so rerunning it should not duplicate Kanban work.

The `/setup#kanban-verification` matrix tracks board initialization, diagnostics, and one dashboard task-create check. Diagnostics and task creation can mark their checks automatically; board initialization remains a manual external Hermes confirmation.

## Starter Profile Artifacts

The dashboard exposes starter profile descriptions and `SOUL.md` bodies at:

```text
/setup/profile-artifacts.md
/setup/profile-personalization-template.md
/setup/profile-personalization-template.json
/setup/profile-installation.md
/setup/profile-installation.json
/setup/profile-installation.ps1
/setup/profile-acceptance.md
/setup/profile-acceptance.json
/setup/profile-acceptance-template.md
/setup/profile-acceptance-template.json
/setup/profile-soul/<profile>.md
/setup/profile-manifest/<profile>.json
/setup/profile-apply/<profile>.ps1
```

Review that artifact before running the generated bootstrap script. These values are intentionally starter values; keep improving them as the company operating style becomes clearer.

The profile acceptance suite is the role-quality test pack for after LLM setup.
Use it to verify that each profile demonstrates the expected judgment before
using the profiles for a real founder idea. Track results in
`/setup#profile-acceptance-tracking`; acceptance verification is blocked until
the matching profile smoke check passes.
Use `/setup/profile-acceptance-template.md` to paste back status and non-secret
evidence for all acceptance cases at once.
Use `/setup/profile-personalization-template.md` to paste no-secret starter
profile updates for multiple profiles before regenerating profile artifacts.

Use the single-profile routes when you want to review or apply one Hermes role at
a time. The per-profile apply script writes identity files only; gateway and LLM
credentials remain in the separate env/config exports.

Use the profile installation audit after bootstrap or per-profile apply. It
checks profile directories, command aliases, starter identity files, and live
file presence without reading `.env`, `config.yaml`, tokens, provider keys, or
logs.

The generated `/setup/bootstrap.ps1` script also writes `.env.example` and `config.yaml.example` files into each Hermes profile home. Those examples include placeholders and any saved non-secret setup values. They are not live secret files.

Use `/setup/founder-input-request.md` to collect non-secret setup values from the
founder, then paste the completed reply template into `/setup#input-import`.
The import flow updates only known non-secret dashboard fields and rejects
secret-looking Slack, Telegram, LLM, OAuth, and environment assignment values.
Use `/setup/founder-inputs.ps1` for an interactive local PowerShell collector
that prompts for those same safe values and optionally posts them back to the
dashboard.
Use `/setup/first-run.md` or `/setup/first-run.ps1` as the guided local starter
that chains safe input collection, guarded Hermes install, runtime preflight, and
activation runner while keeping install and activation phases opt-in.
Use `/setup/progress-board.md` or `/setup/progress-board.json` to review the same
remaining work grouped by do now, after Hermes install, after credentials, and
final verification.
Use `/setup/credential-status-template.md` after loading external credentials
into real Hermes profile files, then paste the completed status-only reply into
`/setup#credential-status-import`.

## No-Secret Setup Artifacts

The dashboard also exports operational setup plans that can be reviewed before secrets exist:

```text
/setup/company-manifest.md
/setup/company-manifest.json
/setup/company-launch-drill.md
/setup/company-launch-drill.json
/setup/team-topology.md
/setup/team-topology.json
/setup/delegation-playbook.md
/setup/delegation-playbook.json
/setup/kickoff-readiness.md
/setup/kickoff-readiness.json
/setup/inputs-needed.md
/setup/founder-handoff.md
/setup/founder-handoff.json
/setup/founder-input-request.md
/setup/founder-input-request.json
/setup/founder-inputs.ps1
/setup/first-run.md
/setup/first-run.json
/setup/first-run.ps1
/setup/progress-board.md
/setup/progress-board.json
/setup/input-ledger.md
/setup/input-ledger.json
/setup/credential-loading.md
/setup/credential-loading.json
/setup/credential-status-template.md
/setup/credential-status-template.json
/setup/founder-next-actions.md
/setup/founder-next-actions.json
/setup/founder-decisions.md
/setup/founder-decisions.json
/setup/slack-plan.md
/setup/slack-manifest/<profile>.json
/setup/slack-manifests.json
/setup/slack-provisioning.md
/setup/slack-provisioning.json
/setup/slack-provisioning.ps1
/setup/slack-channel-template.md
/setup/slack-channel-template.json
/setup/slack-bot-user-map.json
/setup/slack-bot-user-map-template.md
/setup/slack-bot-user-map-template.json
/setup/slack-workspace.md
/setup/slack-invite-matrix.json
/setup/slack-invite-matrix.csv
/setup/telegram-plan.md
/setup/telegram-botfather.md
/setup/telegram-recipient-template.md
/setup/telegram-recipient-template.json
/setup/telegram-provisioning.md
/setup/telegram-provisioning.json
/setup/telegram-provisioning.ps1
/setup/telegram-policy.md
/setup/telegram-policy.json
/setup/messaging-drill.md
/setup/messaging-drill.json
/setup/messaging-verification-template.md
/setup/messaging-verification-template.json
/setup/gateway-operations.md
/setup/gateway-operations.json
/setup/gateway-operations.ps1
/setup/llm-plan.md
/setup/llm-credentials.md
/setup/llm-provisioning.md
/setup/llm-provisioning.json
/setup/llm-provisioning.ps1
/setup/llm-provider-presets.md
/setup/llm-provider-presets.json
/setup/llm-preference-template.md
/setup/llm-preference-template.json
/setup/profile-llm-env/<profile>.env
/setup/llm-finalize.md
/setup/llm-finalize.ps1
/setup/llm-smoke.md
/setup/llm-smoke.json
/setup/secret-audit.md
/setup/secret-audit.ps1
/setup/hermes-runtime.md
/setup/hermes-runtime.json
/setup/hermes-install.ps1
/setup/runtime-preflight.md
/setup/runtime-preflight.json
/setup/runtime-preflight.ps1
/setup/schedule-provisioning.md
/setup/schedule-provisioning.json
/setup/schedule-provisioning.ps1
/setup/schedule-config-template.md
/setup/schedule-config-template.json
/setup/schedule-verification-template.md
/setup/schedule-verification-template.json
/setup/standup-preview.md
/setup/standup-preview.json
/setup/standup-runbook.md
/setup/standup-cron.ps1
/setup/project-workflow.md
/setup/project-workflow.json
/setup/kanban-provisioning.md
/setup/kanban-provisioning.json
/setup/kanban-provisioning.ps1
/setup/kanban-verification-template.md
/setup/kanban-verification-template.json
/setup/kanban-runbook.md
/setup/kanban-diagnostics.ps1
/setup/activation-sequence.md
/setup/activation-runner.md
/setup/activation-runner.ps1
/setup/live-verification.md
/setup/verification-evidence.md
/setup/verification-evidence.json
/setup/readiness-report.md
/setup/activation-checklist.md
/setup/profile-personalization-template.md
/setup/profile-personalization-template.json
/setup/profile-artifacts.md
/setup/profile-installation.md
/setup/profile-installation.json
/setup/profile-installation.ps1
/setup/profile-acceptance.md
/setup/profile-acceptance.json
/setup/profile-acceptance-template.md
/setup/profile-acceptance-template.json
/setup/profile-soul/<profile>.md
/setup/profile-manifest/<profile>.json
/setup/profile-apply/<profile>.ps1
```

These files intentionally avoid storing Slack tokens, Telegram bot tokens, and LLM provider API keys. Use them to create apps, collect IDs, and verify the activation order.

The company manifest is the top-level machine-readable handoff. It combines
profiles, schedules, integration status, activation gates, workflow templates,
and artifact URLs while omitting secret values and raw verification evidence.

The company launch drill is the pre-idea rehearsal view. It ties safe
founder/workspace inputs, local Hermes runtime readiness, tracked setup gates,
founder-reviewed role acceptance, and recorded founder decisions into one
go/no-go packet before the first real company project starts.

The kickoff readiness export is the first-project gate. It allows local draft
workflow creation while keeping live Hermes execution blocked until runtime,
profile installation, Slack, Telegram, Kanban, scheduling, final LLM smoke
checks, and profile acceptance are verified.

The standup preview export is the pre-cron communication drill. It shows the
generated Chief of Staff prompt for active schedules and the expected
Slack-versus-Telegram behavior for routine progress, approvals, blockers, and
failed scheduled operations.

The founder decision queue is the durable steering log. Use it for approvals,
rejections, deferrals, and blocked decisions before agents proceed. Routine
items route to Slack; urgent open items are explicitly marked for Telegram
founder escalation after the Chief of Staff alert bot is connected.

The schedule provisioning pack is the cron installation contract. It lists
active and paused schedules, generated Chief of Staff cron expressions, delivery
policy, verification status, and a dry-run runner that can safely install or
list cron jobs only when `-Execute` is passed. After cron install/list succeeds,
`-PostDashboardStatus` records no-secret evidence against the active schedule
verification checks.

The schedule configuration template is the pre-cron metadata import. Paste it
into `/setup#schedule-config-import` to adjust standup names, times, timezone,
Slack target, Telegram policy, and active state before verification or cron
installation.

The project workflow handoff export is the pre-idea Kanban contract. It shows
which workflow templates create local tasks and documents, how owner agents map
to Kanban assignees, and how local task IDs become Kanban idempotency keys.

The Kanban provisioning pack is the pre-project board contract. It lists board
lanes, workflow-template lane mapping, local task linkage counts, and dry-run
Hermes Kanban init/diagnostics commands without requiring messaging or LLM
credentials.

The LLM smoke drill export is the final provider-verification contract. It shows
the expected environment key names, profile smoke prompts, required three-line
response schema, and completion criteria while leaving provider credential
values outside the dashboard.

The messaging drill export is the Slack/Telegram verification contract. It
combines per-profile Slack DM checks, Slack channel mentions, invite commands,
and Chief-of-Staff-only Telegram urgency cases without storing credentials or
verification evidence.

The founder next-actions export is the compact current-state request packet for
the founder. It combines the next best action, missing safe inputs, external
credential status categories, and remaining verification counts without asking
for token or API-key values.

The founder input request routes are generated from the current setup input
schema. They list safe dashboard values to provide and summarize external
credentials to load later without asking for secret values.

The founder input ledger is the live question list. It separates safe dashboard
values, status-only credential updates, deferred preferences, and the setup
phase each item unlocks without asking for token or API-key values.

The founder return packet combines safe dashboard inputs, external credential
loading requirements, status-only credential reply lines, LLM-last reminders,
and the routes to run when the founder returns with setup information.

The per-profile Slack manifest route is the import-ready starter for a single
Slack app. The combined manifest bundle is for review so you can compare all
profile bots before creating them in Slack.

The Slack provisioning pack turns the workspace matrix into a no-secret channel
setup bridge. Its runner dry-runs by default and calls Slack Web API methods
only when you explicitly pass `-Execute` with a local shell token already
loaded. After successful channel creation, `-PostDashboardInputs` posts returned
Slack channel IDs into the dashboard's safe setup input ledger.

The Slack channel ID template captures non-secret channel IDs when the workspace
is created manually. Paste it into `/setup#slack-channel-import`; the import
validates `C...`, `G...`, or `D...` IDs before updating the setup ledger.

The Slack bot user ID template captures the non-secret bot user IDs for separate
profile bots. Paste it into `/setup#slack-bot-user-import` after Slack app
installation; `/setup/slack-bot-user-map.json` then becomes the invite map for
the provisioning runner without storing any bot token values.

The Slack workspace matrix maps every operating channel to the profile bots that
should be invited there. The JSON and CSV exports are safe handoffs for channel
creation and invite tracking because they contain no token values.

The Telegram BotFather setup sheet is the Chief-of-Staff-only setup artifact. It
includes suggested bot identity, command list, `.env` placeholders, and urgent
versus routine smoke prompts without storing the BotFather token.

The Telegram recipient template captures the non-secret founder user ID and
optional urgent home chat/channel ID with numeric validation. Paste it into
`/setup#telegram-recipient-import` before running the urgent send test.

The Telegram provisioning pack is the local verification bridge after BotFather
setup. It dry-runs by default and can call `getMe`, `setMyCommands`, and one
optional urgent `sendMessage` test only when `-Execute` is passed with the token
already loaded in the local shell. After the urgent send test succeeds,
`-PostDashboardStatus` can record non-secret evidence against the Chief of Staff
Telegram alert check.

The Telegram urgent policy export is the machine-readable escalation rule set.
It defines what should trigger Telegram, what must stay in Slack, and how
standup schedules should treat founder urgency.

The LLM credential matrix maps every profile's provider/model preference to the
profile-local environment keys needed later. The per-profile LLM env starter
contains only provider placeholders, not Slack or Telegram values.

The LLM finalization runner is the final provider step. It audits profile-local
provider key names, optionally runs each Hermes profile model picker, and can
trigger dashboard profile smoke checks after credentials are loaded externally.

The secret audit export checks local Hermes profile `.env` files for required
key names and non-empty values without printing or posting credential values.
Run it for Slack and Telegram first; rerun with `-AuditLlm` only after provider
credentials are loaded last.

The Hermes runtime connect export is the no-secret bridge from official Hermes
install docs to this dashboard's activation sequence. Use it when the CLI is not
installed, then run the runtime preflight export to check local Python, Poetry
command guidance, SQLite paths, Hermes command availability, expected profile
directories, and current integration statuses before credentials are loaded.
The PowerShell runner performs the same local command/path inspection before
activation.

The schedule provisioning pack, standup runbook, and cron script are generated
from the current dashboard schedules. Use them after manual standup verification
and before marking `standup-cron` configured. Add `-PostDashboardStatus` after a
successful cron install/list run to update `/setup#schedule-verification`.
The schedule verification template supports bulk status/evidence import after
manual standup and cron/list checks, while preserving the same LLM and messaging
gates used by manual edits.

The Kanban provisioning pack, runbook, and diagnostics script cover board lanes,
`hermes kanban init`, `hermes kanban diagnostics --json`, dashboard task push
verification, and the criteria for marking `hermes-kanban` configured. The
Kanban provisioning runner can post no-secret board initialization evidence with
`-PostDashboardStatus` after `hermes kanban init` succeeds.
The Kanban verification template supports bulk status/evidence import for board,
diagnostics, and task-create checks after the external Kanban work is complete.

The activation sequence is the single current-state handoff for the founder. It
orders the next action, missing non-secret inputs, external credential statuses,
verification work, and runbook links while keeping LLM credentials last.

The activation runner is a local PowerShell bridge for after Hermes is installed.
It downloads per-profile apply scripts from the dashboard, runs and imports the
no-secret profile installation audit, runs no-secret Kanban initialization, and
can call the Slack, Telegram, schedule, and LLM provisioning
bridges through explicit flags. Child provisioning scripts remain dry-run unless
the runner is also called with `-ExecuteProvisioning`; `-SendTelegramTest` keeps
the urgent Telegram send test deliberate. `-RunLlmFinalization` keeps the final
credential audit separate from earlier no-secret LLM provisioning. Cron install
and profile smoke checks remain separate explicit flags.

The live verification runbook is the final credential-loaded checklist. Use it
after external tokens and provider credentials are in the real Hermes profiles;
it summarizes profile installation, messaging, Kanban, schedule, profile smoke,
profile acceptance, and evidence rules without storing secret values.

The verification evidence pack summarizes which live checks have non-secret
evidence present, which checks remain open, and which verified checks still need
short evidence notes. It omits evidence text, profile prompts, profile outputs,
and logs.

The setup page includes an `External Secret Status` section. It stores only status and notes such as `loaded` or `verified`; token and API-key values remain in Hermes profile `.env` files or provider auth flows.

Stored dashboard forms reject common secret-looking values such as Slack `xoxb-`/`xapp-` tokens, Telegram bot tokens, `sk-...` provider keys, GitHub/AWS/Google-style keys, and secret environment assignments. This guard is intentionally a backstop; secrets should still be handled only in the real Hermes profile runtime or provider auth flow.

The `/setup#messaging-verification` matrix tracks Slack gateway, Slack DM, Slack channel mention, and Chief of Staff Telegram urgent-alert checks. It stores status and non-secret evidence only, then can mark Slack or Telegram integrations configured once every check for that platform is verified.
The messaging verification template supports bulk status/evidence import after
live checks, while preserving the same credential gates used by manual edits.

The gateway operations runbook and PowerShell runner check Hermes profile command
aliases and can run `gateway setup`, `gateway start`, or `gateway install` across
all profiles after Slack and Telegram credentials are loaded externally.
`-PostDashboardStatus` records Slack gateway checks as `loaded` after successful
gateway commands; live DM, channel, and urgent-alert checks remain separate.

The `/setup#schedule-verification` matrix tracks manual standup runs and cron-install/list checks for active schedules. It stores non-secret evidence only and can mark `standup-cron` configured once every active schedule check is verified.
Use `/setup/schedule-verification-template.md` to import those non-secret check
results in bulk.
