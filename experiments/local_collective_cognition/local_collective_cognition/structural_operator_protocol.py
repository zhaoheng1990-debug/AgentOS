"""Protocol v0.9: structural stop, peer, and majority operator competition."""

from __future__ import annotations

from typing import Any

from .calibrated_protocol import CalibratedCollaborationProtocol
from .hierarchical_fingerprint_credit import HierarchicalFingerprintProfile
from .holdout_v7_benchmark import (
    HOLDOUT_V7_BENCHMARK_ID,
    HOLDOUT_V7_ITEM_DOMAINS,
    HOLDOUT_V7_ITEM_FINGERPRINTS,
)
from .structural_operator_credit import StructuralOperatorCreditSnapshot
from .structural_operator_policy import StructuralOperatorCompetitionPolicy
from .structural_operator_receipt import StructuralOperatorEvidenceReceipt


STRUCTURAL_OPERATOR_PROTOCOL_VERSION = "structural_operator_competition_protocol_v0_9"


class StructuralOperatorCompetitionProtocol(CalibratedCollaborationProtocol):
    def __init__(
        self,
        *,
        profiles: dict[str, HierarchicalFingerprintProfile],
        fingerprint_credit_snapshot: dict[str, Any],
        operator_evidence_receipt: StructuralOperatorEvidenceReceipt,
        operator_credit_snapshot: StructuralOperatorCreditSnapshot,
        operator_schedule: dict[str, str],
        **values: Any,
    ) -> None:
        if "policy" not in values:
            values["policy"] = StructuralOperatorCompetitionPolicy(
                operator_credit=operator_credit_snapshot,
                operator_schedule=operator_schedule,
                item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
            )
        values.setdefault("item_domains", HOLDOUT_V7_ITEM_DOMAINS)
        values.setdefault("item_contexts", HOLDOUT_V7_ITEM_FINGERPRINTS)
        values.setdefault("arm_namespace", "HOLDOUT_V7")
        values.setdefault("profile_receipt_hash", fingerprint_credit_snapshot.get("snapshot_hash", ""))
        values.setdefault("exploration_schedule", {})
        super().__init__(profiles=profiles, **values)
        self.fingerprint_credit_snapshot = fingerprint_credit_snapshot
        self.operator_evidence_receipt = operator_evidence_receipt
        self.operator_credit_snapshot = operator_credit_snapshot
        self.operator_schedule = dict(operator_schedule)

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        decisions = tuple(report["route_decisions"])
        peer_outcome = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-peer-outcome",
            calibration_receipt_hash=self.operator_credit_snapshot.snapshot_hash,
            route_decisions=decisions, item_domains=self.item_contexts,
            resolved_actions=("PEER_VERIFICATION_RESOLVED", "PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED"),
        )
        majority_outcome = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-majority-outcome",
            calibration_receipt_hash=self.operator_credit_snapshot.snapshot_hash,
            route_decisions=decisions, item_domains=self.item_contexts,
            resolved_actions=("MAJORITY_RESOLVED",),
        )
        solo_answers = {
            item["model_ids"][0]: item["answer_vector"]
            for item in report["solo_arms"] if len(item["model_ids"]) == 1
        }
        peer_override_decisions = tuple(
            {
                **item,
                "action": "PEER_OVERRIDE_COUNTERFACTUAL",
                "final_answer": solo_answers[item["reviewer_model_id"]][item["item_id"]],
            }
            if item["action"] in {"PEER_VERIFICATION_RESOLVED", "PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED"} else item
            for item in report["route_decisions"]
        )
        peer_override_counterfactual = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-peer-override-counterfactual",
            calibration_receipt_hash=self.operator_credit_snapshot.snapshot_hash,
            route_decisions=peer_override_decisions, item_domains=self.item_contexts,
            resolved_actions=("PEER_OVERRIDE_COUNTERFACTUAL",),
        )
        report["protocol"].update({
            "protocol_version": STRUCTURAL_OPERATOR_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V7_BENCHMARK_ID,
            "fingerprint_credit_snapshot_ref": self.fingerprint_credit_snapshot["snapshot_hash"],
            "operator_evidence_receipt_ref": self.operator_evidence_receipt.receipt_hash,
            "operator_credit_snapshot_ref": self.operator_credit_snapshot.snapshot_hash,
            "v08_operator_outcomes_used_for_v09_route": True,
            "v09_outcomes_used_for_current_route": False,
            "peer_override_counterfactual_used_for_current_answer": False,
            "immediate_and_future_cbit_separated": True,
            "operator_schedule_frozen_before_current_outputs": True,
        })
        report["hierarchical_fingerprint_credit"] = self.fingerprint_credit_snapshot
        report["structural_operator_evidence"] = self.operator_evidence_receipt.as_dict()
        report["structural_operator_credit"] = self.operator_credit_snapshot.as_dict()
        report["operator_schedule"] = self.operator_schedule
        report["peer_verification_outcome_receipt"] = peer_outcome.as_dict()
        report["majority_operator_outcome_receipt"] = majority_outcome.as_dict()
        report["peer_override_counterfactual_receipt"] = peer_override_counterfactual.as_dict()
        report["structural_operator_arm"] = report.pop("calibrated_arm")
        report["comparisons"].update({
            "peer_corrections": peer_outcome.corrected_count,
            "peer_harms": peer_outcome.harmed_count,
            "peer_observed_net_cbit": peer_outcome.observed_net_cbit,
            "peer_override_counterfactual_corrections": peer_override_counterfactual.corrected_count,
            "peer_override_counterfactual_harms": peer_override_counterfactual.harmed_count,
            "peer_override_counterfactual_net_cbit": peer_override_counterfactual.observed_net_cbit,
            "majority_corrections": majority_outcome.corrected_count,
            "majority_harms": majority_outcome.harmed_count,
            "majority_observed_net_cbit": majority_outcome.observed_net_cbit,
            "scheduled_paid_operators": len(self.operator_schedule),
            "runtime_utility_stops": sum(item["action"] == "STOP_RUNTIME_OPERATOR_UTILITY" for item in report["route_decisions"]),
            "structural_operator_improvement_status": report["comparisons"].pop("calibrated_improvement_status"),
        })
        return report
