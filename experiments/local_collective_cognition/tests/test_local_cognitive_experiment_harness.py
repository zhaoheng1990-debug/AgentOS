import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "agentos_core_slim_v0"
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

from agentos_kernel import (  # noqa: E402
    CognitiveWorkBudget,
    ProviderCapabilityProfile,
    ProviderCognitiveTask,
    ProviderTaskRouter,
)
from agentos_runtime import CognitiveWorkAccountingRuntime  # noqa: E402
from local_collective_cognition import (  # noqa: E402
    BenchmarkAnswerTruth,
    BenchmarkQuestion,
    CognitiveWorkExecutionBridge,
    FrozenAnswerBenchmarkHarness,
    LocalStructuredGeneration,
    LocalTransformersJsonAdapter,
    LocalTransformersModelSpec,
    LocalTransformersResidentPool,
    OllamaJsonAdapter,
    ProviderInvocationTelemetry,
    ProviderTelemetryLedger,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.constrained_generation import TokenTrie  # noqa: E402
from local_collective_cognition.constrained_tool_registry import (  # noqa: E402
    build_tool_registry,
    registry_prompt_view,
    validate_tool_registry,
)
from local_collective_cognition.iterative_derivation_contracts import iterative_action_schema  # noqa: E402
from local_collective_cognition.local_constrained_tool_provider import (  # noqa: E402
    CONSTRAINED_TOOL_TASK_KIND,
    LocalConstrainedToolAdapter,
)


EVIDENCE = ("benchmark-source://pilot-v1",)


def task(harness, task_id="benchmark-task-1", *, extra=None):
    inputs = {"benchmark_public_input": harness.provider_inputs(), "round_context": {}}
    inputs.update(extra or {})
    return ProviderCognitiveTask(
        task_id=task_id,
        task_kind="benchmark_answer",
        objective="Answer every public benchmark item.",
        inputs=inputs,
        allowed_evidence=list(EVIDENCE),
        expected_schema={
            "type": "object",
            "required": ["answers", "evidence_refs"],
            "properties": {
                "answers": {"type": "array"},
                "evidence_refs": {"type": "array"},
            },
        },
        timeout_seconds=300,
    )


def harness():
    return FrozenAnswerBenchmarkHarness(
        harness_id="frozen-answer-test",
        benchmark_id="pilot-v1",
        questions=(
            BenchmarkQuestion("q1", "2 + 2 = ?"),
            BenchmarkQuestion("q2", "Capital of France?"),
        ),
        truths=(
            BenchmarkAnswerTruth("q1", "4"),
            BenchmarkAnswerTruth("q2", "Paris"),
        ),
        evidence_refs=EVIDENCE,
    )


class FakeResidentPool:
    all_resident = True
    resident_model_ids = ("small-model",)

    def __init__(self):
        self.calls = []

    def generate_json(self, **values):
        self.calls.append(values)
        return LocalStructuredGeneration(
            result={"answers": [], "evidence_refs": list(EVIDENCE)},
            raw_text='{"answers":[],"evidence_refs":["benchmark-source://pilot-v1"]}',
            input_tokens=31,
            output_tokens=12,
            latency_ms=45,
        )


def test_local_transformers_adapter_records_real_generation_shape():
    source = harness()
    telemetry = ProviderTelemetryLedger()
    pool = FakeResidentPool()
    adapter = LocalTransformersJsonAdapter(
        provider_id="local-transformers",
        model_id="small-model",
        task_kinds=("benchmark_answer",),
        pool=pool,
        telemetry_ledger=telemetry,
        max_new_tokens=64,
    )

    result = adapter.invoke(task(source))
    record = telemetry.items()[0]

    assert result["usage"] == {
        "input_tokens": 31,
        "output_tokens": 12,
        "cached_tokens": 0,
        "provider_calls": 1,
        "latency_ms": 45,
    }
    assert pool.calls[0]["model_id"] == "small-model"
    assert record.backend == "transformers-cuda"
    assert record.latency_ms == 45
    assert record.task_contract_hash == task(source).contract_hash()
    assert record.evidence_ref.startswith("provider-telemetry://")


def test_token_trie_allows_only_registered_prefixes_and_terminal_eos():
    trie = TokenTrie(((10, 20), (10, 30, 40)))

    assert trie.allowed((), 99) == [10]
    assert set(trie.allowed((10,), 99)) == {20, 30}
    assert trie.allowed((10, 20), 99) == [99]
    assert trie.allowed((10, 30), 99) == [40]
    with pytest.raises(ValueError, match="prefix_outside_registry"):
        trie.allowed((11,), 99)


def test_constrained_registry_excludes_mechanical_invalidity_and_hidden_options():
    prior = ({"action": "APPLY", "operator": "ADD", "inputs": ["VALUE_1", "VALUE_1"]},)
    registry = build_tool_registry(
        item_id="q1", candidate_id="CANDIDATE_1", evidence_refs=EVIDENCE,
        symbol_values={"VALUE_1": "4", "VALUE_2": "0", "VALUE_3": "ABCD", "STEP_1": "8"},
        prior_actions=prior,
    )
    validate_tool_registry(registry)
    calls = {item["call"] for item in registry["options"]}

    assert "APPLY(ADD,VALUE_1,VALUE_1)" not in calls
    assert not any(call.startswith("APPLY(DIVIDE,") and call.endswith(",VALUE_2)") for call in calls)
    assert "APPLY(SWAP_HALVES,VALUE_3)" in calls
    assert "FINALIZE(STEP_1,A)" in calls and "ABSTAIN()" in calls
    assert "options" not in registry_prompt_view(registry)
    assert registry["summary"]["hidden_truth_used"] is False


class FakeConstrainedToolPool:
    def __init__(self):
        self.calls = []

    def generate_tool_call(self, **values):
        self.calls.append(values)
        return SimpleNamespace(selected_call=values["calls"][0], input_tokens=19,
                               output_tokens=7, latency_ms=23)


def test_constrained_tool_adapter_returns_registered_result_and_tool_telemetry():
    source, ledger, pool = harness(), ProviderTelemetryLedger(), FakeConstrainedToolPool()
    registry = build_tool_registry(
        item_id="q1", candidate_id="CANDIDATE_1", evidence_refs=EVIDENCE,
        symbol_values={"VALUE_1": "4", "VALUE_2": "2"},
    )
    constrained_task = ProviderCognitiveTask(
        task_id="constrained-tool-q1", task_kind=CONSTRAINED_TOOL_TASK_KIND,
        objective="Choose one registered action.",
        inputs={"benchmark_public_input": source.provider_inputs(),
                "benchmark_item_ids": ["q1"],
                "round_context": {"constrained_tool_channel": registry}},
        allowed_evidence=list(EVIDENCE),
        expected_schema=iterative_action_schema(
            "q1", "CANDIDATE_1", ("VALUE_1", "VALUE_2"),
        ), timeout_seconds=300,
    )
    adapter = LocalConstrainedToolAdapter(
        provider_id="local-constrained", model_id="small-model",
        task_kinds=(CONSTRAINED_TOOL_TASK_KIND,), pool=pool,
        telemetry_ledger=ledger, max_new_tokens=64,
    )

    envelope = adapter.invoke(constrained_task)
    record = ledger.items()[0]

    assert envelope["result"] in [item["result"] for item in registry["options"]]
    assert envelope["usage"]["provider_calls"] == 1
    assert record.backend == "transformers-cuda-constrained-tool"
    assert record.tool_calls == 1 and record.status == "COMPLETED"
    assert '"options"' not in str(pool.calls[0]["messages"])


def test_resident_pool_serializes_concurrent_model_generation(monkeypatch):
    specs = tuple(LocalTransformersModelSpec(f"model-{index}", f"unused-{index}") for index in range(3))
    pool = LocalTransformersResidentPool(specs)
    pool._resident = {item.model_id: (None, None) for item in specs}
    state = {"active": 0, "maximum": 0}
    state_lock = threading.Lock()

    def fake_generate(model_id, messages, max_new_tokens):
        with state_lock:
            state["active"] += 1
            state["maximum"] = max(state["maximum"], state["active"])
        time.sleep(0.03)
        with state_lock:
            state["active"] -= 1
        return LocalStructuredGeneration({}, "{}", 1, 1, 30)

    monkeypatch.setattr(pool, "_generate_unlocked", fake_generate)
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = tuple(executor.map(
            lambda spec: pool.generate_json(
                model_id=spec.model_id, messages=[], max_new_tokens=2
            ),
            specs,
        ))

    assert len(results) == 3
    assert state["maximum"] == 1


def test_ollama_adapter_separates_thinking_and_supports_long_timeout(monkeypatch):
    source = harness()
    telemetry = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local",
        model_id="deepseek-r1:32b",
        task_kinds=("benchmark_answer",),
        telemetry_ledger=telemetry,
        timeout_seconds=900,
        thinking_enabled=True,
    )
    monkeypatch.setattr(adapter, "_post", lambda payload: {
        "done": True,
        "message": {
            "thinking": "private chain of thought",
            "content": json.dumps({"answers": [], "evidence_refs": list(EVIDENCE)}),
        },
        "prompt_eval_count": 50,
        "eval_count": 20,
    })

    result = adapter.invoke(task(source))
    record = telemetry.items()[0]

    assert adapter.profile.max_timeout_seconds == 900
    assert result["result"] == {"answers": [], "evidence_refs": list(EVIDENCE)}
    assert "thinking" not in result
    assert adapter.thinking_text("benchmark-task-1") == "private chain of thought"
    assert record.thinking_present is True
    assert record.thinking_hash == hash_payload("private chain of thought")


