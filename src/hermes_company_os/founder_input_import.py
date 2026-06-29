from __future__ import annotations

import re

from hermes_company_os.setup_import_parsing import strip_inline_comment as _strip_inline_comment

INPUT_LINE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*(?:=|:)\s*(.*?)\s*$")


def parse_founder_input_reply(raw_text: str, setup_inputs: list[dict]) -> dict:
    safe_keys = {
        item["key"]
        for item in setup_inputs
        if item["secret_policy"] == "non_secret"
    }
    deferred_keys = {
        item["key"]
        for item in setup_inputs
        if item["secret_policy"] != "non_secret"
    }
    values: dict[str, str] = {}
    unknown_keys: list[str] = []
    deferred_keys_seen: list[str] = []
    ignored_lines: list[str] = []

    for line in raw_text.splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("```"):
            continue
        match = INPUT_LINE.match(cleaned)
        if not match:
            ignored_lines.append(cleaned)
            continue
        key, value = match.groups()
        normalized_value = _strip_inline_comment(value).strip()
        if key in safe_keys:
            values[key] = normalized_value
        elif key in deferred_keys:
            deferred_keys_seen.append(key)
        else:
            unknown_keys.append(key)

    return {
        "values": values,
        "imported": len(values),
        "unknown_keys": sorted(set(unknown_keys)),
        "deferred_keys": sorted(set(deferred_keys_seen)),
        "ignored_lines": ignored_lines,
    }


def founder_input_import_redirect(summary: dict) -> str:
    return (
        "/setup?"
        f"input_imported={summary['imported']}"
        f"&input_unknown={len(summary['unknown_keys'])}"
        f"&input_deferred={len(summary['deferred_keys'])}"
        f"&input_ignored={len(summary['ignored_lines'])}"
        "#inputs"
    )
