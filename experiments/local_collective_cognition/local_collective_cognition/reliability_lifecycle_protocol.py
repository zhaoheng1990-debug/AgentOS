"""Protocol v0.6: promoted cross-cycle reliability with shadow exploration."""

from __future__ import annotations

from typing import Any

from .evidence_gated_protocol import EvidenceGatedCollaborationProtocol
from .holdout_v4_benchmark import HOLDOUT_V4_BENCHMARK_ID, HOLDOUT_V4_ITEM_DOMAINS
from .reliability_lifecycle import ReliabilityCycleCandidate, ReliabilityPromotionReceipt


RELIABILITY_LIFECYCLE_PROTOCOL_VERSION = "reliability_lifecycle_protocol_v0_6"


class ReliabilityLifecycleCollaborationProtocol(EvidenceGatedCollaborationProtocol):
    def __init__(
        self,
        *,
        lifecycle_snapshot: dict[str, Any],
        cycle_candidate: ReliabilityCycleCandidate,
        promotion_receipt: ReliabilityPromotionReceipt,
        **values: Any,
    ) -> None:
        snapshot_hash = lifecycle_snapshot.get("snapshot_hash", "")
        if promotion_receipt.cycle_candidate_hash != cycle_candidate.candidate_hash:
            raise ValueError("reliability_protocol_promotion_binding_invalid")
        values.setdefault("item_domains", HOLDOUT_V4_ITEM_DOMAINS)
        values.setdefault("arm_namespace", "HOLDOUT_V4")
        values.setdefault("profile_receipt_hash", snapshot_hash)
        super().__init__(**values)
        self.lifecycle_snapshot = dict(lifecycle_snapshot)
        self.cycle_candidate = cycle_candidate
        self.promotion_receipt = promotion_receipt

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": RELIABILITY_LIFECYCLE_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V4_BENCHMARK_ID,
            "reliability_lifecycle_snapshot_ref": self.lifecycle_snapshot["snapshot_hash"],
            "shadow_exploration_candidate_only": True,
            "v05_diagnostics_used_for_v06_route": True,
            "v06_diagnostics_used_for_current_route": False,
        })
        report["reliability_lifecycle"] = {
            "cycle_candidate": self.cycle_candidate.as_dict(),
            "promotion_receipt": self.promotion_receipt.as_dict(),
            "snapshot": self.lifecycle_snapshot,
        }
        report["reliability_lifecycle_arm"] = report.pop("evidence_gated_arm")
        report["comparisons"]["reliability_lifecycle_improvement_status"] = report["comparisons"].pop(
            "evidence_gated_improvement_status"
        )
        return report
