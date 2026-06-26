# Product Wizard UX Research Package

## Package Metadata

- Package title: Product Wizard UX
- Research thread: Worker 2, Hermes Company OS UI/UX Research Batch 1
- Owner: UI/UX Research Agent research thread
- Date: 2026-06-26
- Source docs reviewed:
  - `docs/agentic-company-os-roadmap.md`
  - `docs/ui-ux-research/01-ui-ux-research-agent-doctrine.md`
  - `docs/ui-ux-research/02-codex-subagent-research-operating-model.md`
  - `docs/ui-ux-research/03-ui-ux-research-thread-prompts.md`
  - `docs/ui-ux-research/04-research-package-template.md`
  - `docs/ui-ux-research/packages/README.md`
- Current implementation areas inspected:
  - `src/hermes_company_os/templates/project_new.html`
  - `src/hermes_company_os/templates/project.html`
  - `src/hermes_company_os/main.py`
  - `src/hermes_company_os/product_wizard.py`
  - `src/hermes_company_os/idea_intake.py`
  - `src/hermes_company_os/repository.py`
  - `src/hermes_company_os/database.py`
  - `src/hermes_company_os/seeds.py`
  - `tests/test_product_wizard_generation.py`
  - `tests/test_product_wizard_repository.py`
  - `tests/test_product_wizard_routes.py`
  - `tests/test_product_wizard_acceptance.py`
  - `tests/test_idea_intake.py`
- Scope: Founder-facing Product Wizard UX for idea intake, stage timeline, artifact preview, artifact history, approve/revise/regenerate flow, founder context visibility, Kanban handoff, and future transition from approved plans to Codex execution.
- Out of scope: Source implementation, live Hermes profile execution, AppData or profile file writes, external Kanban writes outside existing fake/test paths, credential handling, visual redesign execution, and changes to live agent autonomy policy.

## Research Question

How should the Product Wizard UX help a founder move from a raw product idea to approved research, PRD, architecture, tasks, code plan, and acceptance artifacts without losing context, approving weak generated work, or prematurely handing work to Kanban or Codex execution?

## Target Workflow

The target workflow starts when the founder opens `/projects/new` to create a structured product workflow. The primary job is to capture enough founder context for Hermes Company OS to generate staged product artifacts in a safe local public-demo mode, then let the founder review, revise, regenerate, and approve one stage at a time.

The expected outcome is an approved sequence of artifacts:

- research;
- PRD;
- architecture;
- tasks;
- code plan;
- acceptance.

The approval moment happens on `/projects/{project_id}` after the founder reviews the active stage artifact, the founder intake context, the stage timeline, and any gating messages. The founder can approve a draft, request revision, regenerate an artifact, or wait if the stage is blocked.

The current exit state is either:

- `wizard_complete`, when all stages are approved;
- Kanban workflow push allowed after the `tasks` stage is approved and Kanban verification is ready;
- future Codex execution handoff after a sufficiently reviewed code plan and acceptance package.

## User And Persona Assumptions

- The founder is operating quickly but still wants explicit approval control before downstream work starts.
- The founder can tolerate a dense operational interface if status, next action, and evidence are easy to scan.
- The founder will revisit generated artifacts across multiple sessions, so history and decision memory matter.
- The founder is likely to compare versions when revision and regeneration produce multiple artifacts.
- The founder needs confidence that the wizard is in local public-demo mode before live Hermes execution exists.
- Agents are currently represented by deterministic local generation and owner metadata, not live profile runs.
- Future live agents will need stronger evidence, failure, and review visibility than the current public-demo flow.
- Reviewer behavior is expected to become stricter after QA Critic, Test Automation, and UI/UX Research Agent reviews are wired.
- Frequency of use is moderate during early company formation and high during active product exploration.
- Urgency varies by launch tier, but Product Wizard should default to careful staged approval over speed.
- Founder confirmation needed: whether Codex execution should require both `code_plan` approval and `acceptance` approval, or whether `code_plan` approval alone can create implementation workstreams in a pending state.

