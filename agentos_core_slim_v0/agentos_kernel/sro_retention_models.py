"""Pure data contracts for project-scoped SRO retention routing."""

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


def hash_payload(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()


def require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def require_sha256(name: str, value: Any) -> str:
    value = require_text(name, value)
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name}_must_be_sha256")
    return value.lower()


def parse_timestamp(name: str, value: Any) -> datetime:
    value = require_text(name, value)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name}_must_be_iso8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name}_must_include_timezone")
    return parsed


def unit_interval(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if Decimal("0") <= parsed <= Decimal("1") else None


@dataclass(frozen=True)
class SerialSelectionWitness:
    """Reference-only minimal serial-memory witness."""

    witness_id: str
    status: str
    project_scope_ref: str
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
    schema_version: str = "serial-selection-witness-v0.2"

    def __post_init__(self) -> None:
        for name in (
            "witness_id",
            "project_scope_ref",
            "selection_context_ref",
            "sro_address_ref",
            "validity_boundary_ref",
            "reconstruction_ref",
            "authority_ref",
            "privacy_boundary",
            "schema_version",
        ):
            require_text(name, getattr(self, name))
        if self.scope != "project_scoped":
            raise ValueError("witness_scope_must_be_project_scoped")
        if not self.project_scope_ref.startswith("project://"):
            raise ValueError("witness_project_scope_ref_must_be_project_uri")
        if self.status not in WITNESS_STATES:
            raise ValueError(f"unknown_witness_status:{self.status}")
        require_sha256("precommit_hash", self.precommit_hash)
        parse_timestamp("sealed_at", self.sealed_at)
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
            "project_scope_ref": self.project_scope_ref,
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
        payload["record_hash"] = hash_payload(payload)
        return payload

    def with_immediate_delta(self, delta_ref: str, *evidence_refs: str) -> "SerialSelectionWitness":
        require_text("delta_ref", delta_ref)
        if self.status != "PRECOMMITTED":
            raise ValueError("immediate_delta_requires_precommitted_witness")
        return replace(
            self,
            status="IMMEDIATE_DELTA_OBSERVED",
            delta_ref=delta_ref,
            evidence_refs=self.evidence_refs + tuple(evidence_refs),
        )

    def with_delayed_value(self, delayed_value_ref: str, *evidence_refs: str) -> "SerialSelectionWitness":
        require_text("delayed_value_ref", delayed_value_ref)
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
            require_text(name, getattr(self, name))
        if self.predicted_route not in SRO_ROUTES:
            raise ValueError(f"unknown_predicted_route:{self.predicted_route}")
        require_sha256("source_witness_hash", self.source_witness_hash)
        require_sha256("target_task_commitment_hash", self.target_task_commitment_hash)
        parse_timestamp("sealed_at", self.sealed_at)
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
        payload["prediction_hash"] = hash_payload(payload)
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
        payload["score_hash"] = hash_payload(payload)
        return payload
