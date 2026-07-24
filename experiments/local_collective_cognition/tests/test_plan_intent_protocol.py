from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "agentos_core_slim_v0"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_collective_cognition.calibrated_enum_scoring import CalibratedEnumScore  # noqa: E402
from local_collective_cognition.calibrated_score_receipt import validate_calibrated_score_receipt  # noqa: E402
from local_collective_cognition.collective_protocol import (  # noqa: E402
    PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol,
)
from local_collective_cognition.holdout_v21_benchmark import (  # noqa: E402
    HOLDOUT_V21_EVIDENCE_REFS, HOLDOUT_V21_QUESTIONS, build_holdout_v21_harness,
)
from local_collective_cognition.iterative_derivation_receipt import IterativeStepReceipt  # noqa: E402
from local_collective_cognition.local_plan_intent_provider import LocalPlanIntentAdapter  # noqa: E402
from local_collective_cognition.plan_consistency_gate import (  # noqa: E402
    PlanConsistencyKernelGate, PlanIntentBudget,
)
from local_collective_cognition.plan_intent_case_runtime import PlanIntentCaseRuntime  # noqa: E402
from local_collective_cognition.plan_intent_contracts import validate_plan_intent_receipt  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402
from local_collective_cognition.failure_decision_accounting import failed_decision_artifacts  # noqa: E402


class PlannedCalibratedPool:
    def __init__(self, plan):
        self.plan = {key: list(value) for key, value in plan.items()}
        self.cached_sizes = set()

    def score_calibrated_enum(self, *, model_id, messages, options):
        stage = messages[-1]["content"].split("Decision stage: ", 1)[1].splitlines()[0]
        selected = self.plan[stage].pop(0)
        assert selected in options
        count = len(options)
        probabilities = ([1.0] if count == 1 else
                         [0.8 if item == selected else 0.2 / (count - 1) for item in options])
        prior = [1.0 / count] * count
        ranked = sorted(probabilities, reverse=True)
        cached = count in self.cached_sizes
        self.cached_sizes.add(count)
        return CalibratedEnumScore(
            selected=selected,
            scores=tuple({"option": item, "label": chr(65 + index),
                          "probability": probabilities[index],
                          "context_probability": probabilities[index],
                          "prior_probability": prior[index],
                          "calibrated_log_ratio": math.log(probabilities[index] / prior[index])}
                         for index, item in enumerate(options)),
            selected_probability=max(probabilities),
            margin=ranked[0] - (ranked[1] if count > 1 else 0.0), entropy=0.5,
            input_tokens=10 if cached else 20, latency_ms=2,
            inference_passes=1 if cached else 2,
            calibration_ref=hash_payload({"model_id": model_id, "menu_size": count,
                                          "probabilities": prior}),
            calibration_cached=cached,
        )


def _adapter(model_id, plan, ledger):
    return LocalPlanIntentAdapter(
        provider_id="fixture-" + model_id, model_id=model_id,
        task_kinds=PILOT_TASK_KINDS, pool=PlannedCalibratedPool(plan),
        telemetry_ledger=ledger, max_attempts=1,
    )


def _arithmetic_plan():
    return {"INTENT_MODE": ["NUMERIC_DERIVATION"],
            "ACTION": ["APPLY", "APPLY", "FINALIZE"],
            "OPERATOR": ["MULTIPLY", "SUBTRACT"],
            "OPERAND_1": ["VALUE_1", "STEP_1"],
            "OPERAND_2": ["VALUE_2", "VALUE_3"],
            "RESULT_STEP": ["STEP_2"], "CANDIDATE": ["B"]}


def _closed_case():
    ledger = ProviderTelemetryLedger()
    adapters = {"small-a": _adapter("small-a", _arithmetic_plan(), ledger),
                "small-b": _adapter("small-b", _arithmetic_plan(), ledger),
                "small-c": _adapter("small-c", {"JUDGMENT": ["CANDIDATE_1"]}, ledger)}
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v21_harness(), small_adapters=adapters,
        baseline_adapter=None, telemetry_ledger=ledger,
        reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    bundle = PlanIntentCaseRuntime(base).adjudicate(
        primary=SimpleNamespace(item_id="arithmetic-22", model_id="small-a", answer="D"),
        peer=SimpleNamespace(item_id="arithmetic-22", model_id="small-b", answer="B"),
        witness=SimpleNamespace(item_id="arithmetic-22", model_id="small-c", answer="B"),
    )
    return bundle, ledger, base.harness


