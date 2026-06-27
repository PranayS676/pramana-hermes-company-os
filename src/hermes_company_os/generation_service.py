from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal, Protocol

from hermes_company_os.product_wizard import (
    ProductWizardArtifact,
    ProductWizardIntake,
    ProductWizardSourceArtifact,
    WizardStage,
    build_wizard_prompt_contract,
    generate_wizard_artifact,
)
from hermes_company_os.secret_guard import secret_violations

GenerationMode = Literal["local_fake_public_demo", "live_hermes"]
LOCAL_DEMO_GENERATION_MODE: GenerationMode = "local_fake_public_demo"
LIVE_HERMES_GENERATION_MODE: GenerationMode = "live_hermes"
SUPPORTED_GENERATION_MODES: tuple[GenerationMode, ...] = (
    LOCAL_DEMO_GENERATION_MODE,
    LIVE_HERMES_GENERATION_MODE,
)
LIVE_HERMES_LOCKED_MESSAGE = (
    "Live Hermes generation is locked. Founder approval and Hermes readiness "
    "gates are required before live profile execution."
)
LIVE_HERMES_DRY_RUN_ADAPTER = "dry_run_live_hermes"
LIVE_HERMES_DRY_RUN_STATUS = "dry_run_succeeded"
LIVE_HERMES_DRY_RUN_MESSAGE = (
    "Live Hermes dry-run adapter produced a public-demo artifact without "
    "external execution."
)
LIVE_HERMES_LIVE_ADAPTER = "real_live_hermes"
LIVE_HERMES_LIVE_STATUS = "live_runner_succeeded"
LIVE_HERMES_LIVE_MESSAGE = (
    "Live Hermes runner completed through the gated command boundary."
)
ApprovedSourceInput = Iterable[
    ProductWizardArtifact | ProductWizardSourceArtifact | Mapping[str, Any]
]


def normalize_generation_mode(mode: str) -> GenerationMode:
    cleaned_mode = mode.strip()
    if cleaned_mode == LOCAL_DEMO_GENERATION_MODE:
        return LOCAL_DEMO_GENERATION_MODE
    if cleaned_mode == LIVE_HERMES_GENERATION_MODE:
        return LIVE_HERMES_GENERATION_MODE
    raise ValueError(f"Unsupported Product Wizard generation mode: {mode}")


@dataclass(frozen=True)
class StageGenerationRequest:
    stage_id: WizardStage | str
    intake: ProductWizardIntake | Mapping[str, Any]
    approved_sources: ApprovedSourceInput = ()
    mode: GenerationMode = LOCAL_DEMO_GENERATION_MODE


class StageGenerationService(Protocol):
    def generate_stage(self, request: StageGenerationRequest) -> ProductWizardArtifact:
        """Generate one Product Wizard stage artifact."""


@dataclass(frozen=True)
class LiveHermesAdapterRequest:
    stage_id: str
    owner_agent_id: str
    supporting_agent_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    prompt_contract: Mapping[str, Any]
    command_preview: tuple[str, ...]
    timeout_seconds: int = 120
    external_execution_enabled: bool = False

    @property
    def prompt_sha256(self) -> str:
        prompt = str(self.prompt_contract.get("prompt", ""))
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LiveHermesAdapterRawResult:
    stdout: str
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    duration_ms: int = 0


class LiveHermesAdapter(Protocol):
    def execute(self, request: LiveHermesAdapterRequest) -> LiveHermesAdapterRawResult:
        """Execute or simulate a Live Hermes generation request."""


class HermesCommandRunner(Protocol):
    def run(
        self,
        command: tuple[str, ...],
        prompt: str,
        timeout_seconds: int,
    ) -> LiveHermesAdapterRawResult:
        """Run a Hermes command with stdin prompt text and captured output."""


