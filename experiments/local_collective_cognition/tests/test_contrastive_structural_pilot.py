from __future__ import annotations

import math
import sys
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(Path(__file__).resolve().parents[1])]

from agentos_kernel import ProviderCognitiveTask  # noqa: E402
from local_collective_cognition.calibrated_score_receipt import build_calibrated_score_receipt  # noqa: E402
from local_collective_cognition.collective_protocol import RoleRun  # noqa: E402
from local_collective_cognition.contrastive_structural_contracts import (  # noqa: E402
    build_contrastive_batch_receipt, validate_contrastive_batch_payload,
    validate_contrastive_batch_receipt, normalize_contrastive_batch_payload,
)
from local_collective_cognition.contrastive_structural_holdout import (  # noqa: E402
    EVIDENCE_REFS, QUESTIONS, build_contrastive_structural_harness,
)
from local_collective_cognition.contrastive_trigger_policy import (  # noqa: E402
    ContrastiveStructureTriggerPolicy, validate_contrastive_trigger_receipt,
)
from local_collective_cognition.problem_formulation_contracts import build_problem_definition_receipt  # noqa: E402
from local_collective_cognition.problem_semantic_channel import problem_semantic_channel_hash  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def _definition_run(item_id, fields, confidence, entropy):
    task = ProviderCognitiveTask(
        task_id="control-" + item_id, task_kind="pilot_problem_formulation",
        objective="define", inputs={
            "benchmark_public_input": {"questions": []},
            "benchmark_item_ids": [item_id], "round_context": {},
        }, allowed_evidence=list(EVIDENCE_REFS), expected_schema={}, timeout_seconds=10,
    )
    scores = [
        {"option": "X", "label": "A", "probability": confidence,
         "context_probability": confidence, "prior_probability": 0.5,
         "calibrated_log_ratio": math.log(confidence / 0.5)},
        {"option": "Y", "label": "B", "probability": 1 - confidence,
         "context_probability": 1 - confidence, "prior_probability": 0.5,
         "calibrated_log_ratio": math.log((1 - confidence) / 0.5)},
    ]
    decision = {
        "stage": "PROBLEM_MODE", "selected": "X",
        "selected_probability": confidence, "margin": 2 * confidence - 1,
        "entropy": entropy, "scores": scores, "input_tokens": 10,
        "latency_ms": 1, "inference_passes": 2,
        "calibration_ref": hash_payload({
            "model_id": "fixture", "menu_size": 2, "probabilities": [0.5, 0.5],
        }),
        "calibration_cached": False,
    }
    decision_receipt = build_calibrated_score_receipt(
        task=task, channel_hash=hash_payload(item_id), decisions=[decision],
        selected_value="|".join(fields), provider_id="fixture", model_id="fixture",
    )
    problem = build_problem_definition_receipt(
        task=task, problem_candidate_id="CONTROL_PROBLEM",
        intent_mode=fields[0], problem_family=fields[1], target_kind=fields[2],
        critical_constraint=fields[3], decision_receipt=decision_receipt,
        provider_id="fixture", model_id="fixture",
    )
    return RoleRun("control-" + item_id, "fixture", {
        "problem_receipt": problem, "decision_receipt": decision_receipt,
    }, (task,), (), ())


def test_trigger_policy_selects_only_two_highest_truth_blind_risks():
    coherent = ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER")
    inconsistent = ("STRING_TRANSFORMATION", "MODULAR_REMAINDER", "DISTANCE", "NONE")
    runs = (
        _definition_run("modular-26", coherent, 0.90, 0.20),
        _definition_run("ratio-26", coherent, 0.55, 0.68),
        _definition_run("sets-26", inconsistent, 0.80, 0.30),
        _definition_run("bayes-26", inconsistent, 0.60, 0.60),
    )
    receipt = ContrastiveStructureTriggerPolicy(max_items=2).evaluate(
        experiment_id="fixture", definition_runs=runs,
    )
    validate_contrastive_trigger_receipt(receipt)
    assert receipt["selected_item_ids"] == ["bayes-26", "sets-26"]
    assert receipt["hidden_truth_used"] is False
    assert all("truth" not in str(record).lower() for record in receipt["candidate_records"])


