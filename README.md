# Hermes Company OS

A founder dashboard for running an AI company through real Hermes profiles.

V1 focuses on plans and documents. Slack is the primary workspace, Telegram is the urgent founder-alert channel, and Hermes Kanban is the intended source of truth for multi-agent work.

## Stack

- Python 3.11
- Poetry
- FastAPI
- SQLite
- Jinja templates
- Real Hermes CLI/profile commands

## Local Setup

```powershell
cd "C:\Users\masadis\OneDrive - Reed Elsevier Group ICO Reed Elsevier Inc\Documents\harmes_practise\hermes-company-os"
py -3.11 -m poetry install
py -3.11 -m poetry run uvicorn hermes_company_os.main:app --host 127.0.0.1 --port 8002 --reload
```

Then open `http://127.0.0.1:8002`.

## Hermes Profiles

Create these profiles in Hermes before using live runs:

```powershell
hermes profile create chief-of-staff --description "Coordinates company agents, summarizes decisions, escalates founder approvals."
hermes profile create product-manager --description "Turns founder intent into focused PRDs, roadmap options, and scope decisions."
hermes profile create research-agent --description "Finds market, competitor, customer, and technical evidence."
hermes profile create engineering-manager --description "Creates ambitious architecture plans with strong testing and AWS thinking."
hermes profile create backend-engineer --description "Designs APIs, services, storage, and backend execution plans."
hermes profile create frontend-engineer --description "Designs efficient product UI flows and frontend implementation plans."
hermes profile create cloud-infra-agent --description "Plans AWS, deployment, observability, reliability, and cost controls."
hermes profile create test-automation-agent --description "Builds unit, integration, E2E, CI, and acceptance test strategy."
hermes profile create marketing-agent --description "Creates positioning, launch plans, messaging, and campaign ideas."
hermes profile create qa-critic --description "Reviews plans for risks, gaps, contradictions, and missing tests."
```

Each profile should have its own Slack bot token if you keep the separate-bot design. Configure those inside each Hermes profile, not in this app.

The setup page exports no-secret Slack app manifest starters for the separate-bot
design at `/setup/slack-manifest/<profile>.json`, plus a combined review bundle at
`/setup/slack-manifests.json`.

Use `/setup/slack-workspace.md` plus `/setup/slack-invite-matrix.json` or
`/setup/slack-invite-matrix.csv` to map channels to profile bots and invite
commands after Slack channels exist.

Use `/setup/slack-provisioning.md` and `/setup/slack-provisioning.ps1` as the
no-secret Slack channel setup bridge. The runner dry-runs by default, can create
channels or invite bots only when you explicitly pass `-Execute`, and reads any
Slack execution token only from your local shell environment.
Use `/setup/slack-channel-template.md` to paste manually created Slack channel
IDs into `/setup#slack-channel-import` with channel-ID validation.
Use `/setup/slack-bot-user-map-template.md` to paste safe Slack bot user IDs for
the separate profile bots into `/setup#slack-bot-user-import`; the generated
`/setup/slack-bot-user-map.json` then reflects captured IDs for invite automation.

Use `hermes model` or the profile alias command, for example `engineering-manager model`, to choose the provider and model for each profile. The setup page has editable per-profile model preferences and exports `config.yaml` starters at `/setup/profile-config/<profile>.yaml`. Provider API keys stay in each Hermes profile `.env` file.

Use `/setup/llm-credentials.md` for the no-secret provider credential matrix and
`/setup/profile-llm-env/<profile>.env` for LLM-only profile env placeholders.
Those exports are intentionally separate from Slack and Telegram setup so final
provider credentials can be added last.

Use `/setup/llm-provisioning.md` and `/setup/llm-provisioning.ps1` as the
last-phase LLM setup bridge. The pack consolidates provider/model choices,
expected env key names, starter file downloads, model-picker commands, and prior
Slack/Telegram/schedule/Kanban gates while keeping API-key values outside this
dashboard.

Use `/setup/llm-provider-presets.md` or `/setup#llm-presets` to apply a
no-secret provider/model strategy across all profiles. Presets update only
provider names, model names, auth method labels, status metadata, and notes;
provider keys are still loaded later in the real Hermes profile runtime.
Use `/setup/llm-preference-template.md` to paste no-secret provider/model
preference updates in bulk without marking any profile verified.

