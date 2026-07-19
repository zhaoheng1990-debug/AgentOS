"""Thin orchestration facade for evidence-bound problem-structure admission."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ProblemStructureAdmissionGate,
    ProblemStructureAdmissionReceipt,
    ProblemStructureCandidate,
    ProviderTaskRouter,
)

from .problem_definition import EndogenousProblemRuntime
from .problem_structure_contracts import (
    PROBLEM_STRUCTURE_ADMISSION_RUNTIME_VERSION,
    ProblemStructureAdmissionSnapshot,
)
from .problem_structure_provider import ProblemStructureProviderAdvisor
from .problem_structure_repository import ProblemStructureRepository
from .problem_structure_source_adapter import ProblemDefinitionStructureAdapter
from .anti_additive_problem_structure import problem_structure_methodology_receipt_hash
from .anti_additive_source import AntiAdditiveMethodologyReceiptSource


class ProblemStructureAdmissionRuntime:
    """Compose source adaptation, Provider support, Kernel admission, and replay."""

    module_id = PROBLEM_STRUCTURE_ADMISSION_RUNTIME_VERSION
    capabilities = (
        "endogenous_problem_structure_admission", "provider_supported_constraint_dimensions",
        "kernel_owned_structure_state", "versioned_problem_structure_revisions",
        "selector_problem_structure_source",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        provider_router: ProviderTaskRouter,
        workspace_root: str | Path,
        admission_gate: ProblemStructureAdmissionGate | None = None,
        anti_additive_source: AntiAdditiveMethodologyReceiptSource | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("problem_structure_admission_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("problem_structure_admission_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.admission_gate = admission_gate or ProblemStructureAdmissionGate()
        self.anti_additive_source = anti_additive_source
        self._repository = ProblemStructureRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )
        self._provider = ProblemStructureProviderAdvisor(
            runtime_id=runtime_id,
            provider_router=provider_router,
            event_sink=self._repository.persist_event,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def admit_from_problem_runtime(
        self,
        *,
        admission_id: str,
        problem_runtime: EndogenousProblemRuntime,
        context_key: str,
        kernel_authorization_ref: str,
        supersedes_receipt_hash: str = "",
        methodology_audit_id: str = "",
    ) -> ProblemStructureAdmissionReceipt:
        try:
            candidate = ProblemDefinitionStructureAdapter(
                problem_runtime,
                context_key=context_key,
            ).build_candidate(
                candidate_id=f"candidate-{admission_id}",
                supersedes_receipt_hash=supersedes_receipt_hash,
            )
        except Exception as exc:
            self._repository.persist_blocked(
                {
                    "admission_id": admission_id,
                    "source_adapter_id": ProblemDefinitionStructureAdapter.adapter_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            raise
        return self.admit_candidate(
            admission_id=admission_id,
            candidate=candidate,
            kernel_authorization_ref=kernel_authorization_ref,
            methodology_audit_id=methodology_audit_id,
        )

    def admit_candidate(
        self,
        *,
        admission_id: str,
        candidate: ProblemStructureCandidate,
        kernel_authorization_ref: str,
        methodology_audit_id: str = "",
    ) -> ProblemStructureAdmissionReceipt:
        if self._repository.receipt(admission_id) is not None:
            raise ValueError(f"duplicate_problem_structure_admission:{admission_id}")
        if candidate.project_scope != self.project_scope:
            raise ValueError("problem_structure_admission_candidate_scope_mismatch")
        self._repository.validate_candidate_revision(candidate)
        try:
            methodology_receipt_hash = problem_structure_methodology_receipt_hash(
                source=self.anti_additive_source,
                methodology_audit_id=methodology_audit_id,
                project_scope=self.project_scope,
                candidate=candidate,
            )
            judgment = self._provider.assess(candidate)
            receipt = self.admission_gate.admit(
                admission_id=admission_id,
                candidate=candidate,
                judgment=judgment,
                kernel_authorization_ref=kernel_authorization_ref,
                anti_additive_methodology_receipt_hash=methodology_receipt_hash,
            )
            self._repository.save(receipt)
            return receipt
        except Exception as exc:
            self._repository.persist_blocked(
                {
                    "admission_id": admission_id,
                    "candidate_hash": candidate.candidate_hash,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            raise

    def problem_structure_admission_receipt(
        self,
        *,
        admission_id: str,
        project_scope: str,
    ) -> ProblemStructureAdmissionReceipt:
        if project_scope != self.project_scope:
            raise ValueError("problem_structure_source_scope_mismatch")
        receipt = self._repository.receipt(admission_id)
        if receipt is None:
            raise KeyError(f"problem_structure_admission_not_found:{admission_id}")
        return receipt

    def receipt(self, admission_id: str) -> ProblemStructureAdmissionReceipt | None:
        return self._repository.receipt(admission_id)

    def latest_receipt(self, *, context_key: str, source_problem_id: str):
        return self._repository.latest(
            context_key=context_key,
            source_problem_id=source_problem_id,
        )

    def snapshot(self) -> ProblemStructureAdmissionSnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, Any]:
        return self._repository.verify_replay()
