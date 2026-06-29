# Accessibility And Responsive UX Research Package

## Package Metadata

- Package title: Accessibility And Responsive UX
- Research thread: Accessibility And Responsive UX
- Owner: Worker 4
- Date: 2026-06-26
- Source docs reviewed:
  - `docs/agentic-company-os-roadmap.md`
  - `docs/ui-ux-research/01-ui-ux-research-agent-doctrine.md`
  - `docs/ui-ux-research/02-codex-subagent-research-operating-model.md`
  - `docs/ui-ux-research/03-ui-ux-research-thread-prompts.md`
  - `docs/ui-ux-research/04-research-package-template.md`
  - `docs/implementation-plans/01-founder-control-plane-implementation-plan.md`
  - `docs/implementation-plans/02-ui-ux-research-agent-implementation-plan.md`
  - W3C WCAG 2 overview: `https://www.w3.org/WAI/standards-guidelines/wcag/`
  - W3C WCAG 2.2 Recommendation: `https://www.w3.org/TR/WCAG22/`
- Current implementation areas inspected:
  - `src/hermes_company_os/templates/dashboard.html`
  - `src/hermes_company_os/templates/project_new.html`
  - `src/hermes_company_os/templates/project.html`
  - `src/hermes_company_os/templates/setup.html`
  - `src/hermes_company_os/templates/agent.html`
  - `src/hermes_company_os/static/styles.css`
  - `tests/test_product_wizard_routes.py`
  - `tests/test_product_wizard_acceptance.py`
  - `tests/test_app.py`
  - `tests/test_docs.py`
- Scope: Keyboard navigation, semantic labels, focus states, contrast, responsive layout, long generated text handling, focus management, and acceptance checks for founder-facing Hermes Company OS surfaces.
- Out of scope: Source implementation, live Hermes profile writes, AppData writes, credentials, visual redesign, and central integration decisions.

## Research Question

What accessibility and responsive requirements should every founder-facing Hermes Company OS dashboard surface meet before UI-heavy implementation, live Hermes execution, agent queues, or Codex project execution are added?

## Target Workflow

The improved workflow is the founder and reviewer path through operational surfaces that already exist or are planned:

- entry point: founder enters through the dashboard, project list, `/projects/new`, a project detail page, setup readiness, or the future founder decision inbox;
- primary job to be done: create and inspect company work, review generated artifacts, resolve decisions, understand blockers, and approve or revise work without losing context;
- expected outcome: the founder can complete the critical path using keyboard, screen reader, zoomed layout, narrow viewport, and long generated content without hidden state or layout breakage;
- approval or review moment: artifact approval, revision request, decision resolution, setup verification, Kanban handoff, launch readiness, or future code execution approval;
- exit state: the founder either approves, rejects, revises, defers, or identifies a blocker with clear evidence and no accidental external action.

Accessibility and responsive quality are not final polish for this workflow. They are part of the operating safety model because Hermes asks the founder to approve generated work and external handoffs.

## User And Persona Assumptions

- Founder behavior: founder will scan dense operational pages quickly, often returning to the same project or decision after context switching.
- Founder behavior needing confirmation: founder may use the dashboard on a laptop as the primary device, with phone access mainly for urgent checks and blocked decisions.
- Agent behavior: agents will produce long prose, lists, evidence summaries, status labels, and future run logs that can exceed normal card sizes.
- Reviewer behavior: QA Critic, Test Automation, and future UI/UX Research Agent reviewers need stable state labels and evidence links they can validate.
- Frequency of use: dashboard, decision, and project pages are repeated daily surfaces; setup and profile pages are less frequent but high-risk when credentials or external integrations are involved.
- Urgency: founder decision, blocker, failed run, and external action states are urgent enough that they must not rely on color alone.
- Information density tolerance: the founder can tolerate dense operational screens when hierarchy, labels, keyboard order, and responsive rules are predictable.
- Assumption needing founder confirmation: whether mobile should support full workflow completion or only review, triage, and emergency decisions.