Use `/setup/llm-finalize.md` and `/setup/llm-finalize.ps1` only after provider
credentials are loaded externally. The runner audits key presence, can call each
profile model picker, and can trigger dashboard profile smoke checks without
printing API-key values.

After credentials are loaded in the real Hermes profile, run the `/setup` Profile Smoke Checks. A successful check records a dashboard run, marks that profile's model preference verified, and marks the matching LLM credential status verified without storing the credential value.

Starter profile descriptions, `SOUL.md` text, capabilities, Hermes command alias, Slack home channel, and Telegram escalation policy can be edited from each agent page in the dashboard. Those edits update the local planning database and regenerated setup artifacts; they do not overwrite live Hermes files until you rerun or manually apply the generated bootstrap/profile artifacts.
Use `/setup/profile-personalization-template.md` when you want to paste no-secret
starter profile updates for multiple Hermes profiles at once.

Each profile also has single-profile exports for iterative review:
`/setup/profile-soul/<profile>.md`, `/setup/profile-manifest/<profile>.json`,
and `/setup/profile-apply/<profile>.ps1`.

Use `/setup/profile-live-assets.md` and `/setup/profile-live-assets.ps1` after
starter profile installation to write no-secret live starter files into each
Hermes profile: `config.yaml`, `COMPANY_CONTEXT.md`, `PROMPTS.md`, and
`OPERATING_RULES.md`. This step does not write profile `.env` values, LLM API
keys, Slack tokens, Telegram tokens, OAuth payloads, or auth stores.

Use `/setup/profile-installation.md` and `/setup/profile-installation.ps1` after
bootstrap/profile apply to check profile directories, starter identity files,
starter env/config files, and command aliases without reading live secret files.
Paste the script output into `/setup#profile-installation-tracking` to bulk-mark
profile installation checks verified or blocked from no-secret audit lines.

Use `/setup/team-topology.md` and `/setup/team-topology.json` for the no-secret
manager/sub-agent map. The starter topology makes Engineering Manager responsible
for Backend Engineer, Frontend Engineer, Cloud Infrastructure Agent, and Test
Automation Agent.

Use `/setup/delegation-playbook.md` and `/setup/delegation-playbook.json` for the
operating loop that turns founder requests into Chief of Staff routing, manager
delegation, specialist work, standup summaries, Kanban handoff, and urgent-only
Telegram escalation.

Use `/setup/profile-acceptance.md` and `/setup/profile-acceptance.json` after
LLM setup to test whether each role behaves according to its starter
personalization before the first real company idea. Track each case in
`/setup#profile-acceptance-tracking`; a case cannot be marked verified until the
matching profile smoke check has passed.
Use `/setup/profile-acceptance-template.md` to paste non-secret acceptance
results back in bulk after those profile prompts have been reviewed.

Use the dashboard Founder Decision Queue to capture approvals, rejections,
deferrals, and blocked items before agents proceed. The queue exports to
`/setup/founder-decisions.md` and `/setup/founder-decisions.json`; routine
decisions stay in Slack, while urgent unresolved decisions are marked for the
future Telegram founder-alert path after credentials exist.

## Why This Does Not Vendor Hermes

This project does not clone or modify `NousResearch/hermes-agent`. Hermes is the runtime dependency: profiles, Slack/Telegram gateways, cron, memory, skills, and Kanban live in the installed Hermes environment. This dashboard sits beside it and provides the founder operating layer.

Clone the upstream Hermes repo only when you want to change Hermes itself, contribute to Hermes, inspect its source, or package a profile distribution/plugin against the Hermes repository layout.

Use `/setup/hermes-runtime.md` for the current no-secret install/connect packet.
It links the upstream repo, official install docs, Windows/WSL install commands,
`/setup/hermes-install.ps1`, `hermes doctor`, and the dashboard post-install
sequence. The install helper is dry-run by default and only runs the official
installer when `-RunInstall` is passed.

## Slack And Telegram

Slack is the main workspace:

- `#founder-command`
- `#agent-standup`
- `#product`
- `#research`
- `#engineering`
- `#marketing`
- `#qa-review`
- `#decisions`
- `#alerts`

