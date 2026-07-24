import ast
import sys
from dataclasses import replace
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    CognitiveWorkBudget,
    CognitiveWorkRoundObservation,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    RuntimeTaskLifecycle,
)
from agentos_runtime import CognitiveWorkAccountingRuntime  # noqa: E402


EVIDENCE = ("evidence://work-source",)


class WorkProvider:
    def __init__(self, results):
        self.results = list(results)
        self.profile = ProviderCapabilityProfile(
            provider_id="provider-work",
            model_id="model-work",
            task_kinds=("cognitive_work_round_assessment",),
            max_timeout_seconds=120,
        )

    def invoke(self, task):
        result = self.results.pop(0)
        return {
            "result": result,
            "usage": {"input_tokens": 12, "output_tokens": 8},
            "provenance_refs": list(EVIDENCE),
        }


def semantic(**overrides):
    values = {
        "evidence_novelty": 0.8,
        "constraint_coverage": 0.7,
        "hypothesis_diversity": 0.7,
        "redundancy": 0.2,
        "error_correlation": 0.2,
        "problem_drift": 0.1,
        "uncertainty": 0.3,
        "recommended_action": "CONTINUE",
        "rationale": "new evidence still reduces the admitted possibility space",
        "evidence_refs": list(EVIDENCE),
    }
    values.update(overrides)
    return values


def budget(**overrides):
    values = {
        "budget_id": "budget-work",
        "max_rounds": 5,
        "max_total_tokens": 10000,
        "max_provider_calls": 10,
        "max_tool_calls": 10,
        "max_latency_ms": 60000,
        "max_api_cost": 10.0,
        "max_tool_cost": 10.0,
    }
    values.update(overrides)
    return CognitiveWorkBudget(**values)


def observation(round_index, cbit, **overrides):
    values = {
        "observation_id": f"work-round-{round_index}",
        "trajectory_id": "task-work-1",
        "project_scope": "project://cognitive-work-test",
        "context_key": "ctx-work",
        "round_index": round_index,
        "stage": "evidence-reasoning",
        "topology_id": "CENTRALIZED_TEAM",
        "agent_ids": ("generator", "reviewer"),
        "model_ids": ("small-model-a", "small-model-b"),
        "input_tokens": 1000,
        "output_tokens": 500,
        "cached_tokens": 100,
        "provider_calls": 2,
        "tool_calls": 1,
        "latency_ms": 1000,
        "api_cost": 0.02,
        "tool_cost": 0.01,
        "observed_cbit_gain": cbit,
        "errors_exposed": 2,
        "errors_corrected": 1,
        "evidence_refs": EVIDENCE,
        "harness_receipt_ref": f"harness://work-{round_index}",
    }
    values.update(overrides)
    return CognitiveWorkRoundObservation(**values)


def runtime(tmp_path, results, *, work_budget=None):
    return CognitiveWorkAccountingRuntime(
        runtime_id="cognitive-work-test",
        project_scope="project://cognitive-work-test",
        provider_router=ProviderTaskRouter([WorkProvider(results)]),
        budget=work_budget or budget(),
        workspace_root=tmp_path,
    )


def test_rounds_account_exact_work_and_stop_when_required_cbit_is_reached(tmp_path):
    engine = runtime(tmp_path, [semantic(), semantic(recommended_action="STOP_SUFFICIENT")])

    first = engine.account_round(
        receipt_id="receipt-work-1",
        observation=observation(1, 0.35),
        kernel_authorization_ref="kernel://cognitive-work/1",
    )
    second = engine.account_round(
        receipt_id="receipt-work-2",
        observation=observation(2, 0.50),
        kernel_authorization_ref="kernel://cognitive-work/2",
    )

    assert first.kernel_control.action == "CONTINUE"
    assert second.kernel_control.action == "STOP_SUFFICIENT"
    assert second.kernel_control.cumulative_cbit_gain == 0.85
    assert second.kernel_control.total_tokens == 3000
    assert second.kernel_control.total_provider_calls == 4
    assert second.kernel_control.total_tool_calls == 2
    assert second.kernel_control.total_latency_ms == 2000
    assert second.kernel_control.total_api_cost == 0.04
    assert second.kernel_control.retention_eligible is True
    assert second.kernel_control.operator_memory_eligible is True
    assert second.kernel_control.budget_hash == budget().as_dict()["budget_hash"]
    assert second.mechanical_audit["status"] == "PASS_MECHANICAL_RUNTIME_OPERATION"
    assert second.as_dict()["global_memory_write_authority"] is False
    assert engine.verify_replay()["valid"] is True


def test_receipt_rejects_tampered_budget_or_receipt_hash(tmp_path):
    engine = runtime(tmp_path, [semantic()])
    receipt = engine.account_round(
        receipt_id="receipt-work-bound",
        observation=observation(1, 0.35),
        kernel_authorization_ref="kernel://cognitive-work/bound",
    )

    with pytest.raises(ValueError, match="budget_binding_invalid"):
        replace(receipt, budget=budget(max_rounds=4))
    with pytest.raises(ValueError, match="provider_audit_status_invalid"):
        replace(receipt, provider_audit={**receipt.provider_audit, "status": "BLOCKED"})
    with pytest.raises(ValueError, match="receipt_hash_mismatch"):
        replace(receipt, receipt_hash="0" * 64)


