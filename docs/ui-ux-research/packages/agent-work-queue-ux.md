# Agent Work Queue UX Research Package

## Package Metadata

- Package title: Agent Work Queue UX
- Research thread: Worker 3, Hermes Company OS UI/UX Research Batch 1
- Owner: UI/UX Research Agent research thread
- Date: 2026-06-26
- Source docs reviewed:
  - `docs/agentic-company-os-roadmap.md`
  - `docs/ui-ux-research/01-ui-ux-research-agent-doctrine.md`
  - `docs/ui-ux-research/02-codex-subagent-research-operating-model.md`
  - `docs/ui-ux-research/03-ui-ux-research-thread-prompts.md`
  - `docs/ui-ux-research/04-research-package-template.md`
  - `docs/implementation-plans/01-founder-control-plane-implementation-plan.md`
  - `docs/implementation-plans/02-ui-ux-research-agent-implementation-plan.md`
- Current implementation areas inspected:
  - `src/hermes_company_os/database.py`
  - `src/hermes_company_os/repository.py`
  - `src/hermes_company_os/main.py`
  - `src/hermes_company_os/templates/dashboard.html`
  - `src/hermes_company_os/templates/agent.html`
  - `src/hermes_company_os/templates/project.html`
  - `tests/test_app.py`
  - `tests/test_product_wizard_acceptance.py`
- Scope: per-agent queues, Chief of Staff triage, queue states, blocked work, review-needed work, founder approval handoffs, and secondary Slack, Telegram, and Kanban handoff signals.
- Out of scope: source implementation, live Hermes profile execution, live AppData writes, credential handling, external Slack/Telegram/Kanban API calls, and final visual design.

## Research Question

How should Hermes Company OS present agent work queues so the founder and Chief of Staff can understand what each agent is doing, triage blocked or review-needed work, and route founder approvals without making autonomous work invisible or premature?

## Target Workflow

The target workflow starts from the dashboard as the operating source of truth. The founder or Chief of Staff opens the queue overview, scans work by urgency and state, drills into a project or agent, and takes only the actions appropriate to their authority.

- Entry point: dashboard queue summary, Chief of Staff triage view, agent detail page, project detail page, or founder decision queue.
- Primary job to be done: see every active work item with owner, project, state, blocker, review status, evidence, and next action.
- Expected outcome: work is assigned, running, blocked, moved to review, or handed to the founder with enough context to approve, reject, defer, or request revision.
- Approval or review moment: approvals, rejections, accepted risk, launch, external actions, and irreversible scope changes create or resolve founder decision records rather than silently changing queue state.
- Exit state: the item is blocked with a named unblocker, waiting for review, approved/rejected by the founder, or done with linked evidence and audit trail.

## User And Persona Assumptions

- Founder behavior: the founder will not live inside each agent page. They need a queue summary that highlights only urgent approvals, blocked work, review-ready outputs, and irreversible decisions.
- Chief of Staff behavior: Chief of Staff is the queue operator. This role may triage, reassign, change priority, request clearer evidence, and block work when dependencies or permissions are missing.
- Agent behavior: agents may move work through execution states such as assigned, running, blocked, and needs_review. Agents may propose completion, but they may not approve, reject, accept risk, launch, authorize external actions, or make irreversible scope changes.
- Reviewer behavior: QA Critic, Test Automation, Product Manager, Engineering Manager, and UI/UX Research Agent need review queues that separate required review from optional commentary.
- Frequency of use: Chief of Staff queue triage is a daily operating surface; founder review is bursty and should be concise.
- Urgency: blocked work that halts execution or exceeds a decision SLA should surface ahead of ordinary running work.
- Information density tolerance: the queue should be dense and scan-friendly, using tables and compact detail panels rather than decorative cards.
- Founder confirmation needed: exact autonomy boundaries, escalation SLAs, and which low-risk work can be marked done without founder review.

## Current-State Notes