Telegram should be wired only to the Chief of Staff profile for urgent founder alerts.

Use `/setup/slack-provisioning.md` and `/setup/slack-provisioning.ps1` to dry-run
or locally create Slack channels. Add `-PostDashboardInputs` after successful
channel creation to save returned channel IDs into `/setup#inputs` without
posting tokens.
Use `/setup/slack-channel-template.md` when channels were created manually and
you need to paste their non-secret Slack channel IDs back into the dashboard.
Use `/setup/slack-bot-user-map-template.md` after installing each separate Slack
app to capture the bot user IDs needed for automated channel invites.

Use `/setup/telegram-botfather.md` for the no-secret BotFather setup sheet,
suggested bot commands, Chief of Staff `.env` placeholders, and urgent-vs-routine
manual smoke prompts.
Use `/setup/telegram-recipient-template.md` to paste the founder Telegram user
ID and optional urgent home chat/channel ID into `/setup#telegram-recipient-import`
with numeric validation before running the urgent send test.

Use `/setup/telegram-provisioning.md` and `/setup/telegram-provisioning.ps1`
after BotFather setup to dry-run or locally execute `getMe`, `setMyCommands`,
and one optional urgent `sendMessage` test. The runner reads the token only from
your local shell when `-Execute` is passed. Add `-PostDashboardStatus` after a
successful urgent send test to record non-secret Telegram verification evidence.

Use `/setup/telegram-policy.md` and `/setup/telegram-policy.json` for the
urgent-alert rules that decide what should trigger Telegram versus stay in Slack.

After external messaging secrets are loaded, use `/setup#messaging-verification` to track Slack gateway, Slack DM, Slack channel mention, and Chief of Staff Telegram urgent-alert checks. Evidence notes are non-secret only.
Use `/setup/messaging-verification-template.md` to paste back status-only live
check results in bulk after running the drills.

Use `/setup/gateway-operations.md` and `/setup/gateway-operations.ps1` after
loading Slack and Telegram credentials externally to check profile command
aliases, run gateway setup, start gateways, or install gateway services across
all profiles. Add `-PostDashboardStatus` after successful gateway setup/install
to mark Slack gateway checks `loaded`; DM, channel mention, and Telegram urgent
alert checks still require live verification.

## Standups

The dashboard defines two daily standups in `America/New_York`:

- 9:00 AM ET
- 3:00 PM ET

The setup page lets you edit standup names, times, timezone, Slack channel, Telegram policy, and active status before cron jobs are created. The live run button calls the Chief of Staff Hermes profile with a standup prompt. To make those automatic, create matching Hermes cron jobs from the Chief of Staff profile after the Slack and Telegram gateways are configured.

Use `/setup/standup-runbook.md` for the scheduling runbook and
`/setup/standup-cron.ps1` for the generated Chief of Staff cron install script.

Use `/setup/schedule-config-template.md` to paste no-secret schedule
configuration changes in bulk before installing cron jobs. This changes standup
metadata only; verification still happens through the schedule verification
checks.

Use `/setup/schedule-provisioning.md` and `/setup/schedule-provisioning.ps1` to
review active schedules, generated Chief of Staff cron expressions, and the
safe dry-run cron install/list runner before standups are treated as live.
After a successful cron install/list run, add `-PostDashboardStatus` to post
no-secret verification evidence into `/setup#schedule-verification`.

Use `/setup#schedule-verification` to track manual standup runs and cron-install/list checks before treating standups as live. Inactive schedules do not block schedule readiness.
Use `/setup/schedule-verification-template.md` to paste no-secret manual-run and
cron/list verification evidence in bulk after those checks complete.

## Configuration

Copy `.env.example` to your shell environment or process manager. These variables configure this dashboard only. Slack and Telegram secrets belong in Hermes profile `.env` files.

## Setup Readiness

Open `/` to see the founder operating board plus the current activation gate and next setup action. Open `/setup` for profile commands, required Slack/Telegram inputs, model config starters, Hermes readiness checks, runtime preflight checks, Kanban setup, and generated bootstrap commands.

The generated `/setup/bootstrap.ps1` script creates missing Hermes profiles, writes starter `SOUL.md` files, and writes no-secret `.env.example` plus `config.yaml.example` files into each profile home. Review and copy those example files into live Hermes files only after you have the real tokens and provider keys.