## Current-State Notes

The current Product Wizard already has a real founder-facing flow.

Relevant routes and screens:

- `/projects/new` renders a structured wizard form with Basics, Audience, Constraints, and Review steps.
- `POST /projects` creates a structured project when `wizard_version` is `product-wizard-v1`.
- `/projects/{project_id}` shows the project title, product wizard timeline, active stage actions, founder intake, artifact preview, generated workflow items, founder readiness, Kanban gate, and artifact history.
- `POST /projects/{project_id}/stages/current/generate` generates the next actionable stage.
- `POST /projects/{project_id}/stages/{stage_id}/approve` approves a draft stage.
- `POST /projects/{project_id}/stages/{stage_id}/revision` records a revision request.
- `POST /projects/{project_id}/stages/{stage_id}/regenerate` creates a new artifact version.
- `POST /projects/{project_id}/kanban` pushes workflow tasks only after the Product Wizard and Kanban gates allow it.

Relevant docs:

- The roadmap defines Product Wizard V1 as the safe baseline and says UI/UX research should precede UI-heavy implementation.
- The UI/UX Research Agent doctrine requires workflow, state, decision, evidence, failure, accessibility, and implementation analysis.
- The operating model says research packages are not authoritative until central integration and founder approval.

Existing state labels:

- Project statuses: `wizard_active`, `wizard_complete`.
- Stage statuses: `ready`, `waiting`, `draft`, `approved`, `needs_revision`, `blocked`.
- Artifact statuses: `draft`, `approved`, `needs_revision`.
- Kanban gate labels: Kanban ready, Kanban verification needed, Kanban gated.

Known test coverage:

- Generator tests cover canonical stages, owner metadata, deterministic rendering, approved-source filtering, prompt contract shape, unknown-stage rejection, and no-secret guarantees.
- Repository tests cover seeded stage order, structured project initialization, one-stage-at-a-time advancement, artifact versioning, revision requests, blocked stages, waiting-stage rejection, secret rejection, and legacy workflow compatibility.
- Route tests cover structured intake rendering, project creation, secret-shaped intake rejection, local public-demo generation, and no-secret page output.
- Acceptance tests cover initial timeline behavior, generate-then-approve flow, revision and regeneration history, happy path to acceptance, and Kanban push blocking until the tasks stage is approved.

Gaps:

- Artifact history is visible, but version chips do not yet let the founder inspect or compare older versions in place.
- Artifact preview renders generated markdown as plain text, so long structured output can be hard to scan.
- Revision requests are a free-text box with a helpful placeholder, but there is no guided structure for missing evidence, scope changes, or quality bar.
- The active stage panel does not yet expose all quality checks, source artifact IDs, owner agent rationale, or generation mode in a scan-friendly decision block.
- Founder readiness shows high-level gates, but it does not yet connect each approval to the evidence required before Kanban or future Codex execution.
- Failed generation and live-agent failure states are not yet first-class in the visible Product Wizard flow.
- Future Codex execution is not represented yet; the UI stops at Kanban push and generated workflow items.

## Screens Needed

### New Product Wizard Intake

- Purpose: Capture founder context safely before staged generation.
- Primary user: Founder.
- Primary action: Create a structured product workflow.
- Secondary actions: Navigate between Basics, Audience, Constraints, and Review; open the idea intake packet.
- Empty state: Blank required fields clearly indicate what must be supplied before creation.
- Blocked state: Secret-shaped or unsafe text is rejected before persistence.
- Failed state: Form validation should return the founder to the invalid step and preserve non-sensitive input.
- Success state: Founder lands on `/projects/{project_id}` with `research` as the first actionable stage.

### Project Stage Workspace

- Purpose: Review the current stage, act on the latest artifact, and understand what is unlocked next.
- Primary user: Founder.
- Primary action: Generate, approve, request revision, or regenerate the current stage.
- Secondary actions: Review founder intake, check Kanban readiness, inspect workflow items, inspect artifact history.
- Empty state: No artifact generated yet; the primary action is Generate.
- Blocked state: Stage is blocked with visible blocker notes and no approval until the blocker is resolved.
- Failed state: Generation failure should show owner, attempted stage, error summary, retry option, and no downstream unlock.
- Success state: Approved stage advances the next stage to `ready`; final approval sets the project to `wizard_complete`.