def test_harness_blocks_hidden_answer_keys_in_provider_inputs():
    source = harness()
    clean = source.audit_provider_task(task(source))
    leaked = source.audit_provider_task(task(
        source,
        task_id="benchmark-task-leaked",
        extra={"review_context": {"expected_answer": "4"}},
    ))

    assert clean.status == "PASS_HIDDEN_ANSWER_ABSENT"
    assert leaked.status == "BLOCK_HIDDEN_ANSWER_RISK"
    assert "inputs.review_context.expected_answer" in leaked.failures
    with pytest.raises(ValueError, match="provider_input_audit_blocked"):
        source.evaluate(
            trial_id="pilot-trial",
            arm="SMALL_TEAM",
            candidate_output={
                "answers": [{"item_id": "q1", "answer": "4"}, {"item_id": "q2", "answer": "Paris"}],
                "evidence_refs": list(EVIDENCE),
            },
            provider_input_audits=(leaked,),
            telemetry_refs=("provider-telemetry://" + "a" * 64,),
        )


def test_harness_admits_only_exact_public_question_slices():
    source = harness()
    provider_task = task(source)
    sliced = replace(
        provider_task,
        task_id="benchmark-task-sliced",
        inputs={
            "benchmark_public_input": source.provider_inputs(("q1",)),
            "benchmark_item_ids": ["q1"],
            "round_context": {},
        },
    )
    mismatched = replace(
        sliced,
        task_id="benchmark-task-slice-mismatch",
        inputs={**sliced.inputs, "benchmark_item_ids": ["q2"]},
    )

    assert source.audit_provider_task(sliced).status == "PASS_HIDDEN_ANSWER_ABSENT"
    assert source.audit_provider_task(mismatched).status == "BLOCK_HIDDEN_ANSWER_RISK"


