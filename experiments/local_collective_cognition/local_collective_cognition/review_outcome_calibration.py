"""Harness-owned prediction/outcome receipt for calibrated reviews."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ReviewOutcomeReceipt:
    experiment_id: str
    calibration_receipt_hash: str
    decision_hash: str
    reviewed_count: int
    corrected_count: int
    harmed_count: int
    unchanged_count: int
    predicted_net_cbit: float
    observed_net_cbit: float
    absolute_calibration_error: float
    outcome_records: tuple[tuple[str, str, int, int, int, int, float], ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    selection_authority: bool = False

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {"outcome_records", "evidence_refs", "receipt_hash"}},
            "outcome_records": [list(item) for item in self.outcome_records],
            "evidence_refs": list(self.evidence_refs),
        }

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.harness_owned or self.selection_authority:
            raise ValueError("review_outcome_authority_invalid")
        if self.reviewed_count != self.corrected_count + self.harmed_count + self.unchanged_count:
            raise ValueError("review_outcome_counts_invalid")
        for value in (self.calibration_receipt_hash, self.decision_hash, self.truth_commitment, self.receipt_hash):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("review_outcome_hash_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("review_outcome_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


def calibrate_review_outcomes(
    *,
    truths: dict[str, str],
    evidence_refs: tuple[str, ...],
    truth_commitment: str,
    experiment_id: str,
    calibration_receipt_hash: str,
    route_decisions: tuple[dict[str, Any], ...],
    item_domains: dict[str, str],
    resolved_actions: tuple[str, ...] = ("REVIEW_RESOLVED",),
) -> ReviewOutcomeReceipt:
    if set(item_domains) != set(truths) or {item.get("item_id") for item in route_decisions} != set(truths):
        raise ValueError("review_outcome_coverage_invalid")
    reviewed = [item for item in route_decisions if item.get("action") in resolved_actions]
    outcomes = []
    for item in reviewed:
        primary_correct = str(item.get("primary_answer", "")).strip().upper() == truths[item["item_id"]]
        final_correct = str(item.get("final_answer", "")).strip().upper() == truths[item["item_id"]]
        status = "CORRECTED" if not primary_correct and final_correct else "HARMED" if primary_correct and not final_correct else "UNCHANGED"
        outcomes.append((item, status))
    corrected = sum(status == "CORRECTED" for _, status in outcomes)
    harmed = sum(status == "HARMED" for _, status in outcomes)
    total_items = len(truths)
    predicted = round(sum(float(item.get("expected_net_cbit", 0.0)) for item, _ in outcomes) / total_items, 12)
    observed = round((corrected - harmed) / total_items, 12)
    records = []
    keys = sorted({(item["reviewer_model_id"], item_domains[item["item_id"]]) for item, _ in outcomes})
    for reviewer, domain in keys:
        selected = [(item, status) for item, status in outcomes if item["reviewer_model_id"] == reviewer and item_domains[item["item_id"]] == domain]
        corrections = sum(status == "CORRECTED" for _, status in selected)
        harms = sum(status == "HARMED" for _, status in selected)
        records.append((reviewer, domain, len(selected), corrections, harms, len(selected) - corrections - harms, round((corrections - harms) / total_items, 12)))
    committed = {
        "experiment_id": experiment_id,
        "calibration_receipt_hash": calibration_receipt_hash,
        "decision_hash": _hash_payload(route_decisions),
        "reviewed_count": len(reviewed),
        "corrected_count": corrected,
        "harmed_count": harmed,
        "unchanged_count": len(reviewed) - corrected - harmed,
        "predicted_net_cbit": predicted,
        "observed_net_cbit": observed,
        "absolute_calibration_error": round(abs(predicted - observed), 12),
        "outcome_records": [list(item) for item in records],
        "evidence_refs": list(evidence_refs),
        "truth_commitment": truth_commitment,
        "harness_owned": True,
        "selection_authority": False,
    }
    return ReviewOutcomeReceipt(
        **{
            **committed,
            "outcome_records": tuple(records),
            "evidence_refs": evidence_refs,
            "receipt_hash": _hash_payload(committed),
        }
    )