Current system has several pieces that can support queue UX, but the Milestone 2 agent work queue is not implemented yet.

- The roadmap defines Milestone 2 as an Agent Work Queue with states `planned`, `assigned`, `running`, `blocked`, `needs_review`, `approved`, `rejected`, and `done`.
- Existing database tables include `tasks`, `documents`, `runs`, `founder_decisions`, `project_workflow_items`, `product_wizard_project_stages`, and `product_wizard_artifacts`, but no dedicated `agent_work_items` queue model yet.
- The dashboard already includes a Founder Decision Queue and an Agent Profiles table.
- The agent detail page currently focuses on identity, capabilities, profile exports, starter profile edits, runtime routing, and direct live profile runs. It does not yet show an agent queue.
- The project detail page already shows Product Wizard timeline, artifact preview, generated company workflow, founder readiness, and Kanban push gates.
- Product Wizard and Kanban behavior already establish useful gating patterns: Kanban push waits for task-stage approval and verified Kanban readiness.
- Existing tests cover founder decision creation/update, secret rejection, Product Wizard stage approval flow, and Kanban blocking. Future queue implementation should reuse those standards.
- Slack, Telegram, and Kanban are already described as coordination channels, but the dashboard should remain the source of truth for queue state and approval state.

## Screens Needed

### Chief of Staff Triage

- Purpose: provide one cross-agent queue for operating cadence, priority, blockers, and handoffs.
- Primary user: Chief of Staff.
- Primary action: triage, assign, reassign, block, unblock, request evidence, or route founder decision.
- Secondary actions: filter by project, agent, state, urgency, review owner, SLA, or external handoff status.
- Empty state: "No active work items. Approved wizard tasks will appear here after the queue is enabled."
- Blocked state: group blocked items first with blocker reason, blocking owner, age, and requested decision.
- Failed state: show failed run or failed handoff evidence with retry policy and next owner.
- Success state: all urgent items have owners, blocked items have explicit unblockers, and review-needed items have reviewers.

### Agent Detail Queue

- Purpose: show one agent's current commitments and whether the agent is overloaded, blocked, waiting on review, or idle.
- Primary user: founder, Chief of Staff, and agent owner.
- Primary action: inspect the agent's queue and open the most urgent item.
- Secondary actions: change priority, reassign to another agent, block item, or open linked project/artifact/run.
- Empty state: "This agent has no queued work."
- Blocked state: blocked items appear above running work and name the blocker and decision route.
- Failed state: failed run or failed external handoff appears inline with linked run evidence.
- Success state: agent queue shows clear state distribution and no item lacks a next action.

### Work Item Detail Drawer Or Page

- Purpose: provide the evidence and controls needed to act on one work item without losing context.
- Primary user: Chief of Staff, reviewer, or founder.
- Primary action: take the next legal transition for the current role.
- Secondary actions: view source inputs, artifact, run record, review findings, Kanban link, Slack context, Telegram escalation history, and decision record.
- Empty state: not applicable because the view opens from an existing item.
- Blocked state: show blocker reason, requested owner, required founder decision, and last update.
- Failed state: show failed run, retry count, error summary, and whether retry is allowed.
- Success state: item has evidence, clear owner, allowed actions, and audit trail.

### Review Needed Workbench

- Purpose: separate "work is ready for review" from "work is approved".
- Primary user: QA Critic, Test Automation, Product Manager, Engineering Manager, UI/UX Research Agent, and founder when required.
- Primary action: accept for review, return with findings, create founder decision, or mark review satisfied.
- Secondary actions: filter by required reviewer, severity, project, launch tier, and missing evidence.
- Empty state: "No work is waiting for review."
- Blocked state: item shows missing evidence or unavailable reviewer.
- Failed state: review cannot complete because artifact, tests, or run evidence is missing.
- Success state: review produces a finding, approval recommendation, accepted-risk request, or rejection recommendation.

### Founder Approval Handoff

