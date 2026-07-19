"""Anti-Additive receipt adapter for problem-structure admission."""

from __future__ import annotations

from agentos_kernel import ProblemStructureCandidate, methodology_candidate_commitment

from .anti_additive_source import (
    AntiAdditiveMethodologyReceiptSource,
    resolve_anti_additive_methodology_receipt,
)


def problem_structure_methodology_receipt_hash(
    *,
    source: AntiAdditiveMethodologyReceiptSource | None,
    methodology_audit_id: str,
    project_scope: str,
    candidate: ProblemStructureCandidate,
) -> str:
    if source is None:
        if methodology_audit_id:
            raise ValueError("problem_structure_anti_additive_source_required")
        return ""
    if not methodology_audit_id:
        raise ValueError("problem_structure_anti_additive_audit_id_required")
    return resolve_anti_additive_methodology_receipt(
        source=source,
        audit_id=methodology_audit_id,
        project_scope=project_scope,
        candidate_id=candidate.candidate_id,
        candidate_payload_hash=methodology_candidate_commitment(candidate.as_dict()),
        target_type="ProblemStructure",
        authority_requirement="CANDIDATE_ONLY",
    ).receipt_hash
