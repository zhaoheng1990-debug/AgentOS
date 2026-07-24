"""Resolve paid peer disagreements without reusing primary-selection credit."""

from __future__ import annotations

from .calibrated_policy import CalibratedCandidateSignal
from .disagreement_resolution_lifecycle import ResolutionCreditSnapshot
from .structural_operator_policy import StructuralOperatorCompetitionPolicy, StructuralOperatorDecision


class IndependentDisagreementResolutionPolicy(StructuralOperatorCompetitionPolicy):
    def __init__(
        self,
        *,
        resolution_credit: ResolutionCreditSnapshot,
        minimum_override_net_cbit: float = 0.10,
        **values,
    ) -> None:
        super().__init__(**values)
        self.resolution_credit = resolution_credit
        self.minimum_override_net_cbit = minimum_override_net_cbit

    def resolve_probe(
        self,
        decision: StructuralOperatorDecision,
        primary: CalibratedCandidateSignal,
        peer: CalibratedCandidateSignal,
    ) -> StructuralOperatorDecision:
        if decision.action != "VERIFY_PEER" or decision.reviewer_model_id != peer.model_id:
            raise ValueError("independent_resolution_binding_invalid")
        if primary.answer == peer.answer:
            return self._resolved(
                decision, action="PEER_AGREEMENT_RESOLVED", answer=primary.answer,
                reason="peer_agreement_requires_no_resolution", policy="AGREEMENT",
            )
        credit = self.resolution_credit.get(self.item_fingerprints[primary.item_id])
        override = (
            credit.evidence_level != "GLOBAL"
            and credit.expected_override_net_cbit >= self.minimum_override_net_cbit
        )
        return self._resolved(
            decision,
            action="PEER_OVERRIDE_RESOLVED" if override else "PRIMARY_KEEP_RESOLVED",
            answer=peer.answer if override else primary.answer,
            reason="independent_resolution_credit_overrides" if override else "independent_resolution_credit_keeps_primary",
            policy="PEER_OVERRIDE" if override else "KEEP_PRIMARY",
            correction=credit.correction_posterior, harm=credit.harm_posterior,
            net=credit.expected_override_net_cbit, evidence=credit.evidence_level,
        )

    @staticmethod
    def _resolved(
        decision,
        *,
        action,
        answer,
        reason,
        policy,
        correction=0.0,
        harm=0.0,
        net=0.0,
        evidence="",
    ):
        return StructuralOperatorDecision(**{
            **decision.__dict__, "action": action, "final_answer": answer, "reason": reason,
            "resolution_policy": policy,
            "resolution_expected_correction": round(correction, 12),
            "resolution_expected_harm": round(harm, 12),
            "resolution_expected_net_cbit": round(net, 12),
            "resolution_evidence_level": evidence,
        })