## Current-State Notes

Current repo state already supports several accessibility and responsive foundations:

- Product Wizard V1 exists at `/projects/new` with structured intake fields, labelled form controls, staged panels, and local public-demo generation.
- Project detail pages show a stage timeline, stage actions, artifact preview, founder intake, Kanban gate, workflow tasks, readiness lines, and artifact history.
- Dashboard includes a founder decision queue, agent list, task/document forms, activation summary, and setup links.
- Setup includes many readiness and verification sections with status pills, forms, save buttons, and generated evidence text.
- `styles.css` defines responsive breakpoints at `980px` and `560px`, uses grid collapse rules for many surfaces, and includes wrapping for artifact and intake text.
- Long generated content is partially protected by `overflow-wrap: anywhere` and `white-space: pre-wrap` in artifact and intake surfaces.
- Route and acceptance tests cover Product Wizard creation, stage generation, approval, revision, Kanban gating, secret rejection, dashboard rendering, and setup route behavior.

Gaps and risks observed from source inspection:

- No explicit global `:focus-visible` or equivalent focus treatment was found in the CSS search. Browser default focus may be inconsistent against custom buttons, status-heavy cards, and dark navigation.
- Wizard step triggers toggle visual `active` state, but the current script does not set `aria-current`, `aria-selected`, `aria-controls`, `hidden`, or focus movement when the active panel changes.
- The wizard invalid handler reveals the panel containing an invalid input, but it does not explicitly move focus to the invalid control or announce the panel change.
- Status pills use color and text, which is good, but state meaning is not consistently backed by semantic regions or screen-reader-oriented summaries.
- Icon-only save buttons usually have `title`, but the safer acceptance target is an accessible name verified in rendered markup and keyboard testing.
- Some setup tracking forms have select and input controls inside dense rows without visible per-control labels. Placeholders and context may not be enough for assistive technology.
- Disabled gates often include explanatory copy nearby, but disabled buttons themselves are not focusable. The blocked reason must be reachable before the skipped disabled control in keyboard order.
- Tests currently assert server behavior and rendered strings, but no dedicated automated checks were found for focus order, keyboard-only completion, contrast, reduced motion, or responsive overflow.

## Screens Needed

### Global Dashboard Shell

- Purpose: provide founder entry into decisions, projects, agents, setup, and operating status.
- Primary user: founder.
- Primary action: identify the next required decision or blocker.
- Secondary actions: navigate to setup, project workspace, agent profile, or exported setup artifacts.
- Empty state: no open decisions, no projects, or no agent work should show explicit next action.
- Blocked state: external readiness blockers should appear before external action controls.
- Failed state: failed runs or setup checks should be grouped with owner and recovery action.
- Success state: readiness and work state should be summarized without hiding the evidence trail.

### New Product Wizard

- Purpose: capture founder idea and constraints before staged generation.
- Primary user: founder.
- Primary action: complete structured intake and create the product workflow.
- Secondary actions: move between steps, review workflow contract, open idea intake artifact.
- Empty state: blank fields show examples without acting as labels.
- Blocked state: required fields prevent submission and focus moves to the invalid field.
- Failed state: submit failure preserves all entered text and identifies the failing field or route error.
- Success state: workflow is created and the founder lands on the new project detail page.

### Project Stage Detail

- Purpose: review generated artifacts, approve or request revision, inspect stage history, and manage Kanban handoff.
- Primary user: founder, reviewer, Product Manager, QA Critic.
- Primary action: decide whether the active artifact is acceptable.
- Secondary actions: regenerate, request revision, inspect intake, inspect artifact history, inspect Kanban gate.
- Empty state: no artifact yet should point to Generate and explain what will be generated.
- Blocked state: blocked stage, task gate, or Kanban prerequisite shows exact missing condition and owner.
- Failed state: failed generation or handoff shows error, retry path, and no silent status advancement.
- Success state: approved stage unlocks the next stage and records evidence.

### Founder Decision Queue And Future Inbox

