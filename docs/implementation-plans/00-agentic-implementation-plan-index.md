# Agentic Implementation Plan Index

This folder turns the agentic roadmap into implementation-ready plans. Each plan should be small enough to hand to a Codex thread or engineering agent without requiring it to invent product decisions.

The current strategy is to move from the Product Wizard foundation toward a mature founder-led agentic company OS through approved milestones.

## Plan Inventory

- `01-founder-control-plane-implementation-plan.md`
  - First product implementation milestone.
  - Builds the founder inbox for decisions, blockers, revisions, risk acceptance, and approvals.

- `02-ui-ux-research-agent-implementation-plan.md`
  - Documentation and later source implementation plan for the UI/UX Research Agent.
  - Establishes research doctrine, parallel Codex research packages, and future profile integration.

## Required Plan Shape

Every implementation plan should include:

- objective;
- current state;
- deliverables;
- data model or route changes if applicable;
- UI changes if applicable;
- tests;
- no-secret scan scope;
- founder approval gates;
- rollout notes;
- handoff package for parallel Codex threads.

## Planning Rules

- Do not implement live autonomy before the founder control surface is trustworthy.
- Do not implement UI-heavy surfaces before UI/UX research packages are integrated.
- Do not wire live Hermes execution until local/demo mode remains safe and tested.
- Do not spawn Codex workstreams from approved code plans until project execution state is modeled.
- Do not create external messages or Kanban tasks without idempotency and audit records.

## Near-Term Sequence

1. Founder Control Plane implementation.
2. UI/UX Research Agent documentation and research package batch.
3. Agent Work Queue implementation plan.
4. Live Hermes Profile Execution implementation plan.
5. Company Memory implementation plan.
6. Codex Project Execution implementation plan.
7. Cross-Agent Review Loop implementation plan.
8. Slack, Telegram, and Kanban Operating Loop implementation plan.
9. Observability and Audit implementation plan.
10. Launch and Release Management implementation plan.

## Verification Standard

Documentation-only plans:

- no-secret scan over docs;
- docs tests if available;
- path/link consistency check.

Source implementation plans:

- focused tests for touched behavior;
- full test suite when schema, routes, templates, or generated artifacts change;
- no-secret scan over generated assets;
- founder-visible acceptance checklist.