class SubprocessHermesCommandRunner:
    def run(
        self,
        command: tuple[str, ...],
        prompt: str,
        timeout_seconds: int,
    ) -> LiveHermesAdapterRawResult:
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                list(command),
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return LiveHermesAdapterRawResult(
                stdout="",
                stderr=f"Hermes command not found: {command[0]}.",
                exit_code=127,
                duration_ms=_elapsed_ms(started_at),
            )
        except subprocess.TimeoutExpired as exc:
            return LiveHermesAdapterRawResult(
                stdout=_process_output_to_text(exc.stdout),
                stderr=_process_output_to_text(exc.stderr),
                exit_code=124,
                timed_out=True,
                duration_ms=_elapsed_ms(started_at),
            )
        return LiveHermesAdapterRawResult(
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            exit_code=completed.returncode,
            duration_ms=_elapsed_ms(started_at),
        )


@dataclass(frozen=True)
class ParsedLiveHermesAdapterResult:
    metadata: dict[str, Any]
    markdown_appendix: str


class DryRunLiveHermesAdapter:
    def execute(self, request: LiveHermesAdapterRequest) -> LiveHermesAdapterRawResult:
        payload = {
            "adapter": LIVE_HERMES_DRY_RUN_ADAPTER,
            "status": LIVE_HERMES_DRY_RUN_STATUS,
            "message": LIVE_HERMES_DRY_RUN_MESSAGE,
            "external_execution": "disabled",
            "stage_id": request.stage_id,
            "owner_agent_id": request.owner_agent_id,
            "supporting_agent_ids": list(request.supporting_agent_ids),
            "source_artifact_ids": list(request.source_artifact_ids),
            "command_preview": list(request.command_preview),
            "timeout_seconds": request.timeout_seconds,
            "prompt_handoff": {
                "contract": "product_wizard_prompt_contract_v1",
                "sha256": request.prompt_sha256,
            },
            "output_parser": {
                "name": "product_wizard_artifact_v1",
                "status": "validated",
            },
        }
        return LiveHermesAdapterRawResult(
            stdout=json.dumps(payload, sort_keys=True),
            duration_ms=0,
        )


class LiveHermesCommandAdapter:
    def __init__(
        self,
        *,
        live_execution_enabled: bool = False,
        runner: HermesCommandRunner | None = None,
    ):
        self.live_execution_enabled = live_execution_enabled
        self.runner = runner or SubprocessHermesCommandRunner()
        self.dry_run_adapter = DryRunLiveHermesAdapter()

    def execute(self, request: LiveHermesAdapterRequest) -> LiveHermesAdapterRawResult:
        if not self.live_execution_enabled or not request.external_execution_enabled:
            return self.dry_run_adapter.execute(request)
        prompt = str(request.prompt_contract.get("prompt", ""))
        raw_result = self.runner.run(
            request.command_preview,
            prompt,
            request.timeout_seconds,
        )
        if raw_result.timed_out or raw_result.exit_code != 0:
            return raw_result
        payload = {
            "adapter": LIVE_HERMES_LIVE_ADAPTER,
            "status": LIVE_HERMES_LIVE_STATUS,
            "message": LIVE_HERMES_LIVE_MESSAGE,
            "external_execution": "enabled",
            "stage_id": request.stage_id,
            "owner_agent_id": request.owner_agent_id,
            "supporting_agent_ids": list(request.supporting_agent_ids),
            "source_artifact_ids": list(request.source_artifact_ids),
            "command_preview": list(request.command_preview),
            "timeout_seconds": request.timeout_seconds,
            "prompt_handoff": {
                "contract": "product_wizard_prompt_contract_v1",
                "sha256": request.prompt_sha256,
            },
            "output_parser": {
                "name": "product_wizard_artifact_v1",
                "status": "validated",
            },
            "stdout_capture": _output_capture(raw_result.stdout, "stdout"),
            "stderr_capture": _output_capture(raw_result.stderr, "stderr"),
        }
        return LiveHermesAdapterRawResult(
            stdout=json.dumps(payload, sort_keys=True),
            stderr=raw_result.stderr,
            exit_code=0,
            duration_ms=raw_result.duration_ms,
        )


