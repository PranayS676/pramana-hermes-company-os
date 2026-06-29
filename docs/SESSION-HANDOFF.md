# Session Handoff — 2026-06-29

A running pointer for the next Claude Code session. Pair this with
[CLAUDE.md](../CLAUDE.md), which holds the durable operating rules.

The repo has been **moved off OneDrive** to the non-synced clone `C:\dev\hermes-company-os`
(git worktrees and the SQLite DB are reliable there). Work from that path.

## In flight — batch `hermes/batch-m3-m6-m8` (not yet on `main`)

Three milestones were built in parallel (isolated worktree lanes, disjoint file
ownership) and integrated on branch **`hermes/batch-m3-m6-m8`**. Full suite
**541 passing**, `ruff` clean, no-secret scan clean, all live flags default-off.
Awaiting founder-approved PR into `main`.

- **M6 — Cross-agent review enforcement** (`review_policy.py`, `repository_stage_lifecycle.py`):
  gated stages can't be approved until required reviews exist and pass. Policy is
  data-driven (`STAGE_REVIEW_POLICIES`: `acceptance` → `qa-critic` + `test-automation-agent`).
  Gated behind `HERMES_REVIEW_ENFORCEMENT_ENABLED` (**default off**); wired in `create_app`
  via `configure_review_enforcement(...)`. Requirements API:
  `/projects/{id}/stages/{stage}/review-requirements.json`.
  - **Follow-up shipped:** `generate_stage_reviews(...)` + `POST /projects/{id}/stages/{stage}/reviews`
    record the required reviews against a stage's *draft* artifact, resolving the
    chicken-and-egg (the post-acceptance review batch still requires acceptance approved).
- **M3 — Live Hermes generation** (`generation_service.py`, `routers/generation.py`):
  three founder-facing modes (`local_demo` / `live_hermes_draft` / `live_hermes_with_review`),
  stage→profile routing, mode-switch route. Live modes fail closed behind
  `HERMES_LIVE_EXECUTION_ENABLED` (**default off**) + readiness; fake runner in tests,
  real `hermes` never required by the suite.
- **M8 UI — Observability dashboard** (`templates/observability.html`,
  `routers/observability.py`): renders the existing run/audit metrics company-wide and
  per-project; links from dashboard + project pages. Read-only.

## Where things stand on `main`

`main` is the demo-safe trunk. It contains, on top of the original
Product Wizard baseline:

- **Phase 0 (structural)** — `CLAUDE.md` shared agent context; repository split into
  domain mixins (`repository_*`), `RepositoryProtocol`, shared `fingerprints` and
  `setup_import_parsing` helpers, and route groups extracted into
  `hermes_company_os/routers/` via the `register_<name>_routes(app)` pattern.
- **M8 — Observability** (`observability.py` + `routers/observability.py`): read-only
  run/audit metrics. Routes: `/observability.json`, `/projects/{id}/observability.json|.md`.
- **M2 — Queue autonomy** (`agent_work_pickup.py`): founder-gated auto-pickup of work
  items (`planned→assigned→running` + audit only). Flag `HERMES_AUTO_PICKUP_ENABLED`
  (**default off**).
- **M7 — Live external dispatch** (Option 1, Hermes command boundary): real sends go
  through `hermes send` / `hermes kanban create` (credentials stay in Hermes, never the
  dashboard) + idempotent `external_dispatch_deliveries` records. Flag
  `HERMES_EXTERNAL_DISPATCH_ENABLED` (**default off**).

Full suite: **491 tests passing**. All live paths default-off and founder-gated.

## Verified environment facts

- **Hermes is installed locally** (`hermes` v0.17.0). The real send interface is
  `hermes send --to slack:<id>|telegram:<id> "<text>"` and `hermes kanban create … --idempotency-key … --json`.
  There is **no `hermes dispatch`** command (older contracts referencing it were corrected).
- Starlette 1.3.1 quirk: use the `register(app)` direct-decorator pattern, not
  `APIRouter`/`include_router` (see CLAUDE.md).

## Workflow we're using (parallel build)

1. Contract-first / shared brief in `CLAUDE.md`, then keep feature work in small,
   isolated files so lanes don't collide.
2. Fan out lanes with disjoint file ownership; integrate on a per-batch branch.
3. One integration gate (full suite + `ruff` + no-secret scan), then promote to `main`
   via a **founder-approved PR**. Slices never merge straight to `main`.

## Recommended next milestones (founder's choice)

With M3/M6/M8 in flight (above), the remaining roadmap milestones are:

- **M4** — Company Memory Layer (reusable founder preferences, standards, accepted risks).
- **M5** — Codex Project Execution Mode (approved code plan → real workstreams).
- **M9** — Launch & Release Management (launch-tier gates, release memo, QA signoff).

Smaller follow-ups worth noting:

- **M6 live review mode** — replace the fake `generate_stage_reviews` records with live
  Hermes-backed reviews once M3 live generation is trusted.
- **M3 live enablement** — founder turns on `HERMES_LIVE_EXECUTION_ENABLED` per stage after
  confirming readiness; currently exercised only via the fake runner.
