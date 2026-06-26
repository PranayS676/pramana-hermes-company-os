from __future__ import annotations

import re
from collections.abc import Mapping

SECRET_PATTERNS = (
    ("Slack bot token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Slack app token", re.compile(r"\bxapp-[A-Za-z0-9-]{10,}\b")),
    ("Telegram bot token", re.compile(r"\b\d{6,14}:[A-Za-z0-9_-]{20,}\b")),
    ("OpenRouter API key", re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{25,}\b")),
    (
        "secret environment assignment",
        re.compile(
            r"\b[A-Z0-9_]*(?:API[_-]?KEY|APP[_-]?TOKEN|BOT[_-]?TOKEN|SECRET)"
            r"\s*=\s*[^\s#]{8,}",
            re.IGNORECASE,
        ),
    ),
)


def secret_violations(values: Mapping[str, str]) -> list[str]:
    violations = []
    for field, value in values.items():
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(value):
                violations.append(f"{field}: {label}")
                break
    return violations


def assert_no_secret_values(values: Mapping[str, str]) -> None:
    violations = secret_violations(values)
    if violations:
        raise ValueError(
            "Do not paste secret values into this dashboard. Store them in the "
            "real Hermes profile environment instead. Detected: "
            + ", ".join(violations)
        )
