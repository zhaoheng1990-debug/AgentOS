"""Harness-owned calibration receipts for confidence and reviewer value."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations
from typing import Any

from .review_outcome_calibration import ReviewOutcomeReceipt, calibrate_review_outcomes
from .disagreement_outcome import DisagreementOperatorReceipt, calibrate_disagreement_operator
from .structural_operator_receipt import StructuralOperatorEvidenceReceipt, calibrate_structural_operators
from .disagreement_resolution_receipt import DisagreementResolutionEvidenceReceipt, calibrate_disagreement_resolution
from .context_resolution_receipt import ContextResolutionEvidenceReceipt, calibrate_resolution_context
from .case_adjudication_receipt import CaseAdjudicationEvidenceReceipt, calibrate_case_adjudication


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _posterior(correct: int, total: int, prior: float, strength: float = 4.0) -> float:
    return round((correct + strength * prior) / (total + strength), 12)


@dataclass(frozen=True)
class ModelCalibrationRecord:
    model_id: str
    correct: int
    total: int
    global_posterior: float
    brier_score: float
    domain_scores: tuple[tuple[str, int, int, float], ...]
    confidence_bins: tuple[tuple[str, int, int, float, float], ...]
    retry_scores: tuple[tuple[str, int, int, float], ...]
    calls_per_item: float
    tokens_per_item: float
    source_harness_receipt_hash: str
    candidate_output_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key not in {"domain_scores", "confidence_bins", "retry_scores"}},
            "domain_scores": [list(item) for item in self.domain_scores],
            "confidence_bins": [list(item) for item in self.confidence_bins],
            "retry_scores": [list(item) for item in self.retry_scores],
        }


@dataclass(frozen=True)
class ReviewerValueRecord:
    primary_model_id: str
    reviewer_model_id: str
    domain: str
    corrections: int
    correction_opportunities: int
    harms: int
    harm_opportunities: int
    disagreements: int
    correction_posterior: float
    harm_posterior: float
    net_value: float

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class RoutingCalibrationReceipt:
    calibration_id: str
    model_records: tuple[ModelCalibrationRecord, ...]
    reviewer_records: tuple[ReviewerValueRecord, ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    selection_authority: bool = False

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "model_records": [item.as_dict() for item in self.model_records],
            "reviewer_records": [item.as_dict() for item in self.reviewer_records],
            "evidence_refs": list(self.evidence_refs),
            "truth_commitment": self.truth_commitment,
            "harness_owned": self.harness_owned,
            "selection_authority": self.selection_authority,
        }

    def __post_init__(self) -> None:
        if not self.calibration_id or not self.model_records or not self.harness_owned or self.selection_authority:
            raise ValueError("routing_calibration_authority_invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.truth_commitment):
            raise ValueError("routing_calibration_truth_commitment_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("routing_calibration_receipt_hash_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


class BenchmarkRoutingCalibrator:
    """Convert hidden correctness into aggregate advisory calibration only."""

    def __init__(self, truths: dict[str, str], evidence_refs: tuple[str, ...], truth_commitment: str) -> None:
        self._truths = dict(truths)
        self.evidence_refs = evidence_refs
        self.truth_commitment = truth_commitment

    def calibrate(
        self,
        *,
        calibration_id: str,
        candidates: tuple[dict[str, Any], ...],
        item_domains: dict[str, str],
    ) -> RoutingCalibrationReceipt:
        if set(item_domains) != set(self._truths) or len(candidates) < 2:
            raise ValueError("routing_calibration_source_invalid")
        observations = {candidate["model_id"]: self._observations(candidate) for candidate in candidates}
        if len(observations) != len(candidates):
            raise ValueError("routing_calibration_model_duplicate")
        model_records = tuple(
            self._model_record(candidate, observations[candidate["model_id"]], item_domains)
            for candidate in candidates
        )
        profiles = {item.model_id: item for item in model_records}
        reviewer_records = tuple(
            self._reviewer_record(primary, reviewer, observations, profiles, item_domains, domain)
            for primary, reviewer in permutations(sorted(observations), 2)
            for domain in sorted(set(item_domains.values()))
        )
        committed = {
            "calibration_id": calibration_id,
            "model_records": [item.as_dict() for item in model_records],
            "reviewer_records": [item.as_dict() for item in reviewer_records],
            "evidence_refs": list(self.evidence_refs),
            "truth_commitment": self.truth_commitment,
            "harness_owned": True,
            "selection_authority": False,
        }
        return RoutingCalibrationReceipt(
            calibration_id=calibration_id,
            model_records=model_records,
            reviewer_records=reviewer_records,
            evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment,
            receipt_hash=_hash_payload(committed),
        )

    def calibrate_outcomes(self, **values: Any) -> ReviewOutcomeReceipt:
        return calibrate_review_outcomes(
            truths=self._truths, evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment, **values,
        )

    def calibrate_disagreement(self, **values: Any) -> DisagreementOperatorReceipt:
        return calibrate_disagreement_operator(
            truths=self._truths, evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment, **values,
        )

    def calibrate_structural_operators(self, **values: Any) -> StructuralOperatorEvidenceReceipt:
        return calibrate_structural_operators(
            truths=self._truths, evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment, **values,
        )

    def calibrate_disagreement_resolution(self, **values: Any) -> DisagreementResolutionEvidenceReceipt:
        return calibrate_disagreement_resolution(
            truths=self._truths, evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment, **values,
        )

    def calibrate_resolution_context(self, **values: Any) -> ContextResolutionEvidenceReceipt:
        return calibrate_resolution_context(
            truths=self._truths, evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment, **values,
        )

    def calibrate_case_adjudication(self, **values: Any) -> CaseAdjudicationEvidenceReceipt:
        return calibrate_case_adjudication(
            truths=self._truths, evidence_refs=self.evidence_refs,
            truth_commitment=self.truth_commitment, **values,
        )

    def _observations(self, candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
        model_id = candidate.get("model_id")
        source_hash = candidate.get("source_harness_receipt_hash")
        answers = candidate.get("answers")
        if not model_id or not re.fullmatch(r"[0-9a-f]{64}", str(source_hash)) or not isinstance(answers, list):
            raise ValueError("routing_calibration_candidate_invalid")
        observed: dict[str, dict[str, Any]] = {}
        for item in answers:
            if not isinstance(item, dict) or set(item) != {"item_id", "answer", "confidence", "had_structured_retry"}:
                raise ValueError("routing_calibration_answer_shape_invalid")
            confidence = item["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
                raise ValueError("routing_calibration_confidence_invalid")
            item_id = item["item_id"]
            if item_id in observed:
                raise ValueError("routing_calibration_answer_duplicate")
            observed[item_id] = {
                "answer": str(item["answer"]).strip().upper(),
                "confidence": float(confidence),
                "had_structured_retry": bool(item["had_structured_retry"]),
            }
        if set(observed) != set(self._truths):
            raise ValueError("routing_calibration_answer_coverage_invalid")
        return observed

    def _model_record(self, candidate: dict[str, Any], observed: dict[str, dict[str, Any]], domains: dict[str, str]) -> ModelCalibrationRecord:
        correct_map = {item_id: item["answer"] == self._truths[item_id] for item_id, item in observed.items()}
        correct = sum(correct_map.values())
        total = len(correct_map)
        global_posterior = round((correct + 1) / (total + 2), 12)
        domain_scores = []
        for domain in sorted(set(domains.values())):
            ids = [item_id for item_id, value in domains.items() if value == domain]
            hits = sum(correct_map[item_id] for item_id in ids)
            domain_scores.append((domain, hits, len(ids), _posterior(hits, len(ids), global_posterior)))
        confidence_bins = []
        for label, lower, upper in (("LOW", 0.0, 0.5), ("MID", 0.5, 0.8), ("HIGH", 0.8, 1.0000001)):
            ids = [item_id for item_id, item in observed.items() if lower <= item["confidence"] < upper]
            hits = sum(correct_map[item_id] for item_id in ids)
            mean = round(sum(observed[item_id]["confidence"] for item_id in ids) / len(ids), 12) if ids else 0.0
            confidence_bins.append((label, hits, len(ids), mean, _posterior(hits, len(ids), global_posterior)))
        retry_scores = []
        for label, retry in (("NO_RETRY", False), ("RETRY", True)):
            ids = [item_id for item_id, item in observed.items() if item["had_structured_retry"] is retry]
            hits = sum(correct_map[item_id] for item_id in ids)
            retry_scores.append((label, hits, len(ids), _posterior(hits, len(ids), global_posterior)))
        brier = round(sum((observed[item_id]["confidence"] - float(correct_map[item_id])) ** 2 for item_id in observed) / total, 12)
        calls = int(candidate.get("provider_calls", 0))
        tokens = int(candidate.get("total_tokens", 0))
        if calls < total or tokens < 1:
            raise ValueError("routing_calibration_work_invalid")
        return ModelCalibrationRecord(
            model_id=candidate["model_id"], correct=correct, total=total,
            global_posterior=global_posterior, brier_score=brier,
            domain_scores=tuple(domain_scores), confidence_bins=tuple(confidence_bins),
            retry_scores=tuple(retry_scores), calls_per_item=round(calls / total, 12),
            tokens_per_item=round(tokens / total, 12),
            source_harness_receipt_hash=candidate["source_harness_receipt_hash"],
            candidate_output_hash=_hash_payload(candidate),
        )

    def _reviewer_record(self, primary: str, reviewer: str, observations, profiles, domains, domain: str) -> ReviewerValueRecord:
        ids = [item_id for item_id, value in domains.items() if value == domain]
        primary_correct = {item_id: observations[primary][item_id]["answer"] == self._truths[item_id] for item_id in ids}
        reviewer_correct = {item_id: observations[reviewer][item_id]["answer"] == self._truths[item_id] for item_id in ids}
        correction_opportunities = sum(not primary_correct[item_id] for item_id in ids)
        corrections = sum(not primary_correct[item_id] and reviewer_correct[item_id] for item_id in ids)
        harm_opportunities = sum(primary_correct.values())
        harms = sum(primary_correct[item_id] and not reviewer_correct[item_id] for item_id in ids)
        disagreements = sum(observations[primary][item_id]["answer"] != observations[reviewer][item_id]["answer"] for item_id in ids)
        reviewer_domain = next(item[3] for item in profiles[reviewer].domain_scores if item[0] == domain)
        correction_posterior = _posterior(corrections, correction_opportunities, reviewer_domain)
        harm_posterior = _posterior(harms, harm_opportunities, 1.0 - reviewer_domain)
        return ReviewerValueRecord(
            primary_model_id=primary, reviewer_model_id=reviewer, domain=domain,
            corrections=corrections, correction_opportunities=correction_opportunities,
            harms=harms, harm_opportunities=harm_opportunities, disagreements=disagreements,
            correction_posterior=correction_posterior, harm_posterior=harm_posterior,
            net_value=round(correction_posterior - 0.5 * harm_posterior, 12),
        )


def routing_calibration_receipt_from_dict(payload: dict[str, Any]) -> RoutingCalibrationReceipt:
    model_records = tuple(
        ModelCalibrationRecord(
            **{
                **item,
                "domain_scores": tuple(tuple(value) for value in item["domain_scores"]),
                "confidence_bins": tuple(tuple(value) for value in item["confidence_bins"]),
                "retry_scores": tuple(tuple(value) for value in item["retry_scores"]),
            }
        )
        for item in payload["model_records"]
    )
    reviewer_records = tuple(ReviewerValueRecord(**item) for item in payload["reviewer_records"])
    return RoutingCalibrationReceipt(
        **{
            **payload,
            "model_records": model_records,
            "reviewer_records": reviewer_records,
            "evidence_refs": tuple(payload["evidence_refs"]),
        }
    )