- Purpose: make approvals, blockers, accepted risks, and revision decisions central and auditable.
- Primary user: founder and Chief of Staff.
- Primary action: resolve or defer one decision with a clear note.
- Secondary actions: filter by urgency, owner, project, source, status, and decision type.
- Empty state: no open decisions should show whether the queue is truly clear or just not configured.
- Blocked state: blocked decisions show impacted project/stage and the work they prevent.
- Failed state: invalid or secret-like resolution input is rejected without losing non-secret entered text.
- Success state: decision status, resolution note, owner, and timestamp are visible in the audit trail.

### Setup Readiness And Verification

- Purpose: configure and verify external readiness without storing secrets in the dashboard.
- Primary user: founder, Chief of Staff, operator.
- Primary action: import safe status and evidence for setup checks.
- Secondary actions: run smoke checks, update status, inspect generated setup artifacts.
- Empty state: unconfigured sections show the next safe non-secret input needed.
- Blocked state: smoke checks, messaging checks, schedule checks, and Kanban checks show prerequisites before action controls.
- Failed state: failed verification shows evidence, recovery owner, and retry route.
- Success state: verified status is visible with non-secret evidence.

### Agent Profile And Future Agent Queue

- Purpose: inspect agent role, routing, generated assets, future work queue, and profile smoke state.
- Primary user: founder, Chief of Staff, Engineering Manager.
- Primary action: inspect whether an agent can safely receive or execute work.
- Secondary actions: update profile metadata, route work, run smoke checks.
- Empty state: no assigned work should distinguish between not configured and currently clear.
- Blocked state: missing profile, model, messaging, or acceptance evidence blocks execution controls.
- Failed state: failed smoke or acceptance check is visible before any run action.
- Success state: agent readiness, recent work, and acceptance evidence are visible.

### Future Observability, Audit, And Codex Execution Screens

- Purpose: inspect autonomous actions, run evidence, workstream status, diffs, tests, and approval gates.
- Primary user: founder, Engineering Manager, QA Critic, Test Automation.
- Primary action: decide whether work can proceed, merge, ship, or needs revision.
- Secondary actions: inspect logs, retry, export audit, compare artifacts, review findings.
- Empty state: no runs or workstreams should be clearly distinct from data loading failure.
- Blocked state: missing tests, unresolved findings, or founder approval gates block progression.
- Failed state: failed run or test failure shows error, owner, retry constraints, and evidence.
- Success state: approved, tested, and audited work has a visible chain of evidence.

## State Model

### Keyboard Reachable

- Label: keyboard reachable
- Meaning: every interactive control can be reached and operated without a mouse.
- Owner: frontend implementation agent.
- Allowed actions: tab, shift-tab, enter, space, arrow keys where applicable, escape for dismissible overlays later.
- Forbidden actions: hover-only actions, pointer-only drag, click-only step changes, hidden keyboard traps.
- Evidence required: keyboard-only smoke script or Playwright test covers dashboard, wizard, project stage, and decision update flow.

### Focus Visible

- Label: focus visible
- Meaning: the currently focused interactive element is visibly distinct in normal, hover, active, and disabled-adjacent contexts.
- Owner: frontend implementation agent and UI/UX Research Agent.
- Allowed actions: global `:focus-visible` treatment; component-specific focus rings where needed.
- Forbidden actions: removing outlines without replacement; relying only on browser defaults in custom controls.
- Evidence required: visual inspection plus automated screenshot or DOM assertion for focused buttons, links, selects, textareas, and wizard step triggers.

### Current Step Or Stage

- Label: current
- Meaning: a wizard step, project stage, tab, or route is the active context.
- Owner: frontend implementation agent.
- Allowed actions: show active state visually and expose it semantically with appropriate ARIA or native pattern.
- Forbidden actions: visual-only active state that a screen reader cannot identify.
- Evidence required: rendered HTML includes accessible current-state semantics for wizard steps and navigation.

### Blocked Or Disabled

