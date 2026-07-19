"""Candidate-only migration policy for legacy retention records."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from agentos_kernel import ConstraintAlignedRetentionGate, SerialSelectionWitness
from agentos_kernel import methodology_candidate_commitment
from .anti_additive_source import (
    AntiAdditiveMethodologyReceiptSource,
    resolve_anti_additive_methodology_receipt,
)

from .sro_retention_contracts import (
    LegacyRetentionMigrationCandidate,
    hash_payload,
    require_text,
    utc_now,
)


class LegacyRetentionMigrator:
    """Classify, revalidate, and reconstruct legacy records without promotion."""

    def __init__(
        self,
        project_scope: str,
        retention_gate: ConstraintAlignedRetentionGate | None = None,
        anti_additive_source: AntiAdditiveMethodologyReceiptSource | None = None,
    ) -> None:
        self.project_scope = project_scope
        self.retention_gate = retention_gate or ConstraintAlignedRetentionGate()
        self.anti_additive_source = anti_additive_source

    def create(
        self,
        candidate: dict[str, Any],
        *,
        migration_authority_ref: str,
        methodology_audit_id: str = "",
    ) -> LegacyRetentionMigrationCandidate:
        self._require_kernel_authority(
            migration_authority_ref,
            "legacy_migration_kernel_authority_required",
        )
        legacy_hash = hash_payload(candidate)
        methodology = self._methodology(candidate, methodology_audit_id)
        decision = self.retention_gate.evaluate(
            candidate,
            methodology_receipt=methodology,
            require_methodology_receipt=self.anti_additive_source is not None,
        )
        evidence_refs = tuple(candidate.get("evidence_refs") or ())
        state = self._initial_state(candidate, decision.eligible_for_retention)
        return LegacyRetentionMigrationCandidate(
            migration_id=f"migration-{legacy_hash[:16]}",
            legacy_candidate_id=require_text("legacy_candidate_id", candidate.get("candidate_id")),
            legacy_candidate_hash=legacy_hash,
            project_scope=str(candidate.get("scope") or ""),
            evidence_refs=evidence_refs,
            accept_decision_ref=str(candidate.get("accept_decision_ref") or ""),
            migration_authority_ref=migration_authority_ref,
            legacy_decision=decision.decision,
            legacy_eligible_for_retention=decision.eligible_for_retention,
            candidate_state=state,
            required_reconstruction_refs=self._required_refs(state),
            created_at=utc_now(),
            anti_additive_methodology_receipt_hash=decision.anti_additive_methodology_receipt_hash,
        )

    def revalidate(
        self,
        migration: LegacyRetentionMigrationCandidate,
        revalidated_candidate: dict[str, Any],
        *,
        kernel_authorization_ref: str,
        methodology_audit_id: str = "",
    ) -> LegacyRetentionMigrationCandidate:
        self._require_kernel_authority(
            kernel_authorization_ref,
            "legacy_revalidation_kernel_authority_required",
        )
        if migration.candidate_state != "PENDING_PROVIDER_REVALIDATION":
            raise ValueError("legacy_migration_not_pending_provider_revalidation")
        if revalidated_candidate.get("candidate_id") != migration.legacy_candidate_id:
            raise ValueError("legacy_revalidation_candidate_id_mismatch")
        if revalidated_candidate.get("legacy_source_hash") != migration.legacy_candidate_hash:
            raise ValueError("legacy_revalidation_source_hash_mismatch")
        if not set(migration.evidence_refs).issubset(revalidated_candidate.get("evidence_refs") or ()):
            raise ValueError("legacy_revalidation_must_preserve_evidence")
        methodology = self._methodology(revalidated_candidate, methodology_audit_id)
        decision = self.retention_gate.evaluate(
            revalidated_candidate,
            methodology_receipt=methodology,
            require_methodology_receipt=self.anti_additive_source is not None,
        )
        return replace(
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
            anti_additive_methodology_receipt_hash=decision.anti_additive_methodology_receipt_hash,
        )

    def _methodology(self, candidate, audit_id):
        if self.anti_additive_source is None:
            if audit_id:
                raise ValueError("retention_anti_additive_source_required")
            return None
        if not audit_id:
            raise ValueError("retention_anti_additive_audit_id_required")
        return resolve_anti_additive_methodology_receipt(
            source=self.anti_additive_source,
            audit_id=audit_id,
            project_scope=self.project_scope,
            candidate_id=str(candidate.get("candidate_id") or ""),
            candidate_payload_hash=methodology_candidate_commitment(candidate),
            target_type="RetentionCandidate",
            authority_requirement="DURABLE_PROJECT_WRITE",
        )

    def reconstruct_witness(
        self,
        migration: LegacyRetentionMigrationCandidate,
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
        self._require_kernel_authority(
            kernel_authorization_ref,
            "sro_witness_registration_kernel_authority_required",
        )
        if migration.candidate_state != "PENDING_WITNESS_RECONSTRUCTION":
            raise ValueError("legacy_migration_not_pending_reconstruction")
        if not set(migration.evidence_refs).issubset(evidence_refs):
            raise ValueError("migrated_witness_must_preserve_legacy_evidence")
        selection_context_ref = f"migration://{migration.migration_id}"
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
        return SerialSelectionWitness(
            witness_id=witness_id,
            status="PRECOMMITTED",
            project_scope_ref=self.project_scope,
            selection_context_ref=selection_context_ref,
            sro_address_ref=sro_address_ref,
            validity_boundary_ref=validity_boundary_ref,
            reconstruction_ref=reconstruction_ref,
            authority_ref=authority_ref,
            privacy_boundary=privacy_boundary,
            precommit_hash=hash_payload(precommit_payload),
            sealed_at=sealed_at,
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def mark_witness_registered(
        migration: LegacyRetentionMigrationCandidate,
        witness_id: str,
    ) -> LegacyRetentionMigrationCandidate:
        return replace(
            migration,
            candidate_state="WITNESS_REGISTERED_PROJECT_SCOPED",
            registered_witness_id=witness_id,
        )

    @staticmethod
    def _initial_state(candidate: dict[str, Any], eligible: bool) -> str:
        if eligible:
            return "PENDING_WITNESS_RECONSTRUCTION"
        legacy_accept_candidate = bool(
            candidate.get("evidence_refs")
            and candidate.get("accept_decision_ref")
            and "ACCEPT" in str(candidate.get("status", ""))
            and candidate.get("scope") in {"project_scoped", "AgentOS project runtime policy selection"}
        )
        return "PENDING_PROVIDER_REVALIDATION" if legacy_accept_candidate else "QUARANTINED_LEGACY_RECORD"

    @staticmethod
    def _required_refs(state: str) -> tuple[str, ...]:
        return (
            "provider_backed_retention_revalidation"
            if state == "PENDING_PROVIDER_REVALIDATION"
            else "sro_address_ref",
            "validity_boundary_ref",
            "reconstruction_ref",
            "authority_ref",
            "privacy_boundary",
        )

    @staticmethod
    def _require_kernel_authority(authority_ref: str, error: str) -> None:
        if not authority_ref.startswith("kernel://"):
            raise ValueError(error)
