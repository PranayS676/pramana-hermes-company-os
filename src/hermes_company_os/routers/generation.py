from __future__ import annotations

from fastapi import FastAPI, Form, HTTPException, Request

from hermes_company_os.generation_service import (
    LIVE_HERMES_GENERATION_MODE,
    GenerationMode,
    LiveHermesCommandAdapter,
    LiveHermesGenerationService,
    StageGenerationRequest,
    available_generation_modes,
    generation_mode_option,
    normalize_selectable_generation_mode,
    resolve_generation_mode_selection,
    stage_profile_routing,
)
from hermes_company_os.live_hermes_readiness import (
    evaluate_live_hermes_readiness,
    evaluate_live_hermes_run_confirmation,
)
from hermes_company_os.product_wizard import (
    FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
    ProductWizardIntake,
)
from hermes_company_os.project_memory import product_wizard_memory_context
from hermes_company_os.repository_protocol import RepositoryProtocol
from hermes_company_os.settings import Settings


def _intake_from_project(project: dict) -> ProductWizardIntake:
    intake = dict(project.get("intake") or {})
    intake.setdefault("project_name", project["name"])
    intake.setdefault("founder_idea", project["founder_idea"])
    return ProductWizardIntake.from_mapping(intake)


def _approved_source_artifacts(
    repository: RepositoryProtocol,
    project_id: str,
) -> list[dict]:
    sources: list[dict] = []
    for stage in repository.list_project_wizard_stages(project_id):
        artifact = repository.latest_project_stage_artifact(project_id, stage["stage_id"])
        if not artifact or artifact["status"] != "approved":
            continue
        sources.append(
            {
                "id": artifact["id"],
                "stage": artifact["stage_id"],
                "title": artifact.get("json", {}).get("title") or stage["name"],
                "content": artifact["markdown_content"],
                "status": "approved",
            }
        )
    return sources


def _resolve_stage_id(
    repository: RepositoryProtocol,
    project_id: str,
    stage_id: str,
) -> str:
    if stage_id != "current":
        return stage_id
    stage = repository.next_actionable_stage(project_id)
    if stage is None:
        raise HTTPException(
            status_code=409,
            detail="No actionable product wizard stage.",
        )
    return stage["stage_id"]


def _live_gate_for(readiness, run_confirmation):
    gate = readiness.gate
    if run_confirmation:
        gate = gate.with_run_confirmation(run_confirmation.fresh)
    return gate


def _live_generation_service(
    request: Request,
    settings: Settings,
    gate,
) -> LiveHermesGenerationService:
    injected_runner = getattr(request.app.state, "live_hermes_command_runner", None)
    adapter = None
    if injected_runner is not None:
        adapter = LiveHermesCommandAdapter(
            live_execution_enabled=settings.hermes_live_execution_enabled,
            runner=injected_runner,
            runner_label=getattr(
                request.app.state,
                "live_hermes_runner_label",
                "injected_runner",
            ),
        )
    return LiveHermesGenerationService(
        gate,
        adapter=adapter,
        timeout_seconds=settings.hermes_timeout_seconds,
        live_execution_enabled=settings.hermes_live_execution_enabled,
    )


