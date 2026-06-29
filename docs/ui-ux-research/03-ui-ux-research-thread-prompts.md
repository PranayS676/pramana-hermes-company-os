# UI/UX Research Thread Prompts

Use these prompts to spawn focused Codex research threads after the founder approves the UI/UX Research Agent doctrine and package template.

Every thread must write one research package using `04-research-package-template.md`.

## Common Instructions For Every Thread

Use this block at the top of every research thread:

```text
You are a focused UI/UX research thread for Hermes Company OS.

Read:
- docs/agentic-company-os-roadmap.md
- docs/ui-ux-research/01-ui-ux-research-agent-doctrine.md
- docs/ui-ux-research/02-codex-subagent-research-operating-model.md
- docs/ui-ux-research/04-research-package-template.md

Your job is research and planning only. Do not edit source code. Do not write live Hermes profile files. Do not touch AppData. Do not include credentials, secret-looking values, raw tokens, or auth material.

Produce one markdown research package. Include workflow analysis, screens and states, accessibility notes, UX risks, implementation recommendations, acceptance checks, and founder decisions needed.
```

## Founder Control Plane UX

```text
Research the Founder Control Plane UX for Hermes Company OS.

Focus on:
- founder decision inbox;
- approvals;
- revisions;
- blockers;
- accepted risks;
- launch decisions;
- audit trail for why decisions were made.

Output target:
docs/ui-ux-research/packages/founder-control-plane-ux.md

Answer:
- What should the founder see first?
- Which decisions require urgent attention?
- How should blocked work be grouped?
- What states must be visible before approval?
- How should revision requests be written?
- What information is needed to trust an agent recommendation?
- What UI should be avoided?
```

## Product Wizard UX

```text
Research the Product Wizard UX for Hermes Company OS.

Focus on:
- idea intake;
- stage timeline;
- artifact preview;
- approve/revise/regenerate flow;
- artifact history;
- founder context visibility;
- transition from plan to execution.

Output target:
docs/ui-ux-research/packages/product-wizard-ux.md

Answer:
- Where does the current flow create confidence?
- Where can the founder get lost?
- What should improve before live Hermes generation?
- How should artifact comparisons work?
- How should revision requests be guided?
- What must be visible before Kanban or Codex execution?
```

## Agent Work Queue UX

```text
Research the Agent Work Queue UX for Hermes Company OS.

Focus on:
- per-agent work queues;
- Chief of Staff triage;
- queue state transitions;
- blocked work;
- review-needed work;
- founder approval handoffs.

Output target:
docs/ui-ux-research/packages/agent-work-queue-ux.md

Answer:
- What queue states must be visible?
- How should work be grouped by agent, project, stage, and urgency?
- How should blocked work request founder input?
- What should an agent detail page show?
- What should the Chief of Staff see across all agents?
- What UI makes autonomous work inspectable?
```

## Observability And Audit UX

```text
Research observability and audit UX for Hermes Company OS.

Focus on:
- live runs;
- retries;
- failures;
- cost and latency if available;
- audit event history;
- source inputs used;
- external messages or Kanban tasks created.

Output target:
docs/ui-ux-research/packages/observability-audit-ux.md

Answer:
- What must the founder inspect after an autonomous action?
- How should failed runs and retries be displayed?
- How should the system explain why work moved forward?
- What audit trail is needed before live autonomy is trusted?
- What should be exportable per project?
```

## Codex Project Execution UX

```text
Research Codex Project Execution UX for Hermes Company OS.

Focus on:
- approved code plan to implementation workstreams;
- branch/repo mapping;
- backend/frontend/test/docs workstreams;
- diff review;
- test evidence;
- PR readiness.

Output target:
docs/ui-ux-research/packages/codex-project-execution-ux.md

Answer:
- What should happen after code plan approval?
- How should multiple Codex workstreams be displayed?
- How should test status and diff status be summarized?
- What founder decisions are needed before repo creation or branch creation?
- How should the UI prevent premature shipping?
```

## Accessibility And Responsive UX

```text
Research accessibility and responsive UX for Hermes Company OS.

Focus on:
- keyboard navigation;
- focus states;
- semantic labels;
- color contrast;
- dense dashboard readability;
- mobile and tablet layout;
- long generated text handling.

Output target:
docs/ui-ux-research/packages/accessibility-responsive-ux.md

Answer:
- What accessibility standards should every dashboard surface meet?
- Which current or planned screens have the highest risk?
- What responsive rules should be required?
- How should generated artifacts avoid layout breakage?
- What acceptance checks should implementation agents run?
```

## Design System And Visual Polish

```text
Research the design system and visual polish direction for Hermes Company OS.

Focus on:
- operational dashboard density;
- controls;
- cards versus tables;
- status colors;
- icons;
- typography;
- spacing;
- visual hierarchy.

Output target:
docs/ui-ux-research/packages/design-system-visual-polish.md

Answer:
- What visual language fits a founder-led company OS?
- Which UI patterns should be standardized?
- What should buttons, statuses, timelines, cards, and tables look like?
- What should be avoided?
- What acceptance checks should prevent inconsistent UI?
```
