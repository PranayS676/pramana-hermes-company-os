# UI/UX Research Batch 1 Integration

This document integrates the first four UI/UX research packages into one implementation-ready direction for Hermes Company OS.

Batch 1 packages:

- `packages/founder-control-plane-ux.md`
- `packages/product-wizard-ux.md`
- `packages/agent-work-queue-ux.md`
- `packages/accessibility-responsive-ux.md`

## Integrated Recommendation

Build the Founder Control Plane as the next source milestone, but do it with the Batch 1 UX findings baked into the acceptance criteria.

The first implementation should not be a generic decision table. It should become the founder operating surface that links:

- founder decisions;
- project stages;
- Product Wizard artifacts;
- blockers;
- revision requests;
- accepted-risk requests;
- launch gates;
- future agent queue items;
- audit evidence.

The dashboard remains the operating source of truth. Slack, Telegram, Kanban, and future Codex workstreams should be displayed as secondary handoff signals until their own live integration milestones are implemented and audited.

## Synthesis

### Founder Control Plane

The current dashboard has a setup-oriented Founder Decision Queue and routes for creating and resolving decisions, but it does not yet provide a project-aware inbox. The new control plane should prioritize urgent blockers, launch decisions, accepted-risk requests, and artifact approvals. It should also explain why a decision exists, what work is blocked, who owns the next action, and what evidence supports approval.

Key integrated rule:

- Accepted-risk, launch, external-action, and final artifact approvals are founder-only by default.

### Product Wizard

The current Product Wizard is a strong safe baseline: structured intake, staged artifacts, local public-demo generation, approval and revision flow, artifact history, and Kanban gating. The next UX improvement is not a cosmetic redesign. It is a stronger review workspace:

- artifact metadata visible before approval;
- generation mode and owner visible;
- source artifacts and quality checks visible;
- structured revision reasons;
- inspectable artifact history;
- clear handoff gates before Kanban or future Codex execution.

Key integrated rule:

- Codex execution should require approved code plan, approved acceptance package, and a separate founder execution approval before real branches or workstreams are created.

### Agent Work Queue

The agent queue should start as a read-first operating model, not autonomous execution. Chief of Staff triage is the cross-agent control surface. Per-agent queues are execution detail surfaces. Founder approval handoffs remain decision records, not hidden queue state changes.

Key integrated rule:

- Agents may move work through execution states, and Chief of Staff may triage, reassign, and block. Founder approval is required for approvals, rejections, accepted risk, launch, external actions, and irreversible scope changes.

### Accessibility And Responsive UX

Accessibility is part of operating safety because the founder is approving generated work and external handoffs. The next source implementation should establish a baseline before adding more UI-heavy surfaces.

Key integrated rule:

- Use WCAG 2.2 Level AA as the default standard for founder-facing UI, plus Hermes-specific checks for visible focus, no hidden blockers, no color-only status, and no generated-text overflow.

## Resolved Decisions

These defaults are now accepted for implementation planning unless the founder overrides them:

- Dashboard remains the operating source of truth.
- Slack, Telegram, Kanban, and Codex are secondary handoff signals until live integration milestones.
- Accepted risk is founder-only.
- Launch decision is founder-only.
- External-risk action approval is founder-only.
- Final artifact approval is founder-only unless a later policy delegates a low-risk category.
- `needs_review` is distinct from `approved`.
- Blocked work must show blocker owner, age, and required action.
- Product Wizard history should become inspectable before it becomes a full diff tool.
- Accessibility and responsive checks are acceptance criteria, not polish.

## Open Founder Decisions

These decisions should be answered before the next source implementation begins:

1. Decision categories
   - Default: artifact approval, revision request, agent question, blocker, accepted risk, external action approval, launch decision.

2. Codex execution gate
   - Default: approved `code_plan`, approved `acceptance`, and separate founder execution approval before real branches or workstreams.

3. Mobile scope
   - Default: mobile supports review and urgent decision triage now; full mobile workflow completion becomes required after the first responsive acceptance pass.

4. Accessibility baseline
   - Default: WCAG 2.2 Level AA plus Hermes-specific checks.

5. Queue autonomy boundary
   - Default: agents can move execution states; Chief of Staff can triage, reassign, and block; founder owns irreversible decisions.

6. Blocker escalation SLA
   - Default: Telegram only for blocked launch, production incident, founder decision SLA exceeded, credential/runtime failure, or work blocked on founder decision after an approved age.