### Stage Timeline

- Purpose: Show where the founder is in the staged plan and which work is locked, active, revised, blocked, or approved.
- Primary user: Founder.
- Primary action: Understand the active stage and approval progression.
- Secondary actions: Jump to stage details if selectable behavior is added later.
- Empty state: New project shows all stages with `research` ready and the rest waiting.
- Blocked state: Blocked stage remains the active stage and visually interrupts the timeline.
- Failed state: Failed generation appears on the stage without changing later stages.
- Success state: Approved stages are clearly completed, the next stage is ready, and waiting stages remain non-actionable.

### Artifact Preview

- Purpose: Let the founder evaluate generated content before approval.
- Primary user: Founder.
- Primary action: Decide whether the artifact is good enough to approve.
- Secondary actions: Scan sections, quality checks, source inputs, owner, generation mode, next decision, and risks.
- Empty state: Show the founder idea and stage expectations before first generation.
- Blocked state: Show blocker notes and required founder or agent input instead of presenting stale artifact text as actionable.
- Failed state: Show failure summary and retry affordance.
- Success state: Show draft or approved artifact with visible evidence and next decision.

### Artifact History And Comparison

- Purpose: Preserve version history and support revision/regeneration trust.
- Primary user: Founder.
- Primary action: Inspect previous versions and compare changes before approval.
- Secondary actions: Filter by stage, show revision notes, show timestamps, show status, restore or reference older version if future policy allows.
- Empty state: Each stage shows Waiting until its first artifact exists.
- Blocked state: History marks the last version that led to a blocker or revision request.
- Failed state: Failed generation attempts should be visible separately from successful artifact versions when run records exist.
- Success state: Founder can see the latest version, prior versions, statuses, and what changed.

### Founder Context Panel

- Purpose: Keep original founder intent visible while reviewing generated work.
- Primary user: Founder.
- Primary action: Confirm whether generated artifacts still reflect the product idea, target audience, problem, constraints, and success metrics.
- Secondary actions: Copy context into revision notes or future founder decision records.
- Empty state: Missing fields are labeled as not specified, not silently omitted.
- Blocked state: Missing critical context is treated as a decision needed before further generation.
- Failed state: Context parsing errors should not generate artifacts from incomplete or misleading data.
- Success state: The panel gives enough grounding to challenge overconfident generated text.

### Plan-To-Execution Gate

- Purpose: Prevent Kanban or Codex execution before the founder has approved enough planning evidence.
- Primary user: Founder.
- Primary action: Push to Kanban now; later, create Codex implementation workstreams.
- Secondary actions: Inspect tasks, linked documents, test expectations, owner agents, and execution blockers.
- Empty state: No workflow items until the tasks stage is approved.
- Blocked state: The button is disabled with a specific reason: tasks not approved, Kanban verification incomplete, code plan not approved, acceptance evidence missing, or founder approval missing.
- Failed state: External task creation failure should leave local tasks intact and show retry evidence.
- Success state: Created tasks are linked to external task IDs or future Codex workstream IDs, with audit evidence.

## State Model

### `ready`

- Meaning: The stage is the next actionable stage and can generate an artifact.
- Owner: Current stage owner agent, with founder as approver.
- Allowed actions: Generate; block if missing required context.
- Forbidden actions: Approve without a draft; push downstream work based on this stage.
- Evidence required: Stage definition, owner, purpose, and approved prior artifacts if required.

### `waiting`

- Meaning: The stage is locked until prior stages are approved.
- Owner: Prior stage owner and founder approver.
- Allowed actions: View stage position and dependency reason.
- Forbidden actions: Generate, approve, revise, regenerate, or execute.
- Evidence required: Clear dependency on prior approved stages.

### `draft`

