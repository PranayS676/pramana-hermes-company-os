from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from hermes_company_os.secret_guard import assert_no_secret_values, secret_violations

EXTERNAL_DISPATCH_COMMAND_CONTRACT_SCHEMA = "external_dispatch_command_contract_v1"
EXTERNAL_DISPATCH_COMMAND_BOUNDARY = "hermes_command_boundary"
EXTERNAL_DISPATCH_COMMAND_BOUNDARY_LABEL = "Hermes command boundary"
DEFAULT_EXTERNAL_DISPATCH_TIMEOUT_SECONDS = 60

CommandRunner = Callable[[list[str]], Any]


def external_dispatch_command_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    platform = str(item["platform"])
    if platform == "slack":
        contract = _slack_contract(item)
    elif platform == "telegram":
        contract = _telegram_contract(item)
    elif platform == "hermes-kanban":
        contract = _kanban_contract(item)
    else:
        raise ValueError(f"Unsupported external dispatch platform: {platform}")
    contract["argv_sha256"] = _fingerprint_json(contract["argv"])
    contract["command_preview_sha256"] = _fingerprint_text(
        str(item.get("command_preview", ""))
    )
    contract["contract_sha256"] = _fingerprint_json(contract)
    assert_no_secret_values({"external_dispatch_contract": json.dumps(contract)})
    return contract


def command_boundary_summary(*, enabled: bool, runner_label: str = "") -> dict[str, Any]:
    return {
        "name": EXTERNAL_DISPATCH_COMMAND_BOUNDARY_LABEL,
        "id": EXTERNAL_DISPATCH_COMMAND_BOUNDARY,
        "status": "enabled" if enabled else "disabled",
        "runner_label": runner_label,
        "contract_schema": EXTERNAL_DISPATCH_COMMAND_CONTRACT_SCHEMA,
        "dry_run_contracts_only": True,
    }


class SubprocessExternalDispatchCommandRunner:
    def run(self, argv: Sequence[str], timeout_seconds: int) -> dict[str, Any]:
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                list(argv),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError:
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": f"Hermes command not found: {argv[0]}.",
                "duration_ms": _elapsed_ms(started_at),
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "returncode": 124,
                "stdout": _process_output_to_text(exc.stdout),
                "stderr": _process_output_to_text(exc.stderr),
                "duration_ms": _elapsed_ms(started_at),
                "timed_out": True,
            }
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "duration_ms": _elapsed_ms(started_at),
            "timed_out": False,
        }


class HermesExternalDispatchCommandAdapter:
    def __init__(
        self,
        *,
        enabled: bool = False,
        runner: CommandRunner | SubprocessExternalDispatchCommandRunner | None = None,
        runner_label: str = "subprocess",
        timeout_seconds: int = DEFAULT_EXTERNAL_DISPATCH_TIMEOUT_SECONDS,
    ):
        self.enabled = enabled
        self.runner = runner or SubprocessExternalDispatchCommandRunner()
        self.runner_label = runner_label
        self.timeout_seconds = timeout_seconds

    def dispatch(self, item: Mapping[str, Any]) -> dict[str, Any]:
        contract = dict(item["adapter_contract"])
        result_base = {
            "item_id": item["id"],
            "platform": item["platform"],
            "action": item["action"],
            "command_boundary": contract["command_boundary"],
            "command_sha256": contract["argv_sha256"],
            "contract_sha256": contract["contract_sha256"],
            "dry_run": bool(contract["dry_run"]),
            "runner_label": self.runner_label,
            "dispatch_attempted": False,
        }
        if not self.enabled:
            result = {
                **result_base,
                "status": "blocked",
                "blocker": "Hermes external dispatch command adapter is disabled.",
                "detail": "No Hermes command runner was called.",
            }
            assert_no_secret_values({"external_dispatch_result": json.dumps(result)})
            return result

        raw_result = self._run(contract["argv"])
        returncode = _returncode(raw_result)
        status = "succeeded" if returncode == 0 else "failed"
        result = {
            **result_base,
            "status": status,
            "returncode": returncode,
            "dispatch_attempted": True,
            "duration_ms": int(raw_result.get("duration_ms", 0) or 0),
            "timed_out": bool(raw_result.get("timed_out", False)),
            "stdout_capture": _output_capture(str(raw_result.get("stdout", "")), "stdout"),
            "stderr_capture": _output_capture(str(raw_result.get("stderr", "")), "stderr"),
            "detail": "Hermes external dispatch command completed.",
            "blocker": (
                ""
                if status == "succeeded"
                else "Hermes command returned a non-zero status."
            ),
        }
        assert_no_secret_values({"external_dispatch_result": json.dumps(result)})
        return result

    def _run(self, argv: Sequence[str]) -> dict[str, Any]:
        if hasattr(self.runner, "run"):
            raw = self.runner.run(list(argv), self.timeout_seconds)  # type: ignore[union-attr]
        else:
            raw = self.runner(list(argv))  # type: ignore[operator]
        if isinstance(raw, Mapping):
            return dict(raw)
        if isinstance(raw, subprocess.CompletedProcess):
            return {
                "returncode": raw.returncode,
                "stdout": raw.stdout or "",
                "stderr": raw.stderr or "",
                "duration_ms": 0,
                "timed_out": False,
            }
        return {
            "returncode": 0,
            "stdout": str(raw),
            "stderr": "",
            "duration_ms": 0,
            "timed_out": False,
        }


