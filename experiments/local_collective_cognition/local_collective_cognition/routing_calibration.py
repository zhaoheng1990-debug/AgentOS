"""Advisory profiles derived from Harness-owned routing calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .benchmark_routing_calibration import ReviewerValueRecord, RoutingCalibrationReceipt


@dataclass(frozen=True)
class CalibratedModelProfile:
    model_id: str
    global_posterior: float
    brier_score: float
    domain_scores: tuple[tuple[str, int, int, float], ...]
    confidence_bins: tuple[tuple[str, int, int, float, float], ...]
    retry_scores: tuple[tuple[str, int, int, float], ...]
    calls_per_item: float
    tokens_per_item: float
    receipt_hash: str

    def domain_reliability(self, domain: str) -> float:
        return next((item[3] for item in self.domain_scores if item[0] == domain), self.global_posterior)

    def confidence_reliability(self, confidence: float) -> float:
        label = "LOW" if confidence < 0.5 else "MID" if confidence < 0.8 else "HIGH"
        return next(item[4] for item in self.confidence_bins if item[0] == label)

    def retry_reliability(self, had_retry: bool) -> float:
        label = "RETRY" if had_retry else "NO_RETRY"
        return next(item[3] for item in self.retry_scores if item[0] == label)

    def calibrated_success(self, domain: str, confidence: float, had_retry: bool) -> float:
        probability = (
            0.45 * self.domain_reliability(domain)
            + 0.35 * self.confidence_reliability(confidence)
            + 0.20 * self.retry_reliability(had_retry)
        )
        return round(min(1.0, max(0.0, probability)), 12)

    def expected_work(self) -> float:
        return round(self.calls_per_item + self.tokens_per_item / 1000.0, 12)

    def as_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {"domain_scores", "confidence_bins", "retry_scores"}},
            "domain_scores": [list(item) for item in self.domain_scores],
            "confidence_bins": [list(item) for item in self.confidence_bins],
            "retry_scores": [list(item) for item in self.retry_scores],
            "advisory_only": True,
            "selection_authority": False,
        }


class ReviewerValueLedger:
    def __init__(self, records: tuple[ReviewerValueRecord, ...], receipt_hash: str) -> None:
        self._records = {(item.primary_model_id, item.reviewer_model_id, item.domain): item for item in records}
        self.receipt_hash = receipt_hash

    def get(self, primary_model_id: str, reviewer_model_id: str, domain: str) -> ReviewerValueRecord:
        try:
            return self._records[(primary_model_id, reviewer_model_id, domain)]
        except KeyError as exc:
            raise ValueError("reviewer_value_binding_missing") from exc

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_hash": self.receipt_hash,
            "records": [item.as_dict() for item in self._records.values()],
            "advisory_only": True,
            "selection_authority": False,
        }


def build_calibrated_profiles(
    receipt: RoutingCalibrationReceipt,
) -> tuple[dict[str, CalibratedModelProfile], ReviewerValueLedger]:
    profiles = {
        item.model_id: CalibratedModelProfile(
            model_id=item.model_id,
            global_posterior=item.global_posterior,
            brier_score=item.brier_score,
            domain_scores=item.domain_scores,
            confidence_bins=item.confidence_bins,
            retry_scores=item.retry_scores,
            calls_per_item=item.calls_per_item,
            tokens_per_item=item.tokens_per_item,
            receipt_hash=receipt.receipt_hash,
        )
        for item in receipt.model_records
    }
    return profiles, ReviewerValueLedger(receipt.reviewer_records, receipt.receipt_hash)