- Meaning: An artifact exists and needs founder review.
- Owner: Artifact owner agent; founder approves or requests revision.
- Allowed actions: Approve, request revision, regenerate, inspect history.
- Forbidden actions: Skip directly to external execution unless the stage's gate permits it.
- Evidence required: Artifact content, owner agent, generation mode, source artifacts, quality checks, risks, test plan, and next decision.

### `approved`

- Meaning: Founder accepted the latest draft for this stage.
- Owner: Founder decision with artifact owner accountable for content.
- Allowed actions: Unlock next stage; request revision if policy permits reopening; include artifact as approved source for dependent stages.
- Forbidden actions: Replace approved artifact without a revision request.
- Evidence required: Approved artifact version, approval timestamp, quality checks, source artifacts, and any acceptance note once approval notes are supported.

### `needs_revision`

- Meaning: Founder rejected or reopened the stage with revision notes.
- Owner: Artifact owner agent.
- Allowed actions: Regenerate, inspect prior version, update revision notes.
- Forbidden actions: Approve stale previous version without a new review policy.
- Evidence required: Revision notes, previous artifact version, missing evidence or quality bar.

### `blocked`

- Meaning: The stage cannot proceed until a founder answer, agent fix, runtime readiness item, or external prerequisite is resolved.
- Owner: Blocker owner should be explicit; currently stored as stage revision notes.
- Allowed actions: View blocker, resolve through a future decision record, regenerate after unblock.
- Forbidden actions: Approve, unlock next stage, push to Kanban or Codex.
- Evidence required: Blocker reason, owner, required action, and date/status.

### `wizard_active`

- Meaning: The project still has actionable Product Wizard stages.
- Owner: Founder with current stage owner agent.
- Allowed actions: Continue stage workflow.
- Forbidden actions: Treat the plan as complete.
- Evidence required: Current stage, latest artifact status, and next required decision.

### `wizard_complete`

- Meaning: All Product Wizard stages are approved.
- Owner: Founder.
- Allowed actions: Move into execution planning, Kanban sync, Codex workstream preparation, or launch-gate review depending on founder policy.
- Forbidden actions: Launch or create real branches without explicit downstream gates.
- Evidence required: Approved stage list, acceptance evidence, test expectations, and execution readiness.

## UX Risks And Anti-Patterns

- Confusing approval state: The founder may see a polished artifact and assume later stages or execution are ready.
- Hidden blockers: A blocked stage currently relies on notes and status; the UI should make the blocking owner and required action explicit.
- Overconfident generated text: Local deterministic artifacts can sound complete even when source evidence is thin.
- Unclear owner: Owner agent metadata exists, but it is not yet prominent enough in the artifact decision surface.
- Weak comparison: Artifact history shows version counts and chips but not the content changes that matter to approval.
- Revision ambiguity: Free-text revision requests can produce vague regeneration loops unless stage-specific prompts structure the ask.
- Premature execution: Kanban is gated by tasks approval, but future Codex execution needs equally explicit code-plan and acceptance gates.
- Missing failure handling: Live Hermes generation will need visible running, failed, retrying, timed out, and blocked states before it is trusted.
- Inaccessible interaction: Timeline and history chips should not rely on color or mouse-only interaction.
- Too much visual decoration: Product Wizard should remain an operational review workspace, not a marketing-style wizard.
- Context drift: The founder idea, constraints, and success metrics can be separated from long artifact prose unless context stays pinned and visible.

## Accessibility And Responsive Notes

- Keyboard behavior: Step navigation, stage actions, artifact history, and future comparison controls must be reachable and operable by keyboard.
- Labels and semantic structure: The stage timeline should expose stage name, status, and whether the stage is active without relying on icon-only labels.
- Contrast and status color concerns: Status pills need text labels and contrast-safe colors; approval, warning, blocked, and ready states cannot rely on color alone.
- Mobile layout concerns: On small screens, stage actions should appear before long artifact content, while founder context and readiness should remain reachable without excessive scrolling.
- Long text handling: Generated artifacts need section-level rendering, anchors, wrapping, and overflow-safe layout so markdown does not become one dense paragraph.
- Focus management: After generate, approve, revise, or regenerate, the redirected page should place the founder near the updated current stage or artifact status.
- Motion or animation constraints: Avoid animated stage transitions that obscure status changes; any motion should respect reduced-motion preferences.
- Error visibility: Validation errors should identify the exact field or stage action and should not discard safe input.