def test_exact_budget_boundary_allows_sufficient_stop(tmp_path):
    engine = runtime(tmp_path, [semantic()], work_budget=budget(max_rounds=1))
    receipt = engine.account_round(
        receipt_id="receipt-work-exact-budget",
        observation=observation(1, 0.85),
        kernel_authorization_ref="kernel://cognitive-work/exact-budget",
    )

    assert receipt.kernel_control.action == "STOP_SUFFICIENT"


def test_exact_budget_boundary_blocks_more_insufficient_work(tmp_path):
    engine = runtime(tmp_path, [semantic()], work_budget=budget(max_rounds=1))
    receipt = engine.account_round(
        receipt_id="receipt-work-budget-stop",
        observation=observation(1, 0.35),
        kernel_authorization_ref="kernel://cognitive-work/budget-stop",
    )

    assert receipt.kernel_control.action == "BLOCK_BUDGET"
    assert receipt.kernel_control.allow_additional_round is False


def test_restart_reconstructs_same_trajectory_and_control_hash(tmp_path):
    engine = runtime(tmp_path, [semantic()])
    receipt = engine.account_round(
        receipt_id="receipt-work-1",
        observation=observation(1, 0.35),
        kernel_authorization_ref="kernel://cognitive-work/1",
    )

    restarted = CognitiveWorkAccountingRuntime(
        runtime_id="cognitive-work-test",
        project_scope="project://cognitive-work-test",
        provider_router=ProviderTaskRouter([]),
        budget=budget(),
        workspace_root=tmp_path,
    )

    assert restarted.latest_control("task-work-1").decision_hash == receipt.kernel_control.decision_hash
    assert restarted.verify_replay()["valid"] is True


def test_low_marginal_redundant_round_stops_without_retention_authority(tmp_path):
    engine = runtime(tmp_path, [semantic(redundancy=0.9, evidence_novelty=0.05)])
    receipt = engine.account_round(
        receipt_id="receipt-work-low",
        observation=observation(1, 0.01),
        kernel_authorization_ref="kernel://cognitive-work/low",
    )

    assert receipt.kernel_control.action == "STOP_LOW_MARGINAL"
    assert receipt.kernel_control.allow_organization_expansion is False
    assert receipt.kernel_control.retention_eligible is False
    assert receipt.kernel_control.operator_memory_eligible is False


def test_provider_failure_blocks_without_fabricated_semantic_assessment(tmp_path):
    engine = CognitiveWorkAccountingRuntime(
        runtime_id="cognitive-work-test",
        project_scope="project://cognitive-work-test",
        provider_router=ProviderTaskRouter([]),
        budget=budget(),
        workspace_root=tmp_path,
    )

    with pytest.raises(RuntimeError, match="cognitive_work_provider_blocked"):
        engine.account_round(
            receipt_id="receipt-work-blocked",
            observation=observation(1, 0.2),
            kernel_authorization_ref="kernel://cognitive-work/blocked",
        )
    assert engine.snapshot().receipts == ()
    assert engine.verify_replay()["valid"] is True


def test_task_lifecycle_applies_kernel_work_control_as_schedule_directive(tmp_path):
    engine = runtime(
        tmp_path / "work",
        [
            semantic(recommended_action="ESCALATE", uncertainty=0.8),
            semantic(recommended_action="ESCALATE", uncertainty=0.8),
        ],
    )
    first = engine.account_round(
        receipt_id="receipt-work-1",
        observation=observation(1, 0.2),
        kernel_authorization_ref="kernel://cognitive-work/1",
    )
    second = engine.account_round(
        receipt_id="receipt-work-2",
        observation=observation(2, 0.2),
        kernel_authorization_ref="kernel://cognitive-work/2",
    )
    lifecycle = RuntimeTaskLifecycle(tmp_path / "tasks")
    lifecycle.intake("task-work-1", "cognitive-trial")
    lifecycle.start("task-work-1")

    assert first.kernel_control.action == "CONTINUE"
    state = lifecycle.apply_cognitive_work_control("task-work-1", second.kernel_control)
    assert second.kernel_control.action == "ESCALATE"
    assert state.state == "WAITING"
    assert state.receipts[-1]["payload"]["cognitive_work_control_hash"] == second.kernel_control.decision_hash


def test_kernel_modules_remain_runtime_and_filesystem_independent():
    forbidden = {"agentos_runtime", "os", "pathlib"}
    for filename in ("cognitive_work_models.py", "cognitive_work_eval.py"):
        tree = ast.parse((CORE_ROOT / "agentos_kernel" / filename).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert imported.isdisjoint(forbidden), (filename, imported)


def test_runtime_facade_stays_thin():
    path = CORE_ROOT / "agentos_runtime" / "cognitive_work_runtime.py"
    nonblank = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(nonblank) <= 180
