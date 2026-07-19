"""Unified read-only source for strongly bound Anti-Additive receipts."""

from __future__ import annotations

from typing import Protocol

from agentos_kernel import AntiAdditiveMethodologyReceipt


ANTI_ADDITIVE_AUTHORITY_REQUIREMENTS = (
    "CANDIDATE_ONLY",
    "DURABLE_PROJECT_WRITE",
)


class AntiAdditiveMethodologyReceiptSource(Protocol):
    def methodology_receipt(
        self, *, audit_id: str, project_scope: str
    ) -> AntiAdditiveMethodologyReceipt: ...

    def verify_replay(self) -> dict[str, object]: ...


def resolve_anti_additive_methodology_receipt(
    *,
    source: AntiAdditiveMethodologyReceiptSource,
    audit_id: str,
    project_scope: str,
    candidate_id: str,
    candidate_payload_hash: str,
    target_type: str,
    authority_requirement: str,
) -> AntiAdditiveMethodologyReceipt:
    if authority_requirement not in ANTI_ADDITIVE_AUTHORITY_REQUIREMENTS:
        raise ValueError("anti_additive_authority_requirement_invalid")
    replay = source.verify_replay()
    if not replay.get("valid"):
        raise ValueError("anti_additive_methodology_source_replay_invalid")
    receipt = source.methodology_receipt(audit_id=audit_id, project_scope=project_scope)
    if replay.get("latest_receipt_hashes", {}).get(audit_id) != receipt.receipt_hash:
        raise ValueError("anti_additive_methodology_source_receipt_not_latest")
    candidate = receipt.candidate
    if (
        candidate.audit_id != audit_id
        or candidate.project_scope != project_scope
        or candidate.candidate_id != candidate_id
        or candidate.candidate_payload_hash != candidate_payload_hash
        or candidate.target_type != target_type
    ):
        raise ValueError("anti_additive_methodology_source_binding_invalid")
    if authority_requirement == "DURABLE_PROJECT_WRITE" and receipt.decision.allowed is not True:
        raise ValueError("anti_additive_methodology_source_durable_authority_required")
    if authority_requirement == "CANDIDATE_ONLY" and receipt.decision.candidate_only_allowed is not True:
        raise ValueError("anti_additive_methodology_source_candidate_authority_required")
    return receipt
