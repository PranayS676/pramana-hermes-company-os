from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass

from hermes_company_os.settings import Settings


@dataclass(frozen=True)
class HermesResult:
    output: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


class HermesClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run_prompt(self, agent: dict, prompt: str) -> HermesResult:
        command = self._command_for(agent)
        args = self._split_command(command)
        if not args:
            return HermesResult(
                output="",
                error=f"No Hermes command configured for {agent['name']}.",
            )

        try:
            completed = subprocess.run(
                args,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.settings.hermes_timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return HermesResult(
                output="",
                error=(
                    f"Hermes command not found: {args[0]}. Create the profile command alias or "
                    "override it with HERMES_COMMAND_<PROFILE_ID>."
                ),
            )
        except subprocess.TimeoutExpired:
            return HermesResult(
                output="",
                error=f"Hermes command timed out after {self.settings.hermes_timeout_seconds}s.",
            )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            message = stderr or stdout or f"Hermes exited with code {completed.returncode}."
            return HermesResult(output=stdout, error=message)
        return HermesResult(output=stdout or "(Hermes returned no output.)")

    def _command_for(self, agent: dict) -> str:
        env_key = f"HERMES_COMMAND_{agent['id'].upper().replace('-', '_')}"
        return os.getenv(env_key, agent["hermes_command"])

    @staticmethod
    def _split_command(command: str) -> list[str]:
        return shlex.split(command, posix=os.name != "nt")