class LocalDemoGenerationService:
    mode: GenerationMode = LOCAL_DEMO_GENERATION_MODE

    def generate_stage(self, request: StageGenerationRequest) -> ProductWizardArtifact:
        if request.mode != self.mode:
            raise ValueError(
                f"Unsupported Product Wizard generation mode: {request.mode}"
            )
        return generate_wizard_artifact(
            request.stage_id,
            request.intake,
            request.approved_sources,
        )


@dataclass(frozen=True)
class LiveHermesGenerationGate:
    enabled: bool = False
    founder_approved: bool = False
    runtime_ready: bool = False

    def blocker(self) -> str:
        if not self.enabled:
            return LIVE_HERMES_LOCKED_MESSAGE
        if not self.founder_approved:
            return "Live Hermes generation is locked until founder approval is recorded."
        if not self.runtime_ready:
            return "Live Hermes generation is locked until Hermes readiness checks pass."
        return ""


class LiveHermesGenerationService:
    mode: GenerationMode = LIVE_HERMES_GENERATION_MODE

    def __init__(
        self,
        gate: LiveHermesGenerationGate | None = None,
        adapter: LiveHermesAdapter | None = None,
        timeout_seconds: int = 120,
        live_execution_enabled: bool = False,
    ):
        self.gate = gate or LiveHermesGenerationGate()
        self.adapter = adapter or LiveHermesCommandAdapter(
            live_execution_enabled=live_execution_enabled
        )
        self.timeout_seconds = timeout_seconds
        self.live_execution_enabled = live_execution_enabled

    def generate_stage(self, request: StageGenerationRequest) -> ProductWizardArtifact:
        if request.mode != self.mode:
            raise ValueError(
                f"Unsupported Product Wizard generation mode: {request.mode}"
            )
        blocker = self.gate.blocker()
        if blocker:
            raise ValueError(blocker)
        prompt_contract = build_wizard_prompt_contract(
            request.stage_id,
            request.intake,
            request.approved_sources,
        )
        adapter_request = _live_hermes_adapter_request(
            prompt_contract,
            timeout_seconds=self.timeout_seconds,
            live_execution_enabled=self.live_execution_enabled,
        )
        raw_result = self.adapter.execute(adapter_request)
        parsed_result = _parse_live_hermes_adapter_result(
            adapter_request,
            raw_result,
        )
        artifact = generate_wizard_artifact(
            request.stage_id,
            request.intake,
            request.approved_sources,
        )
        return replace(
            artifact,
            markdown=artifact.markdown + parsed_result.markdown_appendix,
            generation_mode=LIVE_HERMES_GENERATION_MODE,
            generation_metadata=parsed_result.metadata,
        )


def _live_hermes_adapter_request(
    prompt_contract: Mapping[str, Any],
    *,
    timeout_seconds: int,
    live_execution_enabled: bool,
) -> LiveHermesAdapterRequest:
    stage_id = str(prompt_contract["stage"])
    owner_agent_id = str(prompt_contract["owner_agent_id"])
    supporting_agent_ids = tuple(
        str(agent_id) for agent_id in prompt_contract.get("supporting_agent_ids", [])
    )
    source_artifact_ids = tuple(
        str(source_id) for source_id in prompt_contract.get("source_artifact_ids", [])
    )
    command_preview = (
        "hermes",
        "profiles",
        "run",
        owner_agent_id,
        "--stage",
        stage_id,
        "--output",
        "product-wizard-artifact-json",
    )
    if not live_execution_enabled:
        command_preview = (
            *command_preview[:6],
            "--dry-run",
            *command_preview[6:],
        )
    return LiveHermesAdapterRequest(
        stage_id=stage_id,
        owner_agent_id=owner_agent_id,
        supporting_agent_ids=supporting_agent_ids,
        source_artifact_ids=source_artifact_ids,
        prompt_contract=prompt_contract,
        command_preview=command_preview,
        timeout_seconds=timeout_seconds,
        external_execution_enabled=live_execution_enabled,
    )


