"""Budgeted one-peer probes for uncertain structural task fingerprints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .calibrated_policy import CalibratedCandidateSignal, CalibratedModelPlan, CostAwareReviewPolicy
from .hierarchical_fingerprint_credit import HierarchicalFingerprintProfile
from .routing_calibration import ReviewerValueLedger


@dataclass(frozen=True)
class StructuralProbeDecision:
    item_id: str
    primary_model_id: str
    reviewer_model_id: str
    action: str
    primary_utility: float
    expected_correction: float
    expected_harm: float
    expected_net_cbit: float
    reviewer_cost_ratio: float
    marginal_cbit_per_cost: float
    primary_answer: str
    reason: str
    final_answer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class StructuralMicroProbePolicy:
    def __init__(
        self,
        *,
        profiles: dict[str, HierarchicalFingerprintProfile],
        probe_schedule: dict[str, str],
    ) -> None:
        if not set(probe_schedule.values()).issubset(profiles):
            raise ValueError("structural_probe_profile_binding_invalid")
        self.profiles = dict(profiles)
        self.probe_schedule = dict(probe_schedule)
        self.base = CostAwareReviewPolicy()

    def select_primary(self, plans: tuple[CalibratedModelPlan, ...]) -> CalibratedModelPlan:
        return self.base.select_primary(plans)

    def route(
        self,
        primary: CalibratedCandidateSignal,
        *,
        plans: tuple[CalibratedModelPlan, ...],
        domain: str,
        reviewer_ledger: ReviewerValueLedger,
    ) -> StructuralProbeDecision:
        del domain, reviewer_ledger
        plan_by_model = {item.model_id: item for item in plans}
        if primary.model_id not in plan_by_model:
            raise ValueError("structural_probe_primary_binding_invalid")
        minimum_work = min(item.expected_work for item in plans)
        primary_utility = self.base._primary_utility(plan_by_model[primary.model_id], minimum_work)
        peer_model_id = self.probe_schedule.get(primary.item_id, "")
        common = {
            "item_id": primary.item_id,
            "primary_model_id": primary.model_id,
            "primary_utility": primary_utility,
            "primary_answer": primary.answer,
        }
        if not peer_model_id or peer_model_id == primary.model_id:
            return StructuralProbeDecision(
                **common, reviewer_model_id="", action="STOP_FINGERPRINT_ROUTE",
                expected_correction=0.0, expected_harm=0.0, expected_net_cbit=0.0,
                reviewer_cost_ratio=0.0, marginal_cbit_per_cost=0.0,
                reason="fingerprint_route_has_no_budgeted_probe", final_answer=primary.answer,
            )
        peer = plan_by_model[peer_model_id]
        correction = (1.0 - primary.calibrated_success) * peer.predicted_success
        harm = primary.calibrated_success * (1.0 - peer.predicted_success)
        expected_net = correction - harm
        cost_ratio = peer.expected_work / minimum_work
        return StructuralProbeDecision(
            **common, reviewer_model_id=peer_model_id, action="MICRO_PROBE",
            expected_correction=round(correction, 12), expected_harm=round(harm, 12),
            expected_net_cbit=round(expected_net, 12), reviewer_cost_ratio=round(cost_ratio, 12),
            marginal_cbit_per_cost=round(expected_net / cost_ratio, 12),
            reason="historically_close_low_evidence_fingerprint_probe",
        )

    @staticmethod
    def resolve_probe(
        decision: StructuralProbeDecision,
        primary: CalibratedCandidateSignal,
        peer: CalibratedCandidateSignal,
    ) -> StructuralProbeDecision:
        if decision.action != "MICRO_PROBE" or decision.primary_model_id != primary.model_id or decision.reviewer_model_id != peer.model_id:
            raise ValueError("structural_probe_resolution_binding_invalid")
        if primary.answer == peer.answer:
            answer, reason = primary.answer, "micro_probe_agreement"
        elif peer.calibrated_success > primary.calibrated_success:
            answer, reason = peer.answer, "micro_probe_contextual_override"
        else:
            answer, reason = primary.answer, "micro_probe_primary_survived"
        return StructuralProbeDecision(
            **{**decision.__dict__, "action": "MICRO_PROBE_RESOLVED", "reason": reason, "final_answer": answer}
        )