def completed_telemetry(provider_task, *, suffix="a"):
    return ProviderInvocationTelemetry.create(
        telemetry_id=f"telemetry-{suffix}",
        provider_id="local-transformers",
        model_id="small-model",
        backend="transformers-cuda",
        task_id=provider_task.task_id,
        task_kind=provider_task.task_kind,
        task_contract_hash=provider_task.contract_hash(),
        status="COMPLETED",
        input_tokens=100,
        output_tokens=40,
        cached_tokens=5,
        latency_ms=300,
        api_cost=0.0,
        tool_calls=0,
        tool_cost=0.0,
        evidence_refs=EVIDENCE,
        output_hash=hash_payload({"candidate": suffix}),
        thinking_present=False,
        thinking_char_count=0,
        thinking_hash="",
        error_type="",
    )


def scored_receipt(source, provider_task, telemetry):
    audit = source.audit_provider_task(provider_task)
    return source.evaluate(
        trial_id="pilot-trial",
        arm="SMALL_TEAM",
        candidate_output={
            "answers": [{"item_id": "q1", "answer": "4"}, {"item_id": "q2", "answer": "Paris"}],
            "evidence_refs": list(EVIDENCE),
        },
        provider_input_audits=(audit,),
        telemetry_refs=(telemetry.evidence_ref,),
    )