## Implementation Recommendations

### Recommendation 1: Add A Decision Summary Block To The Active Stage

- Behavior: Show owner agent, generation mode, required source artifacts, quality checks, revision notes, and next decision above the approval controls.
- Affected surface: `/projects/{project_id}` current stage panel and artifact preview.
- Likely data needed: Existing artifact JSON metadata, stage owner fields, stage revision notes, and latest artifact timestamps.
- Acceptance signal: A route/UI assertion can confirm that generated stage metadata, next decision, and quality check labels are visible before approval.

### Recommendation 2: Render Artifact Markdown As Structured Review Content

- Behavior: Render generated markdown sections as readable review blocks with headings, risks, test plan, and acceptance mapping easy to scan.
- Affected surface: Artifact Preview.
- Likely data needed: Existing `markdown_content`; optional parsed section index.
- Acceptance signal: Long artifacts remain readable on desktop and mobile, and route tests assert key section headings are visible.

### Recommendation 3: Make Artifact History Inspectable And Comparable

- Behavior: Let the founder select a version, view its content and metadata, and compare latest versus previous version after revision or regeneration.
- Affected surface: Artifact history panel and artifact preview.
- Likely data needed: Existing artifact versions, statuses, timestamps, revision notes, and owner metadata.
- Acceptance signal: Tests confirm multiple versions render with selectable labels, latest version remains default, and older version status is visible.

### Recommendation 4: Structure Revision Requests By Stage

- Behavior: Replace or supplement the generic revision text box with guided prompts such as missing evidence, scope change, risk concern, test gap, owner mismatch, or acceptance bar.
- Affected surface: Revision request form.
- Likely data needed: Stage ID, stage label, current artifact checks, and revision notes.
- Acceptance signal: Route tests verify revision notes persist, no-secret checks reject unsafe notes, and the UI displays the revision reason before regeneration.

### Recommendation 5: Strengthen Plan-To-Execution Readiness

- Behavior: Keep Kanban disabled until tasks approval and Kanban verification are ready; add future Codex readiness language for code plan approval, acceptance evidence, test commands, branch/repo approval, and founder execution approval.
- Affected surface: Kanban Push panel, Generated Company Workflow panel, future Codex execution gate.
- Likely data needed: Existing task-stage approval check, Kanban readiness check, code plan artifact status, acceptance status, future founder decision records.
- Acceptance signal: Tests cover disabled gate reasons for tasks not approved, Kanban not verified, and future Codex execution not approved.

### Recommendation 6: Add First-Class Failed And Running Generation States Before Live Hermes

- Behavior: Represent running, failed, timed out, retried, and blocked generation attempts separately from artifact versions.
- Affected surface: Stage timeline, current stage panel, artifact history, future run records.
- Likely data needed: Run records linked to project, stage, artifact, owner, error summary, retry count, and source inputs.
- Acceptance signal: Fake-client route tests verify failures do not approve stages, unlock later stages, or hide the retry path.

### Recommendation 7: Keep Founder Context Visible During Review

- Behavior: Make founder idea, target audience, problem, constraints, non-goals, success metric, and launch tier available in a compact persistent context panel or expandable drawer.
- Affected surface: Founder Intake panel and artifact review layout.
- Likely data needed: Existing `company_projects.intake_json`.
- Acceptance signal: UI assertions confirm the critical intake fields remain visible on the project detail page and are not omitted when values are missing.

### Recommendation 8: Connect Product Wizard Approvals To Founder Decision Records

