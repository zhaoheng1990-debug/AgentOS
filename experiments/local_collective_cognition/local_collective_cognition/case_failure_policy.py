"""Fail-closed Kernel-side decision for unavailable case adjudication."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structural_operator_policy import StructuralOperatorDecision


def resolve_case_provider_failure(
    *, decision, primary, peer, witness, item_context: str, context_credit, failure,
) -> StructuralOperatorDecision:
    topology = (
        "THIRD_SUPPORTS_PEER" if witness.answer == peer.answer
        else "THIRD_SUPPORTS_PRIMARY" if witness.answer == primary.answer
        else "ALL_DIFFER"
    )
    historical = context_credit.resolve(
        fingerprint=item_context, primary_model_id=primary.model_id,
        peer_model_id=peer.model_id, support_topology=topology,
    )
    argument_hashes = tuple(
        hash_payload(run.result) for run in failure.runs
        if run.tasks[-1].task_kind == "pilot_disagreement_argument"
    )
    return StructuralOperatorDecision(**{
        **decision.__dict__, "action": "PRIMARY_KEEP_RESOLVED",
        "final_answer": primary.answer, "reason": "current_case_provider_failed_closed",
        "resolution_policy": "CASE_PROVIDER_FAILED_KEEP",
        "resolution_expected_net_cbit": historical.expected_net_cbit,
        "resolution_evidence_level": "CASE_PROVIDER_FAILURE",
        "context_support_topology": topology,
        "context_expected_net_cbit": historical.expected_net_cbit,
        "context_pair_correction_surplus": historical.pair_correction_surplus,
        "context_pair_evidence_count": historical.pair_evidence_count,
        "context_witness_used": True, "case_adjudication_used": True,
        "case_judge_model_id": witness.model_id, "case_selected_candidate": "ABSTAIN",
        "case_adjudicability": "PROVIDER_FAILED", "case_confidence": 0.0,
        "case_decisive_reason": ";".join(failure.failures) or failure.stage,
        "case_argument_hashes": argument_hashes,
        "case_judgment_hash": hash_payload(failure.runs[-1].result),
    })
