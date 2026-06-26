from __future__ import annotations

import json

from hermes_company_os.profile_doctrine import all_acceptance_cases

ROLE_CASES = all_acceptance_cases()


def profile_acceptance_suite(
    agents: list[dict],
    acceptance_checks: list[dict] | None = None,
) -> dict:
    checks_by_id = {check["id"]: check for check in acceptance_checks or []}
    cases = []
    for agent in agents:
        role_cases = ROLE_CASES.get(agent["id"], [])
        for index, case in enumerate(role_cases, start=1):
            case_id = f"{agent['id']}-acceptance-{index}"
            tracked = checks_by_id.get(case_id, {})
            cases.append(
                {
                    "id": case_id,
                    "profile_id": agent["id"],
                    "profile_name": agent["name"],
                    "hermes_command": agent["hermes_command"],
                    "title": case["title"],
                    "prompt": _prompt(agent, case["prompt"]),
                    "expected_signals": case["expected"],
                    "failure_signals": case["failure"],
                    "status": tracked.get("status", "needed"),
                    "has_evidence": bool(tracked.get("evidence", "").strip()),
                    "verification_route": f"/setup/profile-smoke/{agent['id']}",
                    "tracking_route": f"/setup#profile-acceptance-tracking-{case_id}",
                }
            )
    return {
        "title": "Profile Acceptance Suite",
        "purpose": "Verify starter Hermes profiles before using them for founder projects.",
        "cases": cases,
    }


def profile_acceptance_json(
    agents: list[dict],
    acceptance_checks: list[dict] | None = None,
) -> str:
    return json.dumps(profile_acceptance_suite(agents, acceptance_checks), indent=2) + "\n"


def profile_acceptance_markdown(
    agents: list[dict],
    acceptance_checks: list[dict] | None = None,
) -> str:
    suite = profile_acceptance_suite(agents, acceptance_checks)
    lines = [
        "# Profile Acceptance Suite",
        "",
        "Use this after profile identity files are applied and LLM credentials are "
        "loaded. These prompts verify that each Hermes profile behaves according to "
        "its role before you start the first real company idea.",
        "",
        "## How To Use",
        "",
        "1. Run `/setup/runtime-preflight.md` and fix missing profile commands.",
        "2. Review `/setup/llm-provisioning.md`, then finish `/setup/llm-finalize.md` "
        "enough for profile prompts to work.",
        "3. Run each acceptance prompt through the matching Hermes profile command.",
        "4. Compare the response against expected and failure signals.",
        "5. Track pass/fail status in `/setup#profile-acceptance-tracking`.",
        "6. Update profile SOUL/capabilities from the agent page if a case fails.",
        "",
        "## Cases",
        "",
    ]
    for case in suite["cases"]:
        lines.extend(_case_lines(case))
    lines.extend(
        [
            "## Completion Criteria",
            "",
            "- Every profile passes its role-specific acceptance prompt.",
            "- Every tracked acceptance check is marked `verified` in `/setup`.",
            "- Failed cases result in profile SOUL/capability updates.",
            "- Basic `/setup#profile-smoke` checks are still passing after updates.",
            "- No prompt asks a profile to use Slack, Telegram, browsing, or external tools.",
            "",
            "## Exports",
            "",
            "- JSON suite: `/setup/profile-acceptance.json`",
            "- Bulk reply template: `/setup/profile-acceptance-template.md`",
            "- Bulk reply template JSON: `/setup/profile-acceptance-template.json`",
            "- Profile artifacts: `/setup/profile-artifacts.md`",
            "",
        ]
    )
    return "\n".join(lines)


def _prompt(agent: dict, task: str) -> str:
    return "\n".join(
        [
            "Hermes Company OS profile acceptance test.",
            "",
            f"Profile: {agent['name']} ({agent['id']})",
            f"Role: {agent['role']}",
            f"Capabilities: {', '.join(agent['capabilities'])}",
            "",
            "Task:",
            task,
            "",
            "Constraints:",
            "- Do not use Slack, Telegram, browsing, files, or external tools.",
            "- Return a concise structured response.",
            "- Make the role-specific judgment visible.",
        ]
    )


def _case_lines(case: dict) -> list[str]:
    return [
        f"### {case['profile_name']} - {case['title']}",
        "",
        f"- Case ID: `{case['id']}`",
        f"- Status: `{case['status']}`",
        f"- Evidence captured: {'yes' if case['has_evidence'] else 'no'}",
        f"- Profile command: `{case['hermes_command']}`",
        f"- Dashboard smoke route: `{case['verification_route']}`",
        f"- Tracking route: `{case['tracking_route']}`",
        "",
        "Prompt:",
        "",
        "```text",
        case["prompt"],
        "```",
        "",
        "Expected signals:",
        "",
        *[f"- {signal}" for signal in case["expected_signals"]],
        "",
        "Failure signals:",
        "",
        *[f"- {signal}" for signal in case["failure_signals"]],
        "",
    ]
