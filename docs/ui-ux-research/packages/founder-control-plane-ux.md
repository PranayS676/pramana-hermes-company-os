# Founder Control Plane UX Research Package

## Package Metadata

- Package title: Founder Control Plane UX
- Research thread: Worker 1, Hermes Company OS UI/UX Research Batch 1
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
  - `src/hermes_company_os/founder_decisions.py`
  - `src/hermes_company_os/database.py`
  - `src/hermes_company_os/repository.py`
  - `src/hermes_company_os/main.py`
  - `src/hermes_company_os/templates/dashboard.html`
  - `src/hermes_company_os/templates/project.html`
  - `tests/test_founder_decisions.py`
  - `tests/test_app.py`
  - `tests/test_product_wizard_routes.py`
  - `tests/test_product_wizard_repository.py`
  - `tests/test_product_wizard_acceptance.py`
- Scope: Founder decision inbox, approvals, revisions, blockers, accepted risks, launch decisions, and audit trail for why decisions were made.
- Out of scope: Source code changes, live Hermes profile writes, AppData writes, credential handling, external Slack/Telegram/Kanban client implementation, and full Product Wizard UX beyond its control-plane handoff points.

## Research Question

How should Hermes Company OS present founder decisions, blockers, revisions, accepted risks, launch gates, and audit history so the founder can make high-trust operating decisions without allowing agents to silently advance irreversible work?

## Target Workflow

The founder enters the control plane from the dashboard, a project detail page, or a future `/decisions` inbox. The primary job is to triage what needs founder input, inspect the linked evidence, and resolve the decision with a clear action: approve, reject, request revision, answer an agent question, block work, accept risk, approve an external action, or approve/reject launch.

The expected outcome is a durable decision record linked to the project, stage, artifact, owner agent, evidence, and audit events that explain why work moved forward or stayed blocked.

The approval or review moment happens before:

- a wizard artifact becomes accepted source input;
- a revision request sends work back to an owner;
- a blocker is cleared;
- an external-risk action is allowed;
- a risk is accepted instead of fixed;
- a launch moves from readiness to release.

The exit state is either resolved with an explicit founder decision note, still blocked with a named missing input, deferred with a review reason, or rejected with next action guidance.

## User And Persona Assumptions

- Founder behavior: The founder will review decisions in short operating bursts and wants the highest-risk items first. Needs founder confirmation.
- Founder information density tolerance: The founder can tolerate a dense operational screen if grouping, labels, and evidence summaries are clear. Needs founder confirmation.
- Founder urgency model: Urgent means the work is blocked, launch is blocked, or a time-sensitive external action needs a decision. Needs founder confirmation.
- Agent behavior: Agents create decision requests with owner, source, evidence, recommended action, and forbidden actions.
- Reviewer behavior: QA Critic, Test Automation, Product Manager, and Engineering Manager may attach findings, but cannot resolve founder-only categories.
- Frequency of use: The inbox is expected to be a daily operating surface after live agent execution begins.
- Accepted-risk behavior: Accepted-risk decisions are rare and founder-only by default.
- Launch behavior: Launch decisions require tier-specific evidence and cannot be inferred from generated prose alone.

## Current-State Notes

The current implementation already has a limited founder decision queue:

- The dashboard renders a `Founder Decision Queue` section at `/#founder-decisions`.
- Setup exports exist at `/setup/founder-decisions.md` and `/setup/founder-decisions.json`.
- Manual decision creation uses title, owner, urgency, source, Slack channel, Telegram policy, and context.
- Decision updates support `needed`, `approved`, `rejected`, `blocked`, and `deferred`.
- Resolved decisions require a decision note.
- Secret-shaped values are rejected in decision text and update routes.

The current decision data model is still setup-oriented:

- `founder_decisions` stores title, status, urgency, source, owner agent, routing metadata, context, decision, and timestamps.
- It does not yet store project, stage, artifact, decision type, evidence, required approval flag, resolved timestamp, or resolution note.
- It does not yet separate setup decisions from project decisions in a central inbox.