- Purpose: convert queue moments that require founder judgment into decision records with context and evidence.
- Primary user: founder.
- Primary action: approve, reject, defer, request revision, accept risk, or answer an agent question.
- Secondary actions: open source artifact, open review findings, inspect queue history, or return to project.
- Empty state: "No founder approval needed."
- Blocked state: show exactly what cannot proceed until the decision is made.
- Failed state: decision cannot resolve because required evidence is absent or secret-like material was submitted.
- Success state: founder decision updates the linked queue item and preserves audit history.

### Project Queue Strip

- Purpose: show the work created from an approved project or Product Wizard stage without leaving the project page.
- Primary user: founder and Chief of Staff.
- Primary action: inspect what work exists for the project and which agent owns each piece.
- Secondary actions: open queue item, open artifact, open decision, or open Kanban link.
- Empty state: "No agent work items have been created for this project."
- Blocked state: identify which project stage or approval is blocking downstream work.
- Failed state: show failed work item creation or handoff failure.
- Success state: project shows active, blocked, review-needed, and done work counts.

## State Model

| State | Meaning | Owner | Allowed actions | Forbidden actions | Evidence required |
| --- | --- | --- | --- | --- | --- |
| `planned` | Work exists but is not committed to an agent run yet. | Chief of Staff or system from approved plan | assign, prioritize, attach source, cancel before execution | run without owner, approve, mark done | source project, stage, artifact, or manual reason |
| `assigned` | Work has an owner and is ready for that agent to start. | Assigned agent, Chief of Staff | start, reassign, block, request clarification | approve, reject, external handoff | owner, priority, expected output, acceptance criteria |
| `running` | Agent or workstream is actively producing output. | Assigned agent | update progress, attach run, block, move to needs_review | founder approval, launch, mark approved | run record or progress evidence |
| `blocked` | Work cannot proceed until a dependency, decision, credential-free setup, review, or external gate is resolved. | Chief of Staff by default; assigned agent may propose | name blocker, request founder decision, reassign, unblock after evidence | silently continue, hide in lower priority list, mark done | blocker reason, blocking owner, requested action, age |
| `needs_review` | Output exists and requires review before approval or completion. | Reviewer or Chief of Staff | assign reviewer, return with findings, request founder decision, recommend approval | treat as approved, launch, external action | artifact, acceptance criteria, test or review evidence |
| `approved` | Founder or authorized reviewer has approved the work according to policy. | Founder for founder-gated items; reviewer for delegated review | archive, create downstream work, push allowed handoff | bypass required review, mutate evidence | decision or review record with approver and rationale |
| `rejected` | Founder or authorized reviewer rejected the work. | Founder for founder-gated items; reviewer for delegated review | create revision work, close as rejected, document reason | continue as if approved, delete evidence | rejection reason, source output, next recommendation |
| `done` | Work is complete, archived, and linked to evidence. | Chief of Staff or system after required gates pass | reopen with reason, export audit, create follow-up | mark done while approval/review/blocker is open | linked output, review/decision state, completion timestamp |

## UX Risks And Anti-Patterns

- Confusing `needs_review` with `approved`. Review-ready work must never look complete.
- Hiding blocked work below running work. Blockers are the highest operational risk because they stop progress or create unsafe drift.
- Letting agents approve their own output. Agents can propose next state, but founder-gated approvals must stay explicit.
- Treating Slack, Telegram, or Kanban as the system of record. They should mirror or escalate dashboard state, not define it.
- Showing optimistic generated summaries without source inputs, acceptance criteria, or review evidence.
- Combining triage and editing into one dense form. The queue should support fast scan first, then detailed action.
- Using vague labels such as "ready" without saying ready for review, ready for founder approval, ready for Kanban, or ready for launch.
- Making blocked or failed states visually quiet. They need clear status, owner, and next action.
- Depending on hover-only controls for queue actions.
- Allowing long generated text, run errors, or review notes to break table layout.
- Adding autonomous work controls before state transition tests and secret rejection tests exist.

