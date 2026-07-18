"""Adversarial, replication-backed epistemic review protocol.

This module owns bounded epistemic decisions. It does not grant execution
permission, promote assets, or require any particular provider implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EPISTEMIC_REVIEW_VERSION = "epistemic_review_protocol_v0_1"

DECISION_SUPPORTED_BOUNDED = "SUPPORTED_BOUNDED"
DECISION_FALSIFIED = "FALSIFIED"
DECISION_PENDING = "PENDING"

OBJECTION_STATUSES = {"OPEN", "SUSTAINED", "RESOLVED"}
REPLICATION_OUTCOMES = {"PASSED", "FAILED", "INCONCLUSIVE"}


@dataclass(frozen=True)
class ClaimCandidate:
    claim_id: str
    author_agent_id: str
    statement: str
    research_object: str
    observable_proxy: str
    metric: str
    scope: str
    rival_explanations: tuple[str, ...]
    frozen_gate_ref: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        required = {
            "claim_id": self.claim_id,
            "author_agent_id": self.author_agent_id,
            "statement": self.statement,
            "research_object": self.research_object,
            "observable_proxy": self.observable_proxy,
            "metric": self.metric,
            "scope": self.scope,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"claim_required_fields_missing:{','.join(missing)}")


@dataclass(frozen=True)
class ObjectionReceipt:
    objection_id: str
    target_claim_id: str
    reviewer_agent_id: str
    rival_explanation: str
    strongest_falsifier_ref: str
    status: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in OBJECTION_STATUSES:
            raise ValueError(f"unknown_objection_status:{self.status}")
        if not all(
            (
                self.objection_id,
                self.target_claim_id,
                self.reviewer_agent_id,
                self.rival_explanation,
                self.strongest_falsifier_ref,
            )
        ):
            raise ValueError("incomplete_objection_receipt")
        if not self.evidence_refs:
            raise ValueError("objection_evidence_refs_required")


@dataclass(frozen=True)
class ReplicationReceipt:
    replication_id: str
    target_claim_id: str
    replicator_agent_id: str
    independent_context_id: str
    outcome: str
    evidence_refs: tuple[str, ...]
    provider_support_receipt_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.outcome not in REPLICATION_OUTCOMES:
            raise ValueError(f"unknown_replication_outcome:{self.outcome}")
        if not all(
            (
                self.replication_id,
                self.target_claim_id,
                self.replicator_agent_id,
                self.independent_context_id,
            )
        ):
            raise ValueError("incomplete_replication_receipt")
        if not self.evidence_refs:
            raise ValueError("replication_evidence_refs_required")


@dataclass(frozen=True)
class EpistemicReviewDecision:
    claim_id: str
    decision: str
    reasons: tuple[str, ...]
    objection_ids: tuple[str, ...]
    replication_ids: tuple[str, ...]
    independent_replication_count: int
    evidence_refs: tuple[str, ...]
    permission_granted: bool = False
    asset_promotion_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "objection_ids": list(self.objection_ids),
            "replication_ids": list(self.replication_ids),
            "independent_replication_count": self.independent_replication_count,
            "evidence_refs": list(self.evidence_refs),
            "permission_granted": self.permission_granted,
            "asset_promotion_authorized": self.asset_promotion_authorized,
        }


class EpistemicReviewProtocol:
    """P1 falsification-first review independent from permission gates."""

    module_id = EPISTEMIC_REVIEW_VERSION
    capabilities = ("epistemic_review", "adversarial_objection", "independent_replication")

    def assess(
        self,
        claim: ClaimCandidate,
        objections: tuple[ObjectionReceipt, ...] = (),
        replications: tuple[ReplicationReceipt, ...] = (),
    ) -> EpistemicReviewDecision:
        self._validate_targets(claim, objections, replications)
        reasons: list[str] = []

        if not claim.rival_explanations:
            reasons.append("rival_set_required")
        if not claim.frozen_gate_ref:
            reasons.append("frozen_gate_ref_required")
        if not claim.evidence_refs:
            reasons.append("claim_evidence_refs_required")

        independent = tuple(
            receipt
            for receipt in replications
            if receipt.replicator_agent_id != claim.author_agent_id and receipt.independent_context_id
        )
        if any(receipt.outcome == "FAILED" for receipt in independent):
            decision = DECISION_FALSIFIED
            reasons.append("independent_replication_failed")
        elif any(objection.status == "SUSTAINED" for objection in objections):
            decision = DECISION_FALSIFIED
            reasons.append("strongest_falsifier_sustained")
        elif reasons:
            decision = DECISION_PENDING
        elif not independent:
            decision = DECISION_PENDING
            reasons.append("independent_replication_required")
        elif not any(receipt.outcome == "PASSED" for receipt in independent):
            decision = DECISION_PENDING
            reasons.append("independent_replication_inconclusive")
        elif any(objection.status == "OPEN" for objection in objections):
            decision = DECISION_PENDING
            reasons.append("open_objection_requires_resolution")
        else:
            decision = DECISION_SUPPORTED_BOUNDED
            reasons.append("frozen_gate_and_independent_replication_passed")

        evidence_refs = tuple(
            dict.fromkeys(
                (
                    *claim.evidence_refs,
                    *(ref for objection in objections for ref in objection.evidence_refs),
                    *(ref for receipt in replications for ref in receipt.evidence_refs),
                    *(ref for receipt in replications for ref in receipt.provider_support_receipt_refs),
                )
            )
        )
        return EpistemicReviewDecision(
            claim_id=claim.claim_id,
            decision=decision,
            reasons=tuple(reasons),
            objection_ids=tuple(objection.objection_id for objection in objections),
            replication_ids=tuple(receipt.replication_id for receipt in replications),
            independent_replication_count=len(independent),
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _validate_targets(
        claim: ClaimCandidate,
        objections: tuple[ObjectionReceipt, ...],
        replications: tuple[ReplicationReceipt, ...],
    ) -> None:
        if any(objection.target_claim_id != claim.claim_id for objection in objections):
            raise ValueError("objection_target_claim_mismatch")
        if any(receipt.target_claim_id != claim.claim_id for receipt in replications):
            raise ValueError("replication_target_claim_mismatch")
        objection_ids = [objection.objection_id for objection in objections]
        replication_ids = [receipt.replication_id for receipt in replications]
        if len(set(objection_ids)) != len(objection_ids):
            raise ValueError("duplicate_objection_id")
        if len(set(replication_ids)) != len(replication_ids):
            raise ValueError("duplicate_replication_id")
