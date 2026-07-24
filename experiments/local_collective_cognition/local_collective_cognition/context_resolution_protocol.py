"""Protocol v0.12: pair-conditioned resolution with independent context witness."""

from __future__ import annotations

from typing import Any

from .calibrated_resolution_protocol import CalibratedResolutionProtocol
from .context_resolution_policy import ContextAwareResolutionPolicy
from .holdout_v10_benchmark import (
    HOLDOUT_V10_BENCHMARK_ID,
    HOLDOUT_V10_ITEM_DOMAINS,
    HOLDOUT_V10_ITEM_FINGERPRINTS,
)


CONTEXT_RESOLUTION_PROTOCOL_VERSION = "disagreement_resolution_context_protocol_v0_12"


class ContextResolutionProtocol(CalibratedResolutionProtocol):
    def __init__(
        self,
        *,
        context_evidence_receipts,
        context_candidates,
        context_promotions,
        context_credit_snapshot,
        profiles,
        operator_credit_snapshot,
        operator_schedule,
        resolution_credit_snapshot,
        resolution_exploration_schedule,
        **values: Any,
    ) -> None:
        if len(context_evidence_receipts) < 3 or not (
            len(context_evidence_receipts) == len(context_candidates) == len(context_promotions)
        ):
            raise ValueError("context_resolution_cycle_coverage_invalid")
        if "policy" not in values:
            values["policy"] = ContextAwareResolutionPolicy(
                operator_credit=operator_credit_snapshot,
                operator_schedule=operator_schedule,
                item_fingerprints=HOLDOUT_V10_ITEM_FINGERPRINTS,
                resolution_credit=resolution_credit_snapshot,
                exploration_items=tuple(resolution_exploration_schedule),
                context_credit=context_credit_snapshot,
                model_ids=tuple(profiles),
            )
        values.setdefault("item_domains", HOLDOUT_V10_ITEM_DOMAINS)
        values.setdefault("item_contexts", HOLDOUT_V10_ITEM_FINGERPRINTS)
        values.setdefault("arm_namespace", "HOLDOUT_V10")
        super().__init__(
            profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule,
            resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            **values,
        )
        self.context_evidence_receipts = tuple(context_evidence_receipts)
        self.context_candidates = tuple(context_candidates)
        self.context_promotions = tuple(context_promotions)
        self.context_credit_snapshot = context_credit_snapshot

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        decisions = tuple(report["route_decisions"])
        for key in (
            "v09_v10_resolution_outcomes_used_for_v11_route",
            "v08_operator_outcomes_used_for_v11_acquisition_route",
            "v11_outcomes_used_for_current_route",
            "current_exploration_outcomes_used_for_current_route",
        ):
            report["protocol"].pop(key, None)
        report["protocol"].update({
            "protocol_version": CONTEXT_RESOLUTION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V10_BENCHMARK_ID,
            "context_evidence_receipt_refs": list(self.context_credit_snapshot.source_receipt_hashes),
            "context_credit_snapshot_ref": self.context_credit_snapshot.snapshot_hash,
            "v09_v10_v11_context_outcomes_used_for_v12_route": True,
            "v12_outcomes_used_for_current_route": False,
            "independent_context_witness_charged": True,
            "context_witness_truth_access": False,
            "pair_correction_surplus_required": True,
        })
        report["context_resolution_evidence_cycles"] = [item.as_dict() for item in self.context_evidence_receipts]
        report["context_evidence_candidates"] = [item.as_dict() for item in self.context_candidates]
        report["context_promotion_receipts"] = [item.as_dict() for item in self.context_promotions]
        report["context_resolution_credit"] = self.context_credit_snapshot.as_dict()
        report["context_resolution_arm"] = report.pop("calibrated_resolution_arm")
        status = report["comparisons"].pop("calibrated_resolution_improvement_status")
        actual = report["disagreement_resolution_outcome_receipt"]
        report["comparisons"].update({
            "context_witness_items": sum(item["context_witness_used"] for item in decisions),
            "context_peer_overrides": sum(item["resolution_policy"] == "CONTEXT_PEER_OVERRIDE" for item in decisions),
            "context_primary_keeps": sum(item["resolution_policy"] == "CONTEXT_KEEP_PRIMARY" for item in decisions),
            "context_positive_heldout_net_cbit": actual["observed_net_cbit"] > 0.0,
            "context_resolution_improvement_status": status,
        })
        return report
