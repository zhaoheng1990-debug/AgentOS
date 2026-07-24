"""Mechanical selective-review policy over advisory reliability signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CandidateSignal:
    model_id: str
    item_id: str
    answer: str
    confidence: float
    reliability: float
    had_structured_retry: bool = False


@dataclass(frozen=True)
class SelectiveRouteDecision:
    item_id: str
    primary_model_id: str
    reviewer_model_id: str
    action: str
    expected_gain: float
    reason: str
    final_answer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class SelectiveReviewPolicy:
    def __init__(self, *, confidence_threshold: float = 0.75, minimum_expected_gain: float = 0.12) -> None:
        self.confidence_threshold = confidence_threshold
        self.minimum_expected_gain = minimum_expected_gain

    def route(self, signals: tuple[CandidateSignal, ...]) -> SelectiveRouteDecision:
        if len(signals) < 2 or len({item.item_id for item in signals}) != 1:
            raise ValueError("selective_route_signals_invalid")
        ranked = sorted(signals, key=lambda item: (item.reliability, item.confidence, item.model_id), reverse=True)
        primary, reviewer = ranked[0], ranked[1]
        expected_gain = round((1.0 - primary.confidence) * reviewer.reliability, 12)
        if primary.confidence >= self.confidence_threshold and not primary.had_structured_retry:
            return SelectiveRouteDecision(primary.item_id, primary.model_id, "", "STOP_CONFIDENT", expected_gain, "calibrated_primary_confident", primary.answer)
        if expected_gain < self.minimum_expected_gain:
            return SelectiveRouteDecision(primary.item_id, primary.model_id, "", "STOP_LOW_MARGINAL", expected_gain, "review_expected_gain_below_cost_floor", primary.answer)
        return SelectiveRouteDecision(primary.item_id, primary.model_id, reviewer.model_id, "REVIEW", expected_gain, "uncertainty_and_expected_gain_justify_second_model")

    @staticmethod
    def resolve(
        decision: SelectiveRouteDecision,
        primary: CandidateSignal,
        reviewer: CandidateSignal,
    ) -> SelectiveRouteDecision:
        if decision.action != "REVIEW" or decision.primary_model_id != primary.model_id or decision.reviewer_model_id != reviewer.model_id:
            raise ValueError("selective_review_binding_invalid")
        if primary.answer == reviewer.answer:
            answer, reason = primary.answer, "independent_review_agreement"
        else:
            primary_weight = primary.reliability * (0.5 + 0.5 * primary.confidence)
            reviewer_weight = reviewer.reliability * (0.5 + 0.5 * reviewer.confidence)
            answer = reviewer.answer if reviewer_weight > primary_weight else primary.answer
            reason = "reviewer_weight_exceeded_primary" if answer == reviewer.answer else "primary_weight_survived_review"
        return SelectiveRouteDecision(
            decision.item_id,
            decision.primary_model_id,
            decision.reviewer_model_id,
            "REVIEW_RESOLVED",
            decision.expected_gain,
            reason,
            answer,
        )
