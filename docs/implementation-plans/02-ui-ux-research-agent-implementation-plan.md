# UI/UX Research Agent Implementation Plan

## Objective

Create the UI/UX Research Agent as a disciplined research function first, then later promote it into a live Hermes profile after founder approval.

The first implementation is documentation-only:

- doctrine;
- operating model;
- thread prompts;
- research package template;
- roadmap updates;
- implementation-plan integration.

## Current State

Current system has:

- Product Wizard V1 UI.
- Agent profile doctrine for the original 10 Hermes roles.
- Roadmap from 35-40 percent maturity toward a founder-led agentic company OS.
- No dedicated UI/UX Research Agent.
- No standard UX research package format.
- No defined process for multi-chat UX research integration.

## Deliverables

Documentation deliverables:

- UI/UX Research Agent index.
- UI/UX Research Agent doctrine.
- Codex subagent research operating model.
- UI/UX research thread prompts.
- Research package template.
- Updated roadmap milestone.
- Implementation-plan index.
- Founder Control Plane implementation plan.
- UI/UX Research Agent implementation plan.

Future source deliverables after founder approval:

- `ui-ux-research-agent` profile seed.
- Generated profile assets.
- Acceptance checks for UI/UX research outputs.
- Dashboard route or setup artifact for UI/UX research packages.

## Research Operating Model

Use parallel Codex threads only after the package template is stable.

Initial research batch:

1. Founder Control Plane UX.
2. Product Wizard UX.
3. Agent Work Queue UX.
4. Observability and Audit UX.
5. Codex Project Execution UX.
6. Accessibility and Responsive UX.
7. Design System and Visual Polish.

Each thread writes one package under:

`docs/ui-ux-research/packages/`

Central integration then creates:

- conflict-resolution summary;
- integrated UX recommendations;
- implementation backlog;
- founder decisions needed.

## Future Source Integration Direction

After founder approval, add the new profile through the same source-driven pattern used for other Hermes profiles:

- add doctrine entry;
- add seed/default profile;
- add generated SOUL/profile assets;
- add acceptance cases;
- add tests for generated live assets;
- keep AppData/live Hermes files untouched unless explicitly approved.

The agent should not be live until:

- doctrine is approved;
- first research package batch is complete;
- generated profile assets pass no-secret scans;
- profile acceptance checks exist.

## Parallel Codex Workstreams

Documentation batch:

- Doctrine thread: validates agent mandate and decision rights.
- Operating-model thread: validates multi-chat research process.
- Prompt thread: validates focused research prompts.
- Implementation-plan thread: maps research output into next milestones.
- QA thread: scans docs for completeness, contradictions, and no-secret safety.

Source integration batch later:

- Profile data thread: adds source doctrine and seeds.
- Asset generation thread: updates generated profile assets.
- Acceptance thread: adds profile acceptance checks.
- UI thread: exposes UI/UX research package status if needed.
- QA thread: full tests and generated-asset scans.

## Tests

Documentation-only pass:

- no-secret scan over all new docs;
- `py -3.11 -m poetry run pytest tests/test_docs.py`;
- path consistency check for referenced docs.

Future source pass:

- profile live asset tests;
- profile acceptance tests;
- repository seed tests;
- app route tests if UI is added;
- full `pytest`;
- full `ruff check .`;
- generated profile no-secret scan.

## Founder Approval Gates

Founder must approve:

- UI/UX Research Agent doctrine;
- research package template;
- first batch of research threads;
- integrated UX recommendations;
- promotion from docs-only concept to live Hermes profile.

Default recommendation:

- Keep the agent docs-only until the Founder Control Plane UX package and Product Wizard UX package are complete.

## Acceptance Criteria

- Roadmap includes UI/UX Research Agent milestone.
- New docs define doctrine, operating model, prompts, and package template.
- Implementation plans are present and linked.
- No live profile files are touched.
- No source code is changed in the documentation-only pass.
- No-secret scan passes.
- Documentation can be used to spawn parallel Codex research threads without additional decisions.
