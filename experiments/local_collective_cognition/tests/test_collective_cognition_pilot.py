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
    role_run_as_dict,
    role_run_from_dict,
)
from local_collective_cognition.pilot_benchmark import build_pilot_harness  # noqa: E402
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderInvocationTelemetry,
    ProviderTelemetryLedger,
    hash_payload,
)


CORRECT = {
    "logic-1": "A", "modular-1": "B", "probability-1": "C", "code-1": "D",
    "schedule-1": "D", "sets-1": "B", "causal-1": "A", "sequence-1": "C",
    "truth-1": "A", "rate-1": "C", "string-1": "D", "bayes-1": "B",
}


def output_with(overrides=None, evidence_refs=None, item_ids=None):
    answers = {**CORRECT, **(overrides or {})}
    selected = tuple(item_ids or answers)
    return {
        "answers": [
            {"item_id": item_id, "answer": answer, "rationale": "bounded fixture reason"}
            for item_id, answer in answers.items() if item_id in selected
        ],
        "evidence_refs": list(evidence_refs or ("benchmark://local-reasoning-pilot-v0-1",)),
    }


class FakeAdapter:
    def __init__(self, model_id, ledger, solo_output):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id,
            model_id=model_id,
            task_kinds=PILOT_TASK_KINDS,
            max_timeout_seconds=600,
        )
        self.ledger = ledger
        self.solo_output = solo_output
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        target = task.inputs["round_context"].get("target_item_id")
        source = self.solo_output if task.task_kind == "pilot_solo_answer" else output_with()
        result = (
            {
                "item_id": target,
                "answer": next(item["answer"] for item in source["answers"] if item["item_id"] == target),
                "confidence": 0.8,
                "evidence_refs": source["evidence_refs"],
            }
            if target
            else source
        )
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
            latency_ms=20,
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
        return {
            "result": result,
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_pilot_protocol_measures_collaboration_without_truth_leakage():
    ledger = ProviderTelemetryLedger()
    adapters = {
        "small-a": FakeAdapter("small-a", ledger, output_with({"modular-1": "A"})),
        "small-b": FakeAdapter("small-b", ledger, output_with({"probability-1": "A"})),
        "small-c": FakeAdapter("small-c", ledger, output_with({"code-1": "A"})),
    }
    baseline = FakeAdapter("deepseek-32b", ledger, output_with())
    report = LocalCollectiveCognitionProtocol(
        harness=build_pilot_harness(),
        small_adapters=adapters,
        baseline_adapter=baseline,
        telemetry_ledger=ledger,
        reviewer_model_id="small-b",
        synthesizer_model_id="small-c",
    ).run("fixture-pilot")

    assert report["best_small_model"]["score"] == round(11 / 12, 12)
    assert report["majority_arm"]["score"] == 1.0
    assert report["iterative_arm"]["score"] == 1.0
    assert report["deepseek_32b_arm"]["score"] == 1.0
    assert report["iterative_arm"]["provider_calls"] == 60
    assert report["comparisons"]["hypothesis_status"] == "CONSISTENT_WITH_WORK_AMPLIFICATION_HYPOTHESIS"
    for adapter in (*adapters.values(), baseline):
        for task in adapter.tasks:
            serialized = str(task.inputs).lower()
            assert "expected_answer" not in serialized
            assert "ground_truth" not in serialized
            assert "hidden_answer" not in serialized


def test_frozen_pilot_truth_scores_only_inside_harness():
    harness = build_pilot_harness()
    task_adapter_ledger = ProviderTelemetryLedger()
    adapter = FakeAdapter("deepseek-32b", task_adapter_ledger, output_with())
    protocol = LocalCollectiveCognitionProtocol(
        harness=harness,
        small_adapters={
            "a": FakeAdapter("a", task_adapter_ledger, output_with()),
            "b": FakeAdapter("b", task_adapter_ledger, output_with()),
        },
        baseline_adapter=adapter,
        telemetry_ledger=task_adapter_ledger,
        reviewer_model_id="a",
        synthesizer_model_id="b",
    )
    report = protocol.run("fixture-perfect")

    assert report["deepseek_32b_arm"]["correct_count"] == 12
    assert "truth_commitment" not in report["deepseek_32b_arm"]
    assert report["protocol"]["provider_truth_exposure_detected"] is False


def test_baseline_role_checkpoint_round_trips_with_hash_validation():
    ledger = ProviderTelemetryLedger()
    baseline = FakeAdapter("deepseek-32b", ledger, output_with())
    protocol = LocalCollectiveCognitionProtocol(
        harness=build_pilot_harness(),
        small_adapters={
            "a": FakeAdapter("a", ledger, output_with()),
            "b": FakeAdapter("b", ledger, output_with()),
        },
        baseline_adapter=baseline,
        telemetry_ledger=ledger,
        reviewer_model_id="a",
        synthesizer_model_id="b",
    )
    observed = []
    protocol.run("checkpoint-source", baseline_observer=observed.append)
    restored = role_run_from_dict(role_run_as_dict(observed[0]))

    assert restored == observed[0]