def test_plan_intent_closes_calibrated_plan_gate_and_judge():
    bundle, ledger, _ = _closed_case()
    assert [item.status for item in bundle.verification_receipts] == ["VERIFIED", "VERIFIED"]
    for run in (bundle.primary_argument_run, bundle.peer_argument_run):
        plan = run.result["plan_intent_receipt"]
        validate_plan_intent_receipt(plan)
        assert plan["intent_mode"] == "NUMERIC_DERIVATION"
        assert [item["operator"] for item in plan["planned_actions"]] == ["MULTIPLY", "SUBTRACT"]
        assert run.result["plan_gate_receipt"]["status"] == "ALLOW"
        assert all(validate_calibrated_score_receipt(item) is None
                   for item in run.result["decision_receipts"])
    validate_calibrated_score_receipt(bundle.judgment["decision_receipt"])
    assert len(ledger.items()) == 7


def test_plan_kernel_gate_blocks_replay_valid_plan_over_budget():
    bundle, _, harness = _closed_case()
    run = bundle.primary_argument_run.result
    previews = tuple(_step_from_dict(item) for item in run["planning_preview_receipts"])
    gate = PlanConsistencyKernelGate(
        harness, budget=PlanIntentBudget(max_turns=2, max_inference_passes=24,
                                         max_input_tokens=14000),
    )
    outcome = gate.evaluate(receipt=run["plan_intent_receipt"], preview_receipts=previews)
    assert outcome.status == "BLOCK"
    assert outcome.reasons == ("PLAN_TURN_BUDGET_EXCEEDED",)
    assert outcome.final_receipt is None and outcome.gate_receipt["provider_authority"] is False
    assert _receipt_hash_valid(outcome.gate_receipt)
    budget_stop = gate.budget_stop_receipt(
        item_id="arithmetic-22", candidate_id="CANDIDATE_1", turns=2,
        inference_passes=25, input_tokens=100, reason="plan_inference_budget_exceeded",
    )
    assert budget_stop["status"] == "BLOCK" and budget_stop["kernel_owned"] is True
    assert budget_stop["provider_authority"] is False and _receipt_hash_valid(budget_stop)


def test_plan_intent_rejects_rehashed_mode_operator_drift():
    bundle, _, _ = _closed_case()
    plan = dict(bundle.primary_argument_run.result["plan_intent_receipt"])
    plan["intent_mode"] = "STRING_TRANSFORMATION"
    committed = {key: value for key, value in plan.items() if key != "receipt_hash"}
    plan["receipt_hash"] = hash_payload(committed)
    with pytest.raises(ValueError, match="mode_operator_mismatch"):
        validate_plan_intent_receipt(plan)


def test_calibrated_receipt_rejects_rehashed_prior_distribution_tamper():
    bundle, _, _ = _closed_case()
    receipt = dict(bundle.primary_argument_run.result["decision_receipts"][0])
    receipt["decisions"] = [dict(item) for item in receipt["decisions"]]
    receipt["decisions"][0]["scores"] = [dict(item) for item in receipt["decisions"][0]["scores"]]
    scores = receipt["decisions"][0]["scores"]
    scores[0]["prior_probability"] += 0.01
    scores[1]["prior_probability"] -= 0.01
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    receipt["receipt_hash"] = hash_payload(committed)
    with pytest.raises(ValueError, match="selection"):
        validate_calibrated_score_receipt(receipt)


def test_failed_plan_work_preserves_decision_and_budget_receipts():
    budget = {"receipt_hash": "b" * 64}
    decision = {"receipt_hash": "d" * 64}
    artifacts = failed_decision_artifacts((SimpleNamespace(result={
        "decision_receipts": [decision], "plan_budget_receipt": budget,
    }),))
    assert artifacts["failed_decision_receipts"] == [decision]
    assert artifacts["failed_plan_budget_receipts"] == [budget]


