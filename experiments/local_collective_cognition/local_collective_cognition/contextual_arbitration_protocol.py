"""Protocol v0.7: selective majority arbitration under lifecycle credit."""

from __future__ import annotations

from typing import Any

from .contextual_arbitration_policy import ContextualDisagreementPolicy
from .disagreement_outcome import DisagreementOperatorReceipt
from .holdout_v5_benchmark import HOLDOUT_V5_BENCHMARK_ID, HOLDOUT_V5_ITEM_DOMAINS
from .reliability_lifecycle_protocol import ReliabilityLifecycleCollaborationProtocol


CONTEXTUAL_ARBITRATION_PROTOCOL_VERSION = "contextual_disagreement_arbitration_protocol_v0_7"


class ContextualArbitrationProtocol(ReliabilityLifecycleCollaborationProtocol):
    def __init__(self, *, operator_receipt: DisagreementOperatorReceipt, **values: Any) -> None:
        values.setdefault("policy", ContextualDisagreementPolicy(operator_receipt=operator_receipt))
        values.setdefault("item_domains", HOLDOUT_V5_ITEM_DOMAINS)
        values.setdefault("arm_namespace", "HOLDOUT_V5")
        values.setdefault("exploration_schedule", {})
        super().__init__(**values)
        self.operator_receipt = operator_receipt

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        arbitration_outcome = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-majority-arbitration-outcome",
            calibration_receipt_hash=self.operator_receipt.receipt_hash,
            route_decisions=tuple(report["route_decisions"]),
            item_domains=self.item_domains,
            resolved_actions=("MAJORITY_RESOLVED",),
        )
        report["protocol"].update({
            "protocol_version": CONTEXTUAL_ARBITRATION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V5_BENCHMARK_ID,
            "operator_receipt_ref": self.operator_receipt.receipt_hash,
            "majority_operator_scope_bound": True,
            "v06_operator_outcome_used_for_v07_route": True,
            "v07_outcomes_used_for_current_route": False,
        })
        report["disagreement_operator_receipt"] = self.operator_receipt.as_dict()
        report["arbitration_outcome_receipt"] = arbitration_outcome.as_dict()
        report["contextual_arbitration_arm"] = report.pop("reliability_lifecycle_arm")
        report["comparisons"]["arbitration_corrections"] = arbitration_outcome.corrected_count
        report["comparisons"]["arbitration_harms"] = arbitration_outcome.harmed_count
        report["comparisons"]["arbitration_observed_net_cbit"] = arbitration_outcome.observed_net_cbit
        report["comparisons"]["contextual_arbitration_improvement_status"] = report["comparisons"].pop(
            "reliability_lifecycle_improvement_status"
        )
        return report
