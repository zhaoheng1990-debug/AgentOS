"""Current-case adjudication policy with historical credit retained as a prior only."""

from __future__ import annotations

from .context_resolution_policy import ContextAwareResolutionPolicy
from .structural_operator_policy import StructuralOperatorDecision


class CaseAdjudicationPolicy(ContextAwareResolutionPolicy):
    def __init__(self, *, minimum_case_confidence: float = 0.70, **values) -> None:
        super().__init__(**values)
        if not 0.0 <= minimum_case_confidence <= 1.0:
            raise ValueError("case_adjudication_confidence_invalid")
        self.minimum_case_confidence = minimum_case_confidence

    def resolve_probe(self, decision, primary, peer) -> StructuralOperatorDecision:
        resolved = super().resolve_probe(decision, primary, peer)
        if resolved.action != "REQUEST_CONTEXT_WITNESS":
            return resolved
        return StructuralOperatorDecision(**{
            **resolved.__dict__, "action": "REQUEST_CASE_ADJUDICATION",
            "reason": "primary_peer_disagreement_requires_current_case_evidence",
        })

    def resolve_case(self, decision, primary, peer, witness, bundle) -> StructuralOperatorDecision:
        if (
            decision.action != "REQUEST_CASE_ADJUDICATION"
            or decision.primary_model_id != primary.model_id
            or decision.reviewer_model_id != peer.model_id
            or decision.context_model_id != witness.model_id
            or bundle.item_id != primary.item_id
            or bundle.primary_model_id != primary.model_id
            or bundle.peer_model_id != peer.model_id
            or bundle.judge_model_id != witness.model_id
        ):
            raise ValueError("case_adjudication_binding_invalid")
        topology = (
            "THIRD_SUPPORTS_PEER" if witness.answer == peer.answer
            else "THIRD_SUPPORTS_PRIMARY" if witness.answer == primary.answer
            else "ALL_DIFFER"
        )
        historical = self.context_credit.resolve(
            fingerprint=self.item_fingerprints[primary.item_id],
            primary_model_id=primary.model_id, peer_model_id=peer.model_id,
            support_topology=topology,
        )
        judgment = bundle.judgment
        selected = judgment["selected_candidate"]
        adjudicable = judgment["adjudicability"] == "ADJUDICABLE"
        confident = float(judgment["confidence"]) >= self.minimum_case_confidence
        override = adjudicable and confident and selected == bundle.peer_candidate_id
        reason = (
            "current_case_judge_selects_peer" if override
            else "current_case_judge_selects_primary" if selected == bundle.primary_candidate_id
            else "current_case_judgment_abstains_or_below_gate"
        )
        return StructuralOperatorDecision(**{
            **decision.__dict__,
            "action": "PEER_OVERRIDE_RESOLVED" if override else "PRIMARY_KEEP_RESOLVED",
            "final_answer": peer.answer if override else primary.answer,
            "reason": reason,
            "resolution_policy": "CASE_PEER_OVERRIDE" if override else "CASE_KEEP_PRIMARY",
            "resolution_expected_net_cbit": historical.expected_net_cbit,
            "resolution_evidence_level": "CURRENT_CASE_ARGUMENT",
            "context_support_topology": topology,
            "context_expected_net_cbit": historical.expected_net_cbit,
            "context_pair_correction_surplus": historical.pair_correction_surplus,
            "context_pair_evidence_count": historical.pair_evidence_count,
            "context_witness_used": True,
            "case_adjudication_used": True,
            "case_judge_model_id": witness.model_id,
            "case_selected_candidate": selected,
            "case_adjudicability": judgment["adjudicability"],
            "case_confidence": float(judgment["confidence"]),
            "case_decisive_reason": judgment["decisive_reason"],
            "case_argument_hashes": bundle.argument_hashes,
            "case_judgment_hash": bundle.judgment_hash,
        })