def _slack_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    target_input_key = str(item["target_input_key"])
    return _base_contract(
        item,
        adapter="slack",
        command_kind="slack.chat.postMessage",
        target_input_key=target_input_key,
        argv=[
            "hermes",
            "dispatch",
            "slack",
            "post-message",
            "--channel-ref",
            target_input_key,
            "--text",
            str(item["message_preview"]),
            "--dry-run",
        ],
    )


def _telegram_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    target_input_key = str(item["target_input_key"])
    return _base_contract(
        item,
        adapter="telegram",
        command_kind="telegram.sendMessage",
        target_input_key=target_input_key,
        urgent_only=True,
        argv=[
            "hermes",
            "dispatch",
            "telegram",
            "send-message",
            "--recipient-ref",
            target_input_key,
            "--text",
            str(item["message_preview"]),
            "--urgent-only",
            "--dry-run",
        ],
    )


def _kanban_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    return _base_contract(
        item,
        adapter="hermes-kanban",
        command_kind="hermes kanban create",
        idempotency_key=str(item["idempotency_key"]),
        argv=[
            "hermes",
            "kanban",
            "create",
            str(item["title"]),
            "--assignee",
            str(item["owner_agent_id"]),
            "--idempotency-key",
            str(item["idempotency_key"]),
            "--dry-run",
            "--json",
        ],
    )


def _base_contract(
    item: Mapping[str, Any],
    *,
    adapter: str,
    command_kind: str,
    argv: Sequence[str],
    target_input_key: str = "",
    idempotency_key: str = "",
    urgent_only: bool = False,
) -> dict[str, Any]:
    return {
        "schema": EXTERNAL_DISPATCH_COMMAND_CONTRACT_SCHEMA,
        "command_boundary": EXTERNAL_DISPATCH_COMMAND_BOUNDARY,
        "item_id": item["id"],
        "platform": item["platform"],
        "action": item["action"],
        "adapter": adapter,
        "command_kind": command_kind,
        "target_input_key": target_input_key,
        "idempotency_key": idempotency_key,
        "urgent_only": urgent_only,
        "enabled": False,
        "dry_run": True,
        "argv": list(argv),
    }


def _returncode(raw_result: Mapping[str, Any]) -> int:
    if "returncode" in raw_result:
        return int(raw_result.get("returncode") or 0)
    if "exit_code" in raw_result:
        return int(raw_result.get("exit_code") or 0)
    return 0


def _output_capture(value: str, field: str) -> dict[str, Any]:
    text = value.strip()
    preview = text[:500]
    if text and secret_violations({field: text}):
        preview = "REDACTED_SECRET_OUTPUT"
    return {
        "bytes": len(text.encode("utf-8")),
        "sha256": _fingerprint_text(text),
        "preview": preview,
        "redacted": preview == "REDACTED_SECRET_OUTPUT",
    }


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _process_output_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return value.strip()


def _fingerprint_json(value: Mapping | Sequence) -> str:
    return _fingerprint_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _fingerprint_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
