"""Thin facade for modular, Provider-backed SRO retention orchestration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ConstraintAlignedRetentionGate,
    DelayedRetrievalPrediction,
    DelayedRetrievalScore,
    GradedSROCompatibilityGate,
    ProviderTaskRouter,
    SerialSelectionWitness,
)

from .sro_retention_contracts import (
    SRO_RETENTION_RUNTIME_VERSION,
    LegacyRetentionMigrationCandidate,
    SROCalibrationContract,
    SRORetentionRouteReceipt,
    SRORetentionRuntimeSnapshot,
    SRORetentionTask,
    hash_payload,
)
from .sro_retention_migration import LegacyRetentionMigrator
from .sro_retention_provider import ProviderBackedSROMatcher
from .sro_retention_repository import SRORetentionRepository


class SRORetentionRuntime:
    """Coordinate focused SRO services while Kernel retains route authority."""

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
        compatibility_gate = compatibility_gate or GradedSROCompatibilityGate()
        self._repository = SRORetentionRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            module_id=self.module_id,
            workspace_root=workspace_root,
        )
        self._migrator = LegacyRetentionMigrator(project_scope, retention_gate)
        self._matcher = ProviderBackedSROMatcher(
            runtime_id=runtime_id,
            project_scope=project_scope,
            matcher_router=matcher_router,
            compatibility_gate=compatibility_gate,
            event_sink=self._repository.persist_event,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def migrate_legacy_candidate(
        self,
        candidate: dict[str, Any],
        *,
        migration_authority_ref: str,
    ) -> LegacyRetentionMigrationCandidate:
        legacy_hash = hash_payload(candidate)
        existing = self._repository.migration_by_legacy_hash(legacy_hash)
        if existing is not None:
            return existing
        migration = self._migrator.create(
            candidate,
            migration_authority_ref=migration_authority_ref,
        )
        self._repository.save_migration_created(migration)
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
        migration = self._require_migration(migration_id)
        updated = self._migrator.revalidate(
            migration,
            revalidated_candidate,
            kernel_authorization_ref=kernel_authorization_ref,
        )
        self._repository.save_migration_revalidated(
            updated,
            revalidated_candidate_hash=hash_payload(revalidated_candidate),
            kernel_authorization_ref=kernel_authorization_ref,
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
        migration = self._require_migration(migration_id)
        witness = self._migrator.reconstruct_witness(
            migration,
            witness_id=witness_id,
            sro_address_ref=sro_address_ref,
            validity_boundary_ref=validity_boundary_ref,
            reconstruction_ref=reconstruction_ref,
            authority_ref=authority_ref,
            privacy_boundary=privacy_boundary,
            sealed_at=sealed_at,
            evidence_refs=evidence_refs,
            kernel_authorization_ref=kernel_authorization_ref,
        )
        updated = self._migrator.mark_witness_registered(migration, witness.witness_id)
        self._repository.register_witness(
            witness,
            kernel_authorization_ref=kernel_authorization_ref,
            migration=updated,
        )
        return witness

    def register_witness(
        self,
        witness: SerialSelectionWitness,
        *,
        kernel_authorization_ref: str,
    ) -> SerialSelectionWitness:
        self._repository.register_witness(
            witness,
            kernel_authorization_ref=kernel_authorization_ref,
        )
        return witness

    def route_witness(
        self,
        witness_id: str,
        task: SRORetentionTask,
        calibration: SROCalibrationContract,
    ) -> SRORetentionRouteReceipt:
        witness = self._repository.witness(witness_id)
        if witness is None:
            raise KeyError(f"unknown_sro_witness:{witness_id}")
        if task.project_scope != self.project_scope:
            raise ValueError("sro_retention_task_scope_mismatch")
        route_receipt = self._matcher.route(
            witness,
            task,
            calibration,
            route_sequence=self._repository.route_count + 1,
        )
        self._repository.save_route(route_receipt)
        return route_receipt

    def seal_delayed_prediction(
        self,
        route_receipt_id: str,
        *,
        prediction_id: str,
        sealed_at: str,
        evidence_refs: tuple[str, ...],
    ) -> DelayedRetrievalPrediction:
        route = self._repository.route_receipt(route_receipt_id)
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
        delayed_event = self._repository.delayed_ledger.register_prediction(prediction)
        self._repository.persist_event(
            "SRO_DELAYED_PREDICTION_SEALED",
            {"prediction_id": prediction_id, "delayed_event_hash": delayed_event["event_hash"]},
        )
        return prediction

    def score_delayed_outcome(self, prediction_id: str, **outcome: Any) -> DelayedRetrievalScore:
        score = self._repository.delayed_ledger.score_outcome(prediction_id, **outcome)
        delayed_event = self._repository.delayed_ledger.events()[-1]
        self._repository.persist_event(
            "SRO_DELAYED_OUTCOME_SCORED",
            {"prediction_id": prediction_id, "delayed_event_hash": delayed_event["event_hash"]},
        )
        return score

    def snapshot(self) -> SRORetentionRuntimeSnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, Any]:
        return self._repository.verify_replay()

    def migration(self, migration_id: str) -> LegacyRetentionMigrationCandidate | None:
        return self._repository.migration(migration_id)

    def witness(self, witness_id: str) -> SerialSelectionWitness | None:
        return self._repository.witness(witness_id)

    def route_receipt(self, route_receipt_id: str) -> SRORetentionRouteReceipt | None:
        return self._repository.route_receipt(route_receipt_id)

    def _require_migration(self, migration_id: str) -> LegacyRetentionMigrationCandidate:
        migration = self._repository.migration(migration_id)
        if migration is None:
            raise KeyError(f"unknown_legacy_migration:{migration_id}")
        return migration


__all__ = [
    "SRO_RETENTION_RUNTIME_VERSION",
    "LegacyRetentionMigrationCandidate",
    "SROCalibrationContract",
    "SRORetentionRouteReceipt",
    "SRORetentionRuntime",
    "SRORetentionRuntimeSnapshot",
    "SRORetentionTask",
]
