from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "agentos_core_slim_v0"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import ProviderCognitiveTask  # noqa: E402
from local_collective_cognition.collective_protocol import (  # noqa: E402
    PILOT_TASK_KINDS, LocalCollectiveCognitionProtocol,
)
from local_collective_cognition.enum_scoring import EnumScore  # noqa: E402
from local_collective_cognition.hierarchical_score_receipt import validate_score_receipt  # noqa: E402
from local_collective_cognition.hierarchical_tool_channel import (  # noqa: E402
    action_options, build_hierarchical_channel, operand_options, validate_hierarchical_channel,
)
from local_collective_cognition.hierarchical_tool_case_runtime import HierarchicalToolCaseRuntime  # noqa: E402
from local_collective_cognition.holdout_v20_benchmark import (  # noqa: E402
    HOLDOUT_V20_EVIDENCE_REFS, HOLDOUT_V20_QUESTIONS, build_holdout_v20_harness,
)
from local_collective_cognition.iterative_derivation_contracts import iterative_action_schema  # noqa: E402
from local_collective_cognition.local_hierarchical_tool_provider import (  # noqa: E402
    HIERARCHICAL_TOOL_TASK_KIND, LocalHierarchicalToolAdapter,
)
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger  # noqa: E402


class PlannedScorePool:
    def __init__(self, plan):
        self.plan = {key: list(value) for key, value in plan.items()}
        self.messages = []

    def score_enum(self, *, model_id, messages, options):
        self.messages.append(messages)
        stage = messages[-1]["content"].split("Decision stage: ", 1)[1].splitlines()[0]
        selected = self.plan[stage].pop(0)
        assert selected in options
        probabilities = ([1.0] if len(options) == 1 else
                         [0.8 if item == selected else 0.2 / (len(options) - 1)
                          for item in options])
        selected_probability = probabilities[list(options).index(selected)]
        ranked = sorted(probabilities, reverse=True)
        return EnumScore(
            selected=selected,
            scores=tuple({"option": item, "label": chr(65 + index),
                          "probability": probabilities[index]}
                         for index, item in enumerate(options)),
            selected_probability=selected_probability,
            margin=ranked[0] - (ranked[1] if len(ranked) > 1 else 0.0), entropy=0.5,
            input_tokens=17, latency_ms=2,
        )


def _adapter(plan):
    ledger = ProviderTelemetryLedger()
    adapter = LocalHierarchicalToolAdapter(
        provider_id="fixture-provider", model_id="fixture-model",
        task_kinds=PILOT_TASK_KINDS, pool=PlannedScorePool(plan),
        telemetry_ledger=ledger, max_attempts=1,
    )
    return adapter, ledger


def _action_task(channel):
    return ProviderCognitiveTask(
        task_id="hierarchical-action-fixture", task_kind=HIERARCHICAL_TOOL_TASK_KIND,
        objective="derive", inputs={"benchmark_item_ids": ["arithmetic-21"],
            "benchmark_public_input": [], "round_context": {
                "role": "hierarchical_derivation_tool_user", "candidate_id": "CANDIDATE_1",
                "available_symbols": channel["symbol_values"],
                "hierarchical_tool_channel": channel}},
        allowed_evidence=list(HOLDOUT_V20_EVIDENCE_REFS),
        expected_schema=iterative_action_schema(
            "arithmetic-21", "CANDIDATE_1", tuple(channel["symbol_values"]),
        ), timeout_seconds=60,
    )


def test_hierarchical_channel_filters_invalid_and_repeated_pairs():
    channel = build_hierarchical_channel(
        symbol_values={"VALUE_1": "8", "VALUE_2": "0", "VALUE_3": "2"},
        prior_actions=({"action": "APPLY", "operator": "DIVIDE",
                        "inputs": ["VALUE_1", "VALUE_3"]},),
    )
    validate_hierarchical_channel(channel)
    assert action_options(channel) == ("APPLY", "ABSTAIN")
    assert "VALUE_2" not in operand_options(channel, "DIVIDE", left="VALUE_1")
    assert "VALUE_3" not in operand_options(channel, "DIVIDE", left="VALUE_1")


def test_hierarchical_action_is_scored_and_receipted():
    channel = build_hierarchical_channel(symbol_values={"VALUE_1": "86", "VALUE_2": "4"})
    adapter, ledger = _adapter({
        "ACTION": ["APPLY"], "OPERATOR": ["MULTIPLY"],
        "OPERAND_1": ["VALUE_1"], "OPERAND_2": ["VALUE_2"],
    })
    task = _action_task(channel)
    result = adapter.invoke(task)["result"]
    receipt = result["decision_receipt"]
    validate_score_receipt(receipt, task=task)
    assert result["operator"] == "MULTIPLY" and result["inputs"] == ["VALUE_1", "VALUE_2"]
    assert receipt["inference_passes"] == 4
    assert receipt["menu_option_total"] < 30
    operand_two_prompt = adapter.pool.messages[3][-1]["content"]
    assert '"stage": "OPERATOR", "selected": "MULTIPLY"' in operand_two_prompt
    assert '"stage": "OPERAND_1", "selected": "VALUE_1"' in operand_two_prompt
    telemetry = ledger.items()[0]
    assert telemetry.tool_calls == 4 and telemetry.output_hash


