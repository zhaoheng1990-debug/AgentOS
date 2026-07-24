"""Constraint-aligned admission gate for project-scoped retention.

The gate is deliberately decision-only. Durable writes remain owned by the
existing kernel evolution policy and project-scoped store, so passing this
gate does not grant global, production, or theory-baseline write authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .anti_additive_models import AntiAdditiveMethodologyReceipt, methodology_candidate_commitment
from .cognitive_work_models import CognitiveWorkControlDecision, validate_control_binding


SUPPORTED_DECISION_STATUSES = {
    "SUPPORTED_BOUNDED",
    "SUPPORTED_WITH_NEGATIVE_CONTROL",
}

POSITIVE_RETENTION_DIMENSIONS = (
    "future_cbit_gain_score",
    "transferability",
    "search_efficiency",
    "residual_reduction",
)

NEGATIVE_RETENTION_DIMENSIONS = (
    "complexity",
    "negative_transfer_score",
    "scope_ambiguity",
)


@dataclass(frozen=True)
class ConstraintAlignedRetentionDecision:
    """Auditable outcome of the constraint-aligned retention gate."""

    decision: str
    eligible_for_retention: bool
    reason: str
    retention_score: float | None
    hard_gate_failures: tuple[str, ...]
    anti_additive_methodology_receipt_hash: str = ""


class ConstraintAlignedRetentionGate:
    """Apply hard safety gates before a strict scalar retention threshold."""

    def __init__(
        self,
        *,
        constraint_alignment_threshold: float = 0.70,
        negative_transfer_ceiling: float = 0.30,
        scope_ambiguity_ceiling: float = 0.30,
        retention_threshold: float = 1.00,
    ) -> None:
        self.constraint_alignment_threshold = self._threshold(
            "constraint_alignment_threshold", constraint_alignment_threshold
        )
        self.negative_transfer_ceiling = self._threshold(
            "negative_transfer_ceiling", negative_transfer_ceiling
        )
        self.scope_ambiguity_ceiling = self._threshold(
            "scope_ambiguity_ceiling", scope_ambiguity_ceiling
        )
        try:
            self.retention_threshold = Decimal(str(retention_threshold))
        except InvalidOperation as exc:
            raise ValueError("retention_threshold_must_be_numeric") from exc

    def evaluate(
        self,
        candidate: dict[str, Any],
        *,
        methodology_receipt: AntiAdditiveMethodologyReceipt | None = None,
        require_methodology_receipt: bool = False,
        cognitive_work_control: CognitiveWorkControlDecision | None = None,
    ) -> ConstraintAlignedRetentionDecision:
        if cognitive_work_control is not None:
            project_scope = candidate.get("project_scope_ref") or candidate.get("project_scope")
            validate_control_binding(cognitive_work_control, project_scope=project_scope)
            if cognitive_work_control.evidence_ref not in (candidate.get("evidence_refs") or []):
                return self._blocked(
                    "BLOCK_INSUFFICIENT_EVIDENCE",
                    "cognitive_work_control_not_bound_to_retention_evidence",
                    "cognitive_work_evidence_binding",
                )
            if not cognitive_work_control.retention_eligible:
                return self._blocked(
                    "OBSERVE_LOW_RETENTION_SCORE",
                    "cognitive_work_trajectory_not_retention_eligible",
                    "cognitive_work_retention_gate",
                )
        if candidate.get("scope") != "project_scoped":
            return self._blocked(
                "REQUEST_HUMAN_SCOPE_ESCALATION",
                "scope_not_project_scoped",
                "scope_not_project_scoped",
            )

        if candidate.get("decision_status") not in SUPPORTED_DECISION_STATUSES:
            return self._blocked(
                "BLOCK_UNSUPPORTED_DECISION",
                "decision_status_not_bounded_support",
                "unsupported_decision_status",
            )

        if not self._has_evidence_coordinates(candidate):
            return self._blocked(
                "BLOCK_INSUFFICIENT_EVIDENCE",
                "missing_evidence_coordinates_or_replayability",
                "insufficient_evidence",
            )

        dimensions, invalid = self._dimensions(candidate)
        alignment = self._unit_interval(candidate.get("constraint_alignment"))
        if alignment is None:
            invalid.append("constraint_alignment")
        if invalid:
            return self._blocked(
                "BLOCK_INCOMPLETE_RETENTION_METRICS",
                "missing_or_invalid_unit_interval_metrics",
                *(f"invalid_metric:{name}" for name in sorted(set(invalid))),
            )

        negative_transfer = dimensions["negative_transfer_score"]
        if candidate.get("negative_transfer_detected") is True or negative_transfer > self.negative_transfer_ceiling:
            return self._blocked(
                "QUARANTINE_NEGATIVE_TRANSFER",
                "negative_transfer_exceeds_frozen_ceiling",
                "negative_transfer",
                score=self._retention_score(dimensions),
            )

        if alignment < self.constraint_alignment_threshold:
            return self._blocked(
                "BLOCK_CONSTRAINT_MISALIGNMENT",
                "constraint_alignment_below_frozen_threshold",
                "constraint_misalignment",
                score=self._retention_score(dimensions),
            )

        if dimensions["scope_ambiguity"] > self.scope_ambiguity_ceiling:
            return self._blocked(
                "BLOCK_SCOPE_AMBIGUITY",
                "scope_ambiguity_exceeds_frozen_ceiling",
                "scope_ambiguity",
                score=self._retention_score(dimensions),
            )

        score = self._retention_score(dimensions)
        if score <= self.retention_threshold:
            return self._blocked(
                "OBSERVE_LOW_RETENTION_SCORE",
                "retention_score_not_strictly_above_frozen_threshold",
                "retention_score",
                score=score,
            )

        methodology_hash = ""
        if require_methodology_receipt:
            failure = self._methodology_failure(candidate, methodology_receipt)
            if failure:
                return self._blocked(
                    "BLOCK_ANTI_ADDITIVE_METHODOLOGY",
                    failure,
                    "anti_additive_methodology",
                    score=score,
                )
            methodology_hash = methodology_receipt.receipt_hash

        return ConstraintAlignedRetentionDecision(
            decision="RETAIN_PROJECT_SCOPED",
            eligible_for_retention=True,
            reason="all_hard_gates_pass_and_score_above_threshold",
            retention_score=float(score),
            hard_gate_failures=(),
            anti_additive_methodology_receipt_hash=methodology_hash,
        )

    @staticmethod
    def _methodology_failure(candidate, receipt):
        if receipt is None:
            return "anti_additive_methodology_receipt_required"
        if receipt.candidate.candidate_id != candidate.get("candidate_id"):
            return "anti_additive_methodology_candidate_id_mismatch"
        if receipt.candidate.target_type != "RetentionCandidate":
            return "anti_additive_methodology_target_type_mismatch"
        if receipt.candidate.project_scope != candidate.get("project_scope_ref"):
            return "anti_additive_methodology_scope_mismatch"
        if receipt.candidate.candidate_payload_hash != methodology_candidate_commitment(candidate):
            return "anti_additive_methodology_candidate_payload_mismatch"
        if receipt.decision.allowed is not True:
            return "anti_additive_methodology_durable_authority_required"
        return ""

    @staticmethod
    def _has_evidence_coordinates(candidate: dict[str, Any]) -> bool:
        return bool(
            candidate.get("evidence_refs")
            and candidate.get("support_path")
            and candidate.get("accept_decision_ref")
            and candidate.get("replayable_evidence") is True
        )

    @classmethod
    def _dimensions(cls, candidate: dict[str, Any]) -> tuple[dict[str, Decimal], list[str]]:
        values: dict[str, Decimal] = {}
        invalid: list[str] = []
        for name in POSITIVE_RETENTION_DIMENSIONS + NEGATIVE_RETENTION_DIMENSIONS:
            value = cls._unit_interval(candidate.get(name))
            if value is None:
                invalid.append(name)
            else:
                values[name] = value
        return values, invalid

    @staticmethod
    def _unit_interval(value: Any) -> Decimal | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        return parsed if Decimal("0") <= parsed <= Decimal("1") else None

    @classmethod
    def _threshold(cls, name: str, value: float) -> Decimal:
        parsed = cls._unit_interval(value)
        if parsed is None:
            raise ValueError(f"{name}_must_be_in_unit_interval")
        return parsed

    @staticmethod
    def _retention_score(dimensions: dict[str, Decimal]) -> Decimal:
        positive = sum((dimensions[name] for name in POSITIVE_RETENTION_DIMENSIONS), Decimal("0"))
        negative = sum((dimensions[name] for name in NEGATIVE_RETENTION_DIMENSIONS), Decimal("0"))
        return positive - negative

    @staticmethod
    def _blocked(
        decision: str,
        reason: str,
        *failures: str,
        score: Decimal | None = None,
        methodology_receipt_hash: str = "",
    ) -> ConstraintAlignedRetentionDecision:
        return ConstraintAlignedRetentionDecision(
            decision=decision,
            eligible_for_retention=False,
            reason=reason,
            retention_score=float(score) if score is not None else None,
            hard_gate_failures=tuple(failures),
            anti_additive_methodology_receipt_hash=methodology_receipt_hash,
        )