def test_holdout_v21_replays_all_reference_plan_families():
    plans = {
        "arithmetic-22": ("B", (("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("STEP_1", "VALUE_3")))),
        "rate-22": ("B", (("DIVIDE", ("VALUE_1", "VALUE_2")), ("MULTIPLY", ("STEP_1", "VALUE_3")))),
        "percent-22": ("B", (("DIVIDE", ("VALUE_1", "CONST_100")), ("MULTIPLY", ("STEP_1", "VALUE_2")))),
        "sets-22": ("C", (("ADD", ("VALUE_2", "VALUE_3")), ("SUBTRACT", ("STEP_1", "VALUE_4")), ("SUBTRACT", ("VALUE_1", "STEP_2")))),
        "probability-22": ("C", (("ADD", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("VALUE_1", "STEP_1")), ("SUBTRACT", ("VALUE_1", "CONST_1")), ("SUBTRACT", ("STEP_1", "CONST_1")), ("DIVIDE", ("STEP_3", "STEP_4")), ("MULTIPLY", ("STEP_2", "STEP_5")), ("SUBTRACT", ("CONST_1", "STEP_6")))),
        "bayes-22": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("CONST_100", "VALUE_1")), ("SUBTRACT", ("CONST_100", "VALUE_3")), ("MULTIPLY", ("STEP_2", "STEP_3")), ("ADD", ("STEP_1", "STEP_4")), ("DIVIDE", ("STEP_1", "STEP_5")))),
        "modular-22": ("C", (("MODULO", ("VALUE_1", "VALUE_2")),)),
        "ratio-22": ("C", (("ADD", ("VALUE_2", "VALUE_3")), ("MULTIPLY", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("STEP_2", "STEP_1")))),
        "average-22": ("C", (("ADD", ("VALUE_1", "VALUE_2")), ("ADD", ("STEP_1", "VALUE_3")), ("ADD", ("STEP_2", "VALUE_4")), ("ADD", ("STEP_3", "VALUE_5")), ("DIVIDE", ("STEP_4", "VALUE_6")))),
        "code-22": ("D", (("MULTIPLY", ("VALUE_1", "VALUE_5")), ("ADD", ("STEP_1", "VALUE_2")), ("MULTIPLY", ("STEP_2", "VALUE_5")), ("ADD", ("STEP_3", "VALUE_3")), ("MULTIPLY", ("STEP_4", "VALUE_5")), ("ADD", ("STEP_5", "VALUE_4")))),
        "string-22": ("A", (("SWAP_HALVES", ("VALUE_1",)), ("REVERSE_PAIRS", ("STEP_1",)))),
        "unit-22": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_2")),)),
    }
    harness = build_holdout_v21_harness()
    for item_id, (answer, plan) in plans.items():
        symbols, receipts = dict(harness.derivation_scaffold(item_id)), []
        for index, (operator, inputs) in enumerate(plan, 1):
            action = _action(item_id, "APPLY", operator, list(inputs), "PENDING")
            receipt = harness.execute_derivation_step(
                item_id=item_id, candidate_id="CANDIDATE_1", step_id=f"STEP_{index}",
                action=action, symbol_values=symbols,
            )
            receipts.append(receipt); symbols[receipt.step_id] = receipt.result
        final = harness.finalize_derivation_session(
            item_id=item_id, candidate_id="CANDIDATE_1", original_candidate="A",
            action=_action(item_id, "FINALIZE", "NONE", [f"STEP_{len(receipts)}"], answer),
            step_receipts=tuple(receipts), provider_turns=len(receipts) + 1, invalid_actions=0,
        )
        assert final.status == "VERIFIED"
    assert len(plans) == len(HOLDOUT_V21_QUESTIONS) == 12


def _step_from_dict(value):
    return IterativeStepReceipt(**{**value, "inputs": tuple(value["inputs"])})


def _action(item_id, action, operator, inputs, proposed):
    return {"item_id": item_id, "candidate_id": "CANDIDATE_1", "action": action,
            "operator": operator, "inputs": inputs, "proposed_candidate": proposed,
            "evidence_refs": list(HOLDOUT_V21_EVIDENCE_REFS)}


def _receipt_hash_valid(receipt):
    return receipt["receipt_hash"] == hash_payload(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )
