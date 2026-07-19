"""Kernel admission gate for Provider-supported problem structures."""

from __future__ import annotations

from .contextual_policy_models import ContextualProblemStructure
from .problem_structure_admission_models import (
    PROBLEM_STRUCTURE_DIMENSIONS,
    ProblemStructureAdmissionDecision,
    ProblemStructureAdmissionReceipt,
    ProblemStructureCandidate,
    ProblemStructureProviderJudgment,
)


_DIMENSION_SIGNAL_REQUIREMENTS = {
    "premise_uncertainty": {"premise_risk"},
    "evidence_conflict": {"premise_risk", "negative_transfer_risk"},
    "replication_need": {"falsifiability", "tractability"},
    "synthesis_need": {"premise_risk", "negative_transfer_risk"},
    "coordination_complexity": {"tractability", "normalized_cost"},
    "novelty_need": {"novelty"},
}


class ProblemStructureAdmissionGate:
    """Admit one project-scoped structure without transferring authority to Provider."""

    def __init__(
        self,
        *,
        max_dimension_uncertainty: float = 0.45,
        max_global_uncertainty: float = 0.45,
    ) -> None:
        if not 0 <= max_dimension_uncertainty <= 1 or not 0 <= max_global_uncertainty <= 1:
            raise ValueError("problem_structure_admission_uncertainty_limit_invalid")
        self.max_dimension_uncertainty = max_dimension_uncertainty
        self.max_global_uncertainty = max_global_uncertainty

    def admit(
        self,
        *,
        admission_id: str,
        candidate: ProblemStructureCandidate,
        judgment: ProblemStructureProviderJudgment,
        kernel_authorization_ref: str,
        anti_additive_methodology_receipt_hash: str = "",
    ) -> ProblemStructureAdmissionReceipt:
        failures = self.failures(candidate=candidate, judgment=judgment)
        if failures:
            raise ValueError("problem_structure_admission_blocked:" + ";".join(failures))
        state = (
            "ADMITTED_REVISION_PROJECT_SCOPED"
            if candidate.supersedes_receipt_hash
            else "ADMITTED_PROBLEM_STRUCTURE_PROJECT_SCOPED"
        )
        decision = ProblemStructureAdmissionDecision.create(
            admission_id=admission_id,
            candidate_state=state,
            admitted=True,
            reason="provider_supported_structure_passed_kernel_admission_gates",
            candidate_hash=candidate.candidate_hash,
            provider_judgment_hash=judgment.judgment_hash,
            source_seed_hash=candidate.source_seed_hash,
            supersedes_receipt_hash=candidate.supersedes_receipt_hash,
            kernel_authorization_ref=kernel_authorization_ref,
            anti_additive_methodology_receipt_hash=anti_additive_methodology_receipt_hash,
            evidence_refs=candidate.evidence_refs,
        )
        scores = {item.dimension: item.score for item in judgment.dimension_assessments}
        structure = ContextualProblemStructure(
            problem_id=candidate.source_problem_id,
            context_key=candidate.context_key,
            project_scope=candidate.project_scope,
            objective=candidate.objective,
            premise_uncertainty=scores["premise_uncertainty"],
            evidence_conflict=scores["evidence_conflict"],
            replication_need=scores["replication_need"],
            synthesis_need=scores["synthesis_need"],
            coordination_complexity=scores["coordination_complexity"],
            novelty_need=scores["novelty_need"],
            evidence_refs=candidate.evidence_refs,
            structure_receipt_ref=f"problem-structure-admission://{admission_id}",
            structure_receipt_hash=decision.decision_hash,
        )
        return ProblemStructureAdmissionReceipt.create(
            candidate=candidate,
            provider_judgment=judgment,
            decision=decision,
            problem_structure=structure,
        )

    def failures(
        self,
        *,
        candidate: ProblemStructureCandidate,
        judgment: ProblemStructureProviderJudgment,
    ) -> tuple[str, ...]:
        failures = []
        if judgment.candidate_hash != candidate.candidate_hash:
            failures.append("candidate_hash_mismatch")
        if judgment.global_uncertainty > self.max_global_uncertainty:
            failures.append("global_uncertainty_exceeded")
        if not set(judgment.evidence_refs).issubset(candidate.evidence_refs):
            failures.append("judgment_evidence_outside_candidate")
        signal_names = {item.signal_name for item in candidate.source_signals}
        assessments = {item.dimension: item for item in judgment.dimension_assessments}
        for dimension in PROBLEM_STRUCTURE_DIMENSIONS:
            item = assessments[dimension]
            if item.support_status != "CONSISTENT":
                failures.append(f"dimension_support_not_consistent:{dimension}")
            if item.uncertainty > self.max_dimension_uncertainty:
                failures.append(f"dimension_uncertainty_exceeded:{dimension}")
            if not set(item.evidence_refs).issubset(candidate.evidence_refs):
                failures.append(f"dimension_evidence_outside_candidate:{dimension}")
            cited = set(item.source_signal_names)
            if not cited.issubset(signal_names):
                failures.append(f"dimension_source_signal_unknown:{dimension}")
            if not cited.intersection(_DIMENSION_SIGNAL_REQUIREMENTS[dimension]):
                failures.append(f"dimension_source_signal_required:{dimension}")
        return tuple(dict.fromkeys(failures))