def test_hierarchical_judge_uses_bounded_choice_and_persists_scores():
    adapter, ledger = _adapter({"JUDGMENT": ["CANDIDATE_2"]})
    task = ProviderCognitiveTask(
        task_id="hierarchical-judge-fixture", task_kind="pilot_disagreement_adjudication",
        objective="judge", inputs={"benchmark_item_ids": ["arithmetic-21"],
            "benchmark_public_input": [], "round_context": {
                "role": "blinded_verified_case_judge",
                "candidate_records": [{"candidate_id": "CANDIDATE_1"},
                                      {"candidate_id": "CANDIDATE_2"}]}},
        allowed_evidence=list(HOLDOUT_V20_EVIDENCE_REFS),
        expected_schema={"type": "object", "required": ["selected_candidate"],
                         "properties": {"selected_candidate": {"type": "string"}}},
        timeout_seconds=60,
    )
    result = adapter.invoke(task)["result"]
    validate_score_receipt(result["decision_receipt"], task=task)
    assert result["selected_candidate"] == "CANDIDATE_2"
    assert result["confidence"] == 0.8 and result["adjudicability"] == "ADJUDICABLE"
    assert ledger.items()[0].backend == "transformers-cuda-hierarchical-enum"


def test_hierarchical_score_receipt_detects_tampering():
    channel = build_hierarchical_channel(symbol_values={"VALUE_1": "2", "VALUE_2": "3"})
    adapter, _ = _adapter({"ACTION": ["ABSTAIN"]})
    task = _action_task(channel)
    receipt = adapter.invoke(task)["result"]["decision_receipt"]
    receipt["selected_value"] = "FINALIZE(STEP_9,A)"
    with pytest.raises(ValueError, match="receipt_binding"):
        validate_score_receipt(receipt, task=task)


def test_hierarchical_score_receipt_rejects_rehashed_false_distribution():
    from local_collective_cognition.provider_telemetry import hash_payload

    channel = build_hierarchical_channel(symbol_values={"VALUE_1": "2", "VALUE_2": "3"})
    adapter, _ = _adapter({"ACTION": ["ABSTAIN"]})
    task = _action_task(channel)
    receipt = adapter.invoke(task)["result"]["decision_receipt"]
    receipt["decisions"][0]["scores"][0]["probability"] = 0.99
    committed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    receipt["receipt_hash"] = hash_payload(committed)
    with pytest.raises(ValueError, match="distribution"):
        validate_score_receipt(receipt, task=task)


def test_hierarchical_case_closes_two_sessions_and_constrained_judge():
    ledger = ProviderTelemetryLedger()
    session_plan = {
        "ACTION": ["APPLY", "APPLY", "FINALIZE"],
        "OPERATOR": ["MULTIPLY", "SUBTRACT"],
        "OPERAND_1": ["VALUE_1", "STEP_1"],
        "OPERAND_2": ["VALUE_2", "VALUE_3"],
        "RESULT_STEP": ["STEP_2"], "CANDIDATE": ["B"],
    }
    adapters = {
        "small-a": LocalHierarchicalToolAdapter(
            provider_id="fixture-a", model_id="small-a", task_kinds=PILOT_TASK_KINDS,
            pool=PlannedScorePool(session_plan), telemetry_ledger=ledger, max_attempts=1,
        ),
        "small-b": LocalHierarchicalToolAdapter(
            provider_id="fixture-b", model_id="small-b", task_kinds=PILOT_TASK_KINDS,
            pool=PlannedScorePool(session_plan), telemetry_ledger=ledger, max_attempts=1,
        ),
        "small-c": LocalHierarchicalToolAdapter(
            provider_id="fixture-c", model_id="small-c", task_kinds=PILOT_TASK_KINDS,
            pool=PlannedScorePool({"JUDGMENT": ["CANDIDATE_1"]}),
            telemetry_ledger=ledger, max_attempts=1,
        ),
    }
    base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v20_harness(), small_adapters=adapters,
        baseline_adapter=None, telemetry_ledger=ledger,
        reviewer_model_id="small-b", synthesizer_model_id="small-c",
    )
    bundle = HierarchicalToolCaseRuntime(base).adjudicate(
        primary=SimpleNamespace(item_id="arithmetic-21", model_id="small-a", answer="D"),
        peer=SimpleNamespace(item_id="arithmetic-21", model_id="small-b", answer="B"),
        witness=SimpleNamespace(item_id="arithmetic-21", model_id="small-c", answer="B"),
    )
    assert [item.status for item in bundle.verification_receipts] == ["VERIFIED", "VERIFIED"]
    assert all(len(run.result["decision_receipts"]) == 3
               for run in (bundle.primary_argument_run, bundle.peer_argument_run))
    assert bundle.judgment["decision_receipt"]["decisions"][0]["stage"] == "JUDGMENT"
    assert len(ledger.items()) == 7


