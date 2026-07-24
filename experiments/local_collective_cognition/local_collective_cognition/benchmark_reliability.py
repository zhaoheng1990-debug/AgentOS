"""Held-out domain reliability receipts for the local benchmark Harness."""

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
class BenchmarkReliabilityReceipt:
    calibration_id: str
    model_id: str
    source_harness_receipt_hash: str
    candidate_output_hash: str
    domain_scores: tuple[tuple[str, int, int, float], ...]
    evidence_refs: tuple[str, ...]
    truth_commitment: str
    receipt_hash: str
    harness_owned: bool = True
    selection_authority: bool = False

    def __post_init__(self) -> None:
        if not self.calibration_id or not self.model_id or not self.harness_owned or self.selection_authority:
            raise ValueError("benchmark_reliability_authority_invalid")
        for value in (self.source_harness_receipt_hash, self.candidate_output_hash, self.truth_commitment, self.receipt_hash):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("benchmark_reliability_hash_invalid")
        if not self.domain_scores or len({item[0] for item in self.domain_scores}) != len(self.domain_scores):
            raise ValueError("benchmark_reliability_domains_invalid")
        for _, correct, total, score in self.domain_scores:
            if total < 1 or not 0 <= correct <= total or score != round(correct / total, 12):
                raise ValueError("benchmark_reliability_score_invalid")
        if self.receipt_hash != _hash_payload(self._committed_dict()):
            raise ValueError("benchmark_reliability_commitment_invalid")

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "model_id": self.model_id,
            "source_harness_receipt_hash": self.source_harness_receipt_hash,
            "candidate_output_hash": self.candidate_output_hash,
            "domain_scores": [list(item) for item in self.domain_scores],
            "evidence_refs": list(self.evidence_refs),
            "truth_commitment": self.truth_commitment,
            "harness_owned": self.harness_owned,
            "selection_authority": self.selection_authority,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}


class BenchmarkReliabilityCalibrator:
    def __init__(self, truths: dict[str, str], evidence_refs: tuple[str, ...], truth_commitment: str) -> None:
        self._truths = dict(truths)
        self.evidence_refs = evidence_refs
        self.truth_commitment = truth_commitment

    def calibrate(
        self,
        *,
        calibration_id: str,
        model_id: str,
        candidate_output: dict[str, Any],
        item_domains: dict[str, str],
        source_harness_receipt_hash: str,
    ) -> BenchmarkReliabilityReceipt:
        if set(item_domains) != set(self._truths) or not re.fullmatch(r"[0-9a-f]{64}", source_harness_receipt_hash):
            raise ValueError("benchmark_reliability_source_invalid")
        answers = candidate_output.get("answers")
        if not isinstance(answers, list):
            raise ValueError("benchmark_reliability_answers_invalid")
        observed = {item.get("item_id"): str(item.get("answer", "")).strip().upper() for item in answers if isinstance(item, dict)}
        if set(observed) != set(self._truths) or len(observed) != len(answers):
            raise ValueError("benchmark_reliability_coverage_invalid")
        domains = []
        for domain in sorted(set(item_domains.values())):
            ids = tuple(item_id for item_id, value in item_domains.items() if value == domain)
            correct = sum(observed[item_id] == self._truths[item_id] for item_id in ids)
            domains.append((domain, correct, len(ids), round(correct / len(ids), 12)))
        committed = {
            "calibration_id": calibration_id,
            "model_id": model_id,
            "source_harness_receipt_hash": source_harness_receipt_hash,
            "candidate_output_hash": _hash_payload(candidate_output),
            "domain_scores": [list(item) for item in domains],
            "evidence_refs": list(self.evidence_refs),
            "truth_commitment": self.truth_commitment,
            "harness_owned": True,
            "selection_authority": False,
        }
        return BenchmarkReliabilityReceipt(
            **{
                **committed,
                "domain_scores": tuple(domains),
                "evidence_refs": self.evidence_refs,
                "receipt_hash": _hash_payload(committed),
            }
        )

    def candidate_union_ceiling(self, candidate_outputs: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        observed = []
        for candidate in candidate_outputs:
            answers = candidate.get("answers")
            if not isinstance(answers, list):
                raise ValueError("benchmark_union_candidate_invalid")
            answer_map = {item.get("item_id"): str(item.get("answer", "")).strip().upper() for item in answers}
            if set(answer_map) != set(self._truths) or len(answer_map) != len(answers):
                raise ValueError("benchmark_union_candidate_coverage_invalid")
            observed.append(answer_map)
        correct = sum(any(item[item_id] == truth for item in observed) for item_id, truth in self._truths.items())
        committed = {
            "correct_count": correct,
            "total_count": len(self._truths),
            "score": round(correct / len(self._truths), 12),
            "candidate_output_hashes": [_hash_payload(item) for item in candidate_outputs],
            "truth_commitment": self.truth_commitment,
            "harness_owned": True,
            "selection_authority": False,
        }
        return {**committed, "counterfactual_hash": _hash_payload(committed)}
