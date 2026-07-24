"""Project-scoped SRO-conditioned serial-memory routing primitives.

This module separates three decisions that must not be collapsed:

1. whether a candidate is eligible for durable retention (owned by the
   existing ``ConstraintAlignedRetentionGate``);
2. whether and how an already retained witness applies to a later task
   (owned here by ``GradedSROCompatibilityGate``); and
3. whether the predicted reuse route produced delayed value (recorded by the
   append-only ``DelayedRetrievalLedger``).

The runtime validates calibrated matcher receipts but does not embed the
synthetic v1.8 experimental weights.  It grants no global-memory, production,
or theory-baseline write authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any


SRO_MATCHER_ROUTES = (
    "DIRECT_REUSE",
    "LOCAL_RECONSTRUCTION",
    "OBSERVE",
    "REJECT",
    "REVISE",
)
SRO_ROUTES = SRO_MATCHER_ROUTES + ("ABSTAIN",)

WITNESS_STATES = {
    "PRECOMMITTED",
    "IMMEDIATE_DELTA_OBSERVED",
    "DELAYED_VALUE_OBSERVED",
}
VALIDITY_STATES = {"CURRENT", "UNKNOWN", "DRIFTED", "STALE"}
EVIDENCE_SCOPES = {"SYNTHETIC_FORMAL", "INTERNAL_PROJECT", "EXTERNAL_VALIDATED"}
CALIBRATION_STATUSES = {"FROZEN_HELD_OUT", "FROZEN_PROJECT_SCOPED"}

_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _hash_payload(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()


def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def _require_sha256(name: str, value: Any) -> str:
    value = _require_text(name, value)
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name}_must_be_sha256")
    return value.lower()


def _parse_timestamp(name: str, value: Any) -> datetime:
    value = _require_text(name, value)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name}_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name}_must_include_timezone")
    return parsed


def _unit_interval(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if Decimal("0") <= parsed <= Decimal("1") else None


@dataclass(frozen=True)
class SerialSelectionWitness:
    """Reference-only minimal serial-memory witness.

    The schema stores semantic-role addresses and immutable evidence pointers,
    not raw chat or private episode payloads.  A new immutable revision is
    created when immediate or delayed outcomes become observable.
    """

    witness_id: str
    status: str
    selection_context_ref: str
    sro_address_ref: str
    validity_boundary_ref: str
    reconstruction_ref: str
    authority_ref: str
    privacy_boundary: str
    precommit_hash: str
    sealed_at: str
    evidence_refs: tuple[str, ...]
    delta_ref: str = ""
    delayed_value_ref: str = ""
    scope: str = "project_scoped"
    schema_version: str = "serial-selection-witness-v0.1"

    def __post_init__(self) -> None:
        for name in (
            "witness_id",
            "selection_context_ref",
            "sro_address_ref",
            "validity_boundary_ref",
            "reconstruction_ref",
            "authority_ref",
            "privacy_boundary",
            "schema_version",
        ):
            _require_text(name, getattr(self, name))
        if self.scope != "project_scoped":
            raise ValueError("witness_scope_must_be_project_scoped")
        if self.status not in WITNESS_STATES:
            raise ValueError(f"unknown_witness_status:{self.status}")
        _require_sha256("precommit_hash", self.precommit_hash)
        _parse_timestamp("sealed_at", self.sealed_at)
        if not self.evidence_refs or any(not isinstance(ref, str) or not ref for ref in self.evidence_refs):
            raise ValueError("witness_evidence_refs_required")
        if self.status == "PRECOMMITTED" and (self.delta_ref or self.delayed_value_ref):
            raise ValueError("precommitted_witness_cannot_contain_outcome_refs")
        if self.status in {"IMMEDIATE_DELTA_OBSERVED", "DELAYED_VALUE_OBSERVED"} and not self.delta_ref:
            raise ValueError("observed_witness_requires_delta_ref")
        if self.status == "IMMEDIATE_DELTA_OBSERVED" and self.delayed_value_ref:
            raise ValueError("immediate_witness_cannot_contain_delayed_value_ref")
        if self.status == "DELAYED_VALUE_OBSERVED" and not self.delayed_value_ref:
            raise ValueError("delayed_witness_requires_delayed_value_ref")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "witness_id": self.witness_id,
            "status": self.status,
            "scope": self.scope,
            "selection_context_ref": self.selection_context_ref,
            "sro_address_ref": self.sro_address_ref,
            "validity_boundary_ref": self.validity_boundary_ref,
            "reconstruction_ref": self.reconstruction_ref,
            "authority_ref": self.authority_ref,
            "privacy_boundary": self.privacy_boundary,
            "precommit_hash": self.precommit_hash.lower(),
            "sealed_at": self.sealed_at,
            "evidence_refs": list(self.evidence_refs),
            "delta_ref": self.delta_ref,
            "delayed_value_ref": self.delayed_value_ref,
        }
        payload["record_hash"] = _hash_payload(payload)
        return payload

    def with_immediate_delta(self, delta_ref: str, *evidence_refs: str) -> "SerialSelectionWitness":
        _require_text("delta_ref", delta_ref)
        if self.status != "PRECOMMITTED":
            raise ValueError("immediate_delta_requires_precommitted_witness")
        return replace(
            self,
            status="IMMEDIATE_DELTA_OBSERVED",
            delta_ref=delta_ref,
            evidence_refs=self.evidence_refs + tuple(evidence_refs),
        )

    def with_delayed_value(self, delayed_value_ref: str, *evidence_refs: str) -> "SerialSelectionWitness":
        _require_text("delayed_value_ref", delayed_value_ref)
        if self.status != "IMMEDIATE_DELTA_OBSERVED":
            raise ValueError("delayed_value_requires_immediate_delta_witness")
        return replace(
            self,
            status="DELAYED_VALUE_OBSERVED",
            delayed_value_ref=delayed_value_ref,
            evidence_refs=self.evidence_refs + tuple(evidence_refs),
        )


@dataclass(frozen=True)
class GradedSROCompatibilityDecision:
    """Kernel-owned, auditable query-time retention route."""

    route: str
    candidate_admitted: bool
    reuse_allowed: bool
    reconstruction_required: bool
    observation_required: bool
    revision_required: bool
    confidence: float | None
    uncertainty: float | None
    drift_risk: float | None
    reason: str
    decision_factors: tuple[str, ...]
    hard_gate_failures: tuple[str, ...]
    matcher_receipt_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "candidate_admitted": self.candidate_admitted,
            "reuse_allowed": self.reuse_allowed,
            "reconstruction_required": self.reconstruction_required,
            "observation_required": self.observation_required,
            "revision_required": self.revision_required,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "drift_risk": self.drift_risk,
            "reason": self.reason,
            "decision_factors": list(self.decision_factors),
            "hard_gate_failures": list(self.hard_gate_failures),
            "matcher_receipt_hash": self.matcher_receipt_hash,
            "global_memory_write_authority": False,
            "production_activation": False,
        }


class GradedSROCompatibilityGate:
    """Validate a calibrated matcher receipt and emit a bounded route.

    Provider/model cognition supplies the semantic compatibility estimates.
    The Kernel owns validation, safety overrides, abstention, and the final
    project-scoped route.
    """

    SIGNAL_FIELDS = (
        "uncertainty",
        "drift_risk",
        "negative_transfer_risk",
        "structural_compatibility",
        "role_compatibility",
        "boundary_compatibility",
        "interface_compatibility",
        "trace_sufficiency",
        "calibration_error",
    )

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
    ) -> None:
        for name, value in locals().copy().items():
            if name in {"self"}:
                continue
            parsed = _unit_interval(value)
            if parsed is None:
                raise ValueError(f"{name}_must_be_in_unit_interval")
            setattr(self, name, parsed)
        if self.direct_drift_ceiling >= self.revision_drift_threshold:
            raise ValueError("direct_drift_ceiling_must_be_below_revision_drift_threshold")

    def evaluate(self, receipt: dict[str, Any]) -> GradedSROCompatibilityDecision:
        receipt_hash = _hash_payload(receipt)
        if receipt.get("scope") != "project_scoped":
            return self._decision(
                "ABSTAIN",
                receipt_hash,
                "scope_not_project_scoped",
                failures=("scope_not_project_scoped",),
            )

        missing_audit = [
            name
            for name in (
                "matcher_id",
                "matcher_version",
                "task_id",
                "witness_id",
                "evidence_refs",
                "calibration_ref",
                "provider_support_receipt_ref",
            )
            if not receipt.get(name)
        ]
        if receipt.get("replayable_evidence") is not True:
            missing_audit.append("replayable_evidence")
        if missing_audit:
            return self._decision(
                "ABSTAIN",
                receipt_hash,
                "matcher_receipt_missing_audit_contract",
                failures=tuple(f"missing:{name}" for name in sorted(set(missing_audit))),
            )

        evidence_scope = receipt.get("evidence_scope")
        calibration_status = receipt.get("calibration_status")
        if evidence_scope not in EVIDENCE_SCOPES:
            return self._decision(
                "ABSTAIN",
                receipt_hash,
                "unknown_evidence_scope",
                failures=("unknown_evidence_scope",),
            )
        if calibration_status not in CALIBRATION_STATUSES:
            return self._decision(
                "ABSTAIN",
                receipt_hash,
                "matcher_not_frozen_calibrated",
                failures=("matcher_not_frozen_calibrated",),
            )

        values: dict[str, Decimal] = {}
        invalid = []
        for name in self.SIGNAL_FIELDS:
            parsed = _unit_interval(receipt.get(name))
            if parsed is None:
                invalid.append(name)
            else:
                values[name] = parsed
        probabilities, probability_failures = self._probabilities(receipt.get("route_probabilities"))
        invalid.extend(probability_failures)
        validity_state = receipt.get("validity_state")
        if validity_state not in VALIDITY_STATES:
            invalid.append("validity_state")
        if invalid:
            return self._decision(
                "ABSTAIN",
                receipt_hash,
                "invalid_or_incomplete_matcher_metrics",
                failures=tuple(f"invalid:{name}" for name in sorted(set(invalid))),
            )

        confidence = max(probabilities.values())
        uncertainty = values["uncertainty"]
        drift_risk = values["drift_risk"]
        metrics = {
            "confidence": float(confidence),
            "uncertainty": float(uncertainty),
            "drift_risk": float(drift_risk),
        }

        if values["trace_sufficiency"] < self.trace_sufficiency_threshold or validity_state == "UNKNOWN":
            return self._decision(
                "OBSERVE",
                receipt_hash,
                "task_trace_or_validity_state_insufficient",
                factors=("insufficient_trace",),
                **metrics,
            )
        if values["negative_transfer_risk"] > self.negative_transfer_ceiling:
            return self._decision(
                "REJECT",
                receipt_hash,
                "negative_transfer_risk_exceeds_ceiling",
                factors=("negative_transfer_risk",),
                **metrics,
            )
        incompatible = []
        if values["structural_compatibility"] < self.structural_compatibility_threshold:
            incompatible.append("structural_incompatibility")
        if values["role_compatibility"] < self.role_compatibility_threshold:
            incompatible.append("role_incompatibility")
        if values["boundary_compatibility"] < self.boundary_compatibility_threshold:
            incompatible.append("boundary_incompatibility")
        if incompatible:
            return self._decision(
                "REJECT",
                receipt_hash,
                "structural_role_or_boundary_incompatible",
                factors=tuple(incompatible),
                **metrics,
            )
        if validity_state in {"DRIFTED", "STALE"} or drift_risk >= self.revision_drift_threshold:
            return self._decision(
                "REVISE",
                receipt_hash,
                "stored_validity_requires_revision",
                factors=("validity_drift",),
                **metrics,
            )
        if (
            confidence < self.confidence_threshold
            or uncertainty > self.uncertainty_ceiling
            or values["calibration_error"] > self.calibration_error_ceiling
        ):
            factors = []
            if confidence < self.confidence_threshold:
                factors.append("low_confidence")
            if uncertainty > self.uncertainty_ceiling:
                factors.append("high_uncertainty")
            if values["calibration_error"] > self.calibration_error_ceiling:
                factors.append("calibration_error")
            return self._decision(
                "ABSTAIN",
                receipt_hash,
                "matcher_commitment_not_calibrated_enough",
                factors=tuple(factors),
                **metrics,
            )

        predicted = max(SRO_MATCHER_ROUTES, key=lambda route: probabilities[route])
        if predicted == "DIRECT_REUSE":
            if evidence_scope == "SYNTHETIC_FORMAL":
                return self._decision(
                    "LOCAL_RECONSTRUCTION",
                    receipt_hash,
                    "synthetic_formal_evidence_cannot_authorize_direct_reuse",
                    factors=("evidence_scope_ceiling",),
                    **metrics,
                )
            if (
                values["interface_compatibility"] < self.direct_interface_threshold
                or drift_risk > self.direct_drift_ceiling
            ):
                return self._decision(
                    "LOCAL_RECONSTRUCTION",
                    receipt_hash,
                    "compatible_family_requires_local_interface_or_drift_adaptation",
                    factors=("local_adaptation_required",),
                    **metrics,
                )
        return self._decision(
            predicted,
            receipt_hash,
            "frozen_matcher_route_passed_kernel_gates",
            factors=("calibrated_matcher_route",),
            **metrics,
        )

    @staticmethod
    def _probabilities(value: Any) -> tuple[dict[str, Decimal], list[str]]:
        if not isinstance(value, dict) or set(value) != set(SRO_MATCHER_ROUTES):
            return {}, ["route_probabilities"]
        parsed: dict[str, Decimal] = {}
        for route in SRO_MATCHER_ROUTES:
            probability = _unit_interval(value.get(route))
            if probability is None:
                return {}, [f"route_probability:{route}"]
            parsed[route] = probability
        if abs(sum(parsed.values(), Decimal("0")) - Decimal("1")) > Decimal("0.000001"):
            return {}, ["route_probability_sum"]
        return parsed, []

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


@dataclass(frozen=True)
class DelayedRetrievalPrediction:
    """Pre-outcome prediction binding a stored witness to a later task."""

    prediction_id: str
    source_witness_id: str
    target_task_id: str
    predicted_route: str
    source_witness_hash: str
    target_task_commitment_hash: str
    sealed_at: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("prediction_id", "source_witness_id", "target_task_id"):
            _require_text(name, getattr(self, name))
        if self.predicted_route not in SRO_ROUTES:
            raise ValueError(f"unknown_predicted_route:{self.predicted_route}")
        _require_sha256("source_witness_hash", self.source_witness_hash)
        _require_sha256("target_task_commitment_hash", self.target_task_commitment_hash)
        _parse_timestamp("sealed_at", self.sealed_at)
        if not self.evidence_refs or any(not isinstance(ref, str) or not ref for ref in self.evidence_refs):
            raise ValueError("prediction_evidence_refs_required")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "prediction_id": self.prediction_id,
            "source_witness_id": self.source_witness_id,
            "target_task_id": self.target_task_id,
            "predicted_route": self.predicted_route,
            "source_witness_hash": self.source_witness_hash.lower(),
            "target_task_commitment_hash": self.target_task_commitment_hash.lower(),
            "sealed_at": self.sealed_at,
            "evidence_refs": list(self.evidence_refs),
        }
        payload["prediction_hash"] = _hash_payload(payload)
        return payload


@dataclass(frozen=True)
class DelayedRetrievalScore:
    prediction_id: str
    predicted_route: str
    observed_route: str
    route_supported: bool
    role_reconstruction_fidelity: float
    negative_transfer_penalty: float
    delayed_retrieval_score: float
    outcome_ref: str
    outcome_hash: str
    revealed_at: str
    scoring_authority_ref: str

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "prediction_id": self.prediction_id,
            "predicted_route": self.predicted_route,
            "observed_route": self.observed_route,
            "route_supported": self.route_supported,
            "role_reconstruction_fidelity": self.role_reconstruction_fidelity,
            "negative_transfer_penalty": self.negative_transfer_penalty,
            "delayed_retrieval_score": self.delayed_retrieval_score,
            "outcome_ref": self.outcome_ref,
            "outcome_hash": self.outcome_hash,
            "revealed_at": self.revealed_at,
            "scoring_authority_ref": self.scoring_authority_ref,
        }
        payload["score_hash"] = _hash_payload(payload)
        return payload


class DelayedRetrievalLedger:
    """Append-only prediction/reveal ledger with a deterministic hash chain."""

    def __init__(self) -> None:
        self._predictions: dict[str, DelayedRetrievalPrediction] = {}
        self._scores: dict[str, DelayedRetrievalScore] = {}
        self._events: list[dict[str, Any]] = []

    def register_prediction(self, prediction: DelayedRetrievalPrediction) -> dict[str, Any]:
        if prediction.prediction_id in self._predictions:
            raise ValueError(f"duplicate_delayed_retrieval_prediction:{prediction.prediction_id}")
        self._predictions[prediction.prediction_id] = prediction
        return self._append("PREDICTION_SEALED", prediction.as_dict())

    def score_outcome(
        self,
        prediction_id: str,
        *,
        observed_route: str,
        role_reconstruction_fidelity: float,
        negative_transfer_penalty: float,
        outcome_ref: str,
        outcome_hash: str,
        revealed_at: str,
        scoring_authority_ref: str,
    ) -> DelayedRetrievalScore:
        if prediction_id not in self._predictions:
            raise ValueError(f"unknown_delayed_retrieval_prediction:{prediction_id}")
        if prediction_id in self._scores:
            raise ValueError(f"duplicate_delayed_retrieval_outcome:{prediction_id}")
        if observed_route not in SRO_ROUTES:
            raise ValueError(f"unknown_observed_route:{observed_route}")
        fidelity = _unit_interval(role_reconstruction_fidelity)
        penalty = _unit_interval(negative_transfer_penalty)
        if fidelity is None:
            raise ValueError("role_reconstruction_fidelity_must_be_in_unit_interval")
        if penalty is None:
            raise ValueError("negative_transfer_penalty_must_be_in_unit_interval")
        _require_text("outcome_ref", outcome_ref)
        outcome_hash = _require_sha256("outcome_hash", outcome_hash)
        scoring_authority_ref = _require_text("scoring_authority_ref", scoring_authority_ref)
        reveal_time = _parse_timestamp("revealed_at", revealed_at)
        prediction = self._predictions[prediction_id]
        if reveal_time <= _parse_timestamp("sealed_at", prediction.sealed_at):
            raise ValueError("delayed_retrieval_outcome_must_follow_prediction_seal")
        score = DelayedRetrievalScore(
            prediction_id=prediction_id,
            predicted_route=prediction.predicted_route,
            observed_route=observed_route,
            route_supported=prediction.predicted_route == observed_route,
            role_reconstruction_fidelity=float(fidelity),
            negative_transfer_penalty=float(penalty),
            delayed_retrieval_score=float(fidelity - penalty),
            outcome_ref=outcome_ref,
            outcome_hash=outcome_hash,
            revealed_at=revealed_at,
            scoring_authority_ref=scoring_authority_ref,
        )
        self._scores[prediction_id] = score
        self._append("OUTCOME_REVEALED_AND_SCORED", score.as_dict())
        return score

    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(event) for event in self._events)

    def prediction(self, prediction_id: str) -> DelayedRetrievalPrediction | None:
        return self._predictions.get(prediction_id)

    def score(self, prediction_id: str) -> DelayedRetrievalScore | None:
        return self._scores.get(prediction_id)

    def _append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        previous_hash = self._events[-1]["event_hash"] if self._events else ""
        event = {
            "sequence": len(self._events) + 1,
            "event_type": event_type,
            "previous_event_hash": previous_hash,
            "payload": payload,
        }
        event["event_hash"] = _hash_payload(event)
        self._events.append(event)
        return dict(event)