def register_generation_routes(app: FastAPI) -> None:
    """Register the Milestone 3 generation mode-switch routes.

    These sit beside the existing wizard ``/generate`` form flow and expose the
    roadmap-facing generation-mode catalog (``local_demo``, ``live_hermes_draft``,
    ``live_hermes_with_review``) as a JSON-driven route switch. Live modes are
    guarded by the ``HERMES_LIVE_EXECUTION_ENABLED`` flag (default off) and by the
    Live Hermes readiness checks; when unavailable the switch fails closed into a
    blocked-state generation run rather than crashing or silently falling back to
    local generation.
    """

    @app.get("/projects/{project_id}/stages/{stage_id}/generation-modes.json")
    def project_stage_generation_modes(
        request: Request,
        project_id: str,
        stage_id: str,
    ) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        settings: Settings = request.app.state.settings
        if repository.get_project(project_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = _resolve_stage_id(repository, project_id, stage_id)
        stage = repository.get_project_wizard_stage(project_id, resolved_stage_id)
        if stage is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown product wizard stage: {resolved_stage_id}",
            )
        readiness = evaluate_live_hermes_readiness(
            repository,
            project_id,
            resolved_stage_id,
        )
        modes = available_generation_modes(
            live_execution_flag_enabled=settings.hermes_live_execution_enabled,
            readiness_ready=readiness.ready,
            readiness_blocker=readiness.blocker,
        )
        return {
            "project_id": project_id,
            "stage_id": resolved_stage_id,
            "live_execution_flag_enabled": settings.hermes_live_execution_enabled,
            "default_mode": "local_demo",
            "routing": stage_profile_routing(resolved_stage_id).to_dict(),
            "readiness": readiness.to_dict(),
            "modes": modes,
        }

    @app.post("/projects/{project_id}/stages/{stage_id}/generate-mode")
    def generate_project_stage_with_mode(
        request: Request,
        project_id: str,
        stage_id: str,
        generation_mode: str = Form("local_demo"),
    ) -> dict:
        repository: RepositoryProtocol = request.app.state.repository
        settings: Settings = request.app.state.settings
        project = repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        resolved_stage_id = _resolve_stage_id(repository, project_id, stage_id)
        if repository.get_project_wizard_stage(project_id, resolved_stage_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown product wizard stage: {resolved_stage_id}",
            )
        try:
            selectable_mode = normalize_selectable_generation_mode(generation_mode)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        option = generation_mode_option(selectable_mode)
        engine_mode: GenerationMode = option.engine_mode

        readiness = None
        run_confirmation = None
        if option.requires_live_hermes:
            readiness = evaluate_live_hermes_readiness(
                repository,
                project_id,
                resolved_stage_id,
            )
            run_confirmation = evaluate_live_hermes_run_confirmation(
                repository,
                project_id,
                resolved_stage_id,
            )

        resolved_mode = resolve_generation_mode_selection(
            selectable_mode,
            live_execution_flag_enabled=settings.hermes_live_execution_enabled,
            readiness_ready=bool(readiness and readiness.ready),
            readiness_blocker=readiness.blocker if readiness else "",
        )

        source_artifacts = _approved_source_artifacts(repository, project_id)
        memory_context = product_wizard_memory_context(repository, project_id)

        # Every attempt is recorded, including blocked ones, so the founder has a
        # full audit trail. The run is created in the engine (underlying) mode.
        generation_run_id = repository.create_generation_run(
            project_id=project_id,
            stage_id=resolved_stage_id,
            generation_mode=engine_mode,
            source_artifact_ids=[source["id"] for source in source_artifacts],
            memory_ids=[memory["id"] for memory in memory_context],
        )

        # Fail closed: an unavailable live mode produces a blocked-state run
        # (failed run record) rather than crashing or silently using local mode.
        if not resolved_mode.available:
            repository.fail_generation_run(generation_run_id, resolved_mode.blocker)
            raise HTTPException(
                status_code=409,
                detail={
                    "blocker": resolved_mode.blocker,
                    "generation_run_id": generation_run_id,
                    "selected_mode": selectable_mode,
                    "state": "blocked",
                },
            )

        generation_request = StageGenerationRequest(
            stage_id=resolved_stage_id,
            intake=_intake_from_project(project),
            approved_sources=source_artifacts,
            memory_context=memory_context,
            memory_policy=FOUNDER_APPROVED_PRODUCT_WIZARD_MEMORY_POLICY,
            mode=engine_mode,
        )

        if engine_mode == LIVE_HERMES_GENERATION_MODE:
            service = _live_generation_service(
                request,
                settings,
                _live_gate_for(readiness, run_confirmation),
            )
        else:
            service = request.app.state.generation_service

        try:
            if engine_mode == LIVE_HERMES_GENERATION_MODE and (
                settings.hermes_live_execution_enabled
                and run_confirmation
                and not run_confirmation.fresh
            ):
                raise ValueError(run_confirmation.blocker)
            artifact = service.generate_stage(generation_request)
            artifact_id = repository.save_stage_artifact_draft(
                project_id=project_id,
                stage_id=resolved_stage_id,
                markdown_content=artifact.markdown,
                json_content=artifact.metadata,
                owner_agent_id=artifact.owner_agent_id,
            )
            repository.complete_generation_run(
                generation_run_id,
                artifact_id,
                source_artifact_ids=list(artifact.source_artifact_ids),
                memory_ids=list(artifact.memory_ids),
            )
        except ValueError as exc:
            repository.fail_generation_run(generation_run_id, str(exc))
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return {
            "project_id": project_id,
            "stage_id": resolved_stage_id,
            "selected_mode": selectable_mode,
            "engine_mode": engine_mode,
            "requires_review": option.requires_review,
            "generation_run_id": generation_run_id,
            "artifact_id": artifact_id,
            "state": "generated",
        }
