"""Runtime-facing immutable contracts for SRO retention orchestration."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from agentos_kernel.sro_retention_models import (
    CALIBRATION_STATUSES,
    EVIDENCE_SCOPES,
    SerialSelectionWitness,
)


SRO_RETENTION_RUNTIME_VERSION = "provider_backed_sro_retention_runtime_v0_2"
MIGRATION_STATES = {
    "PENDING_PROVIDER_REVALIDATION",
    "PENDING_WITNESS_RECONSTRUCTION",
    "QUARANTINED_LEGACY_RECORD",
    "WITNESS_REGISTERED_PROJECT_SCOPED",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def require_hash(name: str, value: Any) -> str:
    value = require_text(name, value)
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name}_must_be_sha256")
    return value.lower()


def require_refs(name: str, value: tuple[str, ...]) -> tuple[str, ...]:
    if not value or len(value) != len(set(value)) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{name}_must_be_unique_nonempty_refs")
    return value


@dataclass(frozen=True)
class SRORetentionTask:
    task_id: str
    project_scope: str
    objective: str
    context_ref: str
    constraint_field_ref: str
    evidence_refs: tuple[str, ...]
    validity_requirement: str = "CURRENT_OR_EXPLICIT_REVISION"

    def __post_init__(self) -> None:
        for name in (
            "task_id",
            "project_scope",
            "objective",
            "context_ref",
            "constraint_field_ref",
            "validity_requirement",
        ):
            require_text(name, getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("sro_retention_task_scope_must_be_project_uri")
        require_refs("sro_retention_task_evidence_refs", self.evidence_refs)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "task_id": self.task_id,
            "project_scope": self.project_scope,
            "objective": self.objective,
            "context_ref": self.context_ref,
            "constraint_field_ref": self.constraint_field_ref,
            "evidence_refs": list(self.evidence_refs),
            "validity_requirement": self.validity_requirement,
        }
        payload["task_commitment_hash"] = hash_payload(payload)
        return payload

    @property
    def task_commitment_hash(self) -> str:
        return self.as_dict()["task_commitment_hash"]


@dataclass(frozen=True)
class SROCalibrationContract:
    matcher_id: str
    matcher_version: str
    calibration_ref: str
    calibration_status: str
    evidence_scope: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("matcher_id", "matcher_version", "calibration_ref"):
            require_text(name, getattr(self, name))
        if self.calibration_status not in CALIBRATION_STATUSES:
            raise ValueError("sro_calibration_status_invalid")
        if self.evidence_scope not in EVIDENCE_SCOPES:
            raise ValueError("sro_calibration_evidence_scope_invalid")
        require_refs("sro_calibration_evidence_refs", self.evidence_refs)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "matcher_id": self.matcher_id,
            "matcher_version": self.matcher_version,
            "calibration_ref": self.calibration_ref,
            "calibration_status": self.calibration_status,
            "evidence_scope": self.evidence_scope,
            "evidence_refs": list(self.evidence_refs),
        }
        payload["calibration_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class LegacyRetentionMigrationCandidate:
    migration_id: str
    legacy_candidate_id: str
    legacy_candidate_hash: str
    project_scope: str
    evidence_refs: tuple[str, ...]
    accept_decision_ref: str
    migration_authority_ref: str
    legacy_decision: str
    legacy_eligible_for_retention: bool
    candidate_state: str
    required_reconstruction_refs: tuple[str, ...]
    created_at: str
    registered_witness_id: str = ""
    anti_additive_methodology_receipt_hash: str = ""

    def __post_init__(self) -> None:
        for name in (
            "migration_id",
            "legacy_candidate_id",
            "project_scope",
            "migration_authority_ref",
            "legacy_decision",
            "created_at",
        ):
            require_text(name, getattr(self, name))
        require_hash("legacy_candidate_hash", self.legacy_candidate_hash)
        require_text("legacy_migration_project_scope", self.project_scope)
        if not self.migration_authority_ref.startswith("kernel://"):
            raise ValueError("legacy_migration_kernel_authority_required")
        if self.candidate_state not in MIGRATION_STATES:
            raise ValueError("legacy_migration_state_invalid")
        if self.evidence_refs:
            require_refs("legacy_migration_evidence_refs", self.evidence_refs)
        if self.anti_additive_methodology_receipt_hash:
            require_hash(
                "legacy_migration_anti_additive_receipt_hash",
                self.anti_additive_methodology_receipt_hash,
            )

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "migration_id": self.migration_id,
            "legacy_candidate_id": self.legacy_candidate_id,
            "legacy_candidate_hash": self.legacy_candidate_hash,
            "project_scope": self.project_scope,
            "evidence_refs": list(self.evidence_refs),
            "accept_decision_ref": self.accept_decision_ref,
            "migration_authority_ref": self.migration_authority_ref,
            "legacy_decision": self.legacy_decision,
            "legacy_eligible_for_retention": self.legacy_eligible_for_retention,
            "candidate_state": self.candidate_state,
            "required_reconstruction_refs": list(self.required_reconstruction_refs),
            "created_at": self.created_at,
            "registered_witness_id": self.registered_witness_id,
            "anti_additive_methodology_receipt_hash": self.anti_additive_methodology_receipt_hash,
        }
        payload["migration_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class SRORetentionRouteReceipt:
    route_receipt_id: str
    witness_id: str
    witness_hash: str
    task_id: str
    task_commitment_hash: str
    calibration_hash: str
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    matcher_receipt: dict[str, Any]
    decision: dict[str, Any]
    evidence_refs: tuple[str, ...]
    created_at: str
    candidate_state: str = "ROUTE_DECIDED_PROJECT_SCOPED"

    def __post_init__(self) -> None:
        for name in ("route_receipt_id", "witness_id", "task_id", "created_at", "candidate_state"):
            require_text(name, getattr(self, name))
        for name in ("witness_hash", "task_commitment_hash", "calibration_hash"):
            require_hash(name, getattr(self, name))
        require_refs("sro_route_evidence_refs", self.evidence_refs)
        if self.candidate_state != "ROUTE_DECIDED_PROJECT_SCOPED":
            raise ValueError("sro_route_candidate_state_invalid")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "route_receipt_id": self.route_receipt_id,
            "witness_id": self.witness_id,
            "witness_hash": self.witness_hash,
            "task_id": self.task_id,
            "task_commitment_hash": self.task_commitment_hash,
            "calibration_hash": self.calibration_hash,
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
            "matcher_receipt": self.matcher_receipt,
            "decision": self.decision,
            "evidence_refs": list(self.evidence_refs),
            "created_at": self.created_at,
            "candidate_state": self.candidate_state,
            "global_memory_write_authority": False,
            "production_activation": False,
        }
        payload["route_receipt_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class SRORetentionRuntimeSnapshot:
    runtime_id: str
    project_scope: str
    migrations: tuple[LegacyRetentionMigrationCandidate, ...]
    witnesses: tuple[SerialSelectionWitness, ...]
    route_receipts: tuple[SRORetentionRouteReceipt, ...]
    delayed_retrieval_replay: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "migrations": [item.as_dict() for item in self.migrations],
            "witnesses": [item.as_dict() for item in self.witnesses],
            "route_receipts": [item.as_dict() for item in self.route_receipts],
            "delayed_retrieval_replay": self.delayed_retrieval_replay,
        }
