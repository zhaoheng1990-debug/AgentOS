"""Read-only port for admitted project-scoped problem structures."""

from __future__ import annotations

from typing import Protocol

from agentos_kernel import ContextualProblemStructure, ProblemStructureAdmissionReceipt


class AdmittedProblemStructureSource(Protocol):
    def problem_structure_admission_receipt(
        self,
        *,
        admission_id: str,
        project_scope: str,
    ) -> ProblemStructureAdmissionReceipt:
        """Return one Kernel-admitted receipt by explicit identity."""


def resolve_problem_structure(
    *,
    source: AdmittedProblemStructureSource | None,
    project_scope: str,
    admission_id: str,
    direct_problem: ContextualProblemStructure | None,
) -> ContextualProblemStructure:
    if source is not None:
        if direct_problem is not None:
            raise ValueError("contextual_policy_direct_problem_forbidden_with_admission_source")
        if not admission_id:
            raise ValueError("contextual_policy_problem_admission_id_required")
        receipt = source.problem_structure_admission_receipt(
            admission_id=admission_id,
            project_scope=project_scope,
        )
        if (
            receipt.decision.admission_id != admission_id
            or receipt.decision.admitted is not True
            or receipt.problem_structure.project_scope != project_scope
            or receipt.problem_structure.structure_receipt_hash != receipt.decision.decision_hash
        ):
            raise ValueError("contextual_policy_problem_admission_receipt_invalid")
        problem = receipt.problem_structure
        if problem.structure_receipt_ref != f"problem-structure-admission://{admission_id}":
            raise ValueError("contextual_policy_problem_admission_receipt_invalid")
    else:
        if direct_problem is None:
            raise ValueError("contextual_policy_problem_required")
        if admission_id:
            raise ValueError("contextual_policy_problem_admission_source_required")
        problem = direct_problem
    if problem.project_scope != project_scope:
        raise ValueError("contextual_policy_problem_scope_mismatch")
    return problem
