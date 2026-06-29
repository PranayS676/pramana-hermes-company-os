# Session Handoff — 2026-06-29

A running pointer for the next Claude Code session (especially after the repo moves
off OneDrive, since that starts a fresh session with no chat memory). Pair this with
[CLAUDE.md](../CLAUDE.md), which holds the durable operating rules.

## Where things stand

`main` is the demo-safe trunk. As of this handoff it contains, on top of the original
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

- **M6** — cross-agent review enforcement (block stage approval until required reviews exist).
- **M3** — live Hermes profile generation (now grounded: `hermes` is on PATH).
- **M8 UI** — surface the observability metrics in the dashboard (currently JSON/MD only).

## Pending operational task — move off OneDrive

The repo currently lives under a OneDrive-synced path, which intermittently locks files
(broke git worktrees this session). Move to a non-synced path:

```powershell
git status                                  # clean? everything pushed?
# pause OneDrive sync (tray icon)
git clone https://github.com/PranayS676/pramana-hermes-company-os C:\dev\hermes-company-os
cd C:\dev\hermes-company-os
py -3.11 -m poetry install
py -3.11 -m poetry run pytest -q            # expect ~491 passed
```

Optional: copy `data/company_os.db` over if you want to keep local dashboard state
(it is git-ignored). `~/.hermes/` (profiles/secrets) is in your home dir and is
unaffected by the move.
