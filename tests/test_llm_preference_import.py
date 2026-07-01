import json

from hermes_company_os.llm_preference_import import (
    llm_preference_import_redirect,
    llm_preference_template_json,
    llm_preference_template_markdown,
    parse_llm_preference_reply,
)
from hermes_company_os.secret_guard import secret_violations

PREFERENCES = [
    {
        "agent_id": "chief-of-staff",
        "agent_name": "Chief of Staff",
        "provider": "openai-codex",
        "model": "gpt-5-codex",
        "fallback_provider": "",
        "fallback_model": "",
        "auth_method": "deferred_profile_secret",
        "status": "planned",
        "notes": "Credentials remain external.",
    },
    {
        "agent_id": "research-agent",
        "agent_name": "Research Agent",
        "provider": "openai-codex",
        "model": "gpt-5-codex",
        "fallback_provider": "",
        "fallback_model": "",
        "auth_method": "deferred_profile_secret",
        "status": "verified",
        "notes": "Previously smoke verified.",
    },
]


def test_llm_preference_template_exports_no_secret_json():
    markdown = llm_preference_template_markdown(PREFERENCES)
    payload = json.loads(llm_preference_template_json(PREFERENCES))
    raw = markdown + json.dumps(payload)

    assert "LLM Preference Reply Template" in markdown
    assert payload["verification_last"] is True
    assert payload["entry_points"]["bulk_import"] == "/setup/models#llm-preference-import"
    assert payload["preferences"][1]["status"] == "ready_for_verification"
    assert "verified" not in payload["allowed_statuses"]
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw
    assert secret_violations({"raw": raw}) == []


def test_parse_llm_preference_reply_collects_partial_updates():
    summary = parse_llm_preference_reply(
        json.dumps(
            {
                "preferences": [
                    {
                        "agent_id": "chief-of-staff",
                        "provider": "openai-codex",
                        "model": "gpt-5-codex",
                        "status": "needs_secret",
                    },
                    {
                        "agent_id": "research-agent",
                        "provider": "openrouter",
                        "model": "anthropic/claude-sonnet-4",
                        "fallback_provider": "openai-codex",
                        "fallback_model": "gpt-5-codex",
                        "auth_method": "profile_env",
                    },
                ]
            }
        ),
        PREFERENCES,
    )

    assert summary["updates"]["chief-of-staff"] == {
        "model": "gpt-5-codex",
        "provider": "openai-codex",
        "status": "needs_secret",
    }
    assert summary["updates"]["research-agent"] == {
        "auth_method": "profile_env",
        "fallback_model": "gpt-5-codex",
        "fallback_provider": "openai-codex",
        "model": "anthropic/claude-sonnet-4",
        "provider": "openrouter",
    }
    assert summary["imported"] == 2


def test_parse_llm_preference_reply_rejects_verified_and_bad_payloads():
    summary = parse_llm_preference_reply(
        json.dumps(
            {
                "preferences": [
                    {"agent_id": "missing-agent", "provider": "openai"},
                    {"agent_id": "chief-of-staff", "status": "verified"},
                    {"agent_id": "research-agent", "model": ""},
                    {"agent_id": "research-agent", "agent_name": "Ignored only"},
                    "not an object",
                ]
            }
        ),
        PREFERENCES,
    )

    assert summary["updates"] == {}
    assert summary["unknown_ids"] == ["missing-agent"]
    assert summary["invalid_preferences"] == [
        "chief-of-staff",
        "preference-5",
        "research-agent",
    ]
    assert summary["ignored_fields"] == ["research-agent.agent_name"]


def test_parse_llm_preference_reply_supports_markdown_fence():
    summary = parse_llm_preference_reply(
        """```json
        {"preferences":[{"agent_id":"chief-of-staff","status":"ready_for_verification"}]}
        ```""",
        PREFERENCES,
    )

    assert summary["updates"] == {
        "chief-of-staff": {"status": "ready_for_verification"}
    }


def test_llm_preference_import_redirect_targets_import_panel():
    redirect = llm_preference_import_redirect(
        {
            "imported": 2,
            "unknown_ids": ["missing"],
            "invalid_preferences": ["bad"],
            "ignored_fields": ["agent_name"],
        }
    )

    assert redirect == (
        "/setup/models?llm_preference_imported=2"
        "&llm_preference_unknown=1"
        "&llm_preference_invalid=1"
        "&llm_preference_ignored=1#llm-preference-import"
    )