- Label: blocked
- Meaning: an action cannot proceed because prerequisite evidence, approval, setup, or review is missing.
- Owner: product and frontend implementation agents.
- Allowed actions: explain reason, link to prerequisite, keep non-destructive alternatives available.
- Forbidden actions: disabled button with reason only in `title`; hidden blocker behind color or icon.
- Evidence required: route tests assert blocker copy appears before or near the blocked action and keyboard order reaches explanation.

### Generated Artifact Long Text

- Label: generated artifact long text
- Meaning: AI-generated prose, lists, evidence, run logs, or revision notes exceed normal panel length or contain long tokens.
- Owner: frontend implementation agent and Test Automation.
- Allowed actions: wrap, preserve line breaks, constrain panel width, provide scroll only inside intentional log panes, keep actions visible.
- Forbidden actions: horizontal page overflow, text clipping, unbounded cards that push actions out of reach, hidden evidence.
- Evidence required: generated long-text fixture renders without horizontal overflow at desktop, tablet, and mobile widths.

### Validation Error

- Label: validation error
- Meaning: submitted or required input is invalid, missing, unsafe, or rejected by secret guard.
- Owner: backend route and frontend implementation agents.
- Allowed actions: preserve safe entered values, show field-level message, move focus to error summary or invalid field, keep secret-like rejected values out of persistence.
- Forbidden actions: generic error page for a form field issue, lost input, silent failure.
- Evidence required: route tests for invalid input and UI tests for focus movement and visible error copy.

### Live Update Or Run In Progress

- Label: running
- Meaning: future live Hermes, smoke, standup, Kanban, or Codex work is in progress.
- Owner: agent orchestration and frontend implementation agents.
- Allowed actions: show progress state, owner, started time, safe cancellation if supported, and refresh behavior.
- Forbidden actions: optimistic completion, invisible background work, progress that updates only by color.
- Evidence required: fake-client tests assert running, completed, failed, and retry states render distinctly.

### Responsive Constrained Layout

- Label: constrained
- Meaning: viewport width, zoom, or text scaling forces a layout change.
- Owner: frontend implementation agent.
- Allowed actions: collapse grids, stack actions, preserve source order, keep primary action and blocker copy adjacent.
- Forbidden actions: overlapping text, hidden status meaning, horizontal page scroll except intentional code/log panes.
- Evidence required: screenshots or DOM checks at mobile, tablet, and desktop sizes with long content fixtures.

## UX Risks And Anti-Patterns

- Invisible or low-contrast focus makes founder approvals risky because the wrong action can be triggered without clear current focus.
- Wizard panels use JavaScript-only active classes. Without ARIA and focus management, keyboard and assistive-technology users may lose context.
- Disabled external action buttons can be skipped by keyboard users, so the blocker explanation must be reachable and visible without relying on the disabled control.
- Status pills can become color shorthand. Every status needs readable text and, for critical states, surrounding copy that explains impact.
- Long generated artifacts can bury approve, revise, or blocker controls if actions are not placed predictably and repeated where needed.
- Dense setup verification rows can become inaccessible if select and evidence fields rely on surrounding visual context rather than labels.
- Icon-only buttons with only visual icons or browser `title` behavior may have unreliable accessible names across assistive technologies.
- Small mobile layouts can preserve content but still fail workflow if action order changes or primary and secondary actions separate from their evidence.
- Generated text may contain long URLs, filenames, command fragments, or model output that breaks layout despite normal prose wrapping.
- Future live-run updates can create silent state changes unless progress, failure, and completion states are announced or refreshed in a predictable region.
- Premature visual polish can hide operational hierarchy, especially if decorative cards compete with blocker, evidence, and decision states.

## Accessibility And Responsive Notes

### Standards Baseline

- Use WCAG 2.2 Level AA as the baseline for founder-facing web UI. W3C presents WCAG 2.2 as the latest WCAG 2 version and encourages use of the latest version; WCAG 2.2 conformance is backwards compatible with WCAG 2.1 and 2.0.
- Treat keyboard access, visible focus, meaningful sequence, labels or names, contrast, target size, error identification, and accessible authentication patterns as implementation acceptance requirements, not optional polish.
- Add Hermes-specific checks beyond WCAG AA where operational risk is higher: no color-only status, no hidden blockers, no focus loss after generation or validation errors, and no horizontal overflow from generated artifacts.

