"""Provider-backed orchestration for project-scoped SRO retention reuse."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ConstraintAlignedRetentionGate,
    DelayedRetrievalLedger,
    DelayedRetrievalPrediction,
    DelayedRetrievalScore,
    GradedSROCompatibilityDecision,
    GradedSROCompatibilityGate,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    SerialSelectionWitness,
)
from agentos_kernel.provider_cognition_layer import (
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED
from agentos_kernel.sro_retention_runtime import CALIBRATION_STATUSES, EVIDENCE_SCOPES

from .deliberation import DeliberationEventStore


SRO_RETENTION_RUNTIME_VERSION = "provider_backed_sro_retention_runtime_v0_2"
_PASS_PROVIDER_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}
_MIGRATION_STATES = {
    "PENDING_PROVIDER_REVALIDATION",
    "PENDING_WITNESS_RECONSTRUCTION",
    "QUARANTINED_LEGACY_RECORD",
    "WITNESS_REGISTERED_PROJECT_SCOPED",
}
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def _require_hash(name: str, value: Any) -> str:
    value = _require_text(name, value)
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name}_must_be_sha256")
    return value.lower()


def _require_refs(name: str, value: tuple[str, ...]) -> tuple[str, ...]:
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
            _require_text(name, getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("sro_retention_task_scope_must_be_project_uri")
        _require_refs("sro_retention_task_evidence_refs", self.evidence_refs)

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
        payload["task_commitment_hash"] = _hash_payload(payload)
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
            _require_text(name, getattr(self, name))
        if self.calibration_status not in CALIBRATION_STATUSES:
            raise ValueError("sro_calibration_status_invalid")
        if self.evidence_scope not in EVIDENCE_SCOPES:
            raise ValueError("sro_calibration_evidence_scope_invalid")
        _require_refs("sro_calibration_evidence_refs", self.evidence_refs)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "matcher_id": self.matcher_id,
            "matcher_version": self.matcher_version,
            "calibration_ref": self.calibration_ref,
            "calibration_status": self.calibration_status,
            "evidence_scope": self.evidence_scope,
            "evidence_refs": list(self.evidence_refs),
        }
        payload["calibration_hash"] = _hash_payload(payload)
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

    def __post_init__(self) -> None:
        for name in (
            "migration_id",
            "legacy_candidate_id",
            "project_scope",
            "migration_authority_ref",
            "legacy_decision",
            "created_at",
        ):
            _require_text(name, getattr(self, name))
        _require_hash("legacy_candidate_hash", self.legacy_candidate_hash)
        _require_text("legacy_migration_project_scope", self.project_scope)
        if not self.migration_authority_ref.startswith("kernel://"):
            raise ValueError("legacy_migration_kernel_authority_required")
        if self.candidate_state not in _MIGRATION_STATES:
            raise ValueError("legacy_migration_state_invalid")
        if self.evidence_refs:
            _require_refs("legacy_migration_evidence_refs", self.evidence_refs)

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
        }
        payload["migration_hash"] = _hash_payload(payload)
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
            _require_text(name, getattr(self, name))
        for name in ("witness_hash", "task_commitment_hash", "calibration_hash"):
            _require_hash(name, getattr(self, name))
        _require_refs("sro_route_evidence_refs", self.evidence_refs)
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
        payload["route_receipt_hash"] = _hash_payload(payload)
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


class SRORetentionRuntime:
    """Own provider-backed witness routing, migration, persistence, and replay."""

    module_id = SRO_RETENTION_RUNTIME_VERSION
    capabilities = (
        "provider_backed_sro_routing",
        "strong_witness_task_receipt_binding",
        "persistent_delayed_retrieval",
        "candidate_only_legacy_migration",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        matcher_router: ProviderTaskRouter,
        workspace_root: str | Path,
        compatibility_gate: GradedSROCompatibilityGate | None = None,
        retention_gate: ConstraintAlignedRetentionGate | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("sro_retention_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("sro_retention_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.matcher_router = matcher_router
        self.compatibility_gate = compatibility_gate or GradedSROCompatibilityGate()
        self.retention_gate = retention_gate or ConstraintAlignedRetentionGate()
        self._cognition = ProviderBackedRuntimeCognitionLayer()
        self._migrations: dict[str, LegacyRetentionMigrationCandidate] = {}
        self._witnesses: dict[str, SerialSelectionWitness] = {}
        self._route_receipts: dict[str, SRORetentionRouteReceipt] = {}
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "sro-retention-public", runtime_id)
        self._delayed_ledger = DelayedRetrievalLedger(
            self._event_store.path / "delayed_retrieval_events.jsonl"
        )
        existing_events = self._event_store.events()
        if existing_events:
            verification = self._event_store.verify()
            if not verification["valid"]:
                raise ValueError("sro_retention_runtime_replay_invalid:" + ";".join(verification["failures"]))
            self._replay(existing_events)
            self._assert_snapshot_current()
        else:
            self._persist(
                "SRO_RETENTION_RUNTIME_INITIALIZED",
                {"project_scope": project_scope, "module_id": self.module_id},
            )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def migrate_legacy_candidate(
        self,
        candidate: dict[str, Any],
        *,
        migration_authority_ref: str,
    ) -> LegacyRetentionMigrationCandidate:
        if not migration_authority_ref.startswith("kernel://"):
            raise ValueError("legacy_migration_kernel_authority_required")
        legacy_hash = _hash_payload(candidate)
        for existing in self._migrations.values():
            if existing.legacy_candidate_hash == legacy_hash:
                return existing
        decision = self.retention_gate.evaluate(candidate)
        evidence_refs = tuple(candidate.get("evidence_refs") or ())
        legacy_accept_candidate = bool(
            candidate.get("evidence_refs")
            and candidate.get("accept_decision_ref")
            and "ACCEPT" in str(candidate.get("status", ""))
            and candidate.get("scope") in {"project_scoped", "AgentOS project runtime policy selection"}
        )
        state = (
            "PENDING_WITNESS_RECONSTRUCTION"
            if decision.eligible_for_retention
            else "PENDING_PROVIDER_REVALIDATION"
            if legacy_accept_candidate
            else "QUARANTINED_LEGACY_RECORD"
        )
        migration = LegacyRetentionMigrationCandidate(
            migration_id=f"migration-{legacy_hash[:16]}",
            legacy_candidate_id=_require_text("legacy_candidate_id", candidate.get("candidate_id")),
            legacy_candidate_hash=legacy_hash,
            project_scope=str(candidate.get("scope") or ""),
            evidence_refs=evidence_refs,
            accept_decision_ref=str(candidate.get("accept_decision_ref") or ""),
            migration_authority_ref=migration_authority_ref,
            legacy_decision=decision.decision,
            legacy_eligible_for_retention=decision.eligible_for_retention,
            candidate_state=state,
            required_reconstruction_refs=(
                (
                    "provider_backed_retention_revalidation"
                    if state == "PENDING_PROVIDER_REVALIDATION"
                    else "sro_address_ref"
                ),
                "validity_boundary_ref",
                "reconstruction_ref",
                "authority_ref",
                "privacy_boundary",
            ),
            created_at=_utc_now(),
        )
        self._migrations[migration.migration_id] = migration
        self._persist("LEGACY_RETENTION_MIGRATION_CANDIDATE_CREATED", {"migration": migration.as_dict()})
        return migration

    def migrate_legacy_candidates(
        self,
        candidates: tuple[dict[str, Any], ...],
        *,
        migration_authority_ref: str,
    ) -> tuple[LegacyRetentionMigrationCandidate, ...]:
        return tuple(
            self.migrate_legacy_candidate(
                candidate,
                migration_authority_ref=migration_authority_ref,
            )
            for candidate in candidates
        )

    def revalidate_legacy_migration(
        self,
        migration_id: str,
        revalidated_candidate: dict[str, Any],
        *,
        kernel_authorization_ref: str,
    ) -> LegacyRetentionMigrationCandidate:
        if not kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("legacy_revalidation_kernel_authority_required")
        migration = self._migrations.get(migration_id)
        if migration is None:
            raise KeyError(f"unknown_legacy_migration:{migration_id}")
        if migration.candidate_state != "PENDING_PROVIDER_REVALIDATION":
            raise ValueError("legacy_migration_not_pending_provider_revalidation")
        if revalidated_candidate.get("candidate_id") != migration.legacy_candidate_id:
            raise ValueError("legacy_revalidation_candidate_id_mismatch")
        if revalidated_candidate.get("legacy_source_hash") != migration.legacy_candidate_hash:
            raise ValueError("legacy_revalidation_source_hash_mismatch")
        if not set(migration.evidence_refs).issubset(revalidated_candidate.get("evidence_refs") or ()):
            raise ValueError("legacy_revalidation_must_preserve_evidence")
        decision = self.retention_gate.evaluate(revalidated_candidate)
        updated = replace(
            migration,
            legacy_decision=decision.decision,
            legacy_eligible_for_retention=decision.eligible_for_retention,
            project_scope=str(revalidated_candidate.get("scope") or migration.project_scope),
            evidence_refs=tuple(revalidated_candidate.get("evidence_refs") or ()),
            accept_decision_ref=str(
                revalidated_candidate.get("accept_decision_ref") or migration.accept_decision_ref
            ),
            candidate_state=(
                "PENDING_WITNESS_RECONSTRUCTION"
                if decision.eligible_for_retention
                else "QUARANTINED_LEGACY_RECORD"
            ),
            required_reconstruction_refs=(
                "sro_address_ref",
                "validity_boundary_ref",
                "reconstruction_ref",
                "authority_ref",
                "privacy_boundary",
            ),
        )
        self._migrations[migration_id] = updated
        self._persist(
            "LEGACY_RETENTION_MIGRATION_REVALIDATED",
            {
                "migration": updated.as_dict(),
                "revalidated_candidate_hash": _hash_payload(revalidated_candidate),
                "kernel_authorization_ref": kernel_authorization_ref,
            },
        )
        return updated

    def reconstruct_migrated_witness(
        self,
        migration_id: str,
        *,
        witness_id: str,
        sro_address_ref: str,
        validity_boundary_ref: str,
        reconstruction_ref: str,
        authority_ref: str,
        privacy_boundary: str,
        sealed_at: str,
        evidence_refs: tuple[str, ...],
        kernel_authorization_ref: str,
    ) -> SerialSelectionWitness:
        if not kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("sro_witness_registration_kernel_authority_required")
        migration = self._migrations.get(migration_id)
        if migration is None:
            raise KeyError(f"unknown_legacy_migration:{migration_id}")
        if migration.candidate_state != "PENDING_WITNESS_RECONSTRUCTION":
            raise ValueError("legacy_migration_not_pending_reconstruction")
        if not set(migration.evidence_refs).issubset(evidence_refs):
            raise ValueError("migrated_witness_must_preserve_legacy_evidence")
        selection_context_ref = f"migration://{migration_id}"
        precommit_payload = {
            "legacy_candidate_hash": migration.legacy_candidate_hash,
            "witness_id": witness_id,
            "selection_context_ref": selection_context_ref,
            "sro_address_ref": sro_address_ref,
            "validity_boundary_ref": validity_boundary_ref,
            "reconstruction_ref": reconstruction_ref,
            "authority_ref": authority_ref,
            "privacy_boundary": privacy_boundary,
            "sealed_at": sealed_at,
            "evidence_refs": list(evidence_refs),
            "kernel_authorization_ref": kernel_authorization_ref,
        }
        witness = SerialSelectionWitness(
            witness_id=witness_id,
            status="PRECOMMITTED",
            project_scope_ref=self.project_scope,
            selection_context_ref=selection_context_ref,
            sro_address_ref=sro_address_ref,
            validity_boundary_ref=validity_boundary_ref,
            reconstruction_ref=reconstruction_ref,
            authority_ref=authority_ref,
            privacy_boundary=privacy_boundary,
            precommit_hash=_hash_payload(precommit_payload),
            sealed_at=sealed_at,
            evidence_refs=evidence_refs,
        )
        self._register_witness(witness, kernel_authorization_ref, migration_id=migration_id)
        return witness

    def register_witness(
        self,
        witness: SerialSelectionWitness,
        *,
        kernel_authorization_ref: str,
    ) -> SerialSelectionWitness:
        self._register_witness(witness, kernel_authorization_ref)
        return witness

    def route_witness(
        self,
        witness_id: str,
        task: SRORetentionTask,
        calibration: SROCalibrationContract,
    ) -> SRORetentionRouteReceipt:
        witness = self._witnesses.get(witness_id)
        if witness is None:
            raise KeyError(f"unknown_sro_witness:{witness_id}")
        if task.project_scope != self.project_scope:
            raise ValueError("sro_retention_task_scope_mismatch")
        allowed_evidence = tuple(
            dict.fromkeys((*witness.evidence_refs, *task.evidence_refs, *calibration.evidence_refs))
        )
        provider_task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-sro-route-{len(self._route_receipts) + 1}",
            task_kind="graded_sro_retention_candidate_routing",
            objective=(
                "Estimate query-conditioned SRO compatibility for exactly one bound witness-task pair. Return "
                "calibrated five-route probabilities and semantic metrics only. Do not claim route authority, "
                "memory-write authority, production activation, or alter the supplied witness/task identities. "
                "confidence must equal the largest route probability. Cite only admitted evidence refs."
            ),
            inputs={
                "witness": witness.as_dict(),
                "target_task": task.as_dict(),
                "calibration_contract": calibration.as_dict(),
                "runtime_project_scope": self.project_scope,
            },
            allowed_evidence=list(allowed_evidence),
            expected_schema=self._provider_schema(),
            failure_semantics="block_sro_route_without_bound_provider_support",
        )
        envelope = self.matcher_router.route(provider_task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._persist("SRO_PROVIDER_ROUTE_BLOCKED", {"provider_envelope": envelope.as_dict()})
            raise RuntimeError(f"sro_retention_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        expected_semantic_fields = set(self._provider_schema()["required"])
        if set(semantic) != expected_semantic_fields:
            self._persist("SRO_PROVIDER_ROUTE_BLOCKED", {"provider_envelope": envelope.as_dict()})
            raise ValueError("sro_retention_provider_field_set_invalid")
        provider_refs = semantic.get("evidence_refs")
        if (
            not isinstance(provider_refs, list)
            or not provider_refs
            or len(provider_refs) != len(set(provider_refs))
            or not set(provider_refs).issubset(allowed_evidence)
        ):
            self._persist("SRO_PROVIDER_ROUTE_BLOCKED", {"provider_envelope": envelope.as_dict()})
            raise ValueError("sro_retention_provider_evidence_invalid")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(allowed_evidence):
            self._persist("SRO_PROVIDER_ROUTE_BLOCKED", {"provider_envelope": envelope.as_dict()})
            raise ValueError("sro_retention_provider_provenance_invalid")

        support_receipt = dict(semantic)
        support_receipt["evidence_scope"] = calibration.evidence_scope
        provider_audit = self._cognition.audit_operation(
            "graded_sro_retention_candidate_routing",
            {
                "operation_id": "graded_sro_retention_candidate_routing",
                "provider_support_receipt": support_receipt,
                "provider_support_receipt_hash": _hash_payload(support_receipt),
            },
        )
        if provider_audit.get("status") not in _PASS_PROVIDER_AUDITS:
            self._persist(
                "SRO_PROVIDER_ROUTE_BLOCKED",
                {"provider_envelope": envelope.as_dict(), "provider_audit": provider_audit},
            )
            raise ValueError(f"sro_retention_provider_audit_failed:{provider_audit.get('status')}")

        invocation = envelope.invocation_receipt.as_dict()
        if (
            invocation.get("input_hash") != provider_task.contract_hash()
            or invocation.get("output_hash") != _hash_payload(semantic)
        ):
            self._persist("SRO_PROVIDER_ROUTE_BLOCKED", {"provider_envelope": envelope.as_dict()})
            raise ValueError("sro_retention_provider_invocation_binding_invalid")
        invocation_hash = invocation["receipt_hash"]
        calibration_payload = calibration.as_dict()
        matcher_receipt = {
            "matcher_id": calibration.matcher_id,
            "matcher_version": calibration.matcher_version,
            "task_id": task.task_id,
            "task_commitment_hash": task.task_commitment_hash,
            "witness_id": witness.witness_id,
            "witness_hash": witness.as_dict()["record_hash"],
            "project_scope_ref": self.project_scope,
            "scope": "project_scoped",
            "evidence_refs": provider_refs,
            "calibration_ref": calibration.calibration_ref,
            "calibration_status": calibration.calibration_status,
            "evidence_scope": calibration.evidence_scope,
            "provider_support_receipt_ref": f"provider-receipt://{invocation_hash}",
            "provider_invocation_receipt_hash": invocation_hash,
            "cognition_audit_hash": _hash_payload(provider_audit),
            "replayable_evidence": True,
            **{key: value for key, value in semantic.items() if key != "evidence_refs"},
        }
        decision = self.compatibility_gate.evaluate(
            matcher_receipt,
            witness=witness,
            task_commitment_hash=task.task_commitment_hash,
            provider_invocation_receipt_hash=invocation_hash,
        )
        route_id = f"sro-route-{_hash_payload([witness.witness_id, task.task_id, invocation_hash])[:16]}"
        route_receipt = SRORetentionRouteReceipt(
            route_receipt_id=route_id,
            witness_id=witness.witness_id,
            witness_hash=witness.as_dict()["record_hash"],
            task_id=task.task_id,
            task_commitment_hash=task.task_commitment_hash,
            calibration_hash=calibration_payload["calibration_hash"],
            provider_invocation_receipt=invocation,
            provider_audit=provider_audit,
            matcher_receipt=matcher_receipt,
            decision=decision.as_dict(),
            evidence_refs=tuple(provider_refs),
            created_at=_utc_now(),
        )
        if route_id in self._route_receipts:
            raise ValueError(f"duplicate_sro_route_receipt:{route_id}")
        self._route_receipts[route_id] = route_receipt
        self._persist("SRO_RETENTION_ROUTE_DECIDED", {"route_receipt": route_receipt.as_dict()})
        return route_receipt

    def seal_delayed_prediction(
        self,
        route_receipt_id: str,
        *,
        prediction_id: str,
        sealed_at: str,
        evidence_refs: tuple[str, ...],
    ) -> DelayedRetrievalPrediction:
        route = self._route_receipts.get(route_receipt_id)
        if route is None:
            raise KeyError(f"unknown_sro_route_receipt:{route_receipt_id}")
        if not set(route.evidence_refs).issubset(evidence_refs):
            raise ValueError("delayed_prediction_must_preserve_route_evidence")
        prediction = DelayedRetrievalPrediction(
            prediction_id=prediction_id,
            source_witness_id=route.witness_id,
            target_task_id=route.task_id,
            predicted_route=route.decision["route"],
            source_witness_hash=route.witness_hash,
            target_task_commitment_hash=route.task_commitment_hash,
            sealed_at=sealed_at,
            evidence_refs=evidence_refs,
        )
        delayed_event = self._delayed_ledger.register_prediction(prediction)
        self._persist(
            "SRO_DELAYED_PREDICTION_SEALED",
            {"prediction_id": prediction_id, "delayed_event_hash": delayed_event["event_hash"]},
        )
        return prediction

    def score_delayed_outcome(self, prediction_id: str, **outcome: Any) -> DelayedRetrievalScore:
        score = self._delayed_ledger.score_outcome(prediction_id, **outcome)
        delayed_event = self._delayed_ledger.events()[-1]
        self._persist(
            "SRO_DELAYED_OUTCOME_SCORED",
            {"prediction_id": prediction_id, "delayed_event_hash": delayed_event["event_hash"]},
        )
        return score

    def snapshot(self) -> SRORetentionRuntimeSnapshot:
        return SRORetentionRuntimeSnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            migrations=tuple(self._migrations[key] for key in sorted(self._migrations)),
            witnesses=tuple(self._witnesses[key] for key in sorted(self._witnesses)),
            route_receipts=tuple(self._route_receipts[key] for key in sorted(self._route_receipts)),
            delayed_retrieval_replay=self._delayed_ledger.verify_replay(),
        )

    def verify_replay(self) -> dict[str, Any]:
        runtime_replay = self._event_store.verify()
        delayed_replay = self._delayed_ledger.verify_replay()
        snapshot_current = self._snapshot_is_current()
        failures = [
            *(f"runtime:{item}" for item in runtime_replay["failures"]),
            *(f"delayed:{item}" for item in delayed_replay["failures"]),
        ]
        if not snapshot_current:
            failures.append("runtime:snapshot_state_mismatch")
        return {
            "valid": not failures,
            "runtime_replay": runtime_replay,
            "delayed_retrieval_replay": delayed_replay,
            "snapshot_state_current": snapshot_current,
            "failures": failures,
        }

    def migration(self, migration_id: str) -> LegacyRetentionMigrationCandidate | None:
        return self._migrations.get(migration_id)

    def witness(self, witness_id: str) -> SerialSelectionWitness | None:
        return self._witnesses.get(witness_id)

    def route_receipt(self, route_receipt_id: str) -> SRORetentionRouteReceipt | None:
        return self._route_receipts.get(route_receipt_id)

    def _register_witness(
        self,
        witness: SerialSelectionWitness,
        kernel_authorization_ref: str,
        *,
        migration_id: str = "",
    ) -> None:
        if not kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("sro_witness_registration_kernel_authority_required")
        if witness.witness_id in self._witnesses:
            raise ValueError(f"duplicate_sro_witness:{witness.witness_id}")
        if witness.project_scope_ref != self.project_scope:
            raise ValueError("sro_witness_project_scope_mismatch")
        migration = None
        if migration_id:
            migration = self._migrations[migration_id]
            if witness.selection_context_ref != f"migration://{migration_id}":
                raise ValueError("migrated_witness_selection_context_mismatch")
            migration = replace(
                migration,
                candidate_state="WITNESS_REGISTERED_PROJECT_SCOPED",
                registered_witness_id=witness.witness_id,
            )
            self._migrations[migration_id] = migration
        self._witnesses[witness.witness_id] = witness
        self._persist(
            "SRO_WITNESS_REGISTERED",
            {
                "witness": witness.as_dict(),
                "kernel_authorization_ref": kernel_authorization_ref,
                "migration": migration.as_dict() if migration else None,
            },
        )

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def _replay(self, events: tuple[dict[str, Any], ...]) -> None:
        for event in events:
            payload = event.get("payload") or {}
            event_type = event.get("event_type")
            if event_type == "LEGACY_RETENTION_MIGRATION_CANDIDATE_CREATED":
                migration = self._migration_from_dict(payload["migration"])
                self._migrations[migration.migration_id] = migration
            elif event_type == "LEGACY_RETENTION_MIGRATION_REVALIDATED":
                migration = self._migration_from_dict(payload["migration"])
                self._migrations[migration.migration_id] = migration
            elif event_type == "SRO_WITNESS_REGISTERED":
                witness = self._witness_from_dict(payload["witness"])
                self._witnesses[witness.witness_id] = witness
                if payload.get("migration"):
                    migration = self._migration_from_dict(payload["migration"])
                    self._migrations[migration.migration_id] = migration
            elif event_type == "SRO_RETENTION_ROUTE_DECIDED":
                route = self._route_from_dict(payload["route_receipt"])
                self._route_receipts[route.route_receipt_id] = route
            elif event_type in {
                "SRO_RETENTION_RUNTIME_INITIALIZED",
                "SRO_PROVIDER_ROUTE_BLOCKED",
                "SRO_DELAYED_PREDICTION_SEALED",
                "SRO_DELAYED_OUTCOME_SCORED",
            }:
                continue
            else:
                raise ValueError(f"unknown_sro_runtime_event_type:{event_type}")

    def _assert_snapshot_current(self) -> None:
        if not self._snapshot_is_current():
            raise ValueError("sro_retention_runtime_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        record = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return record.get("snapshot_hash") == _hash_payload(self.snapshot().as_dict())

    @staticmethod
    def _witness_from_dict(payload: dict[str, Any]) -> SerialSelectionWitness:
        item = dict(payload)
        recorded_hash = item.pop("record_hash", "")
        item["evidence_refs"] = tuple(item["evidence_refs"])
        witness = SerialSelectionWitness(**item)
        if witness.as_dict()["record_hash"] != recorded_hash:
            raise ValueError("sro_witness_replay_hash_mismatch")
        return witness

    @staticmethod
    def _migration_from_dict(payload: dict[str, Any]) -> LegacyRetentionMigrationCandidate:
        item = dict(payload)
        recorded_hash = item.pop("migration_hash", "")
        item["evidence_refs"] = tuple(item["evidence_refs"])
        item["required_reconstruction_refs"] = tuple(item["required_reconstruction_refs"])
        migration = LegacyRetentionMigrationCandidate(**item)
        if migration.as_dict()["migration_hash"] != recorded_hash:
            raise ValueError("legacy_migration_replay_hash_mismatch")
        return migration

    @staticmethod
    def _route_from_dict(payload: dict[str, Any]) -> SRORetentionRouteReceipt:
        item = dict(payload)
        recorded_hash = item.pop("route_receipt_hash", "")
        item.pop("global_memory_write_authority", None)
        item.pop("production_activation", None)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        route = SRORetentionRouteReceipt(**item)
        if route.as_dict()["route_receipt_hash"] != recorded_hash:
            raise ValueError("sro_route_receipt_replay_hash_mismatch")
        return route

    @staticmethod
    def _provider_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": [
                "route_probabilities",
                "uncertainty",
                "drift_risk",
                "negative_transfer_risk",
                "structural_compatibility",
                "role_compatibility",
                "boundary_compatibility",
                "interface_compatibility",
                "trace_sufficiency",
                "calibration_error",
                "validity_state",
                "confidence",
                "evidence_refs",
            ],
            "properties": {
                "route_probabilities": {"type": "object"},
                "uncertainty": {"type": "number"},
                "drift_risk": {"type": "number"},
                "negative_transfer_risk": {"type": "number"},
                "structural_compatibility": {"type": "number"},
                "role_compatibility": {"type": "number"},
                "boundary_compatibility": {"type": "number"},
                "interface_compatibility": {"type": "number"},
                "trace_sufficiency": {"type": "number"},
                "calibration_error": {"type": "number"},
                "validity_state": {"type": "string"},
                "confidence": {"type": "number"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
