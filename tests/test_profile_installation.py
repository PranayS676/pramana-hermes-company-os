import json

from hermes_company_os.profile_installation import (
    profile_installation_json,
    profile_installation_markdown,
    profile_installation_payload,
    profile_installation_powershell,
)
from hermes_company_os.secret_guard import secret_violations

AGENTS = [
    {
        "id": "chief-of-staff",
        "name": "Chief of Staff",
        "hermes_command": "chief-of-staff",
    },
    {
        "id": "engineering-manager",
        "name": "Engineering Manager",
        "hermes_command": "engineering-manager",
    },
]


def test_profile_installation_payload_lists_expected_files_and_entry_points():
    payload = profile_installation_payload(agents=AGENTS)

    assert payload["title"] == "Hermes Profile Installation Audit"
    assert payload["profile_root"] == "$HermesHome\\profiles"
    assert payload["identity_files"] == [
        "SOUL.md",
        "capabilities.json",
        "profile-manifest.json",
    ]
    assert payload["starter_files"] == [".env.example", "config.yaml.example"]
    assert payload["live_files_checked_for_presence_only"] == [".env", "config.yaml"]
    assert payload["profiles"][0]["profile_path"] == (
        "$HermesHome\\profiles\\chief-of-staff"
    )
    assert payload["profiles"][0]["apply_script"] == (
        "/setup/profile-apply/chief-of-staff.ps1"
    )
    assert payload["entry_points"]["runtime_preflight"] == (
        "/setup/runtime-preflight.md"
    )
    assert payload["entry_points"]["gateway_operations"] == (
        "/setup/gateway-operations.md"
    )


def test_profile_installation_exports_no_secret_audit_markdown_json_and_script():
    checks = [
        {
            "id": "chief-of-staff-profile-installation",
            "agent_id": "chief-of-staff",
            "agent_name": "Chief of Staff",
            "label": "Chief of Staff profile installation verified",
            "status": "verified",
            "evidence": "Local directory was checked.",
        }
    ]
    markdown = profile_installation_markdown(
        agents=AGENTS,
        profile_installation_checks=checks,
    )
    payload = json.loads(
        profile_installation_json(
            agents=AGENTS,
            profile_installation_checks=checks,
        )
    )
    script = profile_installation_powershell(AGENTS)
    raw = json.dumps(payload) + markdown + script

    assert "Hermes Profile Installation Audit" in markdown
    assert "/setup/bootstrap.ps1" in markdown
    assert "Credential Boundary" in markdown
    assert "Dashboard Tracking" in markdown
    assert payload["title"] == "Hermes Profile Installation Audit"
    assert payload["tracking"]["status"] == {"verified": 1}
    assert payload["tracking"]["checks"][0]["has_evidence"] is True
    assert payload["profiles"][1]["command"] == "engineering-manager"
    assert "Hermes Company OS profile installation audit" in script
    assert "HERMES_HOME" in script
    assert "LOCALAPPDATA" in script
    assert "Test-CommandAlias" in script
    assert "File contents were not printed" in script
    assert '"$fileName presence"' in script
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert "Local directory was checked" not in raw
    assert secret_violations({"raw": raw}) == []
