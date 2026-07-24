"""Candidate-only migration from serial witnesses to selection-first records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentos_kernel.selection_retention_models import (
    ProspectiveSelectionEvent,
    hash_selection_payload,
)
from agentos_kernel.sro_retention_models import SerialSelectionWitness


@dataclass(frozen=True)
class LegacySelectionMigrationCandidate:
    migration_id: str
    legacy_witness_id: str
    legacy_witness_hash: str
    project_scope: str
    preserved_evidence_refs: tuple[str, ...]
    missing_selection_fields: tuple[str, ...]
    candidate_state: str = "PENDING_SELECTION_RECONSTRUCTION"

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "migration_id": self.migration_id,
            "legacy_witness_id": self.legacy_witness_id,
            "legacy_witness_hash": self.legacy_witness_hash,
            "project_scope": self.project_scope,
            "preserved_evidence_refs": list(
                self.preserved_evidence_refs
            ),
            "missing_selection_fields": list(
                self.missing_selection_fields
            ),
            "candidate_state": self.candidate_state,
            "automatic_promotion_allowed": False,
        }
        return {**payload, "migration_hash": hash_selection_payload(payload)}


class SerialSelectionWitnessAdapter:
    def create(
        self, witness: SerialSelectionWitness
    ) -> LegacySelectionMigrationCandidate:
        witness_hash = witness.as_dict()["record_hash"]
        return LegacySelectionMigrationCandidate(
            migration_id=f"selection-migration-{witness_hash[:16]}",
            legacy_witness_id=witness.witness_id,
            legacy_witness_hash=witness_hash,
            project_scope=witness.project_scope_ref,
            preserved_evidence_refs=witness.evidence_refs,
            missing_selection_fields=(
                "alternatives",
                "selected_ref",
                "rejected_refs",
                "deferred_refs",
                "path_change_hypothesis_ref",
            ),
        )

    def reconstruct(
        self,
        *,
        migration: LegacySelectionMigrationCandidate,
        witness: SerialSelectionWitness,
        selection_event_id: str,
        alternatives: tuple[str, ...],
        selected_ref: str,
        rejected_refs: tuple[str, ...],
        deferred_refs: tuple[str, ...],
        path_change_hypothesis_ref: str,
        kernel_authority_ref: str,
    ) -> ProspectiveSelectionEvent:
        if migration.candidate_state != "PENDING_SELECTION_RECONSTRUCTION":
            raise ValueError("legacy_selection_migration_state_invalid")
        witness_hash = witness.as_dict()["record_hash"]
        if (
            migration.legacy_witness_id != witness.witness_id
            or migration.legacy_witness_hash != witness_hash
            or migration.project_scope != witness.project_scope_ref
        ):
            raise ValueError("legacy_selection_witness_binding_invalid")
        return ProspectiveSelectionEvent.create(
            selection_event_id=selection_event_id,
            project_scope=witness.project_scope_ref,
            selection_context_ref=witness.selection_context_ref,
            alternatives=alternatives,
            selected_ref=selected_ref,
            rejected_refs=rejected_refs,
            deferred_refs=deferred_refs,
            path_change_hypothesis_ref=path_change_hypothesis_ref,
            sro_address_ref=witness.sro_address_ref,
            validity_boundary_ref=witness.validity_boundary_ref,
            reconstruction_ref=witness.reconstruction_ref,
            authority_ref=kernel_authority_ref,
            evidence_refs=witness.evidence_refs,
            sealed_at=witness.sealed_at,
        )
