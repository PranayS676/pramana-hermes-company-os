import json

from hermes_company_os.secret_guard import secret_violations
from hermes_company_os.telegram_recipient_import import (
    parse_telegram_recipient_reply,
    telegram_recipient_import_redirect,
    telegram_recipient_template_json,
    telegram_recipient_template_markdown,
)


def test_telegram_recipient_templates_are_no_secret_and_show_current_values():
    setup_values = {
        "founder_telegram_user_id": "123456789",
        "telegram_home_channel": "-100987654321",
    }
    markdown = telegram_recipient_template_markdown(setup_values)
    payload = json.loads(telegram_recipient_template_json(setup_values))
    raw = markdown + json.dumps(payload)

    assert "Telegram Recipient ID Reply Template" in markdown
    assert "founder_telegram_user_id=123456789" in markdown
    assert "telegram_home_channel=-100987654321" in markdown
    assert payload["entry_points"]["bulk_import"] == "/setup/inputs#telegram-recipient-import"
    assert payload["values"]["founder_telegram_user_id"] == "123456789"
    assert secret_violations({"raw": raw}) == []


def test_parse_telegram_recipient_reply_accepts_json_and_lines():
    json_summary = parse_telegram_recipient_reply(
        '{"founder_telegram_user_id":"123456789","telegram_home_channel":"-100987654321"}'
    )
    line_summary = parse_telegram_recipient_reply(
        "founder_telegram_user_id=987654321\nunknown_key=123\nnot a key value line"
    )

    assert json_summary["values"] == {
        "founder_telegram_user_id": "123456789",
        "telegram_home_channel": "-100987654321",
    }
    assert line_summary["values"] == {"founder_telegram_user_id": "987654321"}
    assert line_summary["unknown_keys"] == ["unknown_key"]
    assert line_summary["ignored_lines"] == ["not a key value line"]


def test_parse_telegram_recipient_reply_rejects_invalid_ids_and_placeholders():
    summary = parse_telegram_recipient_reply(
        """
        founder_telegram_user_id=REPLACE_WITH_USER_ID
        telegram_home_channel=not-a-number
        """
    )

    assert summary["values"] == {}
    assert summary["invalid_keys"] == ["telegram_home_channel"]
    assert summary["ignored_lines"] == ["founder_telegram_user_id=<empty>"]


def test_telegram_recipient_redirect_counts_import_summary():
    summary = {
        "imported": 2,
        "unknown_keys": ["unknown"],
        "invalid_keys": [],
        "ignored_lines": ["ignored"],
    }

    assert telegram_recipient_import_redirect(summary) == (
        "/setup/inputs?telegram_recipient_imported=2&telegram_recipient_unknown=1"
        "&telegram_recipient_invalid=0&telegram_recipient_ignored=1"
        "#telegram-recipient-import"
    )
