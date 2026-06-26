# Preflight Inputs

Collect these before the company enters idea/research mode. Store only safe
dashboard values in Hermes Company OS. Load Slack tokens, Telegram bot tokens,
provider keys, OAuth payloads, and private endpoints outside this dashboard in
the real Hermes profile runtime, then report status only.

For the live generated checklist, use:

```text
/setup/input-ledger.md
/setup/input-ledger.json
```

## Safe Dashboard Values

These values are safe to paste into `/setup#inputs` or import through
`/setup#input-import`. Use `/setup/first-run.ps1` for the guided local starter,
or `/setup/founder-inputs.ps1` for only the safe-input prompt.

### Founder

- Founder name to use in agent outputs.
- Slack member ID.
- Telegram user ID.
- Normal business timezone. Default: `America/New_York`.
- Whether standups should run only weekdays or every day.
- Whether the default 9 AM and 3 PM standup times should change before cron jobs
  are created.

### Slack Workspace

- Workspace name.
- Channel IDs for:
  - `#founder-command`
  - `#agent-standup`
  - `#product`
  - `#research`
  - `#engineering`
  - `#marketing`
  - `#qa-review`
  - `#decisions`
  - `#alerts`

### Telegram Routing

- Founder Telegram user ID.
- Urgent chat ID if alerts should go to a group/channel instead of direct chat.

### LLM Preference Metadata

LLM credentials are intentionally last. Safe metadata can be captured early if
known:

- Preferred provider name.
- Preferred model name.
- Fallback provider/model.
- Budget or rate-limit preference.

Do not paste provider credential values into the dashboard or this repo.

### Hermes Profiles

- Confirm profile IDs:
  - `chief-of-staff`
  - `product-manager`
  - `research-agent`
  - `engineering-manager`
  - `backend-engineer`
  - `frontend-engineer`
  - `cloud-infra-agent`
  - `test-automation-agent`
  - `marketing-agent`
  - `qa-critic`
- Confirm whether profile gateways should run foreground, as user services, or
  through an external process manager.

### Kanban

- Confirm the default board lanes are acceptable for now.
- Confirm whether all agents should be valid Kanban assignees immediately.
- Confirm whether the Chief of Staff is allowed to dispatch tasks automatically.

## External Credential Status Only

Load real credential values into the correct Hermes profile environment or
provider auth flow. Then update only status metadata in `/setup#secret-status` or
through `/setup#credential-status-import`.

Allowed status words:

- `needed`
- `loaded`
- `verified`
- `deferred`

Use `/setup/credential-status-template.md` for the current generated status
reply. Do not include credential values, request headers, OAuth payloads,
private endpoint URLs, or raw logs.

## Activation Order

1. Run `/setup/first-run.ps1`, or capture safe founder/workspace IDs with
   `/setup/founder-inputs.ps1` or `/setup/founder-input-request.md`.
2. Apply starter profile artifacts.
3. Verify starter profile installation with `/setup/profile-installation.ps1`.
4. Create Slack apps and load Slack credentials externally.
5. Create the Chief of Staff Telegram bot and load its credential externally.
6. Verify Slack and Telegram messaging.
7. Initialize and verify Kanban.
8. Verify manual standups, then install cron.
9. Load and verify LLM provider credentials last.
10. Run profile smoke checks.
11. Run role acceptance prompts before the first real company idea.
