# Agentic Company OS Roadmap

This document defines the path from the current Product Wizard foundation to a founder-led, multi-agent company operating system. The goal is not to promise a mythical 100 percent autonomous company. The goal is to build a practical system where specialized AI agents can plan, execute, review, escalate, and ship with the founder retaining final control over irreversible decisions.

## Current State

Hermes Company OS is currently about 35-40 percent of the full agentic-company vision.

What is real now:

- Founder dashboard with Hermes profile doctrine, setup gates, and generated no-secret profile assets.
- Product Wizard V1 for structured intake and staged artifacts:
  - research brief;
  - PRD;
  - architecture;
  - tasks;
  - code plan;
  - acceptance checklist.
- One-stage-at-a-time founder approval.
- Draft, approve, revise, and regenerate mechanics for wizard artifacts.
- Kanban push blocked until the task stage is approved.
- Local public-demo generation that does not require live credentials.
- Test coverage for generator, repository, routes, UI-facing acceptance flow, secret guards, and full app regression.

What is not real yet:

- Product Wizard generation does not call live Hermes profiles.
- Agents do not independently pick up work from queues.
- Approved code plans do not spawn Codex implementation workstreams.
- There is no durable cross-project company memory beyond persisted dashboard records.
- Slack, Telegram, Kanban, Hermes, GitHub, and Codex are not yet unified into a live execution loop.
- QA Critic and Test Automation do not yet automatically challenge every agent output before founder approval.
- There is no live run observability layer for cost, latency, failures, retries, or blocked work.

## Target State

The target system is a founder-led AI company OS:

- Founder enters an idea and approves staged decisions.
- Chief of Staff manages priorities, decisions, blockers, escalation, and operating cadence.
- Product Manager turns founder intent into scoped PRDs.
- Research Agent validates market, user, competitor, and evidence quality.
- Engineering Manager decomposes approved plans into executable work.
- Backend, Frontend, and Cloud Infrastructure agents execute implementation plans.
- Test Automation builds repeatable validation coverage.
- QA Critic challenges gaps, risks, contradictions, and launch readiness.
- Marketing Agent prepares positioning only after product claims are evidence-backed.
- Hermes Kanban is the operating truth.
- Slack is routine coordination.
- Telegram is founder urgency only.
- GitHub stores source, branches, commits, pull requests, and release history.
- Codex workstreams implement code with tests and reviewable diffs.

The practical target is 80-90 percent operational maturity. The last 10-20 percent will always require human judgment, product taste, customer feedback, legal/security review, and founder decisions.

## Operating Principles

- Founder control remains explicit. Agents may propose and execute reversible work, but founder approval gates protect major scope, launch, spending, public claims, and production-risk decisions.
- Local/public-demo mode stays separate from live mode. Demo safety must not depend on real credentials.
- Live credentials stay outside the dashboard. The dashboard tracks only status and non-secret evidence.
- Every agent output must have an owner, source inputs, acceptance criteria, and next decision.
- Plans should become tasks only after approval. Tasks should become code only after acceptance criteria are clear.
- Automation should be observable. No invisible autonomous work.
- The system should degrade safely. Failed agents should create blockers, not silently continue.

## Roadmap Overview

### Milestone 0: Preserve The Product Wizard Baseline

Status: complete for V1 implementation.

Purpose:

- Keep the current safe Product Wizard as the baseline branch.
- Ensure the repo has a clean public demo checkpoint before live-agent wiring begins.

Deliverables:

- Product Wizard V1 committed and pushed.
- Full test suite green.
- No-secret scan green.
- Public-demo mode documented.

Acceptance:

- Founder can open `/projects/new`, create a product workflow, generate each stage, approve or revise artifacts, and see Kanban blocked until tasks are approved.

### Milestone 1: Founder Control Plane

Purpose:

Turn scattered approvals, blockers, and decisions into one founder operating surface.

Deliverables:

- Founder Decision Inbox page.
- Decision types:
  - approve artifact;
  - request revision;
  - answer agent question;
  - approve external-risk action;
  - accept risk;
  - block project;
  - launch or reject launch.
- Decision records linked to project, stage, artifact, owner agent, and evidence.
- Dashboard count of waiting founder decisions.
- Route tests for decision creation, resolution, filtering, and secret rejection.

Implementation slices:

1. Add decision schema extensions for project/stage/artifact references.
2. Add repository APIs for open/resolved founder decisions.
3. Add inbox UI.
4. Add wizard integration so revise/approve actions create audit-linked decisions.
5. Add tests and no-secret route scan.

Founder approval gate:

- Founder confirms the decision categories and which actions require explicit approval.

### Milestone 2: Agent Work Queue

Purpose:

Give every profile an operating queue so work can move from planned to assigned to running to blocked to review.

Deliverables:

- `agent_work_items` or equivalent queue model.
- Queue states:
  - planned;
  - assigned;
  - running;
  - blocked;
  - needs_review;
  - approved;
  - rejected;
  - done.
- Work items linked to projects, wizard stages, artifacts, tasks, documents, and run records.
- Agent detail page showing queue.
- Founder and Chief of Staff queue views.
- Tests for state transitions and invalid transitions.

Implementation slices:

1. Add queue schema and seed default lanes.
2. Convert approved wizard artifacts into agent work items.
3. Add queue UI to agent pages.
4. Add Chief of Staff triage view.
5. Add transition tests and route tests.

Founder approval gate:

- Founder approves the queue states and which agents may move work without explicit founder input.

### Milestone 3: Live Hermes Profile Execution

Purpose:

Replace local fake generation with optional live Hermes execution while preserving safe public-demo mode.

Deliverables:

- Generation mode selector:
  - local demo;
  - live Hermes draft;
  - live Hermes with review.
- Stage-to-profile routing:
  - research -> Research Agent;
  - PRD -> Product Manager;
  - architecture/tasks -> Engineering Manager;
  - code plan -> Backend/Frontend/Cloud as needed;
  - acceptance -> QA Critic and Test Automation.
- Prompt contracts for each wizard stage.
- Run records linked to generated artifacts.
- Timeout, error, retry, and blocked-state handling.
- Tests using fake Hermes clients.

Implementation slices:

1. Define stage prompt contracts and output parsing rules.
2. Add a generation service interface.
3. Keep local fake generator as one implementation.
4. Add Hermes-backed implementation using existing profile command execution.
5. Add route switch guarded by readiness checks.
6. Add route and repository tests.

Founder approval gate:

- Founder approves when to turn on live generation for each stage.

### Milestone 4: Company Memory Layer

Purpose:

Make the company remember founder preferences, product strategy, reusable architecture choices, accepted risks, and previous decisions.

Deliverables:

- Memory records with type, owner, source, project scope, confidence, and expiration/review date.
- Memory categories:
  - founder preferences;
  - product strategy;
  - technical standards;
  - accepted risks;
  - rejected ideas;
  - launch learnings;
  - customer evidence.
- Memory retrieval for wizard prompts and live Hermes prompts.
- Founder controls for pinning, revising, or retiring memory.
- Tests for memory creation, retrieval, redaction, and stale-memory handling.

Implementation slices:

1. Add memory schema.
2. Add memory CRUD repository APIs.
3. Add memory UI.
4. Inject approved memory into local wizard generation.
5. Inject approved memory into live Hermes prompt contracts.
6. Add no-secret and stale-memory tests.

Founder approval gate:

- Founder approves which memory categories agents may reuse automatically.

### Milestone 5: Codex Project Execution Mode

Purpose:

After an approved code plan, start real implementation workstreams.

Deliverables:

- Project execution screen.
- Code plan to task decomposition.
- GitHub repo/branch/project mapping.
- Codex workstream plan:
  - backend;
  - frontend;
  - tests;
  - docs;
  - infrastructure;
  - QA review.
- Workstream status:
  - not started;
  - running;
  - blocked;
  - needs review;
  - merged/done.
- Test commands recorded per workstream.
- Diff summary and pull request readiness output.

Implementation slices:

1. Add project execution data model.
2. Convert approved tasks/code plan into executable work packages.
3. Add workstream creation UI and API.
4. Add Codex handoff package generator.
5. Add GitHub branch/PR metadata tracking.
6. Add tests around package generation and state transitions.

Founder approval gate:

- Founder approves creation of real code branches or new repos.

### Milestone 6: Cross-Agent Review Loop

Purpose:

Prevent polished but weak plans or code from moving forward without critique.

Deliverables:

- Required review policies by stage.
- QA Critic review required before acceptance approval.
- Test Automation review required before launch readiness.
- Product Manager review required before major scope changes.
- Engineering Manager review required before implementation starts.
- Review artifact model:
  - finding;
  - severity;
  - owner;
  - evidence;
  - required fix;
  - accepted risk;
  - founder decision needed.
- Tests for blocked approvals when required reviews are missing.

Implementation slices:

1. Add review policy definitions.
2. Add review artifact schema.
3. Add required-review checks to stage approval.
4. Add review UI.
5. Add fake review generation for demo mode.
6. Add live Hermes review mode later.

Founder approval gate:

- Founder approves which review findings can be accepted as risk versus must-fix.

### Milestone 7: Slack, Telegram, And Kanban Operating Loop

Purpose:

Move from dashboard-only operations to live company coordination.

Deliverables:

- Slack event/update policy:
  - routine updates;
  - standups;
  - blocker summaries;
  - review summaries.
- Telegram urgent policy:
  - blocked launch;
  - production incident;
  - founder decision SLA exceeded;
  - credential/runtime failure.