- Behavior: When Milestone 1 founder decision extensions exist, record stage approvals, revision requests, blocked states, and execution approvals as audit-linked founder decisions.
- Affected surface: Founder Readiness panel, future decision inbox, stage approval routes.
- Likely data needed: Project ID, stage ID, artifact ID, decision type, status, owner agent, and evidence.
- Acceptance signal: Repository and route tests confirm approvals and revisions create or resolve linked decision records without storing credentials.

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

### Decision 1: What Approvals Are Required Before Codex Execution?

- Decision: Should Codex execution require approved `code_plan` only, approved `code_plan` plus approved `acceptance`, or a separate founder execution approval?
- Why it matters: This defines the boundary between planning and real implementation workstreams.
- Default recommendation: Require approved `code_plan`, approved `acceptance`, and a separate founder execution approval before creating real branches or workstreams.
- Impact if deferred: The UI can show Codex execution as planned but should keep it disabled.

### Decision 2: Can Approved Stages Be Reopened?

- Decision: Should a founder be allowed to request revision after a stage has been approved and downstream stages have begun?
- Why it matters: Reopening upstream stages can invalidate dependent artifacts.
- Default recommendation: Allow reopening, but mark dependent stages as needing review before further execution.
- Impact if deferred: Current behavior can request revision for non-waiting stages, but the UX should avoid promising dependency invalidation until policy is explicit.

### Decision 3: How Strict Should Revision Guidance Be?

- Decision: Should revision requests stay free-form or require categorized reasons by stage?
- Why it matters: Structured reasons improve regeneration quality and future audit.
- Default recommendation: Keep free text, but add required category chips for evidence gap, scope issue, risk concern, test gap, owner mismatch, or acceptance concern.
- Impact if deferred: The generic revision box remains usable, but revision history will be harder to analyze.

### Decision 4: What Evidence Must Be Visible Before Kanban Push?

- Decision: Is tasks-stage approval enough for Kanban push, or should the code plan and acceptance stage also be approved before external task creation?
- Why it matters: Kanban push can create external operating commitments.
- Default recommendation: Keep the current tasks-stage gate for V1, but add a visible warning that code and launch execution remain gated later.
- Impact if deferred: Keep current tests and behavior, but label the handoff as task planning rather than implementation start.

### Decision 5: How Much Artifact Comparison Is Required In V1?

- Decision: Should V1 support simple version inspection, side-by-side comparison, or full diff highlighting?
- Why it matters: Comparison complexity affects implementation cost and review trust.
- Default recommendation: Start with selectable version inspection plus a concise metadata delta; add full diff only when revision volume justifies it.
- Impact if deferred: Artifact history remains informational and not review-grade.

## Implementation Handoff

- First slice: Improve `/projects/{project_id}` as an operational review workspace by adding a decision summary block, structured artifact section rendering, clearer revision notes, and stronger artifact history inspection without changing generation behavior.
- Likely files or modules:
  - `src/hermes_company_os/templates/project.html`
  - `src/hermes_company_os/static/styles.css`
  - `src/hermes_company_os/main.py`
  - `src/hermes_company_os/repository.py`
  - `tests/test_product_wizard_routes.py`
  - `tests/test_product_wizard_acceptance.py`
  - `tests/test_product_wizard_repository.py`
- Tests to add:
  - Route/UI assertion that generated artifact metadata, quality checks, owner agent, generation mode, and next decision are visible before approval.
  - Route/UI assertion that artifact history exposes version status, selected version, and revision notes.
  - Repository or route test that revision reasons remain attached to the stage and latest artifact context.
  - Gate tests for future Codex execution once the execution model exists.
  - Accessibility-oriented assertions for labels on timeline, history controls, disabled gate reasons, and action buttons.
  - No-secret tests for any new displayed artifact metadata, revision notes, and execution handoff text.
- No-secret scan scope:
  - New and edited UI/UX research docs.
  - Generated Product Wizard artifacts.
  - Project detail route output.
  - Any future founder decision records linked to wizard actions.
- Founder approval gate: Founder should approve the Product Wizard UX direction, the Codex execution gating policy, and the artifact comparison depth before implementation begins.