class CognitiveWorkSemanticProvider:
    profile = ProviderCapabilityProfile(
        provider_id="work-semantic-provider",
        model_id="work-semantic-model",
        task_kinds=("cognitive_work_round_assessment",),
        max_timeout_seconds=120,
    )

    def invoke(self, provider_task):
        return {
            "result": {
                "evidence_novelty": 0.8,
                "constraint_coverage": 0.9,
                "hypothesis_diversity": 0.8,
                "redundancy": 0.2,
                "error_correlation": 0.2,
                "problem_drift": 0.1,
                "uncertainty": 0.1,
                "recommended_action": "STOP_SUFFICIENT",
                "rationale": "held-out exact answers reached the admitted threshold",
                "evidence_refs": list(provider_task.allowed_evidence),
            },
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "provenance_refs": list(provider_task.allowed_evidence),
        }


def work_runtime(tmp_path):
    return CognitiveWorkAccountingRuntime(
        runtime_id="local-experiment-work",
        project_scope="project://local-experiment",
        provider_router=ProviderTaskRouter([CognitiveWorkSemanticProvider()]),
        budget=CognitiveWorkBudget(
            budget_id="local-experiment-budget",
            max_rounds=8,
            max_total_tokens=100000,
            max_provider_calls=100,
            max_tool_calls=10,
            max_latency_ms=1000000,
            max_api_cost=10.0,
            max_tool_cost=10.0,
        ),
        workspace_root=tmp_path,
    )


def test_frozen_answer_receipt_contains_commitments_not_answers():
    source = harness()
    provider_task = task(source)
    telemetry = completed_telemetry(provider_task)
    receipt = scored_receipt(source, provider_task, telemetry)
    serialized = json.dumps(receipt.as_dict(), sort_keys=True)

    assert receipt.exact_accuracy == 1.0
    assert receipt.observed_cbit_gain == 1.0
    assert "expected_answer" not in serialized
    assert "ground_truth" not in serialized
    assert receipt.truth_commitment == source.truth_commitment
    with pytest.raises(ValueError, match="accuracy_invalid"):
        replace(receipt, correct_count=1)


def test_execution_bridge_submits_exact_work_and_harness_cbit(tmp_path):
    source = harness()
    provider_task = task(source)
    telemetry = completed_telemetry(provider_task)
    harness_receipt = scored_receipt(source, provider_task, telemetry)
    runtime = work_runtime(tmp_path)

    bridge_receipt = CognitiveWorkExecutionBridge(runtime).submit_round(
        bridge_receipt_id="bridge-pilot-1",
        trajectory_id="pilot-trajectory",
        context_key="pilot-context",
        round_index=1,
        stage="benchmark-deliberation",
        topology_id="THREE_SMALL_MODEL_TEAM",
        agent_ids=("solver", "reviewer", "replicator"),
        telemetry=(telemetry,),
        harness_receipt=harness_receipt,
        kernel_authorization_ref="kernel://local-experiment/round-1",
    )
    receipt = runtime.snapshot().receipts[0]

    assert receipt.observation.input_tokens == 100
    assert receipt.observation.output_tokens == 40
    assert receipt.observation.cached_tokens == 5
    assert receipt.observation.provider_calls == 1
    assert receipt.observation.latency_ms == 300
    assert receipt.observation.observed_cbit_gain == 1.0
    assert receipt.kernel_control.action == "STOP_SUFFICIENT"
    assert bridge_receipt.control_hash == receipt.kernel_control.decision_hash
    assert runtime.verify_replay()["valid"] is True
    with pytest.raises(ValueError, match="commitment_invalid"):
        replace(bridge_receipt, bridge_hash="0" * 64)