The Product Wizard already creates founder-facing approval moments:

- Project detail supports staged generation, artifact preview, approve, regenerate, and revision request actions.
- Wizard stages use states such as `waiting`, `ready`, `draft`, `needs_revision`, `blocked`, and `approved`.
- Stage artifacts are versioned and can be marked `draft`, `approved`, or `needs_revision`.
- The project page shows a `Founder Readiness` panel and a limited list of founder decisions, but the decisions are not project-filtered or audit-linked.
- Kanban push is blocked until the tasks stage is approved and Kanban verification is ready.

Existing tests cover useful baseline behavior:

- Founder decision payload, exports, route creation, route updates, empty resolution rejection, and secret rejection.
- Product Wizard stage generation, approval, revision, artifact history, secret rejection, and Kanban gating.
- App-level routes for setup exports and decision queue visibility.

Major gaps remain for the Founder Control Plane milestone:

- No standalone `/decisions` inbox route.
- No filters by project, stage, decision type, owner agent, urgency, or resolved state.
- No linked evidence model for project decisions.
- No audit timeline showing who/what created the request, what changed, and why it was resolved.
- No founder-only enforcement for accepted risks, launch decisions, external-risk actions, or final artifact approval.

## Screens Needed

### Founder Decision Inbox

- Purpose: Centralize all open founder decisions, with urgent and blocked work first.
- Primary user: Founder.
- Primary action: Open a decision and resolve it.
- Secondary actions: Filter by project, owner agent, decision type, urgency, blocked state, launch tier, and resolved state.
- Empty state: Show "No open founder decisions" plus recent resolved decisions and a link back to active projects.
- Blocked state: Group blockers at the top and show which work cannot proceed.
- Failed state: Preserve entered text, show the validation error, and keep focus on the failed field.
- Success state: Decision moves to resolved or deferred list with timestamp, founder note, and next work state.

### Dashboard Summary Widget

- Purpose: Make the dashboard answer what needs founder input now.
- Primary user: Founder.
- Primary action: Jump to the most urgent open decision.
- Secondary actions: Open all decisions, open blocked projects, open launch-gate decisions.
- Empty state: Show zero open decisions and the next non-decision operating action.
- Blocked state: Show blocked project count and oldest blocker age.
- Failed state: If counts cannot load, show a non-blocking error and a retry affordance.
- Success state: Counts match the inbox and project detail surfaces.

### Decision Detail And Evidence View

- Purpose: Let the founder trust or challenge the recommendation before acting.
- Primary user: Founder.
- Primary action: Approve, reject, revise, answer, accept risk, block, or launch/reject launch.
- Secondary actions: View linked project, stage, artifact version, source inputs, owner agent, review findings, test evidence, and audit history.
- Empty state: If evidence is missing, show an evidence-missing state instead of an approval prompt.
- Blocked state: Disable irreversible actions until required evidence exists.
- Failed state: Show secret-boundary or invalid-transition errors inline.
- Success state: Show resolution note, resolver, timestamp, and resulting state transition.

### Project Decision Strip

- Purpose: Show decisions relevant to the active project and stage without forcing the founder to leave the project page.
- Primary user: Founder.
- Primary action: Open the current stage decision or unresolved blocker.
- Secondary actions: Request revision, inspect artifact history, open inbox filtered to project.
- Empty state: Show "No founder decision requested for this project" only when true for the active project.
- Blocked state: Show the exact decision blocking the next project action.
- Failed state: If linked decision lookup fails, show the project gate state and route to the full inbox.
- Success state: Decision status on the project page matches the central inbox.

### Revision Request Composer