## Accessibility And Responsive Notes

- Queue rows must be keyboard reachable, and every row action must be available without hover.
- State filters should be real form controls or accessible segmented controls with visible focus.
- Status should use text labels plus color, never color alone.
- Tables should preserve column headers on desktop and collapse into labeled row groups on mobile.
- Blocker reason, review finding, and decision text should wrap predictably with max-height expansion rather than stretching rows without limit.
- The active row or detail drawer should manage focus when opened and restore focus when closed.
- Review and approval actions should use explicit button text, not only icons.
- Disabled actions should explain the missing prerequisite in adjacent text.
- Motion should be minimal. Queue reordering should not animate in a way that hides what changed.
- Long agent names, project names, artifact titles, and Kanban IDs must not overlap action controls.

## Implementation Recommendations

| Recommendation | Behavior | Affected surface | Likely data needed | Acceptance signal |
| --- | --- | --- | --- | --- |
| Add a dedicated queue overview | Show cross-agent counts by state, urgency, blocker age, and review owner. | Dashboard or `/queue` route | work item id, project, owner agent, state, priority, timestamps | Chief of Staff can identify top blocker and top review item in one screen. |
| Add per-agent queue panel | Extend agent detail pages with current assigned/running/blocked/needs_review work. | `/agents/{agent_id}` | filtered work items, run links, review links, decision links | Agent page shows queue without replacing profile/routing sections. |
| Add work item detail view | Provide source inputs, acceptance criteria, evidence, run history, review findings, and legal transitions. | Queue detail drawer or route | queue item, artifact, run, decision, review, Kanban metadata | User can explain why an item is in its current state. |
| Separate review from approval | Treat `needs_review` as its own queue lane with reviewer assignment and findings. | Review workbench and item detail | review policy, reviewer, findings, required evidence | No reviewed item can appear approved without a review or decision record. |
| Route founder gates through decisions | Create or link founder decision records for approvals, rejections, accepted risk, launch, external actions, and irreversible scope changes. | Founder decision queue and queue detail | decision type, owner, context, evidence, linked work item | Founder can resolve a queue blocker from the decision system with audit history. |
| Add blocker-first triage | Sort blocked urgent work ahead of running work and display blocker age. | Chief of Staff triage | blocker reason, blocked_at, blocking owner, SLA | Blocked work cannot be missed in the default triage view. |
| Show secondary handoff signals | Display Slack channel, Telegram escalation policy, Kanban task link, and sync status as secondary metadata. | Queue rows and detail | slack channel, telegram policy, kanban task id, handoff status | Dashboard state remains primary even when external handoffs exist. |
| Enforce transition constraints in UI | Only show actions allowed by role, state, evidence, and approval policy. | Queue actions | current user role, state, policy, evidence completeness | Forbidden transitions are absent or disabled with reasons. |
| Preserve no-secret behavior | Reject secret-like values in blocker notes, review findings, decision context, and external handoff notes. | Forms and routes | secret guard over all queue text fields | Secret-like input is rejected in route tests. |

## Acceptance Checklist

- [x] Target workflow is clear.
- [x] Required screens are listed.
- [x] Required states are listed.
- [x] Founder approval and revision paths are clear.
- [x] Blocked and failed states are handled.
- [x] Accessibility requirements are explicit.
- [x] Recommendations can become tasks.
- [x] Risks and anti-patterns are named.
- [x] Founder decisions needed are explicit.
- [x] No credentials or secret-looking values are included.

## Founder Decisions Needed

### Queue Autonomy Boundary

- Decision: confirm which transitions agents, Chief of Staff, reviewers, and founder may perform.
- Why it matters: queue UX cannot safely show actions until authority is clear.
- Default recommendation: agents may move execution states; Chief of Staff may triage, reassign, and block; founder approval is required for approvals, rejections, accepted risk, launch, external actions, and irreversible scope changes.
- Impact if deferred: implementation can build read-only queue views, but state-changing actions should remain locked.