7. Artifact comparison depth
   - Default: start with selectable version inspection and metadata delta; defer full diff highlighting.

8. Accepted-risk metadata
   - Default: severity, scope, owner, mitigation, founder rationale, linked evidence, and review date.

## Implementation Backlog

### Slice 1: Founder Inbox Foundation

Objective:

- Create a standalone founder decision inbox and project-aware decision detail model.

Capabilities:

- `/decisions` inbox.
- Open decisions first.
- Filters by project, urgency, decision type, owner, and status.
- Decision detail with linked project, stage, artifact, evidence, owner, and audit context.
- Founder-only enforcement for accepted risk, launch, external action, and final artifact approvals.

Acceptance:

- Existing setup decisions still render.
- Project decisions can link to project/stage/artifact.
- Secret-like decision text is rejected.
- Open and urgent counts match dashboard.
- Blocked work appears before routine decisions.

### Slice 2: Product Wizard Review Workspace

Objective:

- Make Product Wizard approval safer before live Hermes generation or Codex execution.

Capabilities:

- Stage decision summary block.
- Artifact owner, generation mode, next decision, source artifacts, and quality checks visible.
- Structured revision reason categories.
- Artifact history supports selecting and inspecting versions.
- Kanban and future Codex gates explain missing prerequisites.

Acceptance:

- Founder can see why an artifact is ready or not ready.
- Revision notes are actionable and stage-linked.
- History shows version, status, owner, and revision context.
- Codex execution copy remains disabled and explicitly future-gated.

### Slice 3: Read-First Agent Queue Model

Objective:

- Prepare the agent queue without increasing autonomy prematurely.

Capabilities:

- Queue state vocabulary: `planned`, `assigned`, `running`, `blocked`, `needs_review`, `approved`, `rejected`, `done`.
- Chief of Staff triage concept.
- Per-agent queue concept.
- Founder decision handoff for irreversible actions.
- Slack, Telegram, and Kanban handoff metadata as secondary status.

Acceptance:

- Queue docs and UI labels distinguish `needs_review` from `approved`.
- Blocked items show owner, age, blocked action, and required founder decision.
- No external handoff is treated as source of truth.

### Slice 4: Accessibility Baseline

Objective:

- Establish UI safety checks before adding more dense founder surfaces.

Capabilities:

- Global visible focus standard.
- Wizard step semantics and focus movement.
- Accessible names for repeated row controls.
- Status labels and non-color signals.
- Long generated text fixtures.
- Responsive workflow checks for dashboard, wizard, project detail, and future inbox.

Acceptance:

- Keyboard path works for critical founder flows.
- Blocker copy is reachable before or adjacent to disabled actions.
- Long generated content does not cause horizontal overflow.
- Status meaning is not color-only.

## Recommended Build Order

1. Founder Inbox Foundation.
2. Accessibility Baseline for existing screens.
3. Product Wizard Review Workspace improvements.
4. Read-first Agent Queue Model.
5. Central integration update and founder approval before live Hermes or Codex execution.

This order keeps founder trust ahead of autonomy.

## Test Strategy

Documentation verification:

- no-secret scan over UI/UX docs;
- docs tests;
- path checks for package and integration docs.

Source implementation verification for the next milestone:

- repository tests for decision fields, filters, and transition rules;
- route tests for inbox, decision detail, create/update/resolve, invalid transitions, and secret rejection;
- Product Wizard route tests for visible metadata, structured revision, artifact history, and gate reasons;
- UI assertions for founder-only labels, blocked reasons, open decision counts, and accessible names;
- browser or DOM checks for keyboard path, focus-visible behavior, long content, and mobile overflow;
- full `pytest` after schema, route, or template changes;
- no-secret scan over generated pages, exports, profile assets, and project artifacts.

## Central Integration Acceptance

- [x] All four assigned research packages exist.
- [x] Founder Control Plane findings are integrated.
- [x] Product Wizard findings are integrated.
- [x] Agent Work Queue findings are integrated.
- [x] Accessibility and responsive findings are integrated.
- [x] Conflicts are resolved into defaults or founder decisions.
- [x] First implementation backlog is ordered.
- [x] No live Hermes or AppData state is touched.
- [x] No credentials or secret-looking values are included.

## Next Goal

Recommended next goal:

`Implement Founder Control Plane Slice 1 with Batch 1 UX acceptance criteria.`

That goal should remain source-focused and should not enable live Hermes execution. It should implement the decision inbox foundation, project-aware decision records, and founder-only transition rules first.