- Purpose: Turn founder dissatisfaction into implementable revision work.
- Primary user: Founder.
- Primary action: Submit a structured revision request.
- Secondary actions: Select missing evidence, product change, quality bar, scope change, or review finding as the reason.
- Empty state: Placeholder prompts the founder to name missing evidence or the acceptance bar.
- Blocked state: If a stage is waiting or already founder-approved with no revision path, explain why revision is not allowed.
- Failed state: Reject secret-shaped text and preserve safe text.
- Success state: Stage becomes `needs_revision`, artifact history remains visible, and owner agent receives a clear revision brief.

### Blockers Board

- Purpose: Separate work that is truly blocked from routine decisions.
- Primary user: Founder and Chief of Staff.
- Primary action: Resolve the blocker or assign the missing input owner.
- Secondary actions: Group by project, owner agent, blocker age, and launch impact.
- Empty state: Show no blocked work and the next review surface.
- Blocked state: Show blocked work as the content, not as a generic empty or error state.
- Failed state: If blocker metadata is incomplete, show source and owner rather than hiding the blocker.
- Success state: Clearing a blocker records the reason and unblocks only the allowed downstream action.

### Accepted Risk Review

- Purpose: Make risk acceptance explicit, rare, scoped, and founder-only.
- Primary user: Founder.
- Primary action: Accept or reject the proposed risk.
- Secondary actions: Require fix instead, defer for review, assign mitigation, set review date.
- Empty state: No open accepted-risk requests.
- Blocked state: Disable "accept risk" until severity, owner, mitigation, scope, and expiration/review date are present.
- Failed state: Reject missing founder rationale or invalid risk scope.
- Success state: Risk is recorded with founder rationale, scope, owner, review date, and linked evidence.

### Launch Decision Gate

- Purpose: Prevent launch from being treated as a generic artifact approval.
- Primary user: Founder.
- Primary action: Approve or reject launch for a specific launch tier.
- Secondary actions: Review QA signoff, Test Automation evidence, release memo, rollback plan, unresolved risks, and marketing claims.
- Empty state: Show launch not ready until acceptance evidence exists.
- Blocked state: Show missing required checks by launch tier.
- Failed state: If launch decision save fails, keep launch blocked and show the reason.
- Success state: Launch decision records tier, evidence, founder rationale, and final go/no-go status.

### Audit Trail

- Purpose: Explain why work moved forward, who approved it, and what evidence supported it.
- Primary user: Founder, Chief of Staff, QA Critic, Engineering Manager.
- Primary action: Inspect chronological decision history.
- Secondary actions: Filter to artifact, stage, project, owner, risk, launch, or external action.
- Empty state: Show that no audit events exist yet for the selected scope.
- Blocked state: If audit history is incomplete for an irreversible action, block the action.
- Failed state: Show partial timeline with clear missing-event warning.
- Success state: Every state-changing decision has a timestamped audit event and linked source.

## State Model

