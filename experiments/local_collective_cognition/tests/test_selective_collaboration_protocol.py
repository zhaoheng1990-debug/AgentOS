from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "agentos_core_slim_v0"
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.collective_protocol import (  # noqa: E402
    PILOT_TASK_KINDS,
    LocalCollectiveCognitionProtocol,
)
from local_collective_cognition.holdout_benchmark import build_holdout_harness  # noqa: E402
from local_collective_cognition.pilot_benchmark import build_pilot_harness  # noqa: E402
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderInvocationTelemetry,
    ProviderTelemetryLedger,
    hash_payload,
)
from local_collective_cognition.selective_calibration import build_reliability_profiles  # noqa: E402
from local_collective_cognition.selective_policy import CandidateSignal, SelectiveReviewPolicy  # noqa: E402
from local_collective_cognition.selective_protocol import SelectiveCollaborationProtocol  # noqa: E402


CALIBRATION_TRUTH = {
    "logic-1": "A", "modular-1": "B", "probability-1": "C", "code-1": "D",
    "schedule-1": "D", "sets-1": "B", "causal-1": "A", "sequence-1": "C",
    "truth-1": "A", "rate-1": "C", "string-1": "D", "bayes-1": "B",
}
HOLDOUT_TRUTH = {
    "logic-2": "A", "schedule-2": "C", "implication-2": "B", "modular-2": "D",
    "probability-2": "B", "sets-2": "C", "sequence-2": "D", "rate-2": "B",
    "bayes-2": "C", "code-2": "A", "string-2": "D", "causal-2": "B",
}


def calibration_report():
    wrong = {item_id: "D" if answer != "D" else "A" for item_id, answer in CALIBRATION_TRUTH.items()}
    return {
        "solo_arms": [
            {"model_ids": ["small-a"], "answer_vector": wrong, "harness_receipt_hash": "a" * 64},
            {"model_ids": ["small-b"], "answer_vector": CALIBRATION_TRUTH, "harness_receipt_hash": "b" * 64},
            {"model_ids": ["small-c"], "answer_vector": wrong, "harness_receipt_hash": "c" * 64},
        ]
    }


class HoldoutAdapter:
    def __init__(self, model_id, ledger, answers, confidence=0.9):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id,
            model_id=model_id,
            task_kinds=PILOT_TASK_KINDS,
            max_timeout_seconds=600,
        )
        self.ledger = ledger
        self.answers = answers
        self.confidence = confidence

    def invoke(self, task):
        item_id = task.inputs["benchmark_item_ids"][0]
        result = {
            "item_id": item_id,
            "answer": self.answers[item_id],
            "confidence": self.confidence,
            "evidence_refs": list(task.allowed_evidence),
        }
        self.ledger.record(ProviderInvocationTelemetry.create(
            telemetry_id=f"fixture-{self.profile.model_id}-{task.task_id}",
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="fixture",
            task_id=task.task_id,
            task_kind=task.task_kind,
            task_contract_hash=task.contract_hash(),
            status="COMPLETED",
            input_tokens=10,
            output_tokens=5,
            cached_tokens=0,
            latency_ms=10,
            api_cost=0.0,
            tool_calls=0,
            tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence),
            output_hash=hash_payload(result),
            thinking_present=False,
            thinking_char_count=0,
            thinking_hash="",
            error_type="",
        ))
        return {"result": result, "usage": {}, "provenance_refs": list(task.allowed_evidence)}


def test_selective_policy_preserves_calibrated_primary_with_less_group_work():
    receipts, profiles = build_reliability_profiles(calibration_report(), build_pilot_harness())
    ledger = ProviderTelemetryLedger()
    wrong = {item_id: "D" if answer != "D" else "A" for item_id, answer in HOLDOUT_TRUTH.items()}
    adapters = {
        "small-a": HoldoutAdapter("small-a", ledger, wrong),
        "small-b": HoldoutAdapter("small-b", ledger, HOLDOUT_TRUTH),
        "small-c": HoldoutAdapter("small-c", ledger, wrong),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_harness(),
        small_adapters=adapters,
        baseline_adapter=HoldoutAdapter("deepseek-32b", ledger, HOLDOUT_TRUTH),
        telemetry_ledger=ledger,
        reviewer_model_id="small-b",
        synthesizer_model_id="small-c",
    )
    report = SelectiveCollaborationProtocol(
        base=base,
        reliability_receipts=receipts,
        reliability_profiles=profiles,
    ).run("selective-fixture")

    assert report["selective_arm"]["score"] == 1.0
    assert report["selective_arm"]["provider_calls"] == 12
    assert report["majority_arm"]["provider_calls"] == 36
    assert report["comparisons"]["reviewed_items"] == 0
    assert report["comparisons"]["candidate_union_ceiling"]["score"] == 1.0
    assert report["comparisons"]["selective_improvement_status"] == "BEST_MEMBER_PRESERVED_WITH_LOWER_GROUP_WORK"


def test_low_confidence_routes_only_when_expected_gain_clears_floor():
    policy = SelectiveReviewPolicy(confidence_threshold=0.75, minimum_expected_gain=0.12)
    signals = (
        CandidateSignal("primary", "q", "A", 0.6, 0.8),
        CandidateSignal("reviewer", "q", "B", 0.9, 0.5),
    )
    decision = policy.route(signals)
    resolved = policy.resolve(decision, signals[0], signals[1])

    assert decision.action == "REVIEW"
    assert resolved.action == "REVIEW_RESOLVED"