def _parse_live_hermes_adapter_result(
    request: LiveHermesAdapterRequest,
    raw_result: LiveHermesAdapterRawResult,
) -> ParsedLiveHermesAdapterResult:
    if raw_result.timed_out:
        raise ValueError(
            "Live Hermes dry-run adapter timed out after "
            f"{request.timeout_seconds} seconds."
        )
    if raw_result.exit_code != 0:
        raise ValueError(
            "Live Hermes dry-run adapter failed: "
            + _safe_adapter_error(raw_result.stderr or f"exit code {raw_result.exit_code}")
        )
    try:
        payload = json.loads(raw_result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Live Hermes adapter returned invalid JSON output.") from exc
    if payload.get("status") not in {LIVE_HERMES_DRY_RUN_STATUS, LIVE_HERMES_LIVE_STATUS}:
        raise ValueError(
            "Live Hermes adapter returned unexpected status: "
            + str(payload.get("status", "missing"))
        )

    metadata = {
        "adapter": str(payload.get("adapter", LIVE_HERMES_DRY_RUN_ADAPTER)),
        "status": str(payload["status"]),
        "message": str(payload.get("message", LIVE_HERMES_DRY_RUN_MESSAGE)),
        "external_execution": str(payload.get("external_execution", "disabled")),
        "stage_id": request.stage_id,
        "owner_agent_id": request.owner_agent_id,
        "supporting_agent_ids": list(request.supporting_agent_ids),
        "source_artifact_ids": list(request.source_artifact_ids),
        "command_preview": list(request.command_preview),
        "timeout_seconds": request.timeout_seconds,
        "duration_ms": raw_result.duration_ms,
        "prompt_handoff": {
            "contract": "product_wizard_prompt_contract_v1",
            "sha256": request.prompt_sha256,
        },
        "output_parser": {
            "name": "product_wizard_artifact_v1",
            "status": "validated",
        },
        "stdout_capture": dict(payload.get("stdout_capture", {})),
        "stderr_capture": dict(payload.get("stderr_capture", {})),
        "captured_error": "",
    }
    markdown_appendix = _live_hermes_adapter_appendix(metadata)
    return ParsedLiveHermesAdapterResult(
        metadata=metadata,
        markdown_appendix=markdown_appendix,
    )


def _safe_adapter_error(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        return "adapter exited without stderr."
    if secret_violations({"adapter_error": cleaned}):
        return "adapter error contained secret-looking content and was redacted."
    return cleaned[:500]


def _live_hermes_adapter_appendix(metadata: Mapping[str, Any]) -> str:
    command_preview = " ".join(str(part) for part in metadata["command_preview"])
    prompt_handoff = metadata["prompt_handoff"]
    output_parser = metadata["output_parser"]
    external_execution = str(metadata["external_execution"])
    title = (
        "Live Hermes Runner"
        if external_execution == "enabled"
        else "Live Hermes Dry Run"
    )
    capture_lines = []
    if external_execution == "enabled":
        stdout_capture = metadata.get("stdout_capture", {})
        stderr_capture = metadata.get("stderr_capture", {})
        capture_lines = [
            "- Captured stdout bytes: "
            f"`{stdout_capture.get('bytes', 0)}` "
            f"`{stdout_capture.get('sha256', '')}`",
            "- Captured stderr bytes: "
            f"`{stderr_capture.get('bytes', 0)}` "
            f"`{stderr_capture.get('sha256', '')}`",
        ]
    return "\n".join(
        [
            "",
            f"## {title}",
            "",
            f"- External execution: `{external_execution}`",
            f"- Adapter: `{metadata['adapter']}`",
            f"- Command preview: `{command_preview}`",
            "- Prompt handoff: "
            f"`{prompt_handoff['contract']}` `{prompt_handoff['sha256']}`",
            f"- Output parser: `{output_parser['name']}` `{output_parser['status']}`",
            f"- Timeout: `{metadata['timeout_seconds']}` seconds",
            *capture_lines,
            "- Captured error: none",
            "",
        ]
    )


def _output_capture(value: str, field: str) -> dict[str, Any]:
    text = value.strip()
    preview = text[:500]
    if text and secret_violations({field: text}):
        preview = "REDACTED_SECRET_OUTPUT"
    return {
        "bytes": len(text.encode("utf-8")),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
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
