from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class KanbanResult:
    ok: bool
    output: str
    task_id: str = ""
    error: str = ""


class KanbanClient:
    def diagnostics(self) -> KanbanResult:
        return self._run(["hermes", "kanban", "diagnostics", "--json"])

    def create_task(self, task: dict) -> KanbanResult:
        summary = task["summary"].strip()
        args = [
            "hermes",
            "kanban",
            "create",
            task["title"],
            "--assignee",
            task["owner_agent_id"],
            "--idempotency-key",
            task["id"],
            "--json",
        ]
        if summary:
            args.extend(["--body", summary])
        result = self._run(args)
        if not result.ok:
            return result
        task_id = self._extract_task_id(result.output)
        return KanbanResult(ok=True, output=result.output, task_id=task_id)

    def _run(self, args: list[str]) -> KanbanResult:
        executable = args[0]
        resolved_executable = shutil.which(executable)
        if resolved_executable is None:
            return KanbanResult(
                ok=False,
                output="",
                error=f"`{executable}` was not found on PATH.",
            )
        try:
            completed = subprocess.run(
                [resolved_executable, *args[1:]],
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
        except subprocess.SubprocessError as error:
            return KanbanResult(ok=False, output="", error=str(error))

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            return KanbanResult(
                ok=False,
                output=stdout,
                error=stderr or stdout or f"Command exited with {completed.returncode}.",
            )
        return KanbanResult(ok=True, output=stdout)

    @staticmethod
    def _extract_task_id(output: str) -> str:
        if not output:
            return ""
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            return ""
        for key in ("id", "task_id", "taskId"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        task = payload.get("task")
        if isinstance(task, dict):
            value = task.get("id")
            if isinstance(value, str):
                return value
        return ""
