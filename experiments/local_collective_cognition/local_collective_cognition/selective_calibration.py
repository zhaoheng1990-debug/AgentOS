"""Build domain-scoped advisory reliability from a frozen prior pilot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .benchmark_reliability import BenchmarkReliabilityReceipt
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness


CALIBRATION_ITEM_DOMAINS = {
    "logic-1": "formal", "schedule-1": "formal", "truth-1": "formal",
    "modular-1": "quantitative", "probability-1": "quantitative", "sets-1": "quantitative",
    "sequence-1": "quantitative", "rate-1": "quantitative", "bayes-1": "quantitative",
    "code-1": "procedural", "string-1": "procedural", "causal-1": "causal",
}


@dataclass(frozen=True)
class DomainReliabilityProfile:
    model_id: str
    domain_scores: tuple[tuple[str, float], ...]
    receipt_hash: str

    def score(self, domain: str) -> float:
        values = dict(self.domain_scores)
        return values.get(domain, sum(values.values()) / len(values))

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "domain_scores": dict(self.domain_scores),
            "receipt_hash": self.receipt_hash,
            "advisory_only": True,
            "selection_authority": False,
        }


def build_reliability_profiles(
    calibration_report: dict[str, Any],
    harness: FrozenAnswerBenchmarkHarness,
) -> tuple[tuple[BenchmarkReliabilityReceipt, ...], dict[str, DomainReliabilityProfile]]:
    receipts = []
    profiles = {}
    for arm in calibration_report["solo_arms"]:
        model_id = arm["model_ids"][0]
        candidate = {
            "answers": [
                {"item_id": item_id, "answer": answer}
                for item_id, answer in arm["answer_vector"].items()
            ],
            "evidence_refs": list(harness.evidence_refs),
        }
        receipt = harness.calibrate_reliability(
            calibration_id="local-pilot-v0-2-domain-calibration",
            model_id=model_id,
            candidate_output=candidate,
            item_domains=CALIBRATION_ITEM_DOMAINS,
            source_harness_receipt_hash=arm["harness_receipt_hash"],
        )
        receipts.append(receipt)
        profiles[model_id] = DomainReliabilityProfile(
            model_id=model_id,
            domain_scores=tuple((domain, score) for domain, _, _, score in receipt.domain_scores),
            receipt_hash=receipt.receipt_hash,
        )
    return tuple(receipts), profiles