### Keyboard Behavior

- Tab order should follow the visual and decision order: context summary, blocker/evidence, primary action, secondary actions, history/details.
- Wizard step triggers should support keyboard activation and expose the active step semantically.
- Changing wizard steps should move focus to the new panel heading or first field unless the user is correcting a specific invalid field.
- Project stage actions should be reachable in a stable order: generate, approve when available, regenerate, revision request.
- Future dialogs, drawers, or compare views must trap focus only while open and restore focus to the invoking control on close.
- Disabled actions should not be the only place where blocked meaning exists.

### Labels And Semantic Structure

- Prefer visible labels for all form fields. Placeholder text is supporting copy, not a label.
- Status controls inside setup and decision rows need accessible names that include the object being updated, for example the check, decision, stage, or integration name.
- Icon buttons need an accessible name independent of `title`; visible text is preferred when space allows, and `aria-label` is acceptable for compact save actions.
- Wizard stepper should use a tab-like or current-step pattern consistently. It needs relationships between triggers and panels.
- Stage timeline items need semantic current state and state text. If they become interactive later, they must become real buttons or links.
- Artifact preview should have a labelled region that ties the title, stage, version, and status to the generated content.

### Contrast And Status Color

- Do not rely on status pill color alone. Keep text labels such as `blocked`, `failed`, `approved`, `needed`, and `urgent`.
- Validate contrast for all status foreground/background pairs, including muted text on `var(--panel-muted)`, amber warning pills, red failure pills, disabled controls, and dark sidebar links.
- Focus rings must meet visible contrast against white panels, muted panels, dark sidebar, and colored status backgrounds.
- Urgent, failed, rejected, and blocked states should include icon or text treatment plus explanatory copy.

### Mobile And Tablet Layout

- The `980px` and `560px` breakpoints are a good foundation, but acceptance should test real workflow completion, not just grid collapse.
- Mobile order should preserve decision safety: blocker and evidence before action, primary action before lower-priority links, revision field adjacent to revision submit.
- Wizard stepper can collapse to two columns on narrow screens, but the active/current state must remain visible and announced.
- Stage timeline should avoid compressing six stages into tiny tiles that hide status. At narrow widths, a vertical sequence may be safer.
- Decision queue rows should stack status, owner, context, resolution, and update controls without separating the save action from the field it submits.
- Setup verification rows should stack status select, evidence input, and save action with labels that remain visible after wrapping.

### Long Text Handling

- Preserve line breaks for generated artifacts, revision notes, evidence, and run logs.
- Wrap long tokens using safe CSS such as `overflow-wrap: anywhere` where the current implementation already does this for artifact and intake text.
- Do not put long generated prose inside fixed-height cards unless the scroll area has a label, keyboard access, and visible overflow affordance.
- Keep approve, revise, and blocker actions visible near long artifacts. For very long artifacts, consider a sticky local action bar or repeated actions after central integration approval.
- Test long generated content with headings, bullets, long filenames, long unbroken words, command-like fragments, and multi-paragraph evidence.

### Focus Management

- After creating a project, focus should land on the project page heading or success context.
- After generating an artifact, focus should land on the artifact preview heading or status summary, not at the top of the page without context.
- After approval, focus should land on the next actionable stage summary.
- After requesting revision, focus should land on a visible revision status or confirmation.
- After validation failure, focus should land on an error summary or the invalid field.
- After saving a decision or setup check, focus should remain near the updated row and a confirmation should be visible.

### Motion And Animation Constraints

- Avoid essential information conveyed through motion.
- Any future live progress animation should respect reduced motion preferences.
- Do not auto-scroll long generated content without user action.
- Avoid flashing or rapidly changing status indicators for live runs.

