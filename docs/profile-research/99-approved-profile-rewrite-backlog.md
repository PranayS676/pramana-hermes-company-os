# Approved Profile Rewrite Backlog

Status: ready for next phase.

This backlog converts the finalized research docs into a controlled implementation sequence. It does not authorize live profile edits by itself.

## Implementation Order

1. Chief of Staff
   - Add launch tiers, escalation matrix, Kanban creation policy, accepted-risk flow, blocker SLA.
   - Verify Slack/Telegram rules stay concise and urgent-only.

2. Product Manager
   - Add PM/EM arbitration, discovery ownership, product-improvement threshold, launch-tier product policy.
   - Verify less-is-more remains strict without bypassing safety.

3. Engineering Manager
   - Add smallest-safe-version doctrine, scale triggers, tiered engineering gate matrix.
   - Verify ambition is retained as a scale appendix and risk challenge.

4. Research Agent
   - Add proof tags, PM/Marketing handoff, tiered research depth.
   - Verify evidence output is concise and not academic by default.

5. Backend Engineer
   - Add module/service boundary rule, library evaluation rule, backend test tiers, refactor-for-scale checklist.
   - Verify no premature microservice bias.

6. Frontend Engineer
   - Add UI-change tiers, minimal UX research rule, frontend gate matrix, PM/Test/QA handoffs.
   - Verify small UI work remains lightweight.

7. Cloud Infrastructure Agent
   - Add AWS scale path, infra gates by tier, approval boundaries, rollback/DR minimums.
   - Verify early experiments do not inherit GA process.

8. Test Automation Agent
   - Add test matrix, default CI budget, flaky-test policy, evidence packet.
   - Verify MVP learning still has a safe fast path.

9. Marketing Agent
   - Add proof-tag usage, ownership boundaries, launch-tier marketing depth, lightweight teaching rule.
   - Verify unsupported claims are blocked.

10. QA / Critic
    - Add risk verdicts, accepted-risk lifecycle, blocker SLA, tiered QA matrix, Test Automation handoff.
    - Verify QA remains recommend/block-by-evidence, not process-heavy.

## Required Checks Per Profile Rewrite

- Update dashboard seed/default profile text if the profile doctrine changes.
- Update current SQLite profile record or import template only after approval.
- Regenerate live starter assets only after source and dashboard state are correct.
- Do not touch `.env`, credentials, Slack tokens, Telegram tokens, or provider keys.
- Run no-secret scans against generated artifacts.
- Run focused tests for changed generators and profile artifacts.
- Run full pytest before declaring the rewrite ready.
- Re-run profile acceptance after LLM credentials are available.

## Acceptance Standard

A rewritten profile is ready when:

- `SOUL.md` is concise enough to steer behavior.
- `PROMPTS.md` captures role-specific doctrine without becoming a textbook.
- `OPERATING_RULES.md` includes shared cross-agent policies.
- Capabilities are explicit and non-overlapping.
- The profile knows what to challenge, what to refuse, and when to escalate.
- The profile respects the credential boundary.
- The profile has at least one role-specific acceptance prompt.