| Label | Meaning | Owner | Allowed actions | Forbidden actions | Evidence required |
| --- | --- | --- | --- | --- | --- |
| `needed` | Founder input is required before work can safely advance. | Requesting agent or Chief of Staff. | Open, answer, approve, reject, defer, request revision, block. | Silent agent resolution for founder-only types. | Context, owner agent, source, recommended action. |
| `urgent` | Urgency overlay for blocked, launch-critical, or time-sensitive decisions. | Chief of Staff or requesting agent. | Escalate, open, resolve, downgrade with reason. | Hiding behind filters or routine ordering. | Reason urgency is justified and what is blocked. |
| `blocked` | Work cannot proceed until a founder answer or missing input exists. | Chief of Staff, owner agent, or system gate. | Resolve blocker, assign owner, request evidence, reject work. | Advancing affected stage, external action, or launch. | Blocked work, blocked action, owner, unblock condition. |
| `evidence_missing` | A decision request exists but lacks proof needed for approval. | Requesting agent. | Request evidence, defer, reject, block. | Approve, launch, accept risk. | Missing evidence checklist by decision type. |
| `draft_ready_for_review` | Artifact or recommendation is ready for founder review. | Owner agent. | Approve, request revision, reject, ask question. | Treat as final accepted source without founder action. | Artifact version, source inputs, acceptance criteria. |
| `revision_requested` | Founder has asked for changes before approval. | Founder and owner agent. | Regenerate, update artifact, inspect revision history. | Mark approved without new review. | Revision request, target artifact/stage, acceptance bar. |
| `risk_acceptance_requested` | Agent or reviewer proposes accepting a known risk. | QA Critic, Engineering Manager, Product Manager, or owner agent. | Founder accept, founder reject, require fix, defer. | Agent resolution, launch without founder rationale. | Severity, impact, mitigation, owner, scope, review date. |
| `risk_accepted` | Founder accepted a scoped risk with rationale. | Founder. | Review, expire, reopen, include in launch evidence. | Treat as permanent or global without scope. | Founder rationale, scope, owner, review date, linked finding. |
| `approved` | Founder approved the requested action. | Founder for founder-only types; agent only for explicitly delegated routine types. | Advance allowed downstream work and write audit event. | Reuse approval outside its scope. | Decision note, linked evidence, timestamp, resolver. |
| `rejected` | Founder rejected the request. | Founder. | Record rationale, return work to owner, close request. | Proceed with rejected action. | Rejection reason and next action. |
| `deferred` | Founder postponed the decision with a reason. | Founder. | Set review date or owner follow-up. | Treat as approved or unblocked. | Deferral reason and next review trigger. |
| `launch_ready` | Launch packet has enough evidence to request founder go/no-go. | QA Critic, Test Automation, Product Manager, Engineering Manager. | Founder approve launch, reject launch, request fixes. | Launch without founder decision. | Tier, checks, QA signoff, tests, rollback, risk list, claims. |
| `launch_approved` | Founder approved launch for a specific tier. | Founder. | Execute launch handoff for that tier and audit it. | Reuse for a higher tier without new approval. | Launch memo, final checks, founder rationale, timestamp. |
| `save_failed` | UI could not persist the requested decision transition. | System. | Retry, edit safe text, cancel. | Assume decision was recorded. | Error reason and preserved non-secret form data. |

## UX Risks And Anti-Patterns

- Mixing setup decisions and project decisions without filters, making project blockers hard to find.
- Showing "ready" without saying ready for what, who owns it, and what evidence exists.
- Letting agents resolve accepted-risk, launch, external-action, or final approval decisions.
- Treating generated artifact prose as proof instead of showing sources, tests, findings, and acceptance criteria.
- Burying blocked work under optimistic dashboard summaries.
- Using hover-only evidence previews or icon-only status without accessible labels.
- Allowing one-line revision requests that do not specify missing evidence or the target acceptance bar.
- Recording accepted risks without severity, scope, owner, mitigation, review date, and founder rationale.
- Making launch a generic approval button instead of a tiered go/no-go process.
- Hiding failed saves or validation errors after a founder submits a decision.
- Adding decorative dashboards that look polished but cannot explain why work moved forward.
- Providing credential or raw-token text fields inside decision, evidence, or audit surfaces.

## Accessibility And Responsive Notes

- Keyboard behavior: Inbox filters, decision rows, action buttons, tabs, drawers, and modals must be reachable and operable by keyboard.
- Focus management: Opening a decision detail view should move focus to the heading; saving or failing should move focus to the confirmation or error summary.
- Labels and semantics: Decision type, status, urgency, owner, project, stage, and action buttons need explicit labels, not only icons or colors.
- Contrast and status color: Status color must be paired with text labels and meet readable contrast in dense rows.
- Mobile layout: The mobile first view should show urgent count, blocked count, decision title, project, owner, and primary action before secondary metadata.
- Long text handling: Evidence, revision notes, artifact excerpts, and decision rationales need wrapping, truncation controls, and detail expansion without horizontal overflow.
- Form errors: Secret-boundary and invalid-transition errors should remain near the field and in a top error summary.
- Motion constraints: Any live update or count animation should be subtle and should not move focused controls.
- Touch targets: Inbox actions and row expansion controls should remain large enough on tablet and phone layouts.