## Implementation Recommendations

### Add A Global Focus Standard

- Behavior: define a visible, high-contrast `:focus-visible` treatment for links, buttons, inputs, selects, textareas, wizard step triggers, artifact history links, and sidebar navigation.
- Affected surface: global CSS and all founder-facing templates.
- Likely data needed: none.
- Acceptance signal: keyboard screenshots or assertions show a clear focus ring on dark sidebar, white panel, muted panel, and colored controls.

### Make Wizard Steps Semantically Current

- Behavior: connect step triggers to panels with stable IDs, expose current step state, hide inactive panels semantically, and move focus on step changes.
- Affected surface: `/projects/new`.
- Likely data needed: step IDs, active step, panel heading IDs.
- Acceptance signal: keyboard-only test can move through all steps, screen-reader semantics identify the current step, invalid required fields reveal and focus the correct panel.

### Add Field-Level Error And Focus Rules

- Behavior: on validation or secret-guard rejection, preserve safe input, show visible error text, and focus the error summary or invalid field.
- Affected surface: wizard forms, decision forms, setup import/update forms, project revision forms.
- Likely data needed: route validation errors mapped to field names where possible.
- Acceptance signal: invalid route tests and UI tests confirm error copy, focus target, and no persistence of unsafe input.

### Strengthen Accessible Names In Dense Rows

- Behavior: every status select, evidence input, and save button in repeated rows gets a unique accessible name that includes the row subject.
- Affected surface: dashboard decision rows, setup readiness rows, profile acceptance rows, messaging/schedule/Kanban verification rows.
- Likely data needed: row title, check label, integration name, decision title.
- Acceptance signal: rendered HTML test or accessibility scan finds no unlabeled inputs, selects, or buttons in repeated operational rows.

### Define Status Semantics And Non-Color Signals

- Behavior: standardize status labels, text explanations, and critical-state copy for `needed`, `blocked`, `failed`, `approved`, `verified`, `deferred`, `urgent`, and future `running`.
- Affected surface: status pills, readiness cards, project stages, decision queue, setup checks, future work queues.
- Likely data needed: status meaning, owner, blocked action, evidence required.
- Acceptance signal: route tests assert status text and blocker explanation render together; contrast check passes for all status variants.

### Create Long-Generated-Text Fixtures

- Behavior: add test fixtures for long artifact bodies, long revision notes, long setup evidence, long run output, and long decision context.
- Affected surface: project detail, dashboard, setup, future observability and Codex execution screens.
- Likely data needed: generated text fixtures with paragraphs, lists, long tokens, and command-like fragments.
- Acceptance signal: responsive checks show no horizontal document overflow and no action overlap at desktop, tablet, and mobile widths.

### Require Responsive Workflow Acceptance

- Behavior: verify complete critical flows at representative widths, not just CSS breakpoints.
- Affected surface: dashboard, `/projects/new`, project detail, setup readiness, future founder inbox.
- Likely data needed: seeded project, draft artifact, blocked Kanban gate, open decision, failed/blocked setup check.
- Acceptance signal: Playwright or equivalent workflow test can complete create, generate, revise, approve, decision update, and setup status update paths at narrow and desktop widths using keyboard.

### Keep Blocker Copy Before Blocked Actions

- Behavior: when an action is disabled or unavailable, show the missing prerequisite and recovery link before or immediately adjacent to the action in reading order.
- Affected surface: Kanban push, smoke checks, standup run, live generation, future Codex workstream start, launch approval.
- Likely data needed: blocker reason, prerequisite route, owner.
- Acceptance signal: route tests assert blocker text and recovery link render whenever the action is disabled or omitted.

### Add Accessibility Review To UI Handoffs

- Behavior: every future UI-heavy implementation handoff includes keyboard, focus, labels, contrast, responsive, long text, and no-secret acceptance checks.
- Affected surface: all future Founder Control Plane, Agent Queue, Observability, Codex Execution, and Launch surfaces.
- Likely data needed: screen inventory, states, fake-client test data, seeded blockers.
- Acceptance signal: implementation PR or package cannot be marked ready without the accessibility checklist completed or explicitly deferred by founder approval.

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

