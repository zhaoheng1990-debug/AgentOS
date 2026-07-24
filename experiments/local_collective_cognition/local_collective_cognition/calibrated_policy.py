"""Cost-aware review routing over calibrated advisory signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .routing_calibration import ReviewerValueLedger


@dataclass(frozen=True)
class CalibratedModelPlan:
    model_id: str
    predicted_success: float
    expected_work: float


@dataclass(frozen=True)
class CalibratedCandidateSignal:
    model_id: str
    item_id: str
    answer: str
    raw_confidence: float
    calibrated_success: float
    expected_work: float
    had_structured_retry: bool = False


@dataclass(frozen=True)
class CalibratedRouteDecision:
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


class CostAwareReviewPolicy:
    def __init__(
        self,
        *,
        confidence_threshold: float = 0.72,
        minimum_marginal_cbit_per_cost: float = 0.06,
        primary_cost_weight: float = 0.04,
        retry_penalty: float = 0.04,
        override_harm_weight: float = 0.5,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.minimum_marginal_cbit_per_cost = minimum_marginal_cbit_per_cost
        self.primary_cost_weight = primary_cost_weight
        self.retry_penalty = retry_penalty
        self.override_harm_weight = override_harm_weight

    def select_primary(self, plans: tuple[CalibratedModelPlan, ...]) -> CalibratedModelPlan:
        if len(plans) < 2 or len({item.model_id for item in plans}) != len(plans):
            raise ValueError("calibrated_model_plans_invalid")
        minimum_work = min(item.expected_work for item in plans)
        return max(plans, key=lambda item: (self._primary_utility(item, minimum_work), item.model_id))

    def route(
        self,
        primary: CalibratedCandidateSignal,
        *,
        plans: tuple[CalibratedModelPlan, ...],
        domain: str,
        reviewer_ledger: ReviewerValueLedger,
    ) -> CalibratedRouteDecision:
        if len(plans) < 2 or primary.model_id not in {item.model_id for item in plans}:
            raise ValueError("calibrated_route_plan_binding_invalid")
        minimum_work = min(item.expected_work for item in plans)
        primary_plan = next(item for item in plans if item.model_id == primary.model_id)
        primary_utility = self._primary_utility(primary_plan, minimum_work)
        if primary.had_structured_retry:
            primary_utility = round(primary_utility - self.retry_penalty, 12)
        candidates = []
        for reviewer in plans:
            if reviewer.model_id == primary.model_id:
                continue
            value = reviewer_ledger.get(primary.model_id, reviewer.model_id, domain)
            expected_correction = (1.0 - primary.calibrated_success) * value.correction_posterior
            expected_harm = primary.calibrated_success * value.harm_posterior * self.override_harm_weight
            expected_net = expected_correction - expected_harm
            cost_ratio = reviewer.expected_work / minimum_work
            marginal = expected_net / cost_ratio
            candidates.append((marginal, expected_net, reviewer, expected_correction, expected_harm, cost_ratio))
        marginal, expected_net, reviewer, correction, harm, cost_ratio = max(candidates, key=lambda item: (item[0], item[2].model_id))
        common = {
            "item_id": primary.item_id,
            "primary_model_id": primary.model_id,
            "primary_utility": primary_utility,
            "expected_correction": round(correction, 12),
            "expected_harm": round(harm, 12),
            "expected_net_cbit": round(expected_net, 12),
            "reviewer_cost_ratio": round(cost_ratio, 12),
            "marginal_cbit_per_cost": round(marginal, 12),
            "primary_answer": primary.answer,
        }
        if primary.calibrated_success >= self.confidence_threshold and not primary.had_structured_retry:
            return CalibratedRouteDecision(
                **common, reviewer_model_id="", action="STOP_CALIBRATED_CONFIDENT",
                reason="calibrated_primary_clears_confidence_gate", final_answer=primary.answer,
            )
        if marginal < self.minimum_marginal_cbit_per_cost:
            return CalibratedRouteDecision(
                **common, reviewer_model_id="", action="STOP_LOW_VALUE_PER_COST",
                reason="review_marginal_cbit_per_cost_below_floor", final_answer=primary.answer,
            )
        return CalibratedRouteDecision(
            **common, reviewer_model_id=reviewer.model_id, action="REVIEW",
            reason="reviewer_value_clears_cost_adjusted_gate",
        )

    def _primary_utility(self, plan: CalibratedModelPlan, minimum_work: float) -> float:
        cost_ratio = plan.expected_work / minimum_work
        return round(plan.predicted_success - self.primary_cost_weight * (cost_ratio - 1.0), 12)

    @staticmethod
    def resolve(
        decision: CalibratedRouteDecision,
        primary: CalibratedCandidateSignal,
        reviewer: CalibratedCandidateSignal,
        *,
        domain: str,
        reviewer_ledger: ReviewerValueLedger,
    ) -> CalibratedRouteDecision:
        if decision.action != "REVIEW" or decision.primary_model_id != primary.model_id or decision.reviewer_model_id != reviewer.model_id:
            raise ValueError("calibrated_review_binding_invalid")
        if primary.answer == reviewer.answer:
            answer, reason = primary.answer, "independent_review_agreement"
        else:
            value = reviewer_ledger.get(primary.model_id, reviewer.model_id, domain)
            primary_weight = primary.calibrated_success + 0.10 * (1.0 - value.harm_posterior)
            reviewer_weight = reviewer.calibrated_success + 0.25 * value.correction_posterior - 0.20 * value.harm_posterior
            answer = reviewer.answer if reviewer_weight > primary_weight else primary.answer
            reason = "calibrated_reviewer_override" if answer == reviewer.answer else "calibrated_primary_survived_review"
        return CalibratedRouteDecision(
            **{
                **decision.__dict__,
                "action": "REVIEW_RESOLVED",
                "reason": reason,
                "final_answer": answer,
            }
        )
