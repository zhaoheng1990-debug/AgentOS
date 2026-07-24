"""Protocol v0.10: independent post-disagreement resolution lifecycle."""

from __future__ import annotations

from typing import Any

from .disagreement_resolution_lifecycle import (
    ResolutionCreditSnapshot,
    ResolutionEvidenceCandidate,
    ResolutionPromotionReceipt,
)
from .disagreement_resolution_receipt import DisagreementResolutionEvidenceReceipt
from .hierarchical_fingerprint_credit import HierarchicalFingerprintProfile
from .holdout_v8_benchmark import (
    HOLDOUT_V8_BENCHMARK_ID,
    HOLDOUT_V8_ITEM_DOMAINS,
    HOLDOUT_V8_ITEM_FINGERPRINTS,
)
from .independent_resolution_policy import IndependentDisagreementResolutionPolicy
from .structural_operator_credit import StructuralOperatorCreditSnapshot
from .structural_operator_protocol import StructuralOperatorCompetitionProtocol
from .structural_operator_receipt import StructuralOperatorEvidenceReceipt


INDEPENDENT_RESOLUTION_PROTOCOL_VERSION = "independent_disagreement_resolution_protocol_v0_10"


class IndependentDisagreementResolutionProtocol(StructuralOperatorCompetitionProtocol):
    def __init__(
        self,
        *,
        profiles: dict[str, HierarchicalFingerprintProfile],
        fingerprint_credit_snapshot: dict[str, Any],
        operator_evidence_receipt: StructuralOperatorEvidenceReceipt,
        operator_credit_snapshot: StructuralOperatorCreditSnapshot,
        operator_schedule: dict[str, str],
        resolution_evidence_receipt: DisagreementResolutionEvidenceReceipt,
        resolution_candidate: ResolutionEvidenceCandidate,
        resolution_promotion: ResolutionPromotionReceipt,
        resolution_credit_snapshot: ResolutionCreditSnapshot,
        **values: Any,
    ) -> None:
        if "policy" not in values:
            values["policy"] = IndependentDisagreementResolutionPolicy(
                operator_credit=operator_credit_snapshot,
                operator_schedule=operator_schedule,
                item_fingerprints=HOLDOUT_V8_ITEM_FINGERPRINTS,
                resolution_credit=resolution_credit_snapshot,
            )
        values.setdefault("item_domains", HOLDOUT_V8_ITEM_DOMAINS)
        values.setdefault("item_contexts", HOLDOUT_V8_ITEM_FINGERPRINTS)
        values.setdefault("arm_namespace", "HOLDOUT_V8")
        super().__init__(
            profiles=profiles,
            fingerprint_credit_snapshot=fingerprint_credit_snapshot,
            operator_evidence_receipt=operator_evidence_receipt,
            operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule,
            **values,
        )
        self.resolution_evidence_receipt = resolution_evidence_receipt
        self.resolution_candidate = resolution_candidate
        self.resolution_promotion = resolution_promotion
        self.resolution_credit_snapshot = resolution_credit_snapshot

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        decisions = tuple(report["route_decisions"])
        outcome = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-resolution-outcome",
            calibration_receipt_hash=self.resolution_credit_snapshot.snapshot_hash,
            route_decisions=decisions,
            item_domains=self.item_contexts,
            resolved_actions=("PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED"),
        )
        report["protocol"].pop("v08_operator_outcomes_used_for_v09_route", None)
        report["protocol"].pop("v09_outcomes_used_for_current_route", None)
        report["protocol"].update({
            "protocol_version": INDEPENDENT_RESOLUTION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V8_BENCHMARK_ID,
            "resolution_evidence_receipt_ref": self.resolution_evidence_receipt.receipt_hash,
            "resolution_credit_snapshot_ref": self.resolution_credit_snapshot.snapshot_hash,
            "v09_resolution_outcomes_used_for_v10_route": True,
            "v08_operator_outcomes_used_for_v10_acquisition_route": True,
            "v09_peer_answers_used_only_via_promoted_resolution_evidence": True,
            "v10_outcomes_used_for_current_route": False,
            "independent_disagreement_resolver": True,
            "primary_selection_credit_used_for_resolution": False,
            "resolution_promotion_required": True,
        })
        report["disagreement_resolution_evidence"] = self.resolution_evidence_receipt.as_dict()
        report["resolution_evidence_candidate"] = self.resolution_candidate.as_dict()
        report["resolution_promotion_receipt"] = self.resolution_promotion.as_dict()
        report["disagreement_resolution_credit"] = self.resolution_credit_snapshot.as_dict()
        report["disagreement_resolution_outcome_receipt"] = outcome.as_dict()
        report["resolution_lifecycle_arm"] = report.pop("structural_operator_arm")
        improvement_status = report["comparisons"].pop("structural_operator_improvement_status")
        report["comparisons"].update({
            "resolution_overrides": sum(item["action"] == "PEER_OVERRIDE_RESOLVED" for item in decisions),
            "resolution_primary_keeps": sum(item["action"] == "PRIMARY_KEEP_RESOLVED" for item in decisions),
            "resolution_corrections": outcome.corrected_count,
            "resolution_harms": outcome.harmed_count,
            "resolution_observed_net_cbit": outcome.observed_net_cbit,
            "resolution_lifecycle_improvement_status": improvement_status,
        })
        return report