## Implementation Recommendations

| Recommendation | Behavior | Affected surface | Likely data needed | Acceptance signal |
| --- | --- | --- | --- | --- |
| Add a standalone decision inbox | Create `/decisions` as the primary founder triage surface with open decisions first. | Routes, template, dashboard navigation. | Decision status, urgency, type, project, owner, created/updated timestamps. | Founder can filter and open all open decisions outside the dashboard anchor. |
| Extend decision records | Link decisions to project, stage, artifact, owner, evidence, and required approval category. | Database, repository, route validation. | `project_id`, `stage_id`, `artifact_id`, `decision_type`, `evidence`, `requires_founder_approval`, `resolved_at`, `resolution_note`. | Existing setup decisions still render and project decisions have links. |
| Add decision-type controls | Present action sets based on decision type. | Inbox detail, forms, route validation. | Decision type enum and allowed transitions. | Artifact approval, revision, blocker, accepted risk, external action, and launch each show appropriate actions. |
| Make accepted risk founder-only | Require founder resolution note, scope, owner, mitigation, and review date before accepting risk. | Accepted Risk Review, repository validation. | Severity, scope, owner, mitigation, review date, linked finding. | Agents can propose risk acceptance but cannot resolve it. |
| Make launch a distinct gate | Separate launch approval from artifact approval and acceptance checklist approval. | Launch Decision Gate, project page, inbox. | Launch tier, required checks, QA signoff, test evidence, rollback plan, release memo. | Launch cannot be approved without tier-specific evidence and founder note. |
| Add structured revision composer | Ask for missing evidence, requested change, acceptance bar, and owner impact. | Project page and decision detail. | Revision reason, notes, target artifact/stage. | Revision requests become specific enough for an agent to act without guessing. |
| Group blockers by impact | Prioritize blocked launch, blocked external action, blocked project stage, then routine blockers. | Inbox, dashboard summary, blockers board. | Blocked action, project/stage, owner, blocker age, urgency. | Founder can identify the highest-impact blocker in one scan. |
| Add audit trail timeline | Record creation, evidence changes, approvals, rejections, revisions, risk acceptance, launch decisions, and external handoffs. | Decision detail, project detail, export. | Audit event type, actor, source, linked entity, timestamp, before/after state. | Every irreversible action has a visible audit event. |
| Add dashboard counts | Show open decisions, urgent decisions, blocked projects, and next founder action. | Dashboard summary widget. | Aggregated decision counts and blocker counts. | Dashboard counts match inbox query results. |
| Preserve the no-secret boundary | Keep credential warnings, validation, and tests for all decision, evidence, revision, and audit text. | All forms and exports. | Secret guard validation for stored text fields. | Secret-shaped values are rejected and not persisted. |

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

### Decision Categories

- Decision: Confirm the first supported decision categories: artifact approval, revision request, agent question, blocker, accepted risk, external action approval, and launch decision.
- Why it matters: Data model, route validation, action labels, and tests depend on a stable category list.
- Default recommendation: Use the categories from the Founder Control Plane implementation plan.
- Impact if deferred: The inbox can be built only as a generic queue, which weakens filtering and transition rules.

### Founder-Only Resolution Rules

- Decision: Confirm which decisions agents may propose but never resolve.
- Why it matters: Autonomy boundaries must be clear before live agents create or act on decisions.
- Default recommendation: Founder-only resolution for launch, accepted risk, external-risk action, and final artifact approval decisions.
- Impact if deferred: Implementation cannot safely enforce irreversible-action boundaries.

### Urgency And Escalation