- Kanban sync:
  - create task;
  - update status;
  - attach evidence;
  - link artifact;
  - mark blocker.
- Idempotency keys to prevent duplicate external tasks/messages.
- Tests using fake clients.

Implementation slices:

1. Add outbound notification event model.
2. Add fake Slack/Telegram/Kanban clients for tests.
3. Add real client adapters behind readiness gates.
4. Add idempotent delivery records.
5. Add dashboard view for sent/failed notifications.

Founder approval gate:

- Founder approves exactly what can trigger Telegram.

### Milestone 8: Observability And Audit

Purpose:

Make autonomous behavior inspectable and debuggable.

Deliverables:

- Run dashboard across all agents.
- Metrics:
  - runs by agent;
  - success/failure;
  - blocked count;
  - average latency;
  - retry count;
  - open founder decisions;
  - open review findings.
- Audit trail:
  - who/what created an artifact;
  - source inputs used;
  - generated output;
  - approvals;
  - revisions;
  - external messages/tasks created.
- Exportable project record.
- Tests for audit integrity.

Implementation slices:

1. Normalize run records for wizard and agent work.
2. Add audit event table.
3. Emit audit events from every state-changing route.
4. Add dashboard metrics.
5. Add export route.
6. Add tests for audit completeness.

Founder approval gate:

- Founder approves the minimum audit history needed before live execution is trusted.

### Milestone 9: Launch And Release Management

Purpose:

Make launch readiness an explicit operating process rather than a final checklist document.

Deliverables:

- Launch gate model:
  - internal experiment;
  - private beta;
  - public beta;
  - general availability.
- Required checks by launch tier.
- Release notes and founder launch memo.
- Rollback plan artifact.
- Marketing claim review.
- QA signoff.
- Founder launch approval.

Implementation slices:

1. Add launch tier policy data.
2. Link acceptance checklist to launch gate.
3. Add release memo generator.
4. Add launch approval route.
5. Add launch evidence export.
6. Add tests for tier-specific gates.

Founder approval gate:

- Founder approves launch tier policy and final launch action.

## Suggested Build Order

The safest sequence is:

1. Founder Control Plane.
2. Agent Work Queue.
3. Live Hermes Profile Execution.
4. Company Memory Layer.
5. Codex Project Execution Mode.
6. Cross-Agent Review Loop.
7. Slack/Telegram/Kanban Operating Loop.
8. Observability And Audit.
9. Launch And Release Management.

This order keeps the system founder-safe before making it more autonomous.

## Parallel Workstreams

Use parallel Codex threads only after each milestone has a stable contract.

Recommended parallelization pattern:

- Backend/data thread: schema, repository APIs, migrations, tests.
- Agent orchestration thread: prompts, generation services, fake/live adapters.
- UI thread: founder surfaces, queue views, review pages, status dashboards.
- QA thread: acceptance tests, route tests, no-secret scans, regression suite.
- Documentation thread: operating model, setup docs, demo script, founder guide.

Central integration should remain one thread at the end of each milestone.

## Testing Standards

Every milestone should include:

- Repository tests for schema and state transitions.
- Route tests for success, blocked, missing project, and invalid transition paths.
- Secret guard tests for every stored text field and generated artifact.
- Fake-client tests for live integrations.
- UI route assertions for founder-visible gates.
- Full `pytest` before merging.
- Full `ruff check .` before merging.
- No-secret scan over generated docs, profile assets, project artifacts, and public-demo outputs.

For live integrations, tests should use fake clients by default. Real Hermes, Slack, Telegram, GitHub, or Kanban calls should be explicit manual/live validation steps, never required for the normal unit test suite.

## Definition Of Mature Enough

The system is mature enough for serious founder-led usage when:

- A founder can enter an idea and approve research, PRD, architecture, tasks, code plan, and acceptance.
- Approved tasks create agent work items.
- Agents can run live through Hermes or stay in local demo mode.
- Founder decisions and blockers are centralized.
- Agent memory is reusable and reviewable.
- Approved code plans can spawn Codex workstreams.
- QA and Test Automation can block launch.
- Slack/Kanban sync is idempotent and observable.
- Telegram is reserved for urgent founder escalation.
- Every major action leaves an audit trail.
- The system can explain why work moved forward, who approved it, and what evidence supported it.

## Immediate Next Step

Build Milestone 1: Founder Control Plane.

First implementation package:

1. Extend founder decision records with optional `project_id`, `stage_id`, `artifact_id`, `decision_type`, and `requires_founder_approval`.
2. Add repository APIs for open and resolved project decisions.
3. Add `/decisions` inbox route and founder dashboard summary.
4. Wire Product Wizard approve/revise actions into decision audit records.
5. Add route, repository, UI, and no-secret tests.

This is the right next step because more autonomy without a stronger founder control plane would make the system harder to trust.
