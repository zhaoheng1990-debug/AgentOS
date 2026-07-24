"""Kernel adoption gate for replay-verified candidate belief revision."""

from __future__ import annotations

from .structural_operator_policy import StructuralOperatorDecision
from .verified_case_policy import VerifiedCaseAdjudicationPolicy


class CandidateRevisionPolicy(VerifiedCaseAdjudicationPolicy):
    def resolve_case(self, decision, primary, peer, witness, bundle) -> StructuralOperatorDecision:
        resolved = super().resolve_case(decision, primary, peer, witness, bundle)
        receipts = {item.candidate_id: item for item in bundle.verification_receipts}
        selected = receipts.get(bundle.judgment["selected_candidate"])
        adopt = (
            selected is not None and selected.status == "VERIFIED"
            and bundle.judgment["adjudicability"] == "ADJUDICABLE"
            and float(bundle.judgment["confidence"]) >= self.minimum_case_confidence
        )
        answer = selected.proposed_candidate if adopt else primary.answer
        revised = adopt and answer != primary.answer
        reason = (
            "provider_revision_replay_and_judgment_pass" if revised
            else "verified_revision_confirms_primary" if adopt
            else "candidate_revision_adoption_gate_not_cleared"
        )
        return StructuralOperatorDecision(**{
            **resolved.__dict__,
            "action": "CANDIDATE_REVISION_RESOLVED" if revised else "PRIMARY_KEEP_RESOLVED",
            "final_answer": answer, "reason": reason,
            "resolution_policy": (
                "PROVIDER_BACKED_CANDIDATE_REVISION" if revised
                else "CANDIDATE_REVISION_CONFIRMED_PRIMARY" if adopt
                else "CANDIDATE_REVISION_KEEP_PRIMARY"
            ),
            "resolution_evidence_level": "CURRENT_CASE_VERIFIED_CANDIDATE_REVISION",
            "case_decisive_reason": (
                f"selected_status={selected.status if selected else 'MISSING'};"
                f"selected_disposition={selected.disposition if selected else 'MISSING'};"
                + bundle.judgment["decisive_reason"]
            ),
        })