### Done State Policy

- Decision: define when `done` can be set and who can set it.
- Why it matters: done can be mistaken for approved or launched.
- Default recommendation: allow Chief of Staff or system automation to mark done only after required review and founder-gated decisions are satisfied.
- Impact if deferred: use `approved` and `needs_review` states, but avoid exposing a done action.

### Blocker Escalation SLA

- Decision: choose when blocked work escalates from dashboard/Slack to Telegram.
- Why it matters: Telegram should remain urgent-only and not become routine noise.
- Default recommendation: Telegram only for blocked launch, production incident, founder decision SLA exceeded, credential/runtime failure, or work blocked on founder decision after an agreed age.
- Impact if deferred: show blocker age in dashboard and Slack summaries, but do not send urgent alerts automatically.

### Review Policy By Work Type

- Decision: define which work types require QA Critic, Test Automation, Product Manager, Engineering Manager, UI/UX Research Agent, or founder review.
- Why it matters: `needs_review` must route to the right reviewer instead of becoming a generic waiting bucket.
- Default recommendation: require QA Critic before acceptance approval, Test Automation before launch readiness, Product Manager before major scope changes, Engineering Manager before implementation starts, and UI/UX Research Agent before UI-heavy implementation.
- Impact if deferred: queue can support manual reviewer assignment, but required-review blocking should not be automated.

### External Handoff Authority

- Decision: confirm what can be pushed to Kanban or messaged to Slack without founder approval.
- Why it matters: external handoffs are operational side effects and need auditability.
- Default recommendation: routine Slack updates and approved Kanban task creation may be delegated after the relevant project stage is approved; Telegram, launch, public claims, and real external-risk actions require founder approval.
- Impact if deferred: queue should display external handoff readiness but keep send/push actions disabled.

## Implementation Handoff

First slice:

- Add a read-first queue model and Chief of Staff triage view before adding live autonomous execution.
- Seed or derive queue items from approved Product Wizard stages and existing workflow items.
- Display state, owner, project, evidence, blocker, review owner, decision link, and external handoff metadata.
- Keep state-changing actions limited to manual dashboard actions until repository and route transition tests are in place.

Likely files or modules:

- `src/hermes_company_os/database.py` for `agent_work_items` or equivalent queue schema.
- `src/hermes_company_os/repository.py` for queue CRUD, filters, and transition validation.
- `src/hermes_company_os/main.py` for queue routes and action handlers.
- `src/hermes_company_os/templates/dashboard.html` or a new queue template for Chief of Staff triage.
- `src/hermes_company_os/templates/agent.html` for per-agent queue panel.
- `src/hermes_company_os/templates/project.html` for project queue strip.
- `src/hermes_company_os/static/styles.css` for dense table, status, responsive, and focus styles.

Tests to add:

- Repository tests for queue schema, default state, state transitions, invalid transitions, and owner validation.
- Route tests for queue list, per-agent queue, work item detail, block/unblock, reassign, review-needed, and founder decision handoff.
- Route tests that reject secret-like values in queue titles, blocker notes, review findings, decision contexts, and handoff notes.
- UI assertions that blocked work, review-needed work, and founder-gated work are visible and labeled.
- Product Wizard integration tests proving approved stages or workflow items create queue items only after the right approval gate.
- Kanban tests proving queue-to-Kanban handoff remains blocked until task-stage approval and Kanban verification are ready.
- Accessibility-focused checks for labels, button text, disabled-action explanation, and mobile row labels.

No-secret scan scope:

- New queue docs.
- Queue form text fields.
- Generated queue exports if added.
- Founder decision context created from queue handoffs.
- External handoff notes for Slack, Telegram, and Kanban.

Founder approval gate:

- Founder must approve queue autonomy boundaries, done-state policy, blocker escalation SLA, review policy by work type, and external handoff authority before source implementation exposes state-changing queue actions.