### Mobile Scope

- Decision: Should mobile support full workflow completion or only review, triage, and urgent decision handling?
- Why it matters: full mobile workflow requires stronger testing for forms, artifact review, revision writing, and setup checks.
- Default recommendation: support full review and decision triage on mobile now; require full mobile completion for core dashboard and Product Wizard after the first responsive acceptance pass.
- Impact if deferred: implementation agents may optimize desktop workflows and leave mobile behavior inconsistent.

### Accessibility Baseline

- Decision: Confirm WCAG 2.2 Level AA as the minimum standard for founder-facing Hermes web UI.
- Why it matters: this gives implementation and QA agents a stable acceptance baseline.
- Default recommendation: adopt WCAG 2.2 Level AA plus Hermes-specific no-hidden-blocker and long-generated-text checks.
- Impact if deferred: each UI thread may choose different accessibility thresholds.

### Automated Accessibility Tooling

- Decision: Should the implementation plan add a browser-based accessibility scan and keyboard workflow test to the normal UI test suite?
- Why it matters: route assertions alone will not catch focus, label, contrast, or mobile overflow regressions.
- Default recommendation: add lightweight Playwright keyboard checks first, then add an automated accessibility scan once the UI surfaces stabilize.
- Impact if deferred: accessibility regressions will rely on manual review.

### Long Artifact Interaction

- Decision: Should very long generated artifacts use a sticky local action bar, repeated approve/revise actions, or a split review layout?
- Why it matters: long artifacts can separate evidence from decision controls and increase accidental approval risk.
- Default recommendation: keep actions near the artifact header now; evaluate sticky or repeated actions after Product Wizard UX and Design System packages are integrated.
- Impact if deferred: long generated output may remain readable but inefficient for approval decisions.

### Critical Status Language

- Decision: Which state labels are founder-approved for critical UX: `blocked`, `failed`, `needed`, `urgent`, `approved`, `verified`, `deferred`, and future `running`?
- Why it matters: status wording must be consistent across dashboard, projects, setup, queues, and live runs.
- Default recommendation: preserve current labels for compatibility, but require each label to have a one-line meaning in the integrated design system.
- Impact if deferred: future screens may use inconsistent status names and weaken audit clarity.

## Implementation Handoff

- First slice: accessibility hardening for existing Product Wizard, project detail, dashboard decision queue, and setup readiness rows before adding new UI-heavy surfaces.
- Likely files or modules:
  - `src/hermes_company_os/static/styles.css`
  - `src/hermes_company_os/templates/project_new.html`
  - `src/hermes_company_os/templates/project.html`
  - `src/hermes_company_os/templates/dashboard.html`
  - `src/hermes_company_os/templates/setup.html`
  - `tests/test_product_wizard_routes.py`
  - `tests/test_product_wizard_acceptance.py`
  - `tests/test_app.py`
  - future browser-level UI tests if the project adds Playwright or another accessibility-capable runner.
- Tests to add:
  - route assertions for blocker copy next to disabled or unavailable actions;
  - rendered HTML assertions for accessible names on repeated row controls;
  - keyboard-only browser checks for `/projects/new`, project detail, decision update, and setup status update;
  - responsive overflow checks for desktop, tablet, and mobile widths with long generated text;
  - contrast verification for status pill variants, disabled buttons, muted text, and focus rings;
  - regression fixture for long artifact body, long decision context, long setup evidence, and long run output;
  - existing full route, docs, secret guard, `pytest`, and `ruff check .` verification before merge.
- No-secret scan scope:
  - this package doc;
  - all integrated UI/UX research docs;
  - generated dashboard/setup/project pages used by new tests;
  - generated profile and project artifacts touched by later implementation.
- Founder approval gate:
  - founder approves the accessibility baseline, mobile workflow scope, and test/tooling threshold before source implementation begins.
