from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(Path(__file__).resolve().parents[1])]

from local_collective_cognition.calibrated_enum_scoring import CalibratedEnumScore  # noqa: E402
from local_collective_cognition.collective_protocol import PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol  # noqa: E402
from local_collective_cognition.holdout_v22_benchmark import (  # noqa: E402
    HOLDOUT_V22_EVIDENCE_REFS, HOLDOUT_V22_QUESTIONS, build_holdout_v22_harness,
)
from local_collective_cognition.local_problem_formulation_provider import LocalProblemFormulationAdapter  # noqa: E402
from local_collective_cognition.plan_intent_contracts import validate_plan_intent_receipt  # noqa: E402
from local_collective_cognition.problem_admission_gate import ProblemAdmissionKernelGate  # noqa: E402
from local_collective_cognition.problem_formulation_case_runtime import ProblemFormulationCaseRuntime  # noqa: E402
from local_collective_cognition.problem_formulation_contracts import validate_problem_definition_receipt  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


class PlannedPool:
    def __init__(self, plan):
        self.plan = {key: list(value) for key, value in plan.items()}
        self.cached = set()

    def score_calibrated_enum(self, *, model_id, messages, options):
        stage = messages[-1]["content"].split("Decision stage: ", 1)[1].splitlines()[0]
        selected = self.plan[stage].pop(0)
        assert selected in options
        count = len(options)
        probs = [1.0] if count == 1 else [
            0.8 if item == selected else 0.2 / (count - 1) for item in options
        ]
        prior = [round(1.0 / count, 12)] * count
        prior[-1] = round(1.0 - sum(prior[:-1]), 12)
        ranked = sorted(probs, reverse=True); cached = count in self.cached; self.cached.add(count)
        return CalibratedEnumScore(
            selected=selected,
            scores=tuple({"option": item, "label": chr(65 + index),
                          "probability": probs[index], "context_probability": probs[index],
                          "prior_probability": prior[index],
                          "calibrated_log_ratio": math.log(probs[index] / prior[index])}
                         for index, item in enumerate(options)),
            selected_probability=max(probs), margin=ranked[0] - (ranked[1] if count > 1 else 0),
            entropy=0.5, input_tokens=10 if cached else 20, latency_ms=1,
            inference_passes=1 if cached else 2,
            calibration_ref=hash_payload({"model_id": model_id, "menu_size": count,
                                          "probabilities": prior}),
            calibration_cached=cached,
        )


def _problem_plan(final="B"):
    return {"PROBLEM_MODE": ["NUMERIC_DERIVATION"],
            "PROBLEM_FAMILY": ["ARITHMETIC_COMPOSITION"],
            "TARGET_KIND": ["FINAL_SCALAR"],
            "CRITICAL_CONSTRAINT": ["ORDER_SENSITIVE"],
            "ACTION": ["APPLY", "APPLY", "FINALIZE"],
            "OPERATOR": ["MULTIPLY", "SUBTRACT"],
            "OPERAND_1": ["VALUE_1", "STEP_1"],
            "OPERAND_2": ["VALUE_2", "VALUE_3"],
            "RESULT_STEP": ["STEP_2"], "CANDIDATE": [final]}


def _runtime_fixture():
    ledger = ProviderTelemetryLedger()
    plans = {"small-a": _problem_plan(), "small-b": _problem_plan(),
             "small-c": {"PROBLEM_COORDINATION": ["PROBLEM_1"],
                         "JUDGMENT": ["CANDIDATE_1"]}}
    adapters = {model: LocalProblemFormulationAdapter(
        provider_id="fixture-" + model, model_id=model, task_kinds=PILOT_TASK_KINDS,
        pool=PlannedPool(plan), telemetry_ledger=ledger, max_attempts=1,
    ) for model, plan in plans.items()}
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v22_harness(), small_adapters=adapters,
        baseline_adapter=None, telemetry_ledger=ledger,
        reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    bundle = ProblemFormulationCaseRuntime(base).adjudicate(
        primary=SimpleNamespace(item_id="arithmetic-23", model_id="small-a", answer="D"),
        peer=SimpleNamespace(item_id="arithmetic-23", model_id="small-b", answer="B"),
        witness=SimpleNamespace(item_id="arithmetic-23", model_id="small-c", answer="B"),
    )
    return bundle, base.harness


def test_problem_formulation_admits_binds_and_replays_before_judgment():
    bundle, harness = _runtime_fixture()
    admissions = []
    for run in (bundle.primary_argument_run, bundle.peer_argument_run):
        definition = run.result["problem_definition_receipt"]
        validate_problem_definition_receipt(definition)
        assert definition["problem_family"] == "ARITHMETIC_COMPOSITION"
        validate_plan_intent_receipt(run.result["plan_intent_receipt"])
        assert run.result["problem_plan_binding_receipt"]["status"] == "ALLOW"
        admissions.append(run.result["problem_admission_receipt"])
    assert admissions[0]["receipt_hash"] == admissions[1]["receipt_hash"]
    audit = harness.audit_problem_definitions(
        experiment_id="fixture", admission_receipts=(admissions[0],),
        candidate_receipts=tuple(
            run.result["problem_definition_receipt"]
            for run in (bundle.primary_argument_run, bundle.peer_argument_run)
        ),
    )
    assert audit["exact_problem_definitions"] == audit["admitted_items"] == 1
    assert audit["exact_candidate_definitions"] == 2
    assert audit["candidate_union_exact_items"] == 1
    assert len(bundle.judge_run.telemetry) == 2


