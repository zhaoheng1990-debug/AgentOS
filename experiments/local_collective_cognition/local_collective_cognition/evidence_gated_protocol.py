"""Protocol v0.5: confidence-bounded reviewer activation on holdout v3."""

from __future__ import annotations

from typing import Any

from .calibrated_protocol import CalibratedCollaborationProtocol
from .evidence_gated_policy import EvidenceSupportedReviewPolicy
from .holdout_v3_benchmark import HOLDOUT_V3_BENCHMARK_ID, HOLDOUT_V3_ITEM_DOMAINS


EVIDENCE_GATED_PROTOCOL_VERSION = "evidence_gated_collaboration_protocol_v0_5"


class EvidenceGatedCollaborationProtocol(CalibratedCollaborationProtocol):
    def __init__(self, **values: Any) -> None:
        values.setdefault("policy", EvidenceSupportedReviewPolicy())
        values.setdefault("item_domains", HOLDOUT_V3_ITEM_DOMAINS)
        values.setdefault("arm_namespace", "HOLDOUT_V3")
        super().__init__(**values)

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": EVIDENCE_GATED_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V3_BENCHMARK_ID,
            "review_activation_rule": "positive_observed_surplus_and_positive_wilson_bounded_net_cbit",
            "v04_holdout_used_for_policy_tuning": False,
            "posthoc_diagnostics_used_for_current_route": False,
        })
        diagnostics = []
        for arm in report["solo_arms"]:
            candidate = {
                "answers": [
                    {"item_id": item_id, "answer": answer}
                    for item_id, answer in arm["answer_vector"].items()
                ],
                "evidence_refs": list(self.base.harness.evidence_refs),
            }
            diagnostics.append(self.base.harness.calibrate_reliability(
                calibration_id=experiment_id + "-posthoc-domain-diagnostic",
                model_id=arm["model_ids"][0],
                candidate_output=candidate,
                item_domains=self.item_domains,
                source_harness_receipt_hash=arm["harness_receipt_hash"],
            ).as_dict())
        report["posthoc_domain_diagnostics"] = {
            "candidate_only": True,
            "routing_authority": False,
            "receipts": diagnostics,
        }
        report["evidence_gated_arm"] = report.pop("calibrated_arm")
        report["comparisons"]["evidence_unsupported_items"] = sum(
            item["action"] == "STOP_REVIEW_EVIDENCE_UNSUPPORTED"
            for item in report["route_decisions"]
        )
        report["comparisons"]["evidence_eligible_items"] = sum(
            bool(item.get("evidence_eligible"))
            for item in report["route_decisions"]
        )
        report["comparisons"]["evidence_gated_improvement_status"] = report["comparisons"].pop(
            "calibrated_improvement_status"
        )
        return report
