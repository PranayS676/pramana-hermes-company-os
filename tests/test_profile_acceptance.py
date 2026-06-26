import json

from hermes_company_os.profile_acceptance import (
    profile_acceptance_json,
    profile_acceptance_markdown,
    profile_acceptance_suite,
)
from hermes_company_os.profile_doctrine import acceptance_cases_for
from hermes_company_os.secret_guard import secret_violations

AGENTS = [
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "role": "Engineering",
        "capabilities": ["architecture", "AWS design", "E2E testing"],
        "hermes_command": "engineering-manager",
    },
    {
        "id": "product-manager",
        "name": "Product Manager",
        "role": "Product",
        "capabilities": ["PRDs", "scope control"],
        "hermes_command": "product-manager",
    },
]


def test_profile_acceptance_suite_builds_role_specific_cases():
    suite = profile_acceptance_suite(
        AGENTS,
        [
            {
                "id": "engineering-manager-acceptance-1",
                "status": "verified",
                "evidence": "Founder accepted.",
            }
        ],
    )

    assert suite["title"] == "Profile Acceptance Suite"
    by_profile = {}
    for case in suite["cases"]:
        by_profile.setdefault(case["profile_id"], []).append(case)
    assert "smallest safe version" in " ".join(
        by_profile["engineering-manager"][0]["expected_signals"]
    )
    assert "founder idea intake" in by_profile["product-manager"][0]["title"].lower()
    assert (
        by_profile["engineering-manager"][0]["verification_route"]
    ) == "/setup/profile-smoke/engineering-manager"
    assert by_profile["engineering-manager"][0]["status"] == "verified"
    assert by_profile["engineering-manager"][0]["has_evidence"] is True
    assert len(suite["cases"]) == (
        len(acceptance_cases_for("engineering-manager"))
        + len(acceptance_cases_for("product-manager"))
    )


def test_profile_acceptance_exports_markdown_and_json_without_secrets():
    checks = [
        {
            "id": "engineering-manager-acceptance-1",
            "status": "failed",
            "evidence": "Needs better AWS tradeoffs.",
        }
    ]
    markdown = profile_acceptance_markdown(AGENTS, checks)
    payload = json.loads(profile_acceptance_json(AGENTS, checks))

    assert "Profile Acceptance Suite" in markdown
    assert "T0 fast path" in markdown
    assert "Do not use Slack, Telegram" in markdown
    assert "/setup/llm-provisioning.md" in markdown
    assert payload["title"] == "Profile Acceptance Suite"
    assert payload["cases"][0]["profile_id"] == "engineering-manager"
    assert payload["cases"][0]["status"] == "failed"
    assert "Status: `failed`" in markdown
    assert "/setup#profile-acceptance-tracking" in markdown
    assert "/setup/profile-acceptance.json" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown
    assert secret_violations({"markdown": markdown, "json": json.dumps(payload)}) == []
