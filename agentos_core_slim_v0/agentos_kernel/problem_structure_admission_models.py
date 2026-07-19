"""Pure contracts for evidence-bound problem-structure admission."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .contextual_policy_models import (
    ContextualProblemStructure,
    hash_payload,
    require_refs,
    require_text,
    require_unit,
)


PROBLEM_STRUCTURE_ADMISSION_VERSION = "problem_structure_admission_kernel_v0_1"
PROBLEM_STRUCTURE_DIMENSIONS = (
    "premise_uncertainty",
    "evidence_conflict",
    "replication_need",
    "synthesis_need",
    "coordination_complexity",
    "novelty_need",
)
PROBLEM_STRUCTURE_SOURCE_SIGNALS = (
    "premise_risk",
    "redundancy_risk",
    "negative_transfer_risk",
    "falsifiability",
    "tractability",
    "normalized_cost",
    "novelty",
    "urgency",
    "expected_cbit_gain",
)
_SUPPORT_STATES = {"CONSISTENT", "CONFLICT", "INSUFFICIENT"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _require_id(name: str, value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"{name}_invalid")


def _require_hash(name: str, value: str, *, optional: bool = False) -> None:
    if optional and not value:
        return
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class ProblemStructureSourceSignal:
    signal_name: str
    value: float
    evidence_refs: tuple[str, ...]
    source_message_hash: str
    signal_hash: str

    def __post_init__(self) -> None:
        if self.signal_name not in PROBLEM_STRUCTURE_SOURCE_SIGNALS:
            raise ValueError("problem_structure_source_signal_name_invalid")
        require_unit("problem_structure_source_signal_value", self.value)
        require_refs("problem_structure_source_signal_evidence_refs", self.evidence_refs)
        _require_hash("problem_structure_source_signal_message_hash", self.source_message_hash)
        if self.signal_hash != hash_payload(self._committed_dict()):
            raise ValueError("problem_structure_source_signal_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ProblemStructureSourceSignal":
        return cls(**values, signal_hash=hash_payload(values))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "signal_name": self.signal_name,
            "value": self.value,
            "evidence_refs": list(self.evidence_refs),
            "source_message_hash": self.source_message_hash,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "signal_hash": self.signal_hash}


@dataclass(frozen=True)
class ProblemStructureCandidate:
    candidate_id: str
    source_problem_id: str
    context_key: str
    project_scope: str
    objective: str
    source_seed_ref: str
    source_seed_hash: str
    evidence_refs: tuple[str, ...]
    rival_explanations: tuple[str, ...]
    unresolved_conflicts: tuple[str, ...]
    required_harnesses: tuple[str, ...]
    source_message_hashes: tuple[str, ...]
    source_execution_receipt_hashes: tuple[str, ...]
    source_signals: tuple[ProblemStructureSourceSignal, ...]
    supersedes_receipt_hash: str
    candidate_hash: str

    def __post_init__(self) -> None:
        for name in ("candidate_id", "source_problem_id"):
            _require_id(f"problem_structure_{name}", getattr(self, name))
        require_text("problem_structure_context_key", self.context_key)
        require_text("problem_structure_objective", self.objective)
        require_text("problem_structure_source_seed_ref", self.source_seed_ref)
        if not self.project_scope.startswith("project://"):
            raise ValueError("problem_structure_candidate_scope_invalid")
        require_refs("problem_structure_candidate_evidence_refs", self.evidence_refs)
        if not self.rival_explanations or not self.required_harnesses:
            raise ValueError("problem_structure_candidate_rivals_and_harnesses_required")
        if len(self.source_message_hashes) != 4 or len(set(self.source_message_hashes)) != 4:
            raise ValueError("problem_structure_candidate_message_surface_invalid")
        if (
            len(self.source_execution_receipt_hashes) != 4
            or len(set(self.source_execution_receipt_hashes)) != 4
        ):
            raise ValueError("problem_structure_candidate_execution_surface_invalid")
        for value in (
            self.source_seed_hash,
            *self.source_message_hashes,
            *self.source_execution_receipt_hashes,
        ):
            _require_hash("problem_structure_candidate_source_hash", value)
        _require_hash(
            "problem_structure_candidate_supersedes_receipt_hash",
            self.supersedes_receipt_hash,
            optional=True,
        )
        signal_names = tuple(item.signal_name for item in self.source_signals)
        if signal_names != PROBLEM_STRUCTURE_SOURCE_SIGNALS:
            raise ValueError("problem_structure_candidate_source_signal_coverage_invalid")
        if any(not set(item.evidence_refs).issubset(self.evidence_refs) for item in self.source_signals):
            raise ValueError("problem_structure_candidate_source_signal_evidence_invalid")
        if any(item.source_message_hash not in self.source_message_hashes for item in self.source_signals):
            raise ValueError("problem_structure_candidate_source_signal_message_invalid")
        if self.candidate_hash != hash_payload(self._committed_dict()):
            raise ValueError("problem_structure_candidate_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ProblemStructureCandidate":
        committed = cls._normalize(values)
        return cls(**values, candidate_hash=hash_payload(committed))

    @staticmethod
    def _normalize(values: dict[str, Any]) -> dict[str, Any]:
        return {
            **values,
            "evidence_refs": list(values["evidence_refs"]),
            "rival_explanations": list(values["rival_explanations"]),
            "unresolved_conflicts": list(values["unresolved_conflicts"]),
            "required_harnesses": list(values["required_harnesses"]),
            "source_message_hashes": list(values["source_message_hashes"]),
            "source_execution_receipt_hashes": list(values["source_execution_receipt_hashes"]),
            "source_signals": [item.as_dict() for item in values["source_signals"]],
        }

    def _committed_dict(self) -> dict[str, Any]:
        return self._normalize(
            {
                "candidate_id": self.candidate_id,
                "source_problem_id": self.source_problem_id,
                "context_key": self.context_key,
                "project_scope": self.project_scope,
                "objective": self.objective,
                "source_seed_ref": self.source_seed_ref,
                "source_seed_hash": self.source_seed_hash,
                "evidence_refs": self.evidence_refs,
                "rival_explanations": self.rival_explanations,
                "unresolved_conflicts": self.unresolved_conflicts,
                "required_harnesses": self.required_harnesses,
                "source_message_hashes": self.source_message_hashes,
                "source_execution_receipt_hashes": self.source_execution_receipt_hashes,
                "source_signals": self.source_signals,
                "supersedes_receipt_hash": self.supersedes_receipt_hash,
            }
        )

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "candidate_hash": self.candidate_hash}


@dataclass(frozen=True)
class ProblemStructureDimensionAssessment:
    dimension: str
    score: float
    uncertainty: float
    support_status: str
    rationale: str
    evidence_refs: tuple[str, ...]
    source_signal_names: tuple[str, ...]
    assessment_hash: str

    def __post_init__(self) -> None:
        if self.dimension not in PROBLEM_STRUCTURE_DIMENSIONS:
            raise ValueError("problem_structure_dimension_invalid")
        require_unit("problem_structure_dimension_score", self.score)
        require_unit("problem_structure_dimension_uncertainty", self.uncertainty)
        if self.support_status not in _SUPPORT_STATES:
            raise ValueError("problem_structure_dimension_support_status_invalid")
        require_text("problem_structure_dimension_rationale", self.rationale)
        require_refs("problem_structure_dimension_evidence_refs", self.evidence_refs)
        if not self.source_signal_names or not set(self.source_signal_names).issubset(
            PROBLEM_STRUCTURE_SOURCE_SIGNALS
        ):
            raise ValueError("problem_structure_dimension_source_signals_invalid")
        if self.assessment_hash != hash_payload(self._committed_dict()):
            raise ValueError("problem_structure_dimension_assessment_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ProblemStructureDimensionAssessment":
        committed = {
            **values,
            "evidence_refs": list(values["evidence_refs"]),
            "source_signal_names": list(values["source_signal_names"]),
        }
        return cls(**values, assessment_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "uncertainty": self.uncertainty,
            "support_status": self.support_status,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "source_signal_names": list(self.source_signal_names),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "assessment_hash": self.assessment_hash}


@dataclass(frozen=True)
class ProblemStructureProviderJudgment:
    candidate_hash: str
    dimension_assessments: tuple[ProblemStructureDimensionAssessment, ...]
    global_uncertainty: float
    evidence_refs: tuple[str, ...]
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    judgment_hash: str

    def __post_init__(self) -> None:
        _require_hash("problem_structure_provider_candidate_hash", self.candidate_hash)
        dimensions = tuple(item.dimension for item in self.dimension_assessments)
        if dimensions != PROBLEM_STRUCTURE_DIMENSIONS:
            raise ValueError("problem_structure_provider_dimension_coverage_invalid")
        require_unit("problem_structure_provider_global_uncertainty", self.global_uncertainty)
        if abs(self.global_uncertainty - max(item.uncertainty for item in self.dimension_assessments)) > 1e-9:
            raise ValueError("problem_structure_provider_global_uncertainty_mismatch")
        require_refs("problem_structure_provider_evidence_refs", self.evidence_refs)
        if self.judgment_hash != hash_payload(self._committed_dict()):
            raise ValueError("problem_structure_provider_judgment_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ProblemStructureProviderJudgment":
        committed = {
            **values,
            "dimension_assessments": [item.as_dict() for item in values["dimension_assessments"]],
            "evidence_refs": list(values["evidence_refs"]),
        }
        return cls(**values, judgment_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "candidate_hash": self.candidate_hash,
            "dimension_assessments": [item.as_dict() for item in self.dimension_assessments],
            "global_uncertainty": self.global_uncertainty,
            "evidence_refs": list(self.evidence_refs),
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "judgment_hash": self.judgment_hash}


@dataclass(frozen=True)
class ProblemStructureAdmissionDecision:
    admission_id: str
    candidate_state: str
    admitted: bool
    reason: str
    candidate_hash: str
    provider_judgment_hash: str
    source_seed_hash: str
    supersedes_receipt_hash: str
    kernel_authorization_ref: str
    anti_additive_methodology_receipt_hash: str
    evidence_refs: tuple[str, ...]
    decision_hash: str

    def __post_init__(self) -> None:
        _require_id("problem_structure_admission_id", self.admission_id)
        expected = (
            "ADMITTED_REVISION_PROJECT_SCOPED"
            if self.supersedes_receipt_hash
            else "ADMITTED_PROBLEM_STRUCTURE_PROJECT_SCOPED"
        )
        if self.candidate_state != expected or self.admitted is not True:
            raise ValueError("problem_structure_admission_state_invalid")
        require_text("problem_structure_admission_reason", self.reason)
        for name in ("candidate_hash", "provider_judgment_hash", "source_seed_hash"):
            _require_hash(f"problem_structure_admission_{name}", getattr(self, name))
        _require_hash(
            "problem_structure_admission_supersedes_receipt_hash",
            self.supersedes_receipt_hash,
            optional=True,
        )
        if not self.kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("problem_structure_admission_kernel_authorization_required")
        _require_hash(
            "problem_structure_admission_anti_additive_receipt_hash",
            self.anti_additive_methodology_receipt_hash,
            optional=True,
        )
        require_refs("problem_structure_admission_evidence_refs", self.evidence_refs)
        if self.decision_hash != hash_payload(self._committed_dict()):
            raise ValueError("problem_structure_admission_decision_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ProblemStructureAdmissionDecision":
        committed = {**values, "evidence_refs": list(values["evidence_refs"])}
        return cls(**values, decision_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "admission_id": self.admission_id,
            "candidate_state": self.candidate_state,
            "admitted": self.admitted,
            "reason": self.reason,
            "candidate_hash": self.candidate_hash,
            "provider_judgment_hash": self.provider_judgment_hash,
            "source_seed_hash": self.source_seed_hash,
            "supersedes_receipt_hash": self.supersedes_receipt_hash,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "anti_additive_methodology_receipt_hash": self.anti_additive_methodology_receipt_hash,
            "evidence_refs": list(self.evidence_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "decision_hash": self.decision_hash}


@dataclass(frozen=True)
class ProblemStructureAdmissionReceipt:
    candidate: ProblemStructureCandidate
    provider_judgment: ProblemStructureProviderJudgment
    decision: ProblemStructureAdmissionDecision
    problem_structure: ContextualProblemStructure
    created_at: str
    receipt_hash: str

    def __post_init__(self) -> None:
        if self.decision.candidate_hash != self.candidate.candidate_hash:
            raise ValueError("problem_structure_receipt_candidate_binding_invalid")
        if self.decision.provider_judgment_hash != self.provider_judgment.judgment_hash:
            raise ValueError("problem_structure_receipt_provider_binding_invalid")
        if self.problem_structure.structure_receipt_hash != self.decision.decision_hash:
            raise ValueError("problem_structure_receipt_decision_binding_invalid")
        if (
            self.problem_structure.problem_id != self.candidate.source_problem_id
            or self.problem_structure.context_key != self.candidate.context_key
            or self.problem_structure.project_scope != self.candidate.project_scope
            or self.problem_structure.objective != self.candidate.objective
            or self.problem_structure.evidence_refs != self.candidate.evidence_refs
        ):
            raise ValueError("problem_structure_receipt_object_binding_invalid")
        if self.receipt_hash != hash_payload(self._committed_dict()):
            raise ValueError("problem_structure_admission_receipt_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        candidate: ProblemStructureCandidate,
        provider_judgment: ProblemStructureProviderJudgment,
        decision: ProblemStructureAdmissionDecision,
        problem_structure: ContextualProblemStructure,
    ) -> "ProblemStructureAdmissionReceipt":
        created_at = _utc_now()
        committed = {
            "candidate": candidate.as_dict(),
            "provider_judgment": provider_judgment.as_dict(),
            "decision": decision.as_dict(),
            "problem_structure": problem_structure.as_dict(),
            "created_at": created_at,
        }
        return cls(
            candidate=candidate,
            provider_judgment=provider_judgment,
            decision=decision,
            problem_structure=problem_structure,
            created_at=created_at,
            receipt_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.as_dict(),
            "provider_judgment": self.provider_judgment.as_dict(),
            "decision": self.decision.as_dict(),
            "problem_structure": self.problem_structure.as_dict(),
            "created_at": self.created_at,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "receipt_hash": self.receipt_hash,
            "global_policy_authority": False,
            "execution_authorized": False,
            "production_activation": False,
        }
