from __future__ import annotations


def strip_inline_comment(value: str) -> str:
    """Drop a trailing `` #comment`` from a pasted no-secret reply value."""
    if " #" not in value:
        return value
    return value.split(" #", 1)[0].rstrip()


def parse_status_value(value: str) -> tuple[str, str]:
    """Split a ``status | trailing`` reply cell into (status, trailing).

    The status is lower-cased and stripped of any inline comment. The trailing
    segment (notes/evidence) is returned only when a ``|`` separator is present.
    """
    status_part, separator, trailing = value.partition("|")
    status = strip_inline_comment(status_part).strip().lower()
    return status, trailing.strip() if separator else ""