def test_adapter_retry_cost_is_preserved_by_execution_bridge(tmp_path):
    source = harness()
    provider_task = task(source)
    telemetry_ledger = ProviderTelemetryLedger()

    class RetryPool:
        def __init__(self):
            self.index = 0

        def generate_json(self, **values):
            self.index += 1
            if self.index == 1:
                return LocalStructuredGeneration(
                    result=None,
                    raw_text="not-json",
                    input_tokens=20,
                    output_tokens=10,
                    latency_ms=50,
                    parse_error="provider_response_contains_no_json_object",
                )
            return LocalStructuredGeneration(
                result={
                    "answers": [
                        {"item_id": "q1", "answer": "4"},
                        {"item_id": "q2", "answer": "Paris"},
                    ],
                    "evidence_refs": list(EVIDENCE),
                },
                raw_text="{}",
                input_tokens=20,
                output_tokens=10,
                latency_ms=50,
            )

    adapter = LocalTransformersJsonAdapter(
        provider_id="local-transformers",
        model_id="small-model",
        task_kinds=("benchmark_answer",),
        pool=RetryPool(),
        telemetry_ledger=telemetry_ledger,
        max_attempts=2,
    )
    result = adapter.invoke(provider_task)["result"]
    telemetry = telemetry_ledger.items()
    audit = source.audit_provider_task(provider_task)
    harness_receipt = source.evaluate(
        trial_id="pilot-retry-trial",
        arm="SMALL_TEAM",
        candidate_output=result,
        provider_input_audits=(audit,),
        telemetry_refs=tuple(item.evidence_ref for item in telemetry),
    )
    runtime = work_runtime(tmp_path)

    CognitiveWorkExecutionBridge(runtime).submit_round(
        bridge_receipt_id="bridge-pilot-retry",
        trajectory_id="pilot-retry-trajectory",
        context_key="pilot-context",
        round_index=1,
        stage="benchmark-deliberation",
        topology_id="THREE_SMALL_MODEL_TEAM",
        agent_ids=("solver",),
        telemetry=telemetry,
        harness_receipt=harness_receipt,
        kernel_authorization_ref="kernel://local-experiment/retry",
    )
    observation = runtime.snapshot().receipts[0].observation

    assert [item.status for item in telemetry] == ["FAILED", "COMPLETED"]
    assert observation.provider_calls == 2
    assert observation.input_tokens == 40
    assert observation.output_tokens == 20
    assert observation.latency_ms == 100


def test_execution_bridge_rejects_unmatched_task_lineage(tmp_path):
    source = harness()
    provider_task = task(source)
    telemetry = completed_telemetry(provider_task)
    receipt = scored_receipt(source, provider_task, telemetry)
    other = completed_telemetry(task(source, task_id="other-task"), suffix="b")

    with pytest.raises(ValueError, match="provider_task_lineage_mismatch"):
        CognitiveWorkExecutionBridge(work_runtime(tmp_path)).submit_round(
            bridge_receipt_id="bridge-pilot-invalid",
            trajectory_id="pilot-trajectory",
            context_key="pilot-context",
            round_index=1,
            stage="benchmark-deliberation",
            topology_id="THREE_SMALL_MODEL_TEAM",
            agent_ids=("solver",),
            telemetry=(other,),
            harness_receipt=receipt,
            kernel_authorization_ref="kernel://local-experiment/invalid",
        )
