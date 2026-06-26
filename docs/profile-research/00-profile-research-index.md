# Profile Research Index

Status: finalized for research-doc use.

This folder captures the approved research basis for Pramana's Hermes profile rewrites. These documents are not live Hermes configuration. They are the source material to use before updating `SOUL.md`, generated prompts, live profile assets, or dashboard seed data.

## Completed Profile Research Docs

- `01-chief-of-staff.md`: operating cadence, escalation, Kanban, launch tiers, risk routing.
- `02-product-manager.md`: product scope, discovery, less-is-more judgment, launch-tier product policy.
- `03-research-agent.md`: evidence hierarchy, proof tags, research depth by tier.
- `04-engineering-manager.md`: architecture arbitration, smallest safe version, engineering gates.
- `05-backend-engineer.md`: backend boundaries, TDD, libraries, scale triggers, backend test tiers.
- `06-frontend-engineer.md`: UI tiering, accessibility, Playwright, UX research depth, frontend handoffs.
- `07-cloud-infra-agent.md`: AWS scale path, security/cost/observability, rollback and DR by tier.
- `08-test-automation-agent.md`: test matrix, CI budget, flaky-test policy, evidence packets.
- `09-marketing-agent.md`: positioning, proof-tagged claims, launch messaging, channel experiments.
- `10-qa-critic.md`: risk review, blocker lifecycle, accepted-risk policy, launch readiness.

## Cross-Agent Docs

- `90-cross-agent-critique.md`: critique findings from the cross-profile audit.
- `91-cross-agent-operating-model.md`: final founder decisions that resolve the open questions.
- `99-approved-profile-rewrite-backlog.md`: implementation backlog for converting research into live profile behavior.

## Final Founder Decisions

Use these decisions consistently across every profile:

- Launch tiers are `T0 Internal Experiment`, `T1 Private Beta`, `T2 Public Beta`, and `T3 GA`.
- Slack is the main workspace. Telegram is only for urgent founder action, failed critical runs, security/data/cost emergencies, or time-sensitive approval blockers.
- Hermes Kanban is the operating truth. Agents may create routine lane-specific cards directly. Chief of Staff owns cross-agent cards, launch gates, blockers, accepted risks, founder decisions, and board hygiene.
- PM owns product bet, target user/job, scope, acceptance criteria, metrics, and product interpretation. Research owns evidence quality and proof tags. Marketing owns positioning, copy, distribution, and demand experiments.
- PM simplicity wins when risk is low and reversible. Engineering Manager controls the minimum safety, reliability, security, maintainability, and operability floor.
- The default engineering approach is smallest safe version first. Scalable architecture belongs in an appendix until explicit scale triggers are met.
- Quality gates are tiered. MVP can reduce scope, polish, automation, and breadth. MVP cannot remove safety, honesty, reversibility, credential safety, data protection, or rollback.
- Public beta and GA require explicit founder approval. First external private beta also requires founder approval; later private-beta changes inside an approved scope may be handled by PM, EM, CoS, and QA.
- High-risk categories require QA review at any tier: credentials, customer data, payments, public messaging, autonomous tool actions, irreversible actions, security/privacy/legal exposure, or cost-runaway paths.
- Accepted risk must have owner, severity, tier, rationale, mitigation, expiry, monitoring, and rollback or unblock path. Public/customer-facing, security/privacy, cost-runaway, and GA risks require Pranay approval.

## Rewrite Rule

Do not convert these docs into live Hermes profile files until a profile-specific rewrite is requested. The next phase should update one profile at a time, then run no-secret scans, tests, generated asset checks, and profile acceptance prompts.

