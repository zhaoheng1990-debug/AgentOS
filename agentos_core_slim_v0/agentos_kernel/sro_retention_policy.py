"""Kernel-owned policy for selecting bounded SRO reuse routes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .sro_retention_models import (
    SRO_MATCHER_ROUTES,
    GradedSROCompatibilityDecision,
    SerialSelectionWitness,
    unit_interval,
)
from .sro_retention_receipt import SROMatcherReceiptValidator, SROReceiptValidationResult
from .cognitive_work_models import CognitiveWorkControlDecision, validate_control_binding


class GradedSROCompatibilityGate:
    """Apply safety thresholds after mechanical receipt validation."""

    def __init__(
        self,
        *,
        confidence_threshold: float = 0.70,
        uncertainty_ceiling: float = 0.30,
        calibration_error_ceiling: float = 0.10,
        trace_sufficiency_threshold: float = 0.60,
        structural_compatibility_threshold: float = 0.60,
        role_compatibility_threshold: float = 0.60,
        boundary_compatibility_threshold: float = 0.70,
        direct_interface_threshold: float = 0.70,
        direct_drift_ceiling: float = 0.30,
        revision_drift_threshold: float = 0.65,
        negative_transfer_ceiling: float = 0.30,
        receipt_validator: SROMatcherReceiptValidator | None = None,
    ) -> None:
        for name, value in locals().copy().items():
            if name in {"self", "receipt_validator"}:
                continue
            parsed = unit_interval(value)
            if parsed is None:
                raise ValueError(f"{name}_must_be_in_unit_interval")
            setattr(self, name, parsed)
        if self.direct_drift_ceiling >= self.revision_drift_threshold:
            raise ValueError("direct_drift_ceiling_must_be_below_revision_drift_threshold")
        self.receipt_validator = receipt_validator or SROMatcherReceiptValidator()

    def evaluate(
        self,
        receipt: dict[str, Any],
        *,
        witness: SerialSelectionWitness | None = None,
        task_commitment_hash: str = "",
        provider_invocation_receipt_hash: str = "",
        cognitive_work_control: CognitiveWorkControlDecision | None = None,
    ) -> GradedSROCompatibilityDecision:
        validation = self.receipt_validator.validate(
            receipt,
            witness=witness,
            task_commitment_hash=task_commitment_hash,
            provider_invocation_receipt_hash=provider_invocation_receipt_hash,
        )
        if not validation.valid:
            return self._decision(
                "ABSTAIN",
                validation.receipt_hash,
                validation.reason,
                failures=validation.failures,
            )
        decision = self._route_validated(validation)
        if cognitive_work_control is None:
            return decision
        if witness is None:
            raise ValueError("cognitive_work_sro_binding_requires_witness")
        validate_control_binding(
            cognitive_work_control,
            project_scope=witness.project_scope_ref,
        )
        if decision.route != "DIRECT_REUSE" or cognitive_work_control.allow_direct_sro_reuse:
            return decision
        route = "REVISE" if cognitive_work_control.action == "REORGANIZE" else "OBSERVE"
        return self._decision(
            route,
            decision.matcher_receipt_hash,
            "cognitive_work_trajectory_does_not_support_direct_reuse",
            confidence=decision.confidence,
            uncertainty=decision.uncertainty,
            drift_risk=decision.drift_risk,
            factors=(f"cognitive_work_control:{cognitive_work_control.decision_hash}",),
        )

    def _route_validated(self, validation: SROReceiptValidationResult) -> GradedSROCompatibilityDecision:
        values = validation.values or {}
        probabilities = validation.probabilities or {}
        confidence = validation.confidence or Decimal("0")
        uncertainty = values["uncertainty"]
        drift_risk = values["drift_risk"]
        metrics = {
            "confidence": float(confidence),
            "uncertainty": float(uncertainty),
            "drift_risk": float(drift_risk),
        }
        if values["trace_sufficiency"] < self.trace_sufficiency_threshold or validation.validity_state == "UNKNOWN":
            return self._decision(
                "OBSERVE",
                validation.receipt_hash,
                "task_trace_or_validity_state_insufficient",
                factors=("insufficient_trace",),
                **metrics,
            )
        if values["negative_transfer_risk"] > self.negative_transfer_ceiling:
            return self._decision(
                "REJECT",
                validation.receipt_hash,
                "negative_transfer_risk_exceeds_ceiling",
                factors=("negative_transfer_risk",),
                **metrics,
            )
        incompatible = self._compatibility_failures(values)
        if incompatible:
            return self._decision(
                "REJECT",
                validation.receipt_hash,
                "structural_role_or_boundary_incompatible",
                factors=incompatible,
                **metrics,
            )
        if validation.validity_state in {"DRIFTED", "STALE"} or drift_risk >= self.revision_drift_threshold:
            return self._decision(
                "REVISE",
                validation.receipt_hash,
                "stored_validity_requires_revision",
                factors=("validity_drift",),
                **metrics,
            )
        calibration_failures = self._calibration_failures(values, confidence)
        if calibration_failures:
            return self._decision(
                "ABSTAIN",
                validation.receipt_hash,
                "matcher_commitment_not_calibrated_enough",
                factors=calibration_failures,
                **metrics,
            )
        predicted = max(SRO_MATCHER_ROUTES, key=lambda route: probabilities[route])
        if predicted == "DIRECT_REUSE" and self._requires_local_reconstruction(validation, values, drift_risk):
            reason = (
                "synthetic_formal_evidence_cannot_authorize_direct_reuse"
                if validation.evidence_scope == "SYNTHETIC_FORMAL"
                else "compatible_family_requires_local_interface_or_drift_adaptation"
            )
            factor = "evidence_scope_ceiling" if validation.evidence_scope == "SYNTHETIC_FORMAL" else "local_adaptation_required"
            return self._decision(
                "LOCAL_RECONSTRUCTION",
                validation.receipt_hash,
                reason,
                factors=(factor,),
                **metrics,
            )
        return self._decision(
            predicted,
            validation.receipt_hash,
            "frozen_matcher_route_passed_kernel_gates",
            factors=("calibrated_matcher_route",),
            **metrics,
        )

    def _compatibility_failures(self, values: dict[str, Decimal]) -> tuple[str, ...]:
        failures = []
        if values["structural_compatibility"] < self.structural_compatibility_threshold:
            failures.append("structural_incompatibility")
        if values["role_compatibility"] < self.role_compatibility_threshold:
            failures.append("role_incompatibility")
        if values["boundary_compatibility"] < self.boundary_compatibility_threshold:
            failures.append("boundary_incompatibility")
        return tuple(failures)

    def _calibration_failures(self, values: dict[str, Decimal], confidence: Decimal) -> tuple[str, ...]:
        failures = []
        if confidence < self.confidence_threshold:
            failures.append("low_confidence")
        if values["uncertainty"] > self.uncertainty_ceiling:
            failures.append("high_uncertainty")
        if values["calibration_error"] > self.calibration_error_ceiling:
            failures.append("calibration_error")
        return tuple(failures)

    def _requires_local_reconstruction(
        self,
        validation: SROReceiptValidationResult,
        values: dict[str, Decimal],
        drift_risk: Decimal,
    ) -> bool:
        return validation.evidence_scope == "SYNTHETIC_FORMAL" or (
            values["interface_compatibility"] < self.direct_interface_threshold
            or drift_risk > self.direct_drift_ceiling
        )

    @staticmethod
    def _decision(
        route: str,
        matcher_receipt_hash: str,
        reason: str,
        *,
        confidence: float | None = None,
        uncertainty: float | None = None,
        drift_risk: float | None = None,
        factors: tuple[str, ...] = (),
        failures: tuple[str, ...] = (),
    ) -> GradedSROCompatibilityDecision:
        return GradedSROCompatibilityDecision(
            route=route,
            candidate_admitted=route in {"DIRECT_REUSE", "LOCAL_RECONSTRUCTION"},
            reuse_allowed=route == "DIRECT_REUSE",
            reconstruction_required=route == "LOCAL_RECONSTRUCTION",
            observation_required=route == "OBSERVE",
            revision_required=route == "REVISE",
            confidence=confidence,
            uncertainty=uncertainty,
            drift_risk=drift_risk,
            reason=reason,
            decision_factors=factors,
            hard_gate_failures=failures,
            matcher_receipt_hash=matcher_receipt_hash,
        )
