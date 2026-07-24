from __future__ import annotations

import math
import sys
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(Path(__file__).resolve().parents[1])]

from agentos_kernel import ProviderCognitiveTask  # noqa: E402
from local_collective_cognition.calibrated_score_receipt import build_calibrated_score_receipt  # noqa: E402
from local_collective_cognition.contrastive_quality_contracts import (  # noqa: E402
    QUALITY_CRITERIA, build_quality_receipt, validate_quality_receipt,
)
from local_collective_cognition.contrastive_quality_gate import (  # noqa: E402
    ContrastivePacketQualityGate, validate_quality_gate_receipt,
)
from local_collective_cognition.contrastive_structural_contracts import (  # noqa: E402
    build_contrastive_batch_receipt, normalize_contrastive_batch_payload,
)
from local_collective_cognition.contrastive_trigger_policy import CONTRASTIVE_TRIGGER_POLICY_VERSION  # noqa: E402
from local_collective_cognition.problem_semantic_channel import quality_semantic_channel_hash  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.local_structure_packet_provider import (  # noqa: E402
    LocalQualityGatedStructureAdapter,
)
from local_collective_cognition.local_transformers_provider import LocalStructuredGeneration  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger  # noqa: E402
from local_collective_cognition.quality_gated_structural_holdout import (  # noqa: E402
    EVIDENCE_REFS, QUESTIONS, build_quality_gated_structural_harness,
)
from local_collective_cognition.structured_provider_json import schema_failures, structured_json_messages  # noqa: E402


def _trigger(item_id):
    committed = {
        "policy_version": CONTRASTIVE_TRIGGER_POLICY_VERSION,
        "experiment_id": "fixture", "selected_item_ids": [item_id],
        "candidate_records": [{"item_id": item_id}], "max_items": 1,
        "confidence_floor": 0.5, "entropy_floor": 0.65,
        "selection_basis": "FORMAL_COHERENCE_PLUS_CONTEXT_CALIBRATED_UNCERTAINTY",
        "kernel_owned": True, "provider_authority": False, "hidden_truth_used": False,
    }
    return {**committed, "receipt_hash": hash_payload(committed)}


def _quality_fixture(criteria=None, packet_text="Two rival structures differ in target; ask which target applies."):
    item_id = "ratio-27"
    harness = build_quality_gated_structural_harness()
    trigger = _trigger(item_id)
    packet = {"item_id": item_id, "contrastive_packet": packet_text}
    batch_payload = {"packets": [packet], "evidence_refs": list(EVIDENCE_REFS)}
    batch_task = ProviderCognitiveTask(
        task_id="batch", task_kind="pilot_object_structure_expansion", objective="expand",
        inputs={"benchmark_public_input": harness.provider_inputs((item_id,)),
                "benchmark_item_ids": [item_id], "round_context": {},
                "audit_context": {"trigger_receipt": trigger}},
        allowed_evidence=list(EVIDENCE_REFS), expected_schema={}, timeout_seconds=10,
    )
    batch = build_contrastive_batch_receipt(
        task=batch_task, payload=batch_payload, trigger_receipt_hash=trigger["receipt_hash"],
        provider_id="elicitor", model_id="elicitor",
    )
    quality_task = ProviderCognitiveTask(
        task_id="quality", task_kind="pilot_structure_packet_quality", objective="judge",
        inputs={"benchmark_public_input": harness.provider_inputs((item_id,)),
                "benchmark_item_ids": [item_id], "round_context": {}},
        allowed_evidence=list(EVIDENCE_REFS), expected_schema={}, timeout_seconds=10,
    )
    observed = criteria or {key: "PRESENT" for key in QUALITY_CRITERIA}
    decisions = []
    for key in QUALITY_CRITERIA:
        selected = observed[key]
        options = ("PRESENT", "ABSENT", "UNCERTAIN")
        probabilities = [0.8 if value == selected else 0.1 for value in options]
        decisions.append({
            "stage": key, "selected": selected, "selected_probability": 0.8,
            "margin": 0.7, "entropy": -sum(p * math.log(p) for p in probabilities),
            "scores": [{"option": value, "label": chr(65 + index),
                        "probability": probabilities[index],
                        "context_probability": probabilities[index],
                        "prior_probability": 1 / 3,
                        "calibrated_log_ratio": math.log(probabilities[index] / (1 / 3))}
                       for index, value in enumerate(options)],
            "input_tokens": 10, "latency_ms": 1, "inference_passes": 2,
            "calibration_ref": hash_payload({"model_id": "judge", "menu_size": 3,
                                             "probabilities": [1 / 3] * 3}),
            "calibration_cached": False,
        })
    decision = build_calibrated_score_receipt(
        task=quality_task, channel_hash=hash_payload("quality"), decisions=decisions,
        selected_value="|".join(observed[key] for key in QUALITY_CRITERIA),
        provider_id="judge", model_id="judge",
    )
    quality = build_quality_receipt(
        task=quality_task, packet=packet, batch_receipt_hash=batch["receipt_hash"],
        criteria=observed, decision_receipt=decision,
        provider_id="judge", model_id="judge",
    )
    validate_quality_receipt(
        quality, task=quality_task, packet=packet, decision_receipt=decision,
        batch_receipt_hash=batch["receipt_hash"],
    )
    return harness, trigger, batch_payload, batch, packet, quality


