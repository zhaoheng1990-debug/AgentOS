"""Mechanical validation and strong binding for SRO matcher receipts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .sro_retention_models import (
    CALIBRATION_STATUSES,
    EVIDENCE_SCOPES,
    SRO_MATCHER_ROUTES,
    VALIDITY_STATES,
    SerialSelectionWitness,
    hash_payload,
    require_sha256,
    unit_interval,
)


@dataclass(frozen=True)
class SROReceiptValidationResult:
    valid: bool
    receipt_hash: str
    reason: str = ""
    failures: tuple[str, ...] = ()
    values: dict[str, Decimal] | None = None
    probabilities: dict[str, Decimal] | None = None
    validity_state: str = ""
    evidence_scope: str = ""
    confidence: Decimal | None = None


class SROMatcherReceiptValidator:
    """Validate receipt shape, hashes, object bindings, calibration, and metrics."""

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
    AUDIT_FIELDS = (
        "matcher_id",
        "matcher_version",
        "task_id",
        "witness_id",
        "witness_hash",
        "project_scope_ref",
        "task_commitment_hash",
        "evidence_refs",
        "calibration_ref",
        "provider_support_receipt_ref",
        "provider_invocation_receipt_hash",
        "cognition_audit_hash",
    )
    HASH_FIELDS = (
        "witness_hash",
        "task_commitment_hash",
        "provider_invocation_receipt_hash",
        "cognition_audit_hash",
    )

    def validate(
        self,
        receipt: dict[str, Any],
        *,
        witness: SerialSelectionWitness | None = None,
        task_commitment_hash: str = "",
        provider_invocation_receipt_hash: str = "",
    ) -> SROReceiptValidationResult:
        receipt_hash = hash_payload(receipt)
        failure = self._validate_contract(receipt, receipt_hash)
        if failure:
            return failure
        failure = self._validate_hashes(receipt, receipt_hash)
        if failure:
            return failure
        failure = self._validate_bindings(
            receipt,
            receipt_hash,
            witness=witness,
            task_commitment_hash=task_commitment_hash,
            provider_invocation_receipt_hash=provider_invocation_receipt_hash,
        )
        if failure:
            return failure
        failure = self._validate_calibration(receipt, receipt_hash)
        if failure:
            return failure
        return self._validate_metrics(receipt, receipt_hash)

    def _validate_contract(
        self, receipt: dict[str, Any], receipt_hash: str
    ) -> SROReceiptValidationResult | None:
        if receipt.get("scope") != "project_scoped":
            return self._failure(receipt_hash, "scope_not_project_scoped", ("scope_not_project_scoped",))
        missing = [name for name in self.AUDIT_FIELDS if not receipt.get(name)]
        if receipt.get("replayable_evidence") is not True:
            missing.append("replayable_evidence")
        if missing:
            return self._failure(
                receipt_hash,
                "matcher_receipt_missing_audit_contract",
                tuple(f"missing:{name}" for name in sorted(set(missing))),
            )
        return None

    def _validate_hashes(
        self, receipt: dict[str, Any], receipt_hash: str
    ) -> SROReceiptValidationResult | None:
        invalid = []
        for name in self.HASH_FIELDS:
            try:
                require_sha256(name, receipt.get(name))
            except ValueError:
                invalid.append(name)
        if invalid:
            return self._failure(
                receipt_hash,
                "matcher_receipt_binding_hash_invalid",
                tuple(f"invalid:{name}" for name in invalid),
            )
        return None

    def _validate_bindings(
        self,
        receipt: dict[str, Any],
        receipt_hash: str,
        *,
        witness: SerialSelectionWitness | None,
        task_commitment_hash: str,
        provider_invocation_receipt_hash: str,
    ) -> SROReceiptValidationResult | None:
        failures = []
        if witness is not None:
            if receipt.get("witness_id") != witness.witness_id:
                failures.append("witness_id_mismatch")
            if receipt.get("witness_hash", "").lower() != witness.as_dict()["record_hash"]:
                failures.append("witness_hash_mismatch")
            if receipt.get("project_scope_ref") != witness.project_scope_ref:
                failures.append("witness_project_scope_mismatch")
        if task_commitment_hash:
            expected = require_sha256("task_commitment_hash", task_commitment_hash)
            if receipt.get("task_commitment_hash", "").lower() != expected:
                failures.append("task_commitment_hash_mismatch")
        if provider_invocation_receipt_hash:
            expected = require_sha256(
                "provider_invocation_receipt_hash", provider_invocation_receipt_hash
            )
            if receipt.get("provider_invocation_receipt_hash", "").lower() != expected:
                failures.append("provider_invocation_receipt_hash_mismatch")
        if failures:
            return self._failure(receipt_hash, "matcher_receipt_strong_binding_failed", tuple(failures))
        return None

    def _validate_calibration(
        self, receipt: dict[str, Any], receipt_hash: str
    ) -> SROReceiptValidationResult | None:
        if receipt.get("evidence_scope") not in EVIDENCE_SCOPES:
            return self._failure(receipt_hash, "unknown_evidence_scope", ("unknown_evidence_scope",))
        if receipt.get("calibration_status") not in CALIBRATION_STATUSES:
            return self._failure(
                receipt_hash,
                "matcher_not_frozen_calibrated",
                ("matcher_not_frozen_calibrated",),
            )
        return None

    def _validate_metrics(
        self, receipt: dict[str, Any], receipt_hash: str
    ) -> SROReceiptValidationResult:
        values: dict[str, Decimal] = {}
        invalid = []
        for name in self.SIGNAL_FIELDS:
            parsed = unit_interval(receipt.get(name))
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
            return self._failure(
                receipt_hash,
                "invalid_or_incomplete_matcher_metrics",
                tuple(f"invalid:{name}" for name in sorted(set(invalid))),
            )
        confidence = max(probabilities.values())
        declared_confidence = unit_interval(receipt.get("confidence"))
        if declared_confidence is None or abs(declared_confidence - confidence) > Decimal("0.000001"):
            return self._failure(
                receipt_hash,
                "matcher_confidence_probability_mismatch",
                ("invalid:confidence",),
            )
        return SROReceiptValidationResult(
            valid=True,
            receipt_hash=receipt_hash,
            values=values,
            probabilities=probabilities,
            validity_state=validity_state,
            evidence_scope=receipt["evidence_scope"],
            confidence=confidence,
        )

    @staticmethod
    def _probabilities(value: Any) -> tuple[dict[str, Decimal], list[str]]:
        if not isinstance(value, dict) or set(value) != set(SRO_MATCHER_ROUTES):
            return {}, ["route_probabilities"]
        parsed: dict[str, Decimal] = {}
        for route in SRO_MATCHER_ROUTES:
            probability = unit_interval(value.get(route))
            if probability is None:
                return {}, [f"route_probability:{route}"]
            parsed[route] = probability
        if abs(sum(parsed.values(), Decimal("0")) - Decimal("1")) > Decimal("0.000001"):
            return {}, ["route_probability_sum"]
        return parsed, []

    @staticmethod
    def _failure(receipt_hash: str, reason: str, failures: tuple[str, ...]) -> SROReceiptValidationResult:
        return SROReceiptValidationResult(
            valid=False,
            receipt_hash=receipt_hash,
            reason=reason,
            failures=failures,
        )