The setup page tracks external secret readiness as status metadata only. Use `External Secret Status` to mark whether Slack tokens, Telegram tokens, or LLM credentials have been loaded into the correct Hermes profile; never paste the secret values into the dashboard.

Use `/setup/credential-loading.md` and `/setup/credential-loading.json` for the
phase order that verifies starter profile installation first, loads Slack and
Telegram credentials, verifies messaging, checks Kanban and scheduling, leaves
LLM provider credentials for final profile smoke verification, and runs profile
acceptance after smoke checks pass.

The server rejects common secret-looking values such as Slack `xoxb-`/`xapp-` tokens, Telegram bot tokens, `sk-...` provider keys, and secret environment assignments in stored forms. Treat this as a backstop, not as a secret manager.

The setup page also exports no-secret planning artifacts:

- `/setup/company-manifest.md`
- `/setup/company-manifest.json`
- `/setup/company-launch-drill.md`
- `/setup/company-launch-drill.json`
- `/setup/kickoff-readiness.md`
- `/setup/kickoff-readiness.json`
- `/setup/inputs-needed.md`
- `/setup/founder-handoff.md`
- `/setup/founder-handoff.json`
- `/setup/founder-input-request.md`
- `/setup/founder-input-request.json`
- `/setup/founder-inputs.ps1`
- `/setup/first-run.md`
- `/setup/first-run.json`
- `/setup/first-run.ps1`
- `/setup/progress-board.md`
- `/setup/progress-board.json`
- `/setup/input-ledger.md`
- `/setup/input-ledger.json`
- `/setup/credential-loading.md`
- `/setup/credential-loading.json`
- `/setup/credential-status-template.md`
- `/setup/credential-status-template.json`
- `/setup/founder-next-actions.md`
- `/setup/founder-next-actions.json`
- `/setup/founder-decisions.md`
- `/setup/founder-decisions.json`
- `/setup/slack-plan.md`
- `/setup/slack-manifests.json`
- `/setup/slack-provisioning.md`
- `/setup/slack-provisioning.json`
- `/setup/slack-provisioning.ps1`
- `/setup/slack-channel-template.md`
- `/setup/slack-channel-template.json`
- `/setup/slack-bot-user-map.json`
- `/setup/slack-bot-user-map-template.md`
- `/setup/slack-bot-user-map-template.json`
- `/setup/slack-workspace.md`
- `/setup/slack-invite-matrix.json`
- `/setup/slack-invite-matrix.csv`
- `/setup/telegram-plan.md`
- `/setup/telegram-botfather.md`
- `/setup/telegram-recipient-template.md`
- `/setup/telegram-recipient-template.json`
- `/setup/telegram-provisioning.md`
- `/setup/telegram-provisioning.json`
- `/setup/telegram-provisioning.ps1`
- `/setup/telegram-policy.md`
- `/setup/telegram-policy.json`
- `/setup/messaging-drill.md`
- `/setup/messaging-drill.json`
- `/setup/messaging-verification-template.md`
- `/setup/messaging-verification-template.json`
- `/setup/gateway-operations.md`
- `/setup/gateway-operations.json`
- `/setup/gateway-operations.ps1`
- `/setup/llm-plan.md`
- `/setup/llm-credentials.md`
- `/setup/llm-provisioning.md`
- `/setup/llm-provisioning.json`
- `/setup/llm-provisioning.ps1`
- `/setup/llm-provider-presets.md`
- `/setup/llm-provider-presets.json`
- `/setup/llm-preference-template.md`
- `/setup/llm-preference-template.json`
- `/setup/profile-llm-env/<profile>.env`
- `/setup/llm-finalize.md`
- `/setup/llm-finalize.ps1`
- `/setup/llm-smoke.md`
- `/setup/llm-smoke.json`
- `/setup/secret-audit.md`
- `/setup/secret-audit.ps1`
- `/setup/hermes-runtime.md`
- `/setup/hermes-runtime.json`
- `/setup/hermes-install.ps1`
- `/setup/runtime-preflight.md`
- `/setup/runtime-preflight.json`
- `/setup/runtime-preflight.ps1`
- `/setup/schedule-provisioning.md`
- `/setup/schedule-provisioning.json`
- `/setup/schedule-provisioning.ps1`
- `/setup/schedule-config-template.md`
- `/setup/schedule-config-template.json`
- `/setup/schedule-verification-template.md`
- `/setup/schedule-verification-template.json`
- `/setup/standup-preview.md`
- `/setup/standup-preview.json`
- `/setup/standup-runbook.md`
- `/setup/standup-cron.ps1`
- `/setup/idea-intake.md`
- `/setup/idea-intake.json`
- `/setup/project-workflow.md`
- `/setup/project-workflow.json`
- `/setup/kanban-provisioning.md`
- `/setup/kanban-provisioning.json`
- `/setup/kanban-provisioning.ps1`
- `/setup/kanban-verification-template.md`
- `/setup/kanban-verification-template.json`
- `/setup/kanban-runbook.md`
- `/setup/kanban-diagnostics.ps1`
- `/setup/activation-sequence.md`
- `/setup/activation-runner.md`
- `/setup/activation-runner.ps1`
- `/setup/live-verification.md`
- `/setup/verification-evidence.md`
- `/setup/verification-evidence.json`
- `/setup/activation-checklist.md`
- `/setup/profile-personalization-template.md`
- `/setup/profile-personalization-template.json`
- `/setup/profile-artifacts.md`
- `/setup/profile-installation.md`
- `/setup/profile-installation.json`
- `/setup/profile-installation.ps1`
- `/setup/team-topology.md`
- `/setup/team-topology.json`
- `/setup/delegation-playbook.md`
- `/setup/delegation-playbook.json`
- `/setup/profile-acceptance.md`
- `/setup/profile-acceptance.json`
- `/setup/profile-acceptance-template.md`
- `/setup/profile-acceptance-template.json`
- `/setup/profile-soul/<profile>.md`
- `/setup/profile-manifest/<profile>.json`
- `/setup/profile-apply/<profile>.ps1`
- `/setup/readiness-report.md`

