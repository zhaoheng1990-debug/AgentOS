"""Conservative reviewer activation using observed support and confidence bounds."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any

from .calibrated_policy import CalibratedCandidateSignal, CalibratedModelPlan, CostAwareReviewPolicy
from .routing_calibration import ReviewerValueLedger


def _wilson_bounds(successes: int, total: int, z: float) -> tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    probability = successes / total
    denominator = 1.0 + z * z / total
    center = (probability + z * z / (2.0 * total)) / denominator
    margin = z * sqrt(probability * (1.0 - probability) / total + z * z / (4.0 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


@dataclass(frozen=True)
class EvidenceGatedRouteDecision:
    item_id: str
    primary_model_id: str
    reviewer_model_id: str
    candidate_reviewer_model_id: str
    action: str
    primary_utility: float
    expected_correction: float
    expected_harm: float
    expected_net_cbit: float
    reviewer_cost_ratio: float
    marginal_cbit_per_cost: float
    observed_support_surplus: int
    correction_lower_bound: float
    harm_upper_bound: float
    conservative_net_cbit: float
    conservative_marginal_cbit_per_cost: float
    evidence_eligible: bool
    primary_answer: str
    reason: str
    final_answer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class EvidenceSupportedReviewPolicy:
    def __init__(
        self,
        *,
        confidence_threshold: float = 0.72,
        minimum_corrections: int = 1,
        minimum_correction_opportunities: int = 2,
        minimum_conservative_marginal: float = 0.02,
        confidence_z: float = 1.281551565545,
        override_harm_weight: float = 0.5,
    ) -> None:
        self.base = CostAwareReviewPolicy(confidence_threshold=confidence_threshold)
        self.confidence_threshold = confidence_threshold
        self.minimum_corrections = minimum_corrections
        self.minimum_correction_opportunities = minimum_correction_opportunities
        self.minimum_conservative_marginal = minimum_conservative_marginal
        self.confidence_z = confidence_z
        self.override_harm_weight = override_harm_weight

    def select_primary(self, plans: tuple[CalibratedModelPlan, ...]) -> CalibratedModelPlan:
        return self.base.select_primary(plans)

    def route(
        self,
        primary: CalibratedCandidateSignal,
        *,
        plans: tuple[CalibratedModelPlan, ...],
        domain: str,
        reviewer_ledger: ReviewerValueLedger,
    ) -> EvidenceGatedRouteDecision:
        if len(plans) < 2 or primary.model_id not in {item.model_id for item in plans}:
            raise ValueError("evidence_route_plan_binding_invalid")
        minimum_work = min(item.expected_work for item in plans)
        primary_plan = next(item for item in plans if item.model_id == primary.model_id)
        primary_utility = self.base._primary_utility(primary_plan, minimum_work)
        if primary.had_structured_retry:
            primary_utility = round(primary_utility - self.base.retry_penalty, 12)
        candidates = []
        for reviewer in plans:
            if reviewer.model_id == primary.model_id:
                continue
            value = reviewer_ledger.get(primary.model_id, reviewer.model_id, domain)
            correction_lower, _ = _wilson_bounds(value.corrections, value.correction_opportunities, self.confidence_z)
            _, harm_upper = _wilson_bounds(value.harms, value.harm_opportunities, self.confidence_z)
            expected_correction = (1.0 - primary.calibrated_success) * value.correction_posterior
            expected_harm = primary.calibrated_success * value.harm_posterior * self.override_harm_weight
            expected_net = expected_correction - expected_harm
            conservative_net = (
                (1.0 - primary.calibrated_success) * correction_lower
                - primary.calibrated_success * harm_upper * self.override_harm_weight
            )
            cost_ratio = reviewer.expected_work / minimum_work
            eligible = (
                value.corrections >= self.minimum_corrections
                and value.correction_opportunities >= self.minimum_correction_opportunities
                and value.corrections > value.harms
                and conservative_net > 0.0
            )
            candidates.append({
                "reviewer": reviewer,
                "value": value,
                "expected_correction": expected_correction,
                "expected_harm": expected_harm,
                "expected_net": expected_net,
                "cost_ratio": cost_ratio,
                "marginal": expected_net / cost_ratio,
                "correction_lower": correction_lower,
                "harm_upper": harm_upper,
                "conservative_net": conservative_net,
                "conservative_marginal": conservative_net / cost_ratio,
                "eligible": eligible,
            })
        best = max(candidates, key=lambda item: (item["conservative_marginal"], item["reviewer"].model_id))
        common = self._common(primary, primary_utility, best)
        if primary.calibrated_success >= self.confidence_threshold and not primary.had_structured_retry:
            return EvidenceGatedRouteDecision(
                **common, reviewer_model_id="", action="STOP_CALIBRATED_CONFIDENT",
                reason="calibrated_primary_clears_confidence_gate", final_answer=primary.answer,
            )
        if not best["eligible"] or best["conservative_marginal"] < self.minimum_conservative_marginal:
            return EvidenceGatedRouteDecision(
                **common, reviewer_model_id="", action="STOP_REVIEW_EVIDENCE_UNSUPPORTED",
                reason="review_pair_lacks_positive_confidence_bounded_support", final_answer=primary.answer,
            )
        return EvidenceGatedRouteDecision(
            **common, reviewer_model_id=best["reviewer"].model_id, action="REVIEW",
            reason="review_pair_clears_evidence_and_cost_gates",
        )

    @staticmethod
    def resolve(
        decision: EvidenceGatedRouteDecision,
        primary: CalibratedCandidateSignal,
        reviewer: CalibratedCandidateSignal,
        *,
        domain: str,
        reviewer_ledger: ReviewerValueLedger,
    ) -> EvidenceGatedRouteDecision:
        if decision.action != "REVIEW" or decision.primary_model_id != primary.model_id or decision.reviewer_model_id != reviewer.model_id:
            raise ValueError("evidence_review_binding_invalid")
        if primary.answer == reviewer.answer:
            answer, reason = primary.answer, "independent_review_agreement"
        else:
            value = reviewer_ledger.get(primary.model_id, reviewer.model_id, domain)
            primary_weight = primary.calibrated_success + 0.10 * (1.0 - value.harm_posterior)
            reviewer_weight = reviewer.calibrated_success + 0.25 * value.correction_posterior - 0.20 * value.harm_posterior
            answer = reviewer.answer if reviewer_weight > primary_weight else primary.answer
            reason = "evidence_supported_reviewer_override" if answer == reviewer.answer else "calibrated_primary_survived_review"
        return EvidenceGatedRouteDecision(**{**decision.__dict__, "action": "REVIEW_RESOLVED", "reason": reason, "final_answer": answer})

    @staticmethod
    def _common(primary: CalibratedCandidateSignal, primary_utility: float, candidate: dict[str, Any]) -> dict[str, Any]:
        value = candidate["value"]
        return {
            "item_id": primary.item_id,
            "primary_model_id": primary.model_id,
            "candidate_reviewer_model_id": candidate["reviewer"].model_id,
            "primary_utility": primary_utility,
            "expected_correction": round(candidate["expected_correction"], 12),
            "expected_harm": round(candidate["expected_harm"], 12),
            "expected_net_cbit": round(candidate["expected_net"], 12),
            "reviewer_cost_ratio": round(candidate["cost_ratio"], 12),
            "marginal_cbit_per_cost": round(candidate["marginal"], 12),
            "observed_support_surplus": value.corrections - value.harms,
            "correction_lower_bound": round(candidate["correction_lower"], 12),
            "harm_upper_bound": round(candidate["harm_upper"], 12),
            "conservative_net_cbit": round(candidate["conservative_net"], 12),
            "conservative_marginal_cbit_per_cost": round(candidate["conservative_marginal"], 12),
            "evidence_eligible": bool(candidate["eligible"]),
            "primary_answer": primary.answer,
        }
