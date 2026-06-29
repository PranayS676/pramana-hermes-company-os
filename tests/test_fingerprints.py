from __future__ import annotations

import json
from hashlib import sha256

from hermes_company_os.fingerprints import fingerprint_json, fingerprint_text


def test_fingerprint_text_matches_sha256_hex_of_utf8():
    assert fingerprint_text("") == sha256(b"").hexdigest()
    assert fingerprint_text("hello") == sha256(b"hello").hexdigest()
    assert len(fingerprint_text("anything")) == 64


def test_fingerprint_json_is_key_order_independent():
    assert fingerprint_json({"a": 1, "b": 2}) == fingerprint_json({"b": 2, "a": 1})


def test_fingerprint_json_uses_sorted_compact_serialization():
    value = {"b": 2, "a": [3, 1]}
    expected = fingerprint_text(
        json.dumps(value, sort_keys=True, separators=(",", ":"))
    )
    assert fingerprint_json(value) == expected


def test_fingerprint_json_distinguishes_different_payloads():
    assert fingerprint_json({"a": 1}) != fingerprint_json({"a": 2})


def test_shared_helper_matches_module_private_aliases():
    # The dispatch/operating-loop/codex modules now source their private
    # fingerprint helpers from this shared util; confirm they are the same.
    from hermes_company_os import (
        codex_execution,
        external_dispatch,
        project_operating_loop,
    )

    payload = {"z": 1, "a": {"nested": [1, 2, 3]}}
    text = "command preview text"
    for module in (external_dispatch, project_operating_loop, codex_execution):
        assert module._fingerprint_json(payload) == fingerprint_json(payload)
        assert module._fingerprint_text(text) == fingerprint_text(text)
