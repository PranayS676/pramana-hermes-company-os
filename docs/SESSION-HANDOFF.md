# Session Handoff — 2026-06-30

A running pointer for the next Claude Code session. Pair with [CLAUDE.md](../CLAUDE.md)
(durable operating rules) and the approved plan at
`C:\Users\masadis\.claude\plans\scalable-knitting-acorn.md`.

Repo lives at **`C:\dev\hermes-company-os`** (non-OneDrive clone). Windows + PowerShell;
Python 3.11 via Poetry.

## First thing: confirm what's on `main`

This session's work (Phases 0–3 below) was finished on branch
**`hermes/dashboard-htmx-declutter`** and pushed, pending a founder merge.

```bash
git -C C:/dev/hermes-company-os log --oneline -3
```
- If you see `feat(ui): button hierarchy …` / `HTMX progressive-enhancement` / `Linear-style dark redesign`, it's **already merged** → skip to "Remaining work".
- If not, the founder still needs to merge the PR for `hermes/dashboard-htmx-declutter`
  into `main` (base `main` ← compare that branch; it's a clean merge, contains everything).
  Note: `gh pr create` is **blocked** for this Enterprise-Managed-User CLI account —
  PRs are opened/merged via the GitHub web UI by PranayS676. After merge:
  `git checkout main && git pull --ff-only origin main`, then prune merged branches +
  the stale `.claude/worktrees/*`.

## What shipped this session (Phases 0–3)

A UI redesign + interaction-feel + backend refactor, built on the approved plan. All on
`hermes/dashboard-htmx-declutter` (which stacks the two subset branches
`hermes/ui-linear-redesign` and `hermes/backend-refine` — close those PRs unmerged).

- **Phase 0 — Linear dark reskin** (`static/styles.css`): rewrote `:root` tokens (near-black
  canvas, indigo `#5e6ad2` accent, subtle shadows) + a dark-theme layer converting hardcoded
  light surfaces, status pills (semantic tints), buttons, sidebar, active states; lighter type
  weights, denser controls, rounded cards, indigo links, hover lifts. **Vendored lucide**
  locally (`static/lucide.min.js`) — all 12 templates point at it, not the CDN. `.claude/`
  gitignored.
- **Phase 1 — Backend refactor** (`hermes/backend-refine`): `routers/_helpers.py`
  (`get_project_or_404`/`get_agent_or_404`); global exception handlers in `create_app`
  (`ValueError→409`, `sqlite3.IntegrityError→400`); extracted `/decisions`, `/queue`,
  `/agents/*` from `main.py` into `routers/{decisions,queue,agents}.py` via the standard
  `register_<name>_routes(app)` pattern. **`main.py` 5586 → 5143 lines.** Protocol verified
  already in sync.
- **Phase 2 — HTMX feel** (`static/htmx.min.js` vendored, `static/app.js` new): `hx-boost="true"`
  on every `<body>` → links/forms AJAX-swap (no full-page-reload flash). `app.js` re-renders
  lucide icons after swaps, drives a top progress bar (`#app-progress`), shows "Saved" toasts
  after successful boosted POSTs (in `htmx:afterSettle`), and routes raw-document links
  (`.md/.json/.ps1/…`) to native navigation so they aren't swapped into the body. Button
  loading state via `.htmx-request`. **Progressive enhancement — works with JS off.**
- **Phase 3 (partial) — button hierarchy**: setup topbar 23 primary link-buttons → subtle
  secondaries (19 real form actions stay primary); dashboard activation gate → 1 primary + 3
  secondary.

**Verification:** full suite **594 passing**, `ruff check .` clean, no-secret scan clean,
app builds. Live flags still default-off.

## Two audit claims that were WRONG (don't re-act on them)
- All 8 routers were already registered in `create_app` (the audit said unregistered).
- `setup.html` nav anchors `#profiles`/`#integrations` have real targets (`id="profiles"` ~L1017,
  `id="integrations"` ~L1220) — nav is not broken.

## Remaining work — Phase 3 tail (plan task #7)
1. **Jinja macros** — add `templates/_macros.html` (`status_pill`, `panel_header`, `list_row`)
   and replace the copy-pasted markup (status-pill repeated ~50×, panel-header ~85×).
2. **Dashboard form declutter** (`templates/dashboard.html`) — move the inline create forms
   (decision / planning-task / document) behind "New…" disclosures so the dashboard reads as
   list-views; dedupe the task form (it appears twice).

### Deferred (noted in the plan, not started)
- Extract the 70+ `/setup` routes into routers (high surface; own batch).
- `project.html` (20+ sections) tabbing / progressive disclosure.
- Command palette (Cmd-K) + global keyboard shortcuts — explicitly out of the approved round.
- Richer per-fragment HTMX swaps (current approach is `hx-boost`, deliberately lighter).
- Live enablement (flip `HERMES_LIVE_EXECUTION_ENABLED` / `_EXTERNAL_DISPATCH_ENABLED` /
  `_REVIEW_ENFORCEMENT_ENABLED` per stage after validating against real Hermes); wire the
  UI/UX Research Agent as a live profile; M7 live inbound polling.

## Environment facts (will bite you)
- **Run the app:** `py -3.11 -m poetry run uvicorn hermes_company_os.main:app --host 127.0.0.1 --port 8002`
  (open http://127.0.0.1:8002). Background servers do NOT survive a session/process exit.
- **Templates are cached** by Jinja — restart uvicorn to see template edits; `static/*` (CSS/JS)
  is served fresh on reload.
- **Preview screenshots time out** on these tall pages (renderer limit) — verify UI via
  `preview_inspect` (computed styles) or `curl` of the served HTML, not screenshots. Client-side
  JS (htmx behavior) can't be fully driven here — ask the founder to click through in a browser.
- Full suite ≈ 4–5 min: `py -3.11 -m poetry run pytest -q` (expect ~594). Lint: `ruff check .`.
- Don't commit/push to `main` directly; short-lived branches + founder-approved web PRs.

## How to start the next session
Say: **"Read CLAUDE.md and docs/SESSION-HANDOFF.md, then do the Phase 3 tail (Jinja macros +
dashboard form declutter) on a branch off main."**
