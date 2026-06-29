from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256


def fingerprint_text(value: str) -> str:
    """Return the SHA256 hex digest of ``value`` encoded as UTF-8."""
    return sha256(value.encode("utf-8")).hexdigest()


def fingerprint_json(value: Mapping | Sequence) -> str:
    """Return a stable SHA256 fingerprint of a JSON-serializable value.

    Keys are sorted and separators are compact so the digest is deterministic
    for equal payloads regardless of input ordering or whitespace.
    """
    return fingerprint_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
