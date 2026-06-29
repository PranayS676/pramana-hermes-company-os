# CLAUDE.md — Hermes Company OS

Shared operating context for Claude Code agents (including subagents) working in this repo.
Read this fully before editing. It encodes constraints and patterns that are **not** obvious
from the code alone.

## What this is

A founder-led AI company operating system: a FastAPI + SQLite + Jinja dashboard that sits
**beside** the real Hermes agent runtime (it does not vendor or modify Hermes). A founder drives
a product idea through a controlled pipeline (idea → research → PRD → architecture → tasks →
code plan → acceptance → approval → execution handoff). Agents generate/review/prepare; every
irreversible or outward-facing action is **staged, audited, and founder-approved**.

Guiding principle: **founder control first, and demo-safety must never depend on real credentials.**

## Safety doctrine (non-negotiable)

- **No live sends by default.** Slack / Telegram / Kanban / Hermes / Codex live paths sit behind
  founder approval gates **and** environment flags that default to **off** (`HERMES_*_ENABLED=false`,
  see `settings.py`). Never enable a live path or flip a flag's default.
- **Never introduce secrets or fake token-shaped strings.** Do not edit `.env`, credential files,
  raw tokens, auth stores, or live AppData Hermes profile files.
- **Run `assert_no_secret_values(...)` / `secret_violations(...)`** (`secret_guard.py`) over every
  stored or generated text payload. Treat it as a backstop, not a secret manager.
- **Preserve public-demo-safe behavior.** If a change could enable real external I/O, stop and ask.
- Ask before anything large or risky. Prefer small slices with tests. Inspect source before editing.
- **Do not commit or push unless explicitly asked.**

## Environment & commands

- Windows 11, PowerShell (primary shell); Python 3.11 via Poetry.
- Tests (full, ~3 min, 445 tests): `py -3.11 -m poetry run pytest`
- Focused tests: `py -3.11 -m poetry run pytest tests/test_x.py -q`
- Lint: `py -3.11 -m poetry run ruff check .`   ·   Autofix: `ruff check --fix <files>`   ·   Format: `ruff format <file>`
- Run app: `py -3.11 -m poetry run uvicorn hermes_company_os.main:app --host 127.0.0.1 --port 8002 --reload`
- No-secret scan: run `secret_violations({path: text})` over changed files before finishing.

## Known environment quirks (will bite you)

- **Starlette 1.3.1 + FastAPI 0.138**: `APIRouter` + `include_router` mounts the router as a
  **sub-application** (it does not flatten into `app.routes`). **Use the `register_*_routes(app)`
  direct-decorator pattern** instead (see `routers/external_dispatch.py`). This matches the rest
  of the dashboard and registers routes normally.
- **No type checker** (no mypy/pyright in the toolchain). `RepositoryProtocol` is a documentation
  contract, not enforced — keep it accurate but don't rely on static checks.
- The repo may live under a OneDrive-synced path; the SQLite DB (`./data/company_os.db`) can hit
  sync/lock issues. Prefer working from a non-synced clone (e.g. `C:\dev\...`).

## Architecture patterns to follow

- **Repository** — public API is `CompanyRepository` (`hermes_company_os.repository`), composed
  from domain mixins (`repository_audit_agents`, `repository_setup_verification`,
  `repository_decisions_work`, `repository_project_workflow`, `repository_generation`,
  `repository_stage_lifecycle`). Free helpers live in `repository_support`. Add new methods to the
  matching mixin, not a new god class.
- **Type service args** that take a repository with `RepositoryProtocol` (`repository_protocol.py`,
  regenerate from the class when methods change).
- **Routes** — extract cohesive groups into `hermes_company_os/routers/<name>.py` as a
  `register_<name>_routes(app)` function using `@app.get/@app.post`. Access state via
  `request.app.state` (repository, settings, templates). Wire it in `create_app` before `return app`.
- **Fingerprints/hashing** — use `hermes_company_os.fingerprints` (`fingerprint_json` / `fingerprint_text`).
- **Setup-importer parsing** — use `hermes_company_os.setup_import_parsing`
  (`strip_inline_comment` / `parse_status_value`).
- **DB schema changes** — add an idempotent step in `database.ensure_schema` and bump `SCHEMA_VERSION`.
- **Live integrations** — gate behind an env flag (default off) + a founder-approval gate, and ship a
  **fake client** for tests. Real Hermes/Slack/Telegram/Kanban/Codex calls are never required by the
  unit suite.

## Testing standards

- **TDD first.** Repository tests for state transitions; route tests for success/blocked/missing/invalid;
  secret-guard coverage for stored/generated text; fake-client tests for live integrations.
- Keep your slice's focused tests + `ruff` green as you go; the full suite is the integration gate.
- Definition of done for a change: focused tests pass · `ruff check .` clean · `git diff --check` clean ·
  no-secret scan clean · live flags still default-off.

## Git & merge cadence

- `main` is the **protected, always-green, always-demo-safe trunk** (the public-demo checkpoint).
- Work on short-lived branches off `main`. For parallel work, give each agent **disjoint file
  ownership**; integrate slices on a per-batch integration branch, then promote to `main` via a
  **founder-approved PR** when green + demo-safe. Slices never merge straight to `main`.
- Branch from a fresh `main` each batch to avoid drift. Don't push/commit unless asked.

## Repo map (orientation)

- `src/hermes_company_os/main.py` — FastAPI `create_app` + most routes (being split into `routers/`).
- `src/hermes_company_os/repository*.py` — data access (`CompanyRepository` + mixins + support).
- `src/hermes_company_os/database.py` — schema, migrations (`ensure_schema`), seeds.
- `src/hermes_company_os/settings.py` — env flags (all live flags default off).
- `src/hermes_company_os/external_dispatch.py` — Slack/Telegram/Kanban command boundary (dry-run).
- `src/hermes_company_os/project_operating_loop.py` — operating-loop / dispatch package assembly.
- `src/hermes_company_os/templates/*.html` — Jinja UI.
- `docs/agentic-company-os-roadmap.md` — milestones M0–M9 and build order.
- `tests/` — pytest suite (fake clients for live integrations).
