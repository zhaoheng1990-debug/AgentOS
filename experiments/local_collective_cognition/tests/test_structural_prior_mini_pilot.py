from __future__ import annotations

import math
import sys
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(Path(__file__).resolve().parents[1])]

from local_collective_cognition.calibrated_enum_scoring import CalibratedEnumScore  # noqa: E402
from local_collective_cognition.collective_protocol import (  # noqa: E402
    PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol,
)
from local_collective_cognition.ephemeral_structural_prior_contracts import validate_structural_prior_receipt  # noqa: E402
from local_collective_cognition.local_problem_formulation_provider import LocalProblemFormulationAdapter  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalStructuredGeneration  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402
from local_collective_cognition.structural_prior_mini_holdout import (  # noqa: E402
    STRUCTURAL_PRIOR_MINI_EVIDENCE_REFS, STRUCTURAL_PRIOR_MINI_QUESTIONS,
    build_structural_prior_mini_harness,
)
from local_collective_cognition.structural_prior_pilot_runtime import StructuralPriorPilotRuntime  # noqa: E402


class HybridPlannedPool:
    def __init__(self, plan, evidence_refs):
        self.plan = {key: list(value) for key, value in plan.items()}
        self.evidence_refs = list(evidence_refs)

    def reset_enum_calibration(self, model_id=None):
        del model_id

    def score_calibrated_enum(self, *, model_id, messages, options):
        stage = messages[-1]["content"].split("Decision stage: ", 1)[1].splitlines()[0]
        selected = self.plan[stage].pop(0)
        count = len(options)
        probs = [1.0] if count == 1 else [
            0.8 if item == selected else 0.2 / (count - 1) for item in options
        ]
        prior = [round(1 / count, 12)] * count
        prior[-1] = round(1 - sum(prior[:-1]), 12)
        ranked = sorted(probs, reverse=True)
        return CalibratedEnumScore(
            selected=selected,
            scores=tuple({
                "option": item, "label": chr(65 + index),
                "probability": probs[index], "context_probability": probs[index],
                "prior_probability": prior[index],
                "calibrated_log_ratio": math.log(probs[index] / prior[index]),
            } for index, item in enumerate(options)),
            selected_probability=max(probs),
            margin=ranked[0] - (ranked[1] if count > 1 else 0), entropy=0.5,
            input_tokens=20, latency_ms=1, inference_passes=2,
            calibration_ref=hash_payload({
                "model_id": model_id, "menu_size": count, "probabilities": prior,
            }),
            calibration_cached=False,
        )

    def generate_json(self, *, model_id, messages, max_new_tokens):
        del model_id, messages, max_new_tokens
        result = {
            "item_id": "modular-25",
            "structure_summary": "A quotient partitions the dividend into full divisor-sized groups and a residual.",
            "entities": ["dividend", "divisor", "remainder"],
            "relations": ["dividend = divisor * quotient + remainder"],
            "invariants": ["the remainder is smaller than the divisor"],
            "boundary_conditions": ["integer division with a nonzero divisor"],
            "discriminating_question": "Is the requested quantity the residual after full groups?",
            "evidence_refs": self.evidence_refs,
        }
        return LocalStructuredGeneration(
            result=result, raw_text="{}", input_tokens=30, output_tokens=20, latency_ms=1,
        )


def _fixture():
    ledger = ProviderTelemetryLedger()
    wrong_then_right = {
        "PROBLEM_MODE": ["STRING_TRANSFORMATION", "NUMERIC_DERIVATION"],
        "PROBLEM_FAMILY": ["STRING_COMPOSITION", "MODULAR_REMAINDER"],
        "TARGET_KIND": ["FINAL_STATE", "REMAINDER"],
        "CRITICAL_CONSTRAINT": ["ORDER_SENSITIVE", "DIVISION_REMAINDER"],
    }
    pools = {
        "small-a": HybridPlannedPool(wrong_then_right, STRUCTURAL_PRIOR_MINI_EVIDENCE_REFS),
        "small-b": HybridPlannedPool({}, STRUCTURAL_PRIOR_MINI_EVIDENCE_REFS),
        "small-c": HybridPlannedPool({}, STRUCTURAL_PRIOR_MINI_EVIDENCE_REFS),
    }
    adapters = {model: LocalProblemFormulationAdapter(
        provider_id="fixture-" + model, model_id=model, task_kinds=PILOT_TASK_KINDS,
        pool=pool, telemetry_ledger=ledger, max_attempts=1,
    ) for model, pool in pools.items()}
    base = LocalCollectiveCognitionProtocol(
        harness=build_structural_prior_mini_harness(), small_adapters=adapters,
        baseline_adapter=None, telemetry_ledger=ledger,
        reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    return StructuralPriorPilotRuntime(base).run(
        experiment_id="fixture",
        assignments=(("modular-25", "small-a", "small-b", "CONTROL_FIRST"),),
    )


def test_structural_prior_paired_runtime_records_object_gain_and_cost():
    report = _fixture()
    audit = report["paired_outcome_receipt"]
    assert audit["control"]["exact_definitions"] == 0
    assert audit["treatment"]["exact_definitions"] == 1
    assert audit["exact_definition_gain"] == 1
    assert report["cognitive_hypothesis_status"] == "PRELIMINARY_EXACT_OBJECT_SUPPORT"
    assert report["hypothesis_status"].endswith("COST_NOT_CLEARED")
    assert report["work"]["cost_gate_passed"] is False
    assert report["work"]["control"]["provider_calls"] == 1
    assert report["work"]["treatment_total"]["provider_calls"] == 2


def test_ephemeral_structural_prior_is_payload_bound_and_not_retainable():
    report = _fixture()
    prior = report["items"][0]["structural_prior"]
    receipt = prior["structural_prior_receipt"]
    payload = {key: value for key, value in prior.items() if key != "structural_prior_receipt"}
    validate_structural_prior_receipt(receipt, payload=payload)
    assert receipt["state"] == "EPHEMERAL_CANDIDATE"
    assert receipt["retention_authorized"] is False
    tampered = {**payload, "structure_summary": "changed"}
    try:
        validate_structural_prior_receipt(receipt, payload=tampered)
    except ValueError as exc:
        assert str(exc) == "structural_prior_payload_binding_invalid"
    else:
        raise AssertionError("tampered structural payload passed validation")


def test_structural_prior_mini_holdout_has_truth_isolation_and_complete_objects():
    harness = build_structural_prior_mini_harness()
    public = harness.provider_inputs()
    assert len(public["questions"]) == len(STRUCTURAL_PRIOR_MINI_QUESTIONS) == 6
    assert "truth" not in str(public).lower()
    assert set(harness._problem_truths) == {item.item_id for item in STRUCTURAL_PRIOR_MINI_QUESTIONS}


def test_structural_prior_mini_holdout_answers_are_mechanically_correct():
    assert 3187 % 61 == 15
    assert Fraction(2310 * 4, 4 + 7) == 840
    assert 850 - (510 + 430 - 240) == 150
    posterior = Fraction(30 * 84, 30 * 84 + (100 - 30) * (100 - 88))
    assert posterior == Fraction(3, 4)
    value = "QRSTUVWX"
    swapped = value[len(value) // 2:] + value[:len(value) // 2]
    transformed = "".join(swapped[index:index + 2][::-1]
                          for index in range(0, len(swapped), 2))
    assert transformed == "VUXWRQTS"
    assert Fraction(72) * Fraction("4.25") == 306
