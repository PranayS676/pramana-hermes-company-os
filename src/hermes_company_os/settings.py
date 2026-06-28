from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(os.getenv("HERMES_COMPANY_OS_DB", "./data/company_os.db"))
    timezone: str = os.getenv("COMPANY_TIMEZONE", "America/New_York")
    hermes_timeout_seconds: int = int(os.getenv("HERMES_TIMEOUT_SECONDS", "300"))
    hermes_live_execution_enabled: bool = field(
        default_factory=lambda: env_flag("HERMES_LIVE_EXECUTION_ENABLED", False)
    )
    codex_execution_enabled: bool = field(
        default_factory=lambda: env_flag("HERMES_CODEX_EXECUTION_ENABLED", False)
    )
    external_dispatch_enabled: bool = field(
        default_factory=lambda: env_flag("HERMES_EXTERNAL_DISPATCH_ENABLED", False)
    )
    codex_workspace_root: Path = Path(os.getenv("HERMES_CODEX_WORKSPACE_ROOT", "."))
    codex_worktree_root: Path = Path(
        os.getenv("HERMES_CODEX_WORKTREE_ROOT", "../codex-worktrees")
    )

    slack_founder_command: str = os.getenv("SLACK_FOUNDER_COMMAND", "#founder-command")
    slack_standup: str = os.getenv("SLACK_STANDUP", "#agent-standup")
    slack_alerts: str = os.getenv("SLACK_ALERTS", "#alerts")
    telegram_urgent_label: str = os.getenv(
        "TELEGRAM_URGENT_LABEL", "Founder Telegram urgent channel"
    )

    @classmethod
    def from_env(cls) -> Settings:
        return cls()

    def resolved_database_path(self) -> Path:
        return self.database_path.expanduser().resolve()