- Decision: Confirm whether `routine` and `urgent` are enough for the first slice, or whether a separate `blocked` urgency should exist.
- Why it matters: Inbox ordering, dashboard counts, and Telegram policy depend on urgency semantics.
- Default recommendation: Keep `routine` and `urgent`; derive blocked grouping from status and blocked action.
- Impact if deferred: The UI may overuse urgency labels or hide blockers behind routine decisions.

### Required Evidence By Decision Type

- Decision: Confirm minimum evidence for artifact approval, blocker resolution, accepted risk, external action, and launch.
- Why it matters: The UI should disable unsafe actions until evidence exists.
- Default recommendation: Require linked project/stage/artifact or finding, owner agent, recommendation, source inputs, and acceptance criteria; require QA/test/rollback evidence for launch.
- Impact if deferred: Approvals may remain subjective and hard to audit.

### Revision Request Structure

- Decision: Confirm whether revision requests must capture missing evidence, requested change, acceptance bar, and owner.
- Why it matters: Agents need clear revision instructions instead of vague feedback.
- Default recommendation: Use structured revision fields in the decision detail and project stage forms.
- Impact if deferred: Revision loops may produce new drafts that do not address the founder's concern.

### Accepted Risk Metadata

- Decision: Confirm required metadata for accepted risks.
- Why it matters: Accepted risk should be scoped, reviewable, and auditable.
- Default recommendation: Require severity, scope, owner, mitigation, founder rationale, and review date.
- Impact if deferred: Accepted risks can become permanent hidden exceptions.

### Launch Tiers

- Decision: Confirm launch tier labels and minimum checks per tier.
- Why it matters: Launch approval needs a tier-specific gate rather than one generic approval.
- Default recommendation: Use the existing tier language: `T0 Internal Experiment`, `T1 Private Beta`, `T2 Public Beta`, and `T3 GA`.
- Impact if deferred: Launch UI cannot know which evidence is required before go/no-go.

### Audit Retention And Export

- Decision: Confirm the minimum audit history required before live execution is trusted.
- Why it matters: Founder trust depends on reconstructing why work moved forward.
- Default recommendation: Keep project-level audit history for decision creation, evidence changes, approval/rejection, revision, blocker transitions, risk acceptance, launch, and external handoffs.
- Impact if deferred: The system may be able to act but not explain itself.

## Implementation Handoff

- First slice: Build a standalone founder decision inbox with filters, linked decision detail, project/stage/artifact fields, decision type, evidence summary, and founder-only enforcement for accepted risk and launch categories.
- Likely files or modules:
  - `src/hermes_company_os/database.py`
  - `src/hermes_company_os/repository.py`
  - `src/hermes_company_os/main.py`
  - `src/hermes_company_os/founder_decisions.py`
  - `src/hermes_company_os/templates/dashboard.html`
  - `src/hermes_company_os/templates/project.html`
  - future `src/hermes_company_os/templates/decisions.html`
  - `src/hermes_company_os/static/styles.css`
- Tests to add:
  - Repository tests for new decision fields, filters, and transition rules.
  - Route tests for `/decisions`, decision detail, filters, create, update, resolve, reject, defer, and invalid transition paths.
  - Product Wizard route tests proving artifact approval and revision requests create or update audit-linked decisions.
  - Secret guard tests for decision context, evidence, revision request, accepted-risk rationale, and launch rationale.
  - UI assertions for open decision count, urgent ordering, blocker grouping, founder-only labels, and disabled unsafe actions.
  - Regression test that existing setup decisions still render and export.
- No-secret scan scope:
  - New docs under `docs/ui-ux-research/`.
  - Decision exports.
  - Generated decision pages.
  - Project artifacts and public-demo outputs touched by the implementation.
- Founder approval gate:
  - Founder approves decision categories, urgency semantics, founder-only resolution rules, accepted-risk metadata, launch-tier checks, and audit minimums before source implementation begins.

This package is a research artifact only. It is not authoritative until central integration reviews it and the founder approves the integrated implementation plan.
