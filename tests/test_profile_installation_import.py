from hermes_company_os.profile_installation_import import (
    parse_profile_installation_audit,
    profile_installation_import_redirect,
)

CHECKS = [
    {
        "id": "chief-of-staff-profile-installation",
        "agent_id": "chief-of-staff",
    },
    {
        "id": "engineering-manager-profile-installation",
        "agent_id": "engineering-manager",
    },
]


def test_parse_profile_installation_audit_verifies_required_files_with_live_deferred():
    summary = parse_profile_installation_audit(
        raw_text="""
        FOUND chief-of-staff profile directory
        FOUND chief-of-staff command alias
        FOUND chief-of-staff SOUL.md
        FOUND chief-of-staff capabilities.json
        FOUND chief-of-staff profile-manifest.json
        FOUND chief-of-staff .env.example
        FOUND chief-of-staff config.yaml.example
        DEFER chief-of-staff .env presence
        DEFER chief-of-staff config.yaml presence
        Profile installation audit finished. File contents were not printed.
        """,
        profile_installation_checks=CHECKS,
    )

    update = summary["updates"]["chief-of-staff-profile-installation"]
    assert update["status"] == "verified"
    assert update["evidence"] == (
        "Profile installation audit passed. Live files deferred: "
        ".env presence, config.yaml presence."
    )
    assert summary["imported"] == 1
    assert summary["ignored_lines"] == []


def test_parse_profile_installation_audit_blocks_missing_required_items():
    summary = parse_profile_installation_audit(
        raw_text="""
        FOUND engineering-manager profile directory
        MISSING engineering-manager command alias
        FOUND engineering-manager SOUL.md
        FOUND engineering-manager capabilities.json
        FOUND engineering-manager profile-manifest.json
        FOUND engineering-manager .env.example
        MISSING engineering-manager config.yaml.example
        """,
        profile_installation_checks=CHECKS,
    )

    update = summary["updates"]["engineering-manager-profile-installation"]
    assert update["status"] == "blocked"
    assert update["evidence"] == (
        "Profile installation audit missing: command alias, config.yaml.example."
    )


def test_parse_profile_installation_audit_tracks_unknown_and_incomplete_lines():
    summary = parse_profile_installation_audit(
        raw_text="""
        FOUND unknown-agent profile directory
        FOUND chief-of-staff profile directory
        not an audit line
        """,
        profile_installation_checks=CHECKS,
    )

    assert summary["updates"] == {}
    assert summary["unknown_agent_ids"] == ["unknown-agent"]
    assert summary["incomplete_agent_ids"] == ["chief-of-staff"]
    assert summary["ignored_lines"] == ["not an audit line"]


def test_profile_installation_import_redirect_summarizes_parse_result():
    redirect = profile_installation_import_redirect(
        {
            "imported": 2,
            "unknown_agent_ids": ["unknown"],
            "incomplete_agent_ids": ["partial"],
            "ignored_lines": ["noise"],
        }
    )

    assert redirect == (
        "/setup?profile_installation_imported=2"
        "&profile_installation_unknown=1"
        "&profile_installation_incomplete=1"
        "&profile_installation_ignored=1"
        "#profile-installation-tracking"
    )
