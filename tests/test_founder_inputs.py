import json

from hermes_company_os.founder_input_import import (
    founder_input_import_redirect,
    parse_founder_input_reply,
)
from hermes_company_os.founder_inputs import (
    founder_input_collector_powershell,
    founder_input_request_json,
    founder_input_request_markdown,
)
from hermes_company_os.secret_guard import secret_violations


def test_founder_input_request_markdown_separates_safe_inputs_from_external_secrets():
    markdown = founder_input_request_markdown(
        setup_inputs=[
            {
                "key": "founder_name",
                "group_name": "founder",
                "label": "Founder name",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
                "help_text": "Name agents should use.",
            },
            {
                "key": "llm_provider",
                "group_name": "llm",
                "label": "LLM provider",
                "value": "",
                "required": 0,
                "secret_policy": "secret_external",
                "help_text": "Deferred until last.",
            },
        ],
        secret_requirements=[
            {
                "category": "slack",
                "status": "needed",
                "label": "Chief of Staff Slack bot token",
                "owner_name": "Chief of Staff",
                "destination": "chief-of-staff Hermes profile .env",
            }
        ],
    )

    assert "Founder Input Request" in markdown
    assert "founder_name=  # Founder name (required)" in markdown
    assert "Safe Dashboard Inputs" in markdown
    assert "Deferred Non-Secret Preferences" in markdown
    assert "External Secrets To Load Later" in markdown
    assert "Focused Setup Reply Templates" in markdown
    assert "/setup#input-import" in markdown
    assert "/setup/slack-channel-template.md" in markdown
    assert "/setup/schedule-config-template.md" in markdown
    assert "Chief of Staff Slack bot token" in markdown
    assert "xoxb-" not in markdown
    assert "xapp-" not in markdown
    assert "sk-" not in markdown


def test_founder_input_request_json_is_structured_and_no_secret_examples():
    payload = json.loads(
        founder_input_request_json(
            setup_inputs=[
                {
                    "key": "slack_workspace_name",
                    "group_name": "slack",
                    "label": "Slack workspace name",
                    "value": "Founder Lab",
                    "required": 1,
                    "secret_policy": "non_secret",
                    "help_text": "Human-readable workspace name.",
                },
                {
                    "key": "llm_model",
                    "group_name": "llm",
                    "label": "LLM model",
                    "value": "",
                    "required": 0,
                    "secret_policy": "secret_external",
                    "help_text": "Deferred until last.",
                },
            ],
            secret_requirements=[],
        )
    )

    assert payload["safe_dashboard_inputs"][0]["status"] == "captured"
    assert payload["deferred_preferences"][0]["key"] == "llm_model"
    focused_by_id = {item["id"]: item for item in payload["focused_setup_imports"]}
    assert focused_by_id["telegram_recipient"]["template"] == (
        "/setup/telegram-recipient-template.md"
    )
    assert focused_by_id["schedule_config"]["dashboard_anchor"] == (
        "/setup#schedule-config-import"
    )
    assert payload["entry_points"]["reply_import"] == "/setup#input-import"
    assert payload["entry_points"]["collector_script"] == "/setup/founder-inputs.ps1"
    assert payload["entry_points"]["safe_inputs"] == "/setup#inputs"
    assert payload["entry_points"]["slack_bot_user_template"] == (
        "/setup/slack-bot-user-map-template.md"
    )
    raw = json.dumps(payload)
    assert "xoxb-" not in raw
    assert "xapp-" not in raw
    assert "sk-" not in raw


def test_founder_input_collector_script_prompts_only_for_safe_values():
    script = founder_input_collector_powershell(
        [
            {
                "key": "founder_name",
                "group_name": "founder",
                "label": "Founder name",
                "value": "",
                "required": 1,
                "secret_policy": "non_secret",
                "help_text": "Name agents should use.",
            },
            {
                "key": "llm_provider",
                "group_name": "llm",
                "label": "LLM provider",
                "value": "",
                "required": 0,
                "secret_policy": "secret_external",
                "help_text": "Deferred until last.",
            },
        ]
    )

    assert "Hermes Company OS founder input collector" in script
    assert "founder_name" in script
    assert "LLM provider" not in script
    assert "PostDashboardInputs" in script
    assert "/setup/founder-input-reply" in script
    assert "Write-Host '```text'" in script
    assert "Write-Host '```'" in script
    assert 'Write-Host "```text"' not in script
    assert "xoxb-" not in script
    assert "xapp-" not in script
    assert "sk-" not in script
    assert "API_KEY=" not in script
    assert secret_violations({"script": script}) == []


def test_parse_founder_input_reply_imports_only_safe_known_keys():
    summary = parse_founder_input_reply(
        raw_text="""
        ```text
        founder_name=Masad  # Founder name
        slack_workspace_name: Hermes Lab
        llm_provider=openai
        unknown_key=value
        not a key value line
        ```
        """,
        setup_inputs=[
            {
                "key": "founder_name",
                "secret_policy": "non_secret",
            },
            {
                "key": "slack_workspace_name",
                "secret_policy": "non_secret",
            },
            {
                "key": "llm_provider",
                "secret_policy": "secret_external",
            },
        ],
    )

    assert summary["values"] == {
        "founder_name": "Masad",
        "slack_workspace_name": "Hermes Lab",
    }
    assert summary["imported"] == 2
    assert summary["deferred_keys"] == ["llm_provider"]
    assert summary["unknown_keys"] == ["unknown_key"]
    assert summary["ignored_lines"] == ["not a key value line"]


def test_founder_input_import_redirect_summarizes_parse_result():
    redirect = founder_input_import_redirect(
        {
            "imported": 2,
            "unknown_keys": ["unknown_key"],
            "deferred_keys": ["llm_provider"],
            "ignored_lines": ["bad line"],
        }
    )

    assert redirect == (
        "/setup?input_imported=2&input_unknown=1&input_deferred=1&input_ignored=1#inputs"
    )