def test_contrastive_batch_receipt_binds_multiple_packets_and_disables_retention():
    harness = build_contrastive_structural_harness()
    item_ids = ("modular-26", "sets-26")
    task = ProviderCognitiveTask(
        task_id="batch", task_kind="pilot_object_structure_expansion", objective="contrast",
        inputs={"benchmark_public_input": harness.provider_inputs(item_ids),
                "benchmark_item_ids": list(item_ids), "round_context": {}},
        allowed_evidence=list(EVIDENCE_REFS), expected_schema={}, timeout_seconds=10,
    )
    provider_payload = {}
    for index, item_id in enumerate(item_ids, 1):
        provider_payload[f"item_{index}_packet"] = (
            "One hypothesis is a residual structure; the rival is an allocation structure. "
            "The contrast is residual versus share. Ask which quantity the request names."
        )
    payload = normalize_contrastive_batch_payload(
        provider_payload, item_ids=item_ids, evidence_refs=EVIDENCE_REFS,
    )
    validate_contrastive_batch_payload(payload, item_ids=item_ids, evidence_refs=EVIDENCE_REFS)
    receipt = build_contrastive_batch_receipt(
        task=task, payload=payload, trigger_receipt_hash=hash_payload("trigger"),
        provider_id="fixture", model_id="fixture", provider_payload=provider_payload,
    )
    validate_contrastive_batch_receipt(
        receipt, task=task, payload=payload,
        trigger_receipt_hash=hash_payload("trigger"), provider_payload=provider_payload,
    )
    assert receipt["item_ids"] == list(item_ids)
    assert receipt["retention_authorized"] is False
    try:
        validate_contrastive_batch_receipt(receipt, payload={**payload, "packets": []})
    except ValueError as exc:
        assert str(exc) == "contrastive_structure_payload_binding_invalid"
    else:
        raise AssertionError("tampered packet batch passed validation")


def test_contrastive_holdout_truth_is_frozen_and_mechanically_correct():
    harness = build_contrastive_structural_harness()
    assert len(QUESTIONS) == 6
    assert "truth" not in str(harness.provider_inputs()).lower()
    assert 3749 % 67 == 64
    assert Fraction(2475 * 3, 3 + 8) == 675
    assert 920 - (560 + 470 - 260) == 150
    assert Fraction(40 * 81, 40 * 81 + 60 * 14) == Fraction(27, 34)
    value = "YZABCDEF"
    swapped = value[4:] + value[:4]
    assert "".join(swapped[i:i + 2][::-1] for i in range(0, 8, 2)) == "DCFEZYBA"
    assert Fraction(88) * Fraction("2.75") == 242


def test_contrastive_semantic_channel_excludes_lineage_hash_noise():
    harness = build_contrastive_structural_harness()
    context = {
        "role": "contrastive_problem_reviser", "problem_candidate_id": "SELECTIVE_PROBLEM",
        "contrastive_structure_packet": {"item_id": "ratio-26", "contrastive_packet": "x"},
        "contrastive_batch_receipt_hash": "a" * 64,
    }
    def task(receipt_hash):
        scoped = {**context, "contrastive_batch_receipt_hash": receipt_hash}
        return ProviderCognitiveTask(
            task_id="revision-ratio", task_kind="pilot_problem_formulation",
            objective="reconsider", inputs={
                "benchmark_public_input": harness.provider_inputs(("ratio-26",)),
                "benchmark_item_ids": ["ratio-26"], "round_context": scoped,
            }, allowed_evidence=list(EVIDENCE_REFS), expected_schema={}, timeout_seconds=10,
        ), scoped
    left, left_context = task("a" * 64)
    right, right_context = task("b" * 64)
    assert left.contract_hash() != right.contract_hash()
    assert problem_semantic_channel_hash(left, left_context) == problem_semantic_channel_hash(
        right, right_context,
    )