def _gate(fixture, prompt="Split 2990 in the ratio 5:8. What is the smaller share?"):
    harness, trigger, payload, batch, packet, quality = fixture
    del harness
    receipt = ContrastivePacketQualityGate().evaluate(
        trigger_receipt=trigger, batch_receipt=batch, batch_payload=payload,
        packet=packet, quality_receipt=quality, public_prompt=prompt,
        proposer_model_id="proposer",
    )
    validate_quality_gate_receipt(receipt)
    return receipt


def test_quality_gate_allows_independent_provider_backed_complete_packet():
    assert _gate(_quality_fixture())["status"] == "ALLOW"


def test_quality_gate_blocks_exact_restatement_even_when_provider_approves():
    prompt = "Split 2990 in the ratio 5:8. What is the smaller share?"
    receipt = _gate(_quality_fixture(packet_text=prompt), prompt=prompt)
    assert receipt["status"] == "BLOCK"
    assert "QUALITY_EXACT_PUBLIC_PROMPT_RESTATEMENT" in receipt["reasons"]


def test_quality_gate_blocks_any_provider_semantic_criterion_not_present():
    criteria = {key: "PRESENT" for key in QUALITY_CRITERIA}
    criteria["DISCRIMINATING_QUESTION"] = "UNCERTAIN"
    receipt = _gate(_quality_fixture(criteria=criteria))
    assert receipt["status"] == "BLOCK"
    assert "QUALITY_PROVIDER_DISCRIMINATING_QUESTION_NOT_PRESENT" in receipt["reasons"]


def test_quality_semantic_channel_and_generic_prompt_exclude_lineage_noise():
    harness = build_quality_gated_structural_harness()
    context = {"role": "independent_contrastive_packet_quality_judge",
               "contrastive_structure_packet": {"item_id": "ratio-27",
                                                  "contrastive_packet": "packet"},
               "contrastive_batch_receipt_hash": "a" * 64}
    def make(marker):
        return ProviderCognitiveTask(
            task_id="quality", task_kind="pilot_structure_packet_quality", objective="judge",
            inputs={"benchmark_public_input": harness.provider_inputs(("ratio-27",)),
                    "benchmark_item_ids": ["ratio-27"],
                    "round_context": {**context, "contrastive_batch_receipt_hash": marker},
                    "audit_context": {"private_marker": "AUDIT_ONLY_" + marker}},
            allowed_evidence=list(EVIDENCE_REFS), expected_schema={}, timeout_seconds=10,
        )
    left, right = make("a" * 64), make("b" * 64)
    assert left.contract_hash() != right.contract_hash()
    assert quality_semantic_channel_hash(left, left.inputs["round_context"]) == (
        quality_semantic_channel_hash(right, right.inputs["round_context"])
    )
    generic_prompt = structured_json_messages(left)[1]["content"]
    assert "audit_context" not in generic_prompt and "AUDIT_ONLY_" not in generic_prompt