def test_holdout_v20_harness_replays_all_reference_families():
    plans = {
        "arithmetic-21": ("B", (("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("STEP_1", "VALUE_3")))),
        "rate-21": ("B", (("DIVIDE", ("VALUE_1", "VALUE_2")), ("MULTIPLY", ("STEP_1", "VALUE_3")))),
        "percent-21": ("C", (("DIVIDE", ("VALUE_1", "CONST_100")), ("MULTIPLY", ("STEP_1", "VALUE_2")))),
        "sets-21": ("C", (("ADD", ("VALUE_2", "VALUE_3")), ("SUBTRACT", ("STEP_1", "VALUE_4")), ("SUBTRACT", ("VALUE_1", "STEP_2")))),
        "probability-21": ("C", (("ADD", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("VALUE_1", "STEP_1")), ("SUBTRACT", ("VALUE_1", "CONST_1")), ("SUBTRACT", ("STEP_1", "CONST_1")), ("DIVIDE", ("STEP_3", "STEP_4")), ("MULTIPLY", ("STEP_2", "STEP_5")), ("SUBTRACT", ("CONST_1", "STEP_6")))),
        "bayes-21": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_2")), ("SUBTRACT", ("CONST_100", "VALUE_1")), ("SUBTRACT", ("CONST_100", "VALUE_3")), ("MULTIPLY", ("STEP_2", "STEP_3")), ("ADD", ("STEP_1", "STEP_4")), ("DIVIDE", ("STEP_1", "STEP_5")))),
        "modular-21": ("B", (("MODULO", ("VALUE_1", "VALUE_2")),)),
        "ratio-21": ("C", (("ADD", ("VALUE_2", "VALUE_3")), ("MULTIPLY", ("VALUE_1", "VALUE_2")), ("DIVIDE", ("STEP_2", "STEP_1")))),
        "average-21": ("C", (("ADD", ("VALUE_1", "VALUE_2")), ("ADD", ("STEP_1", "VALUE_3")), ("ADD", ("STEP_2", "VALUE_4")), ("ADD", ("STEP_3", "VALUE_5")), ("DIVIDE", ("STEP_4", "VALUE_6")))),
        "code-21": ("C", (("MULTIPLY", ("VALUE_1", "VALUE_5")), ("ADD", ("STEP_1", "VALUE_2")), ("MULTIPLY", ("STEP_2", "VALUE_5")), ("ADD", ("STEP_3", "VALUE_3")), ("MULTIPLY", ("STEP_4", "VALUE_5")), ("ADD", ("STEP_5", "VALUE_4")))),
        "string-21": ("A", (("SWAP_HALVES", ("VALUE_1",)), ("REVERSE_PAIRS", ("STEP_1",)))),
        "unit-21": ("B", (("MULTIPLY", ("VALUE_1", "VALUE_2")),)),
    }
    harness = build_holdout_v20_harness()
    for item_id, (answer, plan) in plans.items():
        symbols, receipts = dict(harness.derivation_scaffold(item_id)), []
        for index, (operator, inputs) in enumerate(plan, 1):
            action = _action(item_id, "CANDIDATE_1", "APPLY", operator, list(inputs), "PENDING")
            receipt = harness.execute_derivation_step(
                item_id=item_id, candidate_id="CANDIDATE_1", step_id=f"STEP_{index}",
                action=action, symbol_values=symbols,
            )
            receipts.append(receipt)
            symbols[receipt.step_id] = receipt.result
        final = harness.finalize_derivation_session(
            item_id=item_id, candidate_id="CANDIDATE_1", original_candidate="D",
            action=_action(item_id, "CANDIDATE_1", "FINALIZE", "NONE",
                           [f"STEP_{len(receipts)}"], answer),
            step_receipts=tuple(receipts), provider_turns=len(receipts) + 1,
            invalid_actions=0,
        )
        assert final.status == "VERIFIED" and final.proposed_candidate == answer
    assert len(plans) == len(HOLDOUT_V20_QUESTIONS) == 12


def _action(item_id, candidate_id, action, operator, inputs, proposed):
    return {"item_id": item_id, "candidate_id": candidate_id, "action": action,
            "operator": operator, "inputs": inputs, "proposed_candidate": proposed,
            "evidence_refs": list(HOLDOUT_V20_EVIDENCE_REFS)}
