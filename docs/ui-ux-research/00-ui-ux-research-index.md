# UI/UX Research Program Index

This folder is the source of truth for the future Hermes Company OS UI/UX Research Agent. It defines how UI/UX research is performed, how Codex subagents and multi-chat research threads should be coordinated, and how research becomes implementation plans.

The goal is not visual decoration. The goal is to make the founder-facing operating system usable enough to run a multi-agent company: clear decisions, visible blockers, trustworthy artifacts, reviewable execution, and low-friction approval.

## Current Status

Status: planning and research foundation.

The UI/UX Research Agent is not yet a live Hermes profile. It should become one after founder approval of this doctrine and after the first research packages are integrated.

## Documents

- `01-ui-ux-research-agent-doctrine.md`: mandate, operating principles, responsibilities, decision rights, outputs, and acceptance checks.
- `02-codex-subagent-research-operating-model.md`: how to run parallel Codex research threads and integrate their packages.
- `03-ui-ux-research-thread-prompts.md`: ready-to-use prompts for focused UI/UX research threads.
- `04-research-package-template.md`: standard package format every research thread must produce.

Related implementation plans:

- `../implementation-plans/00-agentic-implementation-plan-index.md`
- `../implementation-plans/01-founder-control-plane-implementation-plan.md`
- `../implementation-plans/02-ui-ux-research-agent-implementation-plan.md`

## Research Tracks

Initial research tracks:

1. Founder Control Plane UX.
2. Product Wizard UX.
3. Agent Work Queue UX.
4. Observability and Audit UX.
5. Codex Project Execution UX.
6. Accessibility and Responsive UX.
7. Design System and Visual Polish.

Each track should be run as a focused Codex thread or subagent assignment, then integrated centrally.

## Research Package Contract

Every research package must include:

- research question;
- target workflow;
- user and persona assumptions;
- screens and states needed;
- UX risks and anti-patterns;
- accessibility notes;
- implementation recommendations;
- acceptance checklist;
- founder decisions needed.

## Founder Approval Gates

Founder approval is required before:

- treating the UI/UX Research Agent as a live Hermes profile;
- spawning the first parallel research batch;
- converting research packages into UI implementation work;
- changing source code for the Founder Control Plane based on research;
- adding new dashboard surfaces that create, approve, or execute agent work.

## Integration Rule

Parallel research output is not authoritative by itself. A central integration pass must merge packages, resolve conflicts, preserve founder decisions, and produce an implementation plan before source work begins.
