from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadinessItem:
    id: str
    label: str
    status: str
    detail: str


class ReadinessService:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self._hermes_version: str | None = None

    def check(self, agents: list[dict], integrations: list[dict]) -> list[ReadinessItem]:
        items = [
            self._command_item("hermes", "Hermes CLI"),
            ReadinessItem(
                id="database",
                label="SQLite database",
                status="ready" if self.database_path.exists() else "missing",
                detail=str(self.database_path),
            ),
        ]
        items.extend(
            self._command_item(agent["hermes_command"], f"{agent['name']} profile command")
            for agent in agents
        )
        items.append(self._integration_summary("Slack integrations", integrations, "slack"))
        items.append(self._integration_summary("Telegram urgent alerts", integrations, "telegram"))
        items.append(self._integration_summary("Kanban integration", integrations, "kanban"))
        items.append(self._integration_summary("Standup cron", integrations, "schedule"))
        items.append(self._integration_summary("LLM provider", integrations, "runtime"))
        return items

    def hermes_version(self) -> str:
        # The Hermes CLI version does not change within a process; spawning the
        # subprocess on every /setup render was a measurable load cost.
        if self._hermes_version is not None:
            return self._hermes_version
        self._hermes_version = self._resolve_hermes_version()
        return self._hermes_version

    def _resolve_hermes_version(self) -> str:
        hermes = shutil.which("hermes")
        if not hermes:
            return "Hermes CLI not found on PATH."
        try:
            completed = subprocess.run(
                [hermes, "--version"],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except subprocess.SubprocessError as error:
            return f"Unable to run hermes --version: {error}"
        output = (completed.stdout or completed.stderr).strip()
        return output or f"hermes --version exited with {completed.returncode}"

    def _command_item(self, command: str, label: str) -> ReadinessItem:
        executable = command.split()[0] if command else ""
        path = shutil.which(executable) if executable else None
        return ReadinessItem(
            id=f"command-{executable or 'missing'}",
            label=label,
            status="ready" if path else "missing",
            detail=path or f"`{executable}` was not found on PATH.",
        )

    @staticmethod
    def _integration_summary(
        label: str,
        integrations: list[dict],
        category: str,
    ) -> ReadinessItem:
        relevant = [item for item in integrations if item["category"] == category]
        ready = [item for item in relevant if item["status"] in {"configured", "ready"}]
        status = "ready" if relevant and len(ready) == len(relevant) else "needs_input"
        if category == "runtime" and relevant and relevant[0]["status"] == "deferred":
            status = "deferred"
        return ReadinessItem(
            id=f"integration-{category}",
            label=label,
            status=status,
            detail=f"{len(ready)} of {len(relevant)} configured",
        )