def test_problem_plan_binding_rejects_rehashed_nested_problem_tamper():
    bundle, _ = _runtime_fixture()
    run = bundle.primary_argument_run.result
    admission = {**run["problem_admission_receipt"],
                 "selected_problem": dict(run["problem_admission_receipt"]["selected_problem"])}
    admission["selected_problem"]["problem_family"] = "MODULAR_REMAINDER"
    committed = {key: value for key, value in admission.items() if key != "receipt_hash"}
    admission["receipt_hash"] = hash_payload(committed)
    binding = ProblemAdmissionKernelGate().bind_plan(
        admission_receipt=admission, plan_receipt=run["plan_intent_receipt"],
    )
    assert binding["status"] == "BLOCK"
    assert "PROBLEM_ADMISSION_SELECTED_RECEIPT_INVALID" in binding["reasons"]


def test_problem_admission_blocks_consensus_abstention():
    bundle, _ = _runtime_fixture()
    definitions = []
    for run in (bundle.primary_argument_run, bundle.peer_argument_run):
        value = dict(run.result["problem_definition_receipt"])
        value.update({"intent_mode": "ABSTAIN", "problem_family": "ABSTAIN",
                      "target_kind": "ABSTAIN", "critical_constraint": "ABSTAIN"})
        value["receipt_hash"] = hash_payload(
            {key: item for key, item in value.items() if key != "receipt_hash"}
        )
        definitions.append(value)
    coordination = dict(bundle.judge_run.result["problem_coordination_receipt"])
    coordination["candidate_receipt_hashes"] = [item["receipt_hash"] for item in definitions]
    coordination["receipt_hash"] = hash_payload(
        {key: item for key, item in coordination.items() if key != "receipt_hash"}
    )
    admission = ProblemAdmissionKernelGate().evaluate(
        candidate_receipts=definitions, coordination_receipt=coordination,
        inference_passes=1, input_tokens=1,
    )
    assert admission["status"] == "BLOCK"
    assert admission["reasons"] == ["PROBLEM_DEFINITION_ABSTAINED"]


def test_holdout_v22_reference_plans_cover_all_problem_families():
    plans = {
        "arithmetic-23": ("B", (("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("STEP_1", "VALUE_3")))),
        "rate-23": ("B", (("DIVIDE", ("VALUE_1", "VALUE_2")), ("MULTIPLY", ("STEP_1", "VALUE_3")))),
        "percent-23": ("C", (("DIVIDE", ("VALUE_1", "CONST_100")), ("MULTIPLY", ("STEP_1", "VALUE_2")))),
        "sets-23": ("C", (("ADD", ("VALUE_2", "VALUE_3")), ("SUBTRACT", ("STEP_1", "VALUE_4")), ("SUBTRACT", ("VALUE_1", "STEP_2")))),
        "probability-23": ("B", (("ADD", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("VALUE_1", "STEP_1")), ("SUBTRACT", ("VALUE_1", "CONST_1")), ("SUBTRACT", ("STEP_1", "CONST_1")), ("DIVIDE", ("STEP_3", "STEP_4")), ("MULTIPLY", ("STEP_2", "STEP_5")), ("SUBTRACT", ("CONST_1", "STEP_6")))),
        "bayes-23": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("CONST_100", "VALUE_1")), ("SUBTRACT", ("CONST_100", "VALUE_3")), ("MULTIPLY", ("STEP_2", "STEP_3")), ("ADD", ("STEP_1", "STEP_4")), ("DIVIDE", ("STEP_1", "STEP_5")))),
        "modular-23": ("C", (("MODULO", ("VALUE_1", "VALUE_2")),)),
        "ratio-23": ("B", (("ADD", ("VALUE_2", "VALUE_3")), ("MULTIPLY", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("STEP_2", "STEP_1")))),
        "average-23": ("B", (("ADD", ("VALUE_1", "VALUE_2")), ("ADD", ("STEP_1", "VALUE_3")), ("ADD", ("STEP_2", "VALUE_4")), ("ADD", ("STEP_3", "VALUE_5")), ("DIVIDE", ("STEP_4", "VALUE_6")))),
        "code-23": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_5")), ("ADD", ("STEP_1", "VALUE_2")), ("MULTIPLY", ("STEP_2", "VALUE_5")), ("ADD", ("STEP_3", "VALUE_3")), ("MULTIPLY", ("STEP_4", "VALUE_5")), ("ADD", ("STEP_5", "VALUE_4")))),
        "string-23": ("D", (("SWAP_HALVES", ("VALUE_1",)), ("REVERSE_PAIRS", ("STEP_1",)))),
        "unit-23": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_2")),)),
    }
    harness = build_holdout_v22_harness()
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
    assert len(plans) == len(HOLDOUT_V22_QUESTIONS) == 12


def _action(item_id, action, operator, inputs, proposed):
    return {"item_id": item_id, "candidate_id": "CANDIDATE_1", "action": action,
            "operator": operator, "inputs": inputs, "proposed_candidate": proposed,
            "evidence_refs": list(HOLDOUT_V22_EVIDENCE_REFS)}
