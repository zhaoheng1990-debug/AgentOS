"""Aggregate Harness gate for primary-error opportunities in revision work."""

from __future__ import annotations

from .argument_opportunity_receipt import (
    ArgumentOpportunityReceipt, _hash, build_argument_opportunity_receipt,
)


def build_candidate_revision_opportunity_receipt(
    *, experiment_id: str, pairs: tuple[dict[str, str], ...],
    truths: dict[str, str], truth_commitment: str,
) -> ArgumentOpportunityReceipt:
    receipt = build_argument_opportunity_receipt(
        experiment_id=experiment_id, pairs=pairs, truths=truths,
        truth_commitment=truth_commitment,
    )
    committed = {
        **receipt._committed(), "gate_passed": receipt.primary_error_opportunities > 0,
        "gate_basis": "PRIMARY_ERROR_OPPORTUNITY",
    }
    return ArgumentOpportunityReceipt(**committed, receipt_hash=_hash(committed))
