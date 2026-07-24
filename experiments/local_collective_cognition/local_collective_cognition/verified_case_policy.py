"""Kernel gate combining Provider judgment with Harness argument replay."""

from __future__ import annotations

from .case_adjudication_policy import CaseAdjudicationPolicy
from .structural_operator_policy import StructuralOperatorDecision


class VerifiedCaseAdjudicationPolicy(CaseAdjudicationPolicy):
    def resolve_case(self, decision, primary, peer, witness, bundle) -> StructuralOperatorDecision:
        resolved = super().resolve_case(decision, primary, peer, witness, bundle)
        receipts = {item.candidate_id: item for item in bundle.verification_receipts}
        if set(receipts) != {bundle.primary_candidate_id, bundle.peer_candidate_id}:
            raise ValueError("verified_case_receipt_binding_invalid")
        primary_status = receipts[bundle.primary_candidate_id].status
        peer_status = receipts[bundle.peer_candidate_id].status
        provider_selects_peer = (
            bundle.judgment["selected_candidate"] == bundle.peer_candidate_id
            and bundle.judgment["adjudicability"] == "ADJUDICABLE"
            and float(bundle.judgment["confidence"]) >= self.minimum_case_confidence
        )
        override = provider_selects_peer and peer_status == "VERIFIED" and primary_status != "VERIFIED"
        if override:
            action, answer, policy = "PEER_OVERRIDE_RESOLVED", peer.answer, "VERIFIED_CASE_PEER_OVERRIDE"
            reason = "provider_judgment_and_replay_select_peer"
        else:
            action, answer, policy = "PRIMARY_KEEP_RESOLVED", primary.answer, "VERIFIED_CASE_KEEP_PRIMARY"
            reason = (
                "both_arguments_verified_conflict_unresolved" if primary_status == peer_status == "VERIFIED"
                else "peer_argument_not_verified" if peer_status != "VERIFIED"
                else "provider_judgment_did_not_clear_override_gate"
            )
        verification = f"primary={primary_status};peer={peer_status};judge={bundle.judgment['selected_candidate']}"
        return StructuralOperatorDecision(**{
            **resolved.__dict__, "action": action, "final_answer": answer,
            "reason": reason, "resolution_policy": policy,
            "resolution_evidence_level": "CURRENT_CASE_VERIFIED_ARGUMENT",
            "case_decisive_reason": verification + ";" + bundle.judgment["decisive_reason"],
        })
