"""Build v0.21 state with v0.20 two-stage evidence as diagnostic prior."""

from __future__ import annotations

from .calibrated_resolution_workflow import build_resolution_receipt_from_report
from .context_resolution_lifecycle import ContextResolutionLifecycle
from .context_resolution_policy import build_context_exploration_schedule
from .context_resolution_workflow import build_context_receipt_from_report
from .holdout_v18_benchmark import HOLDOUT_V18_ITEM_FINGERPRINTS, build_holdout_v18_harness
from .holdout_v19_benchmark import HOLDOUT_V19_ITEM_DOMAINS, HOLDOUT_V19_ROUTING_FINGERPRINTS
from .multi_cycle_resolution import MultiCycleResolutionLifecycle
from .staged_derivation_workflow import build_staged_derivation_state
from .structural_operator_policy import build_structural_operator_schedule


_ACTIONS = ("PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED",
            "CANDIDATE_REVISION_RESOLVED")


def build_constrained_tool_state(*, v20_report_path, **values):
    prior = build_staged_derivation_state(**values)
    resolution = build_resolution_receipt_from_report(
        report_path=v20_report_path, harness=build_holdout_v18_harness(),
        item_fingerprints=HOLDOUT_V18_ITEM_FINGERPRINTS,
        source_credit_hash_key=("context_resolution_credit", "snapshot_hash"),
        source_actions=_ACTIONS,
    )
    context = build_context_receipt_from_report(
        report_path=v20_report_path, harness=build_holdout_v18_harness(),
        item_fingerprints=HOLDOUT_V18_ITEM_FINGERPRINTS,
        source_credit_hash_key=("context_resolution_credit", "snapshot_hash"),
        source_actions=_ACTIONS,
    )
    resolution_receipts = (*prior["resolution_evidence_receipts"], resolution)
    context_receipts = (*prior["context_evidence_receipts"], context)
    resolution_lifecycle, context_lifecycle = MultiCycleResolutionLifecycle(), ContextResolutionLifecycle()
    resolution_candidates, resolution_promotions = _promote_all(resolution_lifecycle, resolution_receipts)
    context_candidates, context_promotions = _promote_all(context_lifecycle, context_receipts)
    context_credit = context_lifecycle.snapshot()
    acquisition = build_structural_operator_schedule(
        profiles=prior["profiles"], operator_credit=prior["operator_credit_snapshot"],
        item_domains=HOLDOUT_V19_ITEM_DOMAINS, item_fingerprints=HOLDOUT_V19_ROUTING_FINGERPRINTS,
        budget=4,
    )
    exploration = build_context_exploration_schedule(
        context_credit=context_credit, profiles=prior["profiles"],
        item_domains=HOLDOUT_V19_ITEM_DOMAINS, item_fingerprints=HOLDOUT_V19_ROUTING_FINGERPRINTS,
        existing_schedule=acquisition, budget=2,
    )
    return {**prior, "operator_schedule": {**acquisition, **exploration},
            "acquisition_schedule": acquisition, "resolution_exploration_schedule": exploration,
            "resolution_evidence_receipts": resolution_receipts,
            "resolution_candidates": resolution_candidates, "resolution_promotions": resolution_promotions,
            "resolution_credit_snapshot": resolution_lifecycle.snapshot(),
            "context_evidence_receipts": context_receipts, "context_candidates": context_candidates,
            "context_promotions": context_promotions, "context_credit_snapshot": context_credit}


def _promote_all(lifecycle, receipts):
    candidates, promotions = [], []
    for receipt in receipts:
        candidate = lifecycle.ingest_candidate(receipt)
        candidates.append(candidate)
        promotions.append(lifecycle.promote(
            candidate_hash=candidate.candidate_hash, validation_ref=receipt.source_report_hash))
    return tuple(candidates), tuple(promotions)
