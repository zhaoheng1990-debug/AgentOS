"""Select majority arbitration only where historical net value clears cost."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .calibrated_policy import CalibratedCandidateSignal, CalibratedModelPlan, CostAwareReviewPolicy
from .disagreement_outcome import DisagreementOperatorReceipt
from .routing_calibration import ReviewerValueLedger


@dataclass(frozen=True)
class ContextualArbitrationDecision:
    item_id: str
    primary_model_id: str
    reviewer_model_id: str
    peer_model_ids: tuple[str, ...]
    action: str
    primary_utility: float
    expected_correction: float
    expected_harm: float
    expected_net_cbit: float
    expected_extra_calls: int
    marginal_cbit_per_cost: float
    observed_support_surplus: int
    historical_disagreements: int
    operator_eligible: bool
    primary_answer: str
    reason: str
    final_answer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "peer_model_ids": list(self.peer_model_ids)}


class ContextualDisagreementPolicy:
    def __init__(
        self,
        *,
        operator_receipt: DisagreementOperatorReceipt,
        minimum_marginal_cbit_per_cost: float = 0.03,
        confidence_stop_threshold: float = 0.78,
    ) -> None:
        self.operator_receipt = operator_receipt
        self.minimum_marginal_cbit_per_cost = minimum_marginal_cbit_per_cost
        self.confidence_stop_threshold = confidence_stop_threshold
        self.base = CostAwareReviewPolicy(confidence_threshold=confidence_stop_threshold)

    def select_primary(self, plans: tuple[CalibratedModelPlan, ...]) -> CalibratedModelPlan:
        return self.base.select_primary(plans)

    def route(
        self,
        primary: CalibratedCandidateSignal,
        *,
        plans: tuple[CalibratedModelPlan, ...],
        domain: str,
        reviewer_ledger: ReviewerValueLedger,
    ) -> ContextualArbitrationDecision:
        del reviewer_ledger
        if primary.model_id not in {item.model_id for item in plans}:
            raise ValueError("contextual_arbitration_primary_binding_invalid")
        record = next(item for item in self.operator_receipt.records if item.domain == domain)
        peer_plans = tuple(item for item in plans if item.model_id != primary.model_id)
        minimum_work = min(item.expected_work for item in plans)
        primary_plan = next(item for item in plans if item.model_id == primary.model_id)
        primary_utility = self.base._primary_utility(primary_plan, minimum_work)
        expected_correction = (1.0 - primary.calibrated_success) * record.correction_posterior
        expected_harm = primary.calibrated_success * record.harm_posterior
        expected_net = expected_correction - expected_harm
        cost_ratio = sum(item.expected_work for item in peer_plans) / minimum_work
        marginal = expected_net / cost_ratio
        eligible = (
            record.corrections > record.harms
            and record.correction_opportunities >= 1
            and record.disagreements >= 1
            and expected_net > 0.0
            and marginal >= self.minimum_marginal_cbit_per_cost
        )
        common = {
            "item_id": primary.item_id,
            "primary_model_id": primary.model_id,
            "reviewer_model_id": "MAJORITY_OPERATOR",
            "peer_model_ids": tuple(item.model_id for item in peer_plans),
            "primary_utility": round(primary_utility, 12),
            "expected_correction": round(expected_correction, 12),
            "expected_harm": round(expected_harm, 12),
            "expected_net_cbit": round(expected_net, 12),
            "expected_extra_calls": len(peer_plans),
            "marginal_cbit_per_cost": round(marginal, 12),
            "observed_support_surplus": record.corrections - record.harms,
            "historical_disagreements": record.disagreements,
            "operator_eligible": eligible,
            "primary_answer": primary.answer,
        }
        if primary.calibrated_success >= self.confidence_stop_threshold and not primary.had_structured_retry:
            return ContextualArbitrationDecision(
                **common, action="STOP_CONTEXT_CONFIDENT",
                reason="primary_confidence_blocks_extra_operator", final_answer=primary.answer,
            )
        if not eligible:
            return ContextualArbitrationDecision(
                **common, action="STOP_OPERATOR_LOW_VALUE",
                reason="majority_operator_lacks_contextual_net_support", final_answer=primary.answer,
            )
        return ContextualArbitrationDecision(
            **common, action="ARBITRATE_MAJORITY",
            reason="majority_operator_clears_contextual_value_per_cost_gate",
        )

    @staticmethod
    def resolve_majority(
        decision: ContextualArbitrationDecision,
        primary: CalibratedCandidateSignal,
        peers: tuple[CalibratedCandidateSignal, ...],
    ) -> ContextualArbitrationDecision:
        if decision.action != "ARBITRATE_MAJORITY" or {item.model_id for item in peers} != set(decision.peer_model_ids):
            raise ValueError("contextual_arbitration_peer_binding_invalid")
        signals = (primary, *peers)
        counts = {answer: sum(item.answer == answer for item in signals) for answer in {item.answer for item in signals}}
        answer, votes = max(counts.items(), key=lambda item: (item[1], item[0]))
        if votes == 1:
            fallback = next((item for item in signals if item.model_id == "qwen2.5-1.5b-instruct"), primary)
            answer, reason = fallback.answer, "all_disagree_qwen_fallback"
        else:
            reason = "strict_peer_majority"
        return ContextualArbitrationDecision(
            **{**decision.__dict__, "action": "MAJORITY_RESOLVED", "reason": reason, "final_answer": answer}
        )
