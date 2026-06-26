import json

from hermes_company_os.slack_manifest import (
    slack_app_manifest,
    slack_app_manifest_json,
    slack_app_manifests_bundle_json,
)


def test_slack_app_manifest_uses_documented_shape_without_tokens():
    manifest = slack_app_manifest(
        {
            "id": "engineering-manager",
            "name": "Engineering Manager",
            "role": "Engineering",
            "slack_channel": "#engineering",
            "hermes_command": "engineering-manager",
        },
        {"slack_channel_engineering": "C123"},
    )

    assert manifest["_metadata"] == {"major_version": 2, "minor_version": 1}
    assert manifest["display_information"]["name"] == "Hermes Engineering Manager"
    assert manifest["display_information"]["background_color"] == "#2563EB"
    assert manifest["features"]["bot_user"]["display_name"] == (
        "Hermes Engineering Manager"
    )
    assert manifest["features"]["bot_user"]["always_online"] is True
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert manifest["settings"]["interactivity"]["is_enabled"] is True
    assert "chat:write" in manifest["oauth_config"]["scopes"]["bot"]
    assert "app_mention" in manifest["settings"]["event_subscriptions"]["bot_events"]
    assert "C123" in manifest["display_information"]["long_description"]
    assert "xoxb-" not in json.dumps(manifest)
    assert "xapp-" not in json.dumps(manifest)


def test_slack_app_manifest_json_round_trips():
    text = slack_app_manifest_json(
        {
            "id": "qa-critic",
            "name": "QA / Critic",
            "role": "Review",
            "slack_channel": "#qa-review",
            "hermes_command": "qa-critic",
        },
        {},
    )

    manifest = json.loads(text)
    assert manifest["display_information"]["name"] == "Hermes QA Critic"
    assert "#qa-review" in manifest["display_information"]["long_description"]


def test_slack_app_manifests_bundle_includes_profiles_and_commands():
    text = slack_app_manifests_bundle_json(
        [
            {
                "id": "product-manager",
                "name": "Product Manager",
                "role": "Product",
                "slack_channel": "#product",
                "hermes_command": "product-manager",
            }
        ],
        {"slack_channel_product": "C456"},
    )

    bundle = json.loads(text)
    assert bundle["product-manager"]["profile"]["hermes_command"] == "product-manager"
    assert bundle["product-manager"]["profile"]["home_channel_id"] == "C456"
    assert bundle["product-manager"]["manifest"]["display_information"]["name"] == (
        "Hermes Product Manager"
    )
