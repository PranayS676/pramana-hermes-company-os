from __future__ import annotations

from pathlib import Path

from hermes_company_os.repository_audit_agents import AuditAndAgentsMixin
from hermes_company_os.repository_decisions_work import DecisionsAndWorkQueueMixin
from hermes_company_os.repository_generation import GenerationExecutionMixin
from hermes_company_os.repository_project_workflow import ProjectWorkflowMixin
from hermes_company_os.repository_setup_verification import SetupVerificationMixin
from hermes_company_os.repository_stage_lifecycle import StageLifecycleMixin


class CompanyRepository(
    AuditAndAgentsMixin,
    SetupVerificationMixin,
    DecisionsAndWorkQueueMixin,
    ProjectWorkflowMixin,
    GenerationExecutionMixin,
    StageLifecycleMixin,
):
    def __init__(self, database_path: Path):
        self.database_path = database_path
