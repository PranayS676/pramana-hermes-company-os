# Cross-Agent Critique

Status: finalized critique summary.

The cross-agent audit found that all ten profile research docs are substantial and useful, but should not be converted directly into live Hermes profile behavior without shared operating rules. The individual docs were strong in isolation; the risk was conflict between roles once they run together.

## Completeness Verdict

All ten expected profile research docs exist and contain enough research, doctrine, and candidate prompt material to support the next rewrite phase. No live profile rewrite should happen directly from the first drafts alone.

## Findings

1. No shared launch-tier policy existed across the first research drafts.
   Product, engineering, cloud, testing, marketing, and QA all used proportionality language, but each role defined it locally. This would make agents disagree about how much evidence, testing, infrastructure, and founder approval are required.

2. PM, Research, and Marketing overlapped on discovery and evidence.
   Product should own the product bet and interpretation. Research should own evidence quality and proof tags. Marketing should own audience framing, positioning, copy, channels, and demand experiments.

3. Engineering ambition needed a common pruning rule.
   Engineering Manager, Backend, and Cloud all value scale and strong architecture. The safe common default is smallest safe version first, with scalable architecture as an appendix and explicit scale triggers.

4. QA and Chief of Staff needed an accepted-risk and blocker model.
   QA should recommend, classify, and judge adequacy. Chief of Staff should route, record, and escalate. Pranay should accept public/customer-facing, strategic, security/privacy, cost-runaway, or GA-level risks.

5. The docs risked process drag without tiering.
   Strong research, testing, observability, and teaching rules are valuable, but applying full public-launch rigor to every experiment would slow the company. Tiering is mandatory.

## Cross-Profile Contradiction Table

| Tension | Final Resolution |
| --- | --- |
| Product less-is-more vs Engineering ambition | PM owns scope and user value; EM owns safety floor. If unresolved, Chief of Staff routes options to Pranay. |
| Backend deep modules vs Cloud distributed scale | Default to deep modules in one deployable. Separate services require explicit scale/ownership/reliability triggers. |
| QA blocker behavior vs Chief of Staff escalation | QA recommends severity and blocker status. CoS records, assigns owner/SLA, and escalates only when needed. |
| Marketing claims vs Research evidence | External claims require proof tags. Unsupported/speculative claims stay internal. |
| Test gates vs MVP learning | Tests are tiered. MVP may reduce polish and scope, not safety or reversibility. |

## Docs That Needed Finalization

Every profile doc needed at least a final founder-decision section so it would no longer end with unresolved questions. The most important revisions were:

- `01-chief-of-staff.md`: launch tiers, escalation matrix, accepted-risk flow, blocker SLA, Kanban creation model.
- `02-product-manager.md`: PM/EM arbitration, discovery ownership, launch-tier product policy, product-improvement threshold.
- `04-engineering-manager.md`: smallest safe version, scale triggers, tiered engineering gates.
- `08-test-automation-agent.md`: launch-tier test matrix, CI budget, flaky-test policy, QA handoff.
- `10-qa-critic.md`: accepted-risk lifecycle, blocker SLA, launch-tier QA matrix.

## Go / No-Go

Go for using these docs as the research basis for profile rewrite.

No-go for directly copying all research prose into live Hermes prompts. The next step must be a profile-specific rewrite pass that turns the research into concise `SOUL.md`, generated prompt rules, operating rules, and acceptance checks.