The company manifest routes are the single structured handoff for future Hermes
or Codex automation. They summarize profiles, schedules, integration statuses,
verification gates, workflow templates, activation next action, and all setup
artifact URLs without copying tokens, API keys, or raw verification evidence.

The company launch drill routes are the pre-idea rehearsal packet. They tie
safe founder/workspace inputs, local Hermes runtime readiness, profile topology,
Slack and Telegram gateway checks, Kanban, standups, final LLM smoke checks,
workflow templates, role acceptance, and recorded founder decisions into one
go/no-go view before the first real startup idea enters the workflow.

The kickoff readiness routes are the first-project gate. They make local draft
workflow creation explicit while marking live Hermes execution, scheduled
standups, and Kanban handoff as blocked until runtime, profile installation,
messaging, scheduling, Kanban, final LLM verification, and profile acceptance
gates are ready.

The standup preview routes show the exact Chief of Staff prompt for each active
schedule plus drill cases for routine Slack-only updates, founder approvals,
blockers, and failed scheduled operations before cron is installed.

The project workflow handoff routes show how the first founder idea becomes
local tasks, draft documents, and eventually Hermes Kanban tasks. They document
the owner-agent mapping, idempotency key, and remote task ID storage before any
live push is attempted.

The idea intake routes provide the safe founder reply template for the first
company idea. They show what context to provide, how it maps to each workflow
template, and which live gates must be ready before pushing beyond local draft
workflow creation.

The LLM smoke drill routes are the final provider verification pack. They list
the expected key names, profile smoke prompts, response schema, and completion
criteria for every Hermes profile without exposing provider API-key values.

The messaging drill routes are the Slack/Telegram smoke test pack. They cover
separate Slack bot DMs, channel mentions, channel invite commands, Chief of
Staff-only Telegram urgency, and the expected Slack-only behavior for routine
updates.

The founder next-actions routes are the compact action packet. They combine the
current activation gate, missing non-secret inputs, external credential statuses,
verification work remaining, open founder decisions, and direct dashboard links
without requesting any secret values.

