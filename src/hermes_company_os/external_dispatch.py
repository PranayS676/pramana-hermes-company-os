from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from hermes_company_os.fingerprints import fingerprint_json as _fingerprint_json
from hermes_company_os.fingerprints import fingerprint_text as _fingerprint_text
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


def operating_loop_package(
    repository: Any,
    project_id: str | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Build a READ-ONLY operating-loop view of external-dispatch deliveries.

    This makes the live coordination loop observable (roadmap M7, slice 5) without
    making any send, live call, or state change. It only reads existing
    ``external_dispatch_deliveries`` rows via the repository.

    When ``project_id`` is ``None`` the package is company-wide: deliveries are
    gathered across every project (each delivery annotated with its project name)
    and sorted newest-first. When a ``project_id`` is given the package is scoped
    to that project. Callers must 404 on an unknown project before calling.

    The returned ``summary`` carries simple counts (total, by-platform, by-status)
    for the dashboard's metric grid. Each delivery row is annotated with a
    non-secret ``detail`` derived from its stored result for failure context.
    """
    if project_id is None:
        scope = {"company_wide": True, "project_id": "", "project_name": "Company-wide"}
        deliveries: list[dict[str, Any]] = []
        for project in repository.list_projects():
            project_deliveries = repository.list_external_dispatch_deliveries(
                project["id"], limit=limit
            )
            project_name = str(project.get("name", "")) or project["id"]
            for delivery in project_deliveries:
                deliveries.append(_annotate_delivery(delivery, project_name))
        deliveries.sort(
            key=lambda row: (row.get("created_at", ""), row.get("id", "")),
            reverse=True,
        )
        deliveries = deliveries[:limit]
    else:
        project = repository.get_project(project_id)
        project_name = (
            str(project.get("name", "")) if project else ""
        ) or project_id
        scope = {
            "company_wide": False,
            "project_id": project_id,
            "project_name": project_name,
        }
        deliveries = [
            _annotate_delivery(delivery, project_name)
            for delivery in repository.list_external_dispatch_deliveries(
                project_id, limit=limit
            )
        ]

    return {
        "scope": scope,
        "deliveries": deliveries,
        "summary": _operating_loop_summary(deliveries),
    }


def _annotate_delivery(delivery: Mapping[str, Any], project_name: str) -> dict[str, Any]:
    annotated = dict(delivery)
    annotated["project_name"] = project_name
    result = annotated.get("result") or {}
    detail = ""
    if isinstance(result, Mapping):
        detail = str(result.get("blocker") or result.get("detail") or "")
    annotated["detail"] = detail
    return annotated


def _operating_loop_summary(deliveries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_platform: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for delivery in deliveries:
        platform = str(delivery.get("platform", "")) or "unknown"
        status = str(delivery.get("status", "")) or "unknown"
        by_platform[platform] = by_platform.get(platform, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "total": len(deliveries),
        "by_platform": dict(sorted(by_platform.items())),
        "by_status": dict(sorted(by_status.items())),
    }


def command_boundary_summary(*, enabled: bool, runner_label: str = "") -> dict[str, Any]:
    return {
        "name": EXTERNAL_DISPATCH_COMMAND_BOUNDARY_LABEL,
        "id": EXTERNAL_DISPATCH_COMMAND_BOUNDARY,
        "status": "enabled" if enabled else "disabled",
        "runner_label": runner_label,
        "contract_schema": EXTERNAL_DISPATCH_COMMAND_CONTRACT_SCHEMA,
        # When disabled, only dry-run contracts are produced (no real `hermes` call).
        # When enabled AND founder-approved, the runner may execute a real send.
        "dry_run_contracts_only": not enabled,
        "real_send_via": "hermes send / hermes kanban create",
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
    channel_ref = _target_value(item)
    return _base_contract(
        item,
        adapter="slack",
        command_kind="slack.chat.postMessage",
        target_input_key=target_input_key,
        target_value=channel_ref,
        # Real Hermes interface: `hermes send --to slack:<channel_ref> "<text>"`.
        # ``hermes send`` reuses Hermes's own creds (~/.hermes/.env); no token here.
        argv=[
            "hermes",
            "send",
            "--to",
            f"slack:{channel_ref}",
            str(item["message_preview"]),
        ],
    )


def _telegram_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    target_input_key = str(item["target_input_key"])
    chat_id = _target_value(item)
    return _base_contract(
        item,
        adapter="telegram",
        command_kind="telegram.sendMessage",
        target_input_key=target_input_key,
        target_value=chat_id,
        # Urgent-only policy preserved as contract metadata; the real interface is
        # `hermes send --to telegram:<chat_id> "<text>"`.
        urgent_only=True,
        argv=[
            "hermes",
            "send",
            "--to",
            f"telegram:{chat_id}",
            str(item["message_preview"]),
        ],
    )


def _kanban_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    return _base_contract(
        item,
        adapter="hermes-kanban",
        command_kind="hermes kanban create",
        idempotency_key=str(item["idempotency_key"]),
        # Real Hermes interface: native idempotency via --idempotency-key.
        argv=[
            "hermes",
            "kanban",
            "create",
            str(item["title"]),
            "--assignee",
            str(item["owner_agent_id"]),
            "--idempotency-key",
            str(item["idempotency_key"]),
            "--json",
        ],
    )


def _target_value(item: Mapping[str, Any]) -> str:
    """Resolve the recipient VALUE (channel id / chat id) for the real argv.

    The preview item carries the resolved setup-input VALUE in ``target_value``
    (e.g. ``C012STANDUP``); fall back to the ``target_input_key`` only when no
    value was resolved so the contract still renders a stable, non-secret argv.
    """
    value = str(item.get("target_value", "")).strip()
    return value or str(item["target_input_key"])


def _base_contract(
    item: Mapping[str, Any],
    *,
    adapter: str,
    command_kind: str,
    argv: Sequence[str],
    target_input_key: str = "",
    target_value: str = "",
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
        "target_value": target_value,
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