def test_quality_gated_holdout_is_fresh_and_mechanically_correct():
    harness = build_quality_gated_structural_harness()
    assert len(QUESTIONS) == 6 and "truth" not in str(harness.provider_inputs()).lower()
    assert 4213 % 73 == 52
    assert Fraction(2990 * 5, 13) == 1150
    assert 1040 - (630 + 520 - 310) == 200
    assert Fraction(25 * 90, 25 * 90 + 75 * 15) == Fraction(2, 3)
    value = "GHIJKLMN"; swapped = value[4:] + value[:4]
    assert "".join(swapped[i:i + 2][::-1] for i in range(0, 8, 2)) == "LKNMHGJI"
    assert Fraction(96) * Fraction("3.125") == 300


def test_structured_json_enforces_declared_additional_properties_boundary():
    schema = {"type": "object", "additionalProperties": False,
              "required": ["packet"], "properties": {"packet": {"type": "string"}}}
    assert schema_failures(schema, {"packet": "ok", "schema_copy": {}}) == (
        "additionalProperty:schema_copy",
    )


def test_structure_transport_strips_only_known_schema_copy_metadata():
    raw = {"item_1_packet": "rivals and contrast", "type": "object",
           "required": ["item_1_packet"], "additionalProperties": False}
    payload = normalize_contrastive_batch_payload(
        raw, item_ids=("ratio-27",), evidence_refs=EVIDENCE_REFS,
    )
    assert payload["packets"][0]["contrastive_packet"] == "rivals and contrast"
    try:
        normalize_contrastive_batch_payload(
            {**raw, "unknown": "noise"}, item_ids=("ratio-27",),
            evidence_refs=EVIDENCE_REFS,
        )
    except ValueError as exc:
        assert str(exc) == "contrastive_structure_provider_payload_shape_invalid"
    else:
        raise AssertionError("unknown Provider metadata passed transport normalization")


def test_structure_adapter_avoids_full_schema_and_hashes_raw_provider_output():
    class Pool:
        def __init__(self):
            self.messages = None

        def generate_json(self, **values):
            self.messages = values["messages"]
            result = {"item_1_packet": "two rivals; contrast; which observation decides?",
                      "type": "object", "required": ["item_1_packet"]}
            return LocalStructuredGeneration(result, str(result), 20, 12, 3)

    harness, pool, ledger = build_quality_gated_structural_harness(), Pool(), ProviderTelemetryLedger()
    task = ProviderCognitiveTask(
        task_id="structure", task_kind="pilot_object_structure_expansion",
        objective="expand", inputs={
            "benchmark_public_input": harness.provider_inputs(("ratio-27",)),
            "benchmark_item_ids": ["ratio-27"],
            "round_context": {"role": "batched_contrastive_structure_elicitor"},
        }, allowed_evidence=list(EVIDENCE_REFS),
        expected_schema={"required": ["item_1_packet"]}, timeout_seconds=10,
    )
    adapter = LocalQualityGatedStructureAdapter(
        provider_id="local", model_id="small", task_kinds=(task.task_kind,),
        pool=pool, telemetry_ledger=ledger, max_attempts=1,
    )
    envelope = adapter.invoke(task)
    assert envelope["result"]["type"] == "object"
    assert ledger.items()[0].output_hash == hash_payload(envelope["result"])
    prompt = pool.messages[1]["content"]
    assert "JSON schema" not in prompt and "Shape example" not in prompt
    assert "<two rival structures" not in prompt

