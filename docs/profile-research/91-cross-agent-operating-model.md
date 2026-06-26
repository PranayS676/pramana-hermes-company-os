# Cross-Agent Operating Model

Status: founder decisions finalized for documentation.

This document answers the open questions raised by the profile research threads and provides the operating policy each Hermes profile should follow after rewrite.

## Launch Tiers

| Tier | Meaning | Founder Approval | Typical Gates |
| --- | --- | --- | --- |
| T0 Internal Experiment | Pranay/internal agents only; learning or throwaway workflow. | Not required unless it changes direction, cost, credentials, data, or schedule materially. | Owner, learning goal, stop condition, no secrets, basic smoke/manual proof. |
| T1 Private Beta | Small invited group or trusted design partners. | Required for first external exposure. Later changes inside approved scope may be approved by PM/EM/CoS/QA. | PM scope, Research evidence, support path, rollback, basic observability, QA review for high-risk surfaces. |
| T2 Public Beta | Public or broad external access, even if unpaid. | Required. | Stronger QA, monitoring, claim audit, privacy/security review, support owner, rollback, public messaging review. |
| T3 GA | Dependable production/customer offering. | Required. | Full readiness packet, support/incident path, SLO/recovery target, accepted-risk review, launch comms, rollback/DR, founder go/no-go. |

First paid customer triggers at least T2 gates unless Pranay explicitly approves a narrower design-partner exception.

## Decision Ownership

| Area | DRI | Input / Challenge |
| --- | --- | --- |
| Founder strategy and Type 1 decisions | Pranay | Chief of Staff prepares options and escalation. |
| Routing, board hygiene, standups, risks, decisions | Chief of Staff | All profiles. |
| Product bet, target user/job, scope, acceptance criteria, metrics | Product Manager | Research, Marketing, EM, QA. |
| Evidence quality, proof tags, source confidence | Research Agent | PM and Marketing consume; QA may challenge. |
| Engineering safety floor, architecture risk, maintainability | Engineering Manager | Backend, Frontend, Cloud, Test Automation, QA. |
| Backend APIs, data model, modules, migrations, service boundaries | Backend Engineer | EM, Cloud, Test Automation. |
| UI implementation, accessibility, state, component boundaries | Frontend Engineer | PM, UX if later added, Test Automation, QA. |
| AWS/cloud path, security boundaries, cost, observability, rollback | Cloud Infrastructure Agent | EM, Backend, QA. |
| Test strategy, CI gates, evidence packets, flake policy | Test Automation Agent | EM and QA. |
| Positioning, copy, launch assets, channels, experiments | Marketing Agent | PM and Research; QA reviews claims/risk. |
| Risk classification, contradictions, launch-readiness challenge | QA / Critic | CoS routes; owners fix or accept. |

## PM / EM Arbitration

PM controls what is worth building. EM controls whether the proposed way of building it is safe enough.

PM simplicity wins when the change is low-risk, reversible, and inside the current launch tier. EM may block or escalate when pruning creates material risk: credential exposure, data loss, security/privacy issue, untestable critical flow, unreliable external behavior, irreversible architecture, or large future migration.

If unresolved, Chief of Staff creates a founder decision card with options:

- PM-preferred scope and learning benefit.
- EM-preferred safety floor and risk rationale.
- Smallest safe compromise.
- Cost/time/risk of deferring.

## Smallest Safe Version

Every engineering plan should include:

1. Smallest safe version for the current tier.
2. Scale appendix with explicit triggers.
3. Tests and observability proportional to tier and blast radius.
4. What will be deleted, simplified, or revisited later.

Scale triggers include external users, real customer data, repeated manual recovery, latency/cost thresholds, data model blocking product changes, concurrency/queueing, tenant isolation, insufficient observability, or founder-approved hardening.

## Escalation

Slack is default. Telegram is urgent only.

| Event | Action |
| --- | --- |
| Routine clarification | Existing Kanban card or Slack thread; no founder escalation. |
| Routine profile task | Agent may create lane-specific Kanban card directly. |
| Product improvement | Kanban proposal and Slack review; batch to Pranay unless direction/scope/tier changes. |
| Founder decision | Chief of Staff decision card and `#founder-command`. |
| Time-sensitive blocker needing founder action | Slack plus Telegram through Chief of Staff. |
| Failed critical run, credential/security/data/cost emergency | `#alerts`, Kanban blocker, Telegram if founder action is needed. |
| Accepted risk | Risk card with owner, expiry, mitigation, monitoring, and approval authority. |

## Risk Acceptance

| Risk Class | Who Can Accept |
| --- | --- |
| Minor internal risk | Owning agent or manager. |
| Major T0/T1 risk without customer/security/privacy/cost exposure | Chief of Staff with owning PM/EM. |
| Public/customer-facing, security/privacy, cost-runaway, brand/legal, strategic, or GA risk | Pranay. |
| Credential leakage, customer-data exposure, active exploit, unsupported public hard claim | Default block; fix before proceeding unless Pranay explicitly records an emergency exception. |

Accepted risks expire:

- T0: 7 days or experiment end.
- T1: 14 days.
- T2: 30 days.
- T3: 30 days maximum, shorter for security/customer data.

Expired accepted risks revert to unresolved major risk or blocker.

## Blocker SLA

- P0: active customer/security/data/cost/critical-run risk. Immediate CoS routing; Telegram if founder action is needed.
- P1: blocks current work or launch gate. Owner and unblock path within 4 business hours.
- P2: blocked task without urgent launch impact. Resolve or update by next standup or 1 business day.
- P3: clarification, cleanup, improvement. Track in Kanban; no escalation.

Default business hours are Monday-Friday, 9:00 AM-5:00 PM ET. High-risk releases should happen 9:00 AM-4:00 PM ET, preferably before the 3:00 PM standup.

## Testing And CI

Default required PR checks should target 10 minutes or less. Longer suites belong in pre-release, nightly, or explicit high-risk gates.

Minimum for every change:

- tier, owner, acceptance criterion or learning goal;
- changed-surface and risk classification;
- no-secret check;
- basic proof/smoke evidence;
- rollback or stop condition when runtime behavior changes.

High-risk overlay always adds deeper review for credentials, customer data, payments, public messaging, autonomous tool actions, irreversible actions, security/privacy/legal exposure, or cost-runaway paths.

## Marketing And Evidence

External-facing marketing claims require proof tags:

- `PROOF-PRIMARY`
- `PROOF-CUSTOMER`
- `PROOF-BENCH`
- `PROOF-COMPETITOR`
- `PROOF-MARKET`
- `PROOF-INFERENCE`
- `PROOF-SPECULATIVE`
- `PROOF-BLOCKED`

Marketing may draft from inference, but public claims must be externally safe, qualified, and Research-backed when material. Public beta and GA require Research review for market/category claims and QA review for claim-risk.

## Default Technical Decisions

- Production database default: Postgres unless a product-specific reason says otherwise.
- Local/internal prototype storage may use SQLite or plain files when simpler.
- Backend service split default: no separate service unless boundary, owner, scaling/reliability, test, observability, and migration criteria are met.
- Frontend stack default: Next.js for production web apps; Vite is acceptable for simple internal tools or isolated frontends.
- UI foundation: customize proven primitives such as Radix/shadcn before creating a custom design system. Create a design system only after repeated needs emerge.
- Cloud default: local-first for T0, simple AWS managed services for T1/T2, formal production discipline for T3.
- AWS region default: `us-east-1` unless compliance, latency, or customer needs say otherwise.
- IaC default: stay tool-neutral until architecture is known; prefer the simplest credible choice that the project can maintain.

