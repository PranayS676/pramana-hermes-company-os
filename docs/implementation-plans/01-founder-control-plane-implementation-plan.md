# Founder Control Plane Implementation Plan

## Objective

Build the founder-facing control surface that makes agentic work trustworthy. The founder should see decisions, blockers, revisions, accepted risks, and approvals in one place before the system gains more autonomy.

This milestone should be implemented before live Hermes generation, agent queues, or Codex execution.

## Current State

Current system has:

- Founder decisions seeded and displayed in limited setup/dashboard contexts.
- Product Wizard stage approve, revise, regenerate, and Kanban gating.
- Project artifacts and stage history.
- No central founder inbox for project decisions.
- No unified state model for decisions created by wizard or future agents.

## Deliverables

- Founder Decision Inbox route.
- Dashboard summary for open founder decisions.
- Decision categories:
  - artifact approval;
  - revision request;
  - agent question;
  - blocker;
  - accepted risk;
  - external action approval;
  - launch decision.
- Decision records linked to project, stage, artifact, owner agent, and evidence.
- Product Wizard approval and revision actions reflected in the decision audit trail.
- Tests for create, list, resolve, reject, filter, and secret rejection.

## Data Model Direction

Extend founder decision records with optional fields:

- `project_id`;
- `stage_id`;
- `artifact_id`;
- `owner_agent_id`;
- `decision_type`;
- `urgency`;
- `requires_founder_approval`;
- `source`;
- `evidence`;
- `resolved_at`;
- `resolution_note`.

Keep fields optional so existing setup decisions remain valid.

## UI Direction

Add a founder inbox view with:

- open decisions first;
- filters by project, urgency, decision type, and owner agent;
- compact decision rows;
- detail panel with context and evidence;
- approve, reject, revise, answer, and mark-risk-accepted actions;
- no credential entry fields.

Dashboard should show:

- open decision count;
- urgent decision count;
- blocked project count;
- next founder action.

## Product Wizard Integration

Wizard should create or update decision records for:

- stage artifact generated and awaiting review;
- revision requested;
- stage approved;
- task stage approved and Kanban eligible;
- acceptance stage ready for launch review.

Approval remains founder-led. Agent outputs should not silently mark founder decisions resolved.

## Parallel Codex Workstreams

Recommended threads after this plan is approved:

- Backend/data thread: schema extension, repository APIs, migration tests.
- UI thread: inbox template, dashboard summary, project detail decision links.
- Route thread: decision list/detail/update routes and validation.
- QA thread: acceptance tests, no-secret tests, invalid transition tests.
- Documentation thread: update operating docs and founder guide.

Central integration must merge the work before commit.

## Tests

Add or update:

- repository tests for decision fields and state transitions;
- route tests for inbox, filters, and updates;
- Product Wizard route tests for decision audit links;
- secret guard tests for decision text and evidence;
- UI assertions for open decision labels and actions;
- regression test that existing setup decisions still render.

Verification commands:

- `py -3.11 -m poetry run pytest tests/test_founder_decisions.py tests/test_app.py`
- `py -3.11 -m poetry run pytest`
- no-secret scan over generated decision pages and docs.

## Founder Approval Gates

Founder must approve:

- decision categories;
- urgency levels;
- actions allowed from inbox;
- which decisions can be marked resolved by an agent versus founder only.

Default recommendation:

- Only founder can resolve launch, accepted-risk, external-action, and final artifact approval decisions.
- Agents can create decisions and propose resolutions.

## Acceptance Criteria

- Founder can see all open project decisions in one inbox.
- Product Wizard review work appears in the same decision system.
- Blocking decisions prevent premature execution.
- Existing setup decisions continue to work.
- Secret-like values are rejected.
- Tests and no-secret scan pass.
