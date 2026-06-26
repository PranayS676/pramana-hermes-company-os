import json

from hermes_company_os.profile_artifacts import (
    profile_apply_powershell,
    profile_artifacts_markdown,
    profile_manifest_json,
    profile_soul_markdown,
)


def test_profile_artifacts_markdown_contains_soul_values():
    markdown = profile_artifacts_markdown(
        [
            {
                "id": "engineering-manager",
                "name": "Engineering Manager",
                "slack_channel": "#engineering",
                "hermes_command": "engineering-manager",
                "description": "Creates architecture plans.",
                "capabilities": ["smallest safe architecture", "rollback planning"],
                "soul": "Think big about testing and AWS.",
            }
        ]
    )

    assert "# Hermes Company OS Profile Artifacts" in markdown
    assert "## Engineering Manager" in markdown
    assert "- smallest safe architecture" in markdown
    assert "- rollback planning" in markdown
    assert "Think big about testing and AWS." in markdown


def test_profile_soul_markdown_exports_single_profile_soul():
    soul = profile_soul_markdown({"soul": "Think big about testing and AWS."})

    assert soul == "Think big about testing and AWS.\n"


def test_profile_manifest_json_exports_routing_and_artifact_links():
    manifest = json.loads(
        profile_manifest_json(
            {
                "id": "engineering-manager",
                "name": "Engineering Manager",
                "role": "Engineering",
                "description": "Creates architecture plans.",
                "soul": "Think big about testing and AWS.",
                "capabilities": ["architecture", "testing"],
                "slack_channel": "#engineering",
                "telegram_policy": "Escalate through Chief of Staff.",
                "hermes_command": "engineering-manager",
            }
        )
    )

    assert manifest["id"] == "engineering-manager"
    assert manifest["routing"]["hermes_command"] == "engineering-manager"
    assert manifest["capabilities"] == ["architecture", "testing"]
    assert manifest["setup_exports"]["profile_env"] == (
        "/setup/profile-env/engineering-manager.env"
    )
    assert "xoxb-" not in json.dumps(manifest)
    assert "xapp-" not in json.dumps(manifest)
    assert "sk-" not in json.dumps(manifest)


def test_profile_apply_powershell_writes_identity_files_without_tokens():
    script = profile_apply_powershell(
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "role": "Engineering",
            "description": "Creates architecture plans.",
            "soul": "Think big about testing and AWS.",
            "capabilities": ["architecture", "testing"],
            "slack_channel": "#engineering",
            "telegram_policy": "Escalate through Chief of Staff.",
            "hermes_command": "engineering-manager",
        }
    )

    assert "hermes profile create engineering-manager" in script
    assert "SOUL.md" in script
    assert "capabilities.json" in script
    assert "profile-manifest.json" in script
    assert "HERMES_HOME" in script
    assert "LOCALAPPDATA" in script
    assert ".env.example" in script
    assert "config.yaml.example" in script
    assert "Invoke-WebRequest" in script
    assert "/setup/profile-env/engineering-manager.env" in script
    assert "/setup/profile-config/engineering-manager.yaml" in script
    assert "SLACK_BOT_TOKEN" not in script
    assert "TELEGRAM_BOT_TOKEN" not in script
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