Before the first company idea, collect the inputs in [docs/preflight-inputs.md](docs/preflight-inputs.md) or use `/setup/founder-input-request.md` as the live dashboard-generated request packet.
When you return with that reply template, paste it into `/setup#input-import`.
The importer updates only known non-secret dashboard fields and rejects
secret-looking Slack tokens, Telegram bot tokens, provider API keys, OAuth
payloads, and secret environment assignments.
Use `/setup/founder-inputs.ps1` when you want a local guided PowerShell prompt
for those same safe dashboard values. It prints the reply text and can post it
back to `/setup/founder-input-reply` only when `-PostDashboardInputs` is passed.

Use `/setup/first-run.md` or `/setup/first-run.ps1` as the guided local starter.
It chains safe input collection, the guarded Hermes installer, runtime preflight,
and the activation runner while keeping install and activation phases opt-in.
Use `/setup/progress-board.md` or `/setup/progress-board.json` to see the same
remaining setup work grouped by stage: do now, after Hermes install, after
credentials, and final verification.

Use `/setup/founder-handoff.md` and `/setup/founder-handoff.json` as the combined
return packet. It includes the safe input reply template, external credential
loading checklist, status-only credential reply template, and next routes to run
after you return.

Use `/setup/input-ledger.md` and `/setup/input-ledger.json` as the live question
ledger. It lists safe dashboard values needed now, status-only credential
updates needed later, deferred inputs, and which setup phase each item unlocks
without asking for token or API-key values.

After you load external credentials into real Hermes profile files, use
`/setup/credential-status-template.md` and paste the completed status-only reply
into `/setup#credential-status-import`. This updates status metadata only and
still rejects token or API-key values.

After external credentials are loaded into Hermes profiles, use
`/setup/live-verification.md` as the final verification runbook.

Use `/setup/verification-evidence.md` and `/setup/verification-evidence.json`
after live checks to see which phases have enough non-secret proof, which checks
are still open, and which verified checks still need evidence notes.

Use `/setup/secret-audit.md` and `/setup/secret-audit.ps1` after loading
external credentials into real Hermes profile `.env` files. The audit checks key
presence only and can mark dashboard secret statuses loaded without sending
values back to the dashboard. LLM credential checks require `-AuditLlm`.

Use `/setup/hermes-runtime.md` first when `hermes` is not on PATH, then download
`/setup/hermes-install.ps1` for the dry-run guarded install helper. After
installation, use `/setup/runtime-preflight.ps1` before activation to inspect
local Python, Hermes CLI, profile directories, and profile aliases without
reading secrets.

After Hermes is installed, use `/setup/activation-runner.md` to review the local
phase runner and `/setup/activation-runner.ps1` to apply starter profiles and
import the no-secret profile installation audit, then run no-secret Kanban setup.
Slack, Telegram, schedule, and LLM provisioning bridges
are available through explicit `-Run...Provisioning` flags, and child scripts
stay dry-run unless `-ExecuteProvisioning` is also supplied. Add
`-SendTelegramTest` only when you want the activation runner to include the
urgent Telegram send test. Use `-RunLlmFinalization` only after provider keys
are loaded externally. Cron install and profile smoke checks remain explicit
flags because they require messaging and provider credentials to be ready.

## Project Workflow Kanban

When a company project is created, the dashboard generates the starter research, PRD, architecture, testing, marketing, critic-review, and founder-decision tasks. From the project detail page, use `Push workflow to Kanban` to create the missing Hermes Kanban tasks in one batch. Already-linked tasks are skipped so the action is safe to repeat.

Use `/setup#kanban-verification` to track board initialization, diagnostics, and one dashboard task-create check before treating Hermes Kanban as the source of truth.
Use `/setup/kanban-verification-template.md` to paste no-secret board,
diagnostics, and task-create evidence in bulk after those checks complete.

Use `/setup/kanban-provisioning.md` and `/setup/kanban-provisioning.ps1` to
review the board lanes, workflow-template lane mapping, and dry-run Hermes
Kanban init/diagnostics commands before the first real project idea.
After `hermes kanban init` succeeds, add `-PostDashboardStatus` to the Kanban
provisioning runner to mark `kanban-board-initialized` verified without storing
secrets or raw credentials.

Use `/setup/kanban-runbook.md` for the Kanban setup sequence and
`/setup/kanban-diagnostics.ps1` for the no-secret local initialization and
diagnostics script.

## Tests

```powershell
py -3.11 -m poetry run pytest
py -3.11 -m poetry run ruff check .
```
