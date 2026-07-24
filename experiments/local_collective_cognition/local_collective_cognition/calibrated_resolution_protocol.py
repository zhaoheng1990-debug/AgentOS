"""Protocol v0.11: multi-cycle resolver calibration with bounded exploration."""

from __future__ import annotations

from typing import Any

from .holdout_v9_benchmark import (
    HOLDOUT_V9_BENCHMARK_ID,
    HOLDOUT_V9_ITEM_DOMAINS,
    HOLDOUT_V9_ITEM_FINGERPRINTS,
)
from .independent_resolution_protocol import IndependentDisagreementResolutionProtocol
from .resolution_exploration_policy import ResolutionExplorationPolicy


CALIBRATED_RESOLUTION_PROTOCOL_VERSION = "multi_cycle_resolution_calibration_protocol_v0_11"


class CalibratedResolutionProtocol(IndependentDisagreementResolutionProtocol):
    def __init__(
        self,
        *,
        resolution_evidence_receipts,
        resolution_candidates,
        resolution_promotions,
        resolution_credit_snapshot,
        acquisition_schedule: dict[str, str],
        resolution_exploration_schedule: dict[str, str],
        operator_credit_snapshot,
        operator_schedule: dict[str, str],
        **values: Any,
    ) -> None:
        if len(resolution_evidence_receipts) < 2 or not (
            len(resolution_evidence_receipts) == len(resolution_candidates) == len(resolution_promotions)
        ):
            raise ValueError("calibrated_resolution_cycle_coverage_invalid")
        if set(acquisition_schedule) & set(resolution_exploration_schedule):
            raise ValueError("calibrated_resolution_schedule_overlap")
        if {**acquisition_schedule, **resolution_exploration_schedule} != operator_schedule:
            raise ValueError("calibrated_resolution_schedule_binding_invalid")
        if "policy" not in values:
            values["policy"] = ResolutionExplorationPolicy(
                operator_credit=operator_credit_snapshot,
                operator_schedule=operator_schedule,
                item_fingerprints=HOLDOUT_V9_ITEM_FINGERPRINTS,
                resolution_credit=resolution_credit_snapshot,
                exploration_items=tuple(resolution_exploration_schedule),
            )
        values.setdefault("item_domains", HOLDOUT_V9_ITEM_DOMAINS)
        values.setdefault("item_contexts", HOLDOUT_V9_ITEM_FINGERPRINTS)
        values.setdefault("arm_namespace", "HOLDOUT_V9")
        super().__init__(
            operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule,
            resolution_evidence_receipt=resolution_evidence_receipts[-1],
            resolution_candidate=resolution_candidates[-1],
            resolution_promotion=resolution_promotions[-1],
            resolution_credit_snapshot=resolution_credit_snapshot,
            **values,
        )
        self.resolution_evidence_receipts = tuple(resolution_evidence_receipts)
        self.resolution_candidates = tuple(resolution_candidates)
        self.resolution_promotions = tuple(resolution_promotions)
        self.acquisition_schedule = dict(acquisition_schedule)
        self.resolution_exploration_schedule = dict(resolution_exploration_schedule)

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        decisions = tuple(report["route_decisions"])
        for key in (
            "v09_resolution_outcomes_used_for_v10_route",
            "v08_operator_outcomes_used_for_v10_acquisition_route",
            "v09_peer_answers_used_only_via_promoted_resolution_evidence",
            "v10_outcomes_used_for_current_route",
            "resolution_evidence_receipt_ref",
        ):
            report["protocol"].pop(key, None)
        credit = self.resolution_credit_snapshot
        report["protocol"].update({
            "protocol_version": CALIBRATED_RESOLUTION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V9_BENCHMARK_ID,
            "resolution_evidence_receipt_refs": list(credit.source_receipt_hashes),
            "v09_v10_resolution_outcomes_used_for_v11_route": True,
            "v08_operator_outcomes_used_for_v11_acquisition_route": True,
            "v11_outcomes_used_for_current_route": False,
            "resolver_prediction_count": credit.prediction_count,
            "resolver_prediction_mean_absolute_error": credit.mean_absolute_error,
            "resolution_exploration_budget": len(self.resolution_exploration_schedule),
            "current_exploration_outcomes_used_for_current_route": False,
        })
        report.pop("disagreement_resolution_evidence", None)
        report.pop("resolution_evidence_candidate", None)
        report.pop("resolution_promotion_receipt", None)
        report["disagreement_resolution_evidence_cycles"] = [
            item.as_dict() for item in self.resolution_evidence_receipts
        ]
        report["resolution_evidence_candidates"] = [item.as_dict() for item in self.resolution_candidates]
        report["resolution_promotion_receipts"] = [item.as_dict() for item in self.resolution_promotions]
        report["acquisition_schedule"] = self.acquisition_schedule
        report["resolution_exploration_schedule"] = self.resolution_exploration_schedule
        report["calibrated_resolution_arm"] = report.pop("resolution_lifecycle_arm")
        status = report["comparisons"].pop("resolution_lifecycle_improvement_status")
        counterfactual = report["peer_override_counterfactual_receipt"]
        actual = report["disagreement_resolution_outcome_receipt"]
        overrides = sum(item["action"] == "PEER_OVERRIDE_RESOLVED" for item in decisions)
        if actual["observed_net_cbit"] > 0.0:
            gate_status = "POSITIVE_HELDOUT_NET_CBIT"
        elif overrides == 0 and counterfactual["corrected_count"] > counterfactual["harmed_count"]:
            gate_status = "OVERCONSERVATIVE_MISSED_CORRECTION"
        elif overrides == 0 and counterfactual["harmed_count"] > counterfactual["corrected_count"]:
            gate_status = "SAFE_ABSTENTION_PREVENTED_HARM"
        else:
            gate_status = "INCONCLUSIVE_NO_RESOLUTION_EFFECT"
        report["comparisons"].update({
            "resolver_evidence_cycles": len(self.resolution_evidence_receipts),
            "resolver_prediction_count": credit.prediction_count,
            "resolver_prediction_mean_absolute_error": credit.mean_absolute_error,
            "scheduled_resolution_explorations": len(self.resolution_exploration_schedule),
            "executed_resolution_explorations": sum(item["resolution_exploration"] for item in decisions),
            "resolver_gate_status": gate_status,
            "resolver_missed_corrections": counterfactual["corrected_count"] if overrides == 0 else 0,
            "resolver_prevented_harms": counterfactual["harmed_count"] if overrides == 0 else 0,
            "calibrated_resolution_improvement_status": status,
        })
        return report
