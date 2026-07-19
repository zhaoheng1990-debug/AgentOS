"""End-to-end smoke from contextual selection through real execution feedback."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    AgentRegistry,
    ContextualProblemStructure,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    SelectionExecutionBudget,
)
from agentos_runtime import (  # noqa: E402
    ContextualOrganizationPolicyRuntime,
    SelectionExecutionFeedbackBridge,
    TeamExecutionPolicyAdapter,
)
from examples.cognitive_team_execution_project_source_smoke import (  # noqa: E402
    _build_runtime,
    _descriptor,
    load_life_case,
)


RETURN_PACK_NAME = "AgentOS_SelectionExecutionFeedbackBridge_ReturnPack_v0_1.zip"
CONTEXT_KEY = "ctx-life-selection-feedback"


def _execution_budget(run_id: int) -> SelectionExecutionBudget:
    return SelectionExecutionBudget.create(
        budget_ref=f"budget://life-selection-feedback/run-{run_id}",
        max_protocol_runs=3,
        max_provider_calls_total=60,
        max_normalized_cost_per_protocol=1.0,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(data)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


class DynamicPolicyProvider:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-contextual-policy-provider",
            model_id="scripted-contextual-policy-model",
            task_kinds=("contextual_organization_policy_assessment",),
            max_timeout_seconds=120,
        )
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        refs = [task.allowed_evidence[0]]
        assessments = []
        for policy in task.inputs["registered_policies"]:
            policy_id = policy["policy_id"]
            preferred = policy_id == "DYNAMIC_TEAM"
            assessments.append(
                {
                    "policy_id": policy_id,
                    "structure_fit": 0.96 if preferred else 0.45,
                    "expected_cbit_gain": 0.84 if preferred else 0.45,
                    "estimated_normalized_cost": 0.65 if preferred else 0.60,
                    "residual_risk": 0.20,
                    "anti_additive_signal": 0.15,
                    "uncertainty": 0.20 if preferred else 0.25,
                    "rationale": f"exact-context bounded assessment for {policy_id}",
                    "evidence_refs": refs,
                }
            )
        return {
            "result": {
                "recommended_policy_id": "DYNAMIC_TEAM",
                "policy_assessments": assessments,
                "global_uncertainty": 0.25,
                "evidence_refs": refs,
            },
            "usage": {"total_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def _selection_registry(case, execution_runtime):
    registry = AgentRegistry()
    for index in range(4):
        registry.register(execution_runtime.registry.get(f"dynamic-{index}"))
    coordinator = _descriptor(
        case,
        "coordinator-dynamic_team",
        "COORDINATOR",
        "route_proposal",
        "deepseek",
        "deepseek-v4-flash",
    )
    registry.register(coordinator)
    return registry, coordinator


def _problem(case) -> ContextualProblemStructure:
    return ContextualProblemStructure(
        problem_id="problem-life-selection-feedback",
        context_key=CONTEXT_KEY,
        project_scope=case.scope,
        objective=case.objective,
        premise_uncertainty=0.8,
        evidence_conflict=0.8,
        replication_need=0.8,
        synthesis_need=0.8,
        coordination_complexity=0.8,
        novelty_need=0.5,
        evidence_refs=case.evidence_refs,
        structure_receipt_ref="provider-receipt://life-selection-feedback/problem-structure",
        structure_receipt_hash=_hash_payload({"case_id": case.case_id, "context_key": CONTEXT_KEY}),
    )


def _budget() -> OrganizationBudgetEnvelope:
    return OrganizationBudgetEnvelope(
        budget_ref="budget://life-selection-feedback",
        max_roles=5,
        max_provider_calls=6,
        max_coordination_steps=5,
        max_normalized_cost=0.9,
    )


def _risk() -> OrganizationRiskEnvelope:
    return OrganizationRiskEnvelope(
        risk_ref="risk://life-selection-feedback",
        max_residual_risk=0.5,
        max_provider_uncertainty=0.4,
        max_anti_additive_signal=0.5,
        matched_evidence_required_above_risk=0.4,
        allow_unmatched_exploration=True,
        exploration_max_roles=5,
    )


def _selector(*, output_dir, case, registry, provider, record_source=None):
    return ContextualOrganizationPolicyRuntime(
        runtime_id=f"life-feedback-selector-{output_dir.name}",
        project_scope=case.scope,
        registry=registry,
        provider_router=ProviderTaskRouter([provider]),
        workspace_root=output_dir,
        record_source=record_source,
    )


def _select(runtime, case, selection_id):
    return runtime.select_policy(
        selection_id=selection_id,
        problem=_problem(case),
        evidence_tier="SCRIPTED_FIXTURE",
        budget=_budget(),
        risk=_risk(),
        kernel_authorization_ref=f"kernel://life-selection-feedback/{selection_id}",
    )


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", RETURN_PACK_NAME}:
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    payload = {"status": status, "created_at": _utc_now(), "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    _write_json(output_dir / "manifest.json", payload)
    return payload


def _return_pack(output_dir: Path) -> Path:
    path = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def run_smoke(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    case = load_life_case()
    execution_one, recordings_one = _build_runtime(
        case, output_dir / "execution-one", "scripted", True
    )
    registry, coordinator = _selection_registry(case, execution_one)
    policy_provider = DynamicPolicyProvider()
    initial_selector = _selector(
        output_dir=output_dir / "selector-initial",
        case=case,
        registry=registry,
        provider=policy_provider,
    )
    initial_selection = _select(initial_selector, case, "life-feedback-initial")
    bridge = SelectionExecutionFeedbackBridge(
        runtime_id="life-selection-feedback-bridge",
        project_scope=case.scope,
        workspace_root=output_dir / "feedback-runtime",
    )
    first = bridge.execute_and_admit(
        bridge_run_id="life-feedback-run-1",
        selection=initial_selection,
        executor=TeamExecutionPolicyAdapter(
            adapter_id="life-team-execution-adapter-1",
            runtime=execution_one,
            best_member_agent_id="framer-deepseek",
            coordinator_descriptors={"DYNAMIC_TEAM": coordinator},
        ),
        trial_group_id="life-feedback-group-1",
        trial_id=execution_one.trial_spec.trial_id,
        trial_evidence_refs=case.evidence_refs,
        execution_budget=_execution_budget(1),
        kernel_execution_authorization_ref="kernel://life-selection-feedback/run-1",
    )

    execution_two, recordings_two = _build_runtime(
        case, output_dir / "execution-two", "scripted", True
    )
    second = bridge.execute_and_admit(
        bridge_run_id="life-feedback-run-2",
        selection=initial_selection,
        executor=TeamExecutionPolicyAdapter(
            adapter_id="life-team-execution-adapter-2",
            runtime=execution_two,
            best_member_agent_id="framer-deepseek",
            coordinator_descriptors={"DYNAMIC_TEAM": coordinator},
        ),
        trial_group_id="life-feedback-group-2",
        trial_id=execution_two.trial_spec.trial_id,
        trial_evidence_refs=case.evidence_refs,
        execution_budget=_execution_budget(2),
        kernel_execution_authorization_ref="kernel://life-selection-feedback/run-2",
    )
    restarted = SelectionExecutionFeedbackBridge(
        runtime_id="life-selection-feedback-bridge",
        project_scope=case.scope,
        workspace_root=output_dir / "feedback-runtime",
    )
    downstream_provider = DynamicPolicyProvider()
    downstream_selector = _selector(
        output_dir=output_dir / "selector-downstream",
        case=case,
        registry=registry,
        provider=downstream_provider,
        record_source=restarted,
    )
    downstream_selection = _select(downstream_selector, case, "life-feedback-downstream")
    first_dynamic = next(item for item in first.matched_evidence if item.policy_id == "DYNAMIC_TEAM")
    second_dynamic = next(item for item in second.matched_evidence if item.policy_id == "DYNAMIC_TEAM")
    gates = {
        "initial_selection_is_exploratory": (
            initial_selection.kernel_decision.selected_policy_id == "DYNAMIC_TEAM"
            and initial_selection.kernel_decision.activation_mode == "EXPLORATORY_TRIAL_ONLY"
        ),
        "real_team_execution_adapter_used": all(
            item.execution_bundle.execution_adapter_id.startswith("life-team-execution-adapter-")
            for item in (first, second)
        ),
        "harness_feedback_admitted": all(
            record.harness_receipt_ref.startswith("harness://")
            for receipt in (first, second)
            for record in receipt.admitted_records
        ),
        "actual_three_arm_execution_is_budgeted": all(
            len(receipt.execution_bundle.executed_protocol_ids) == 3
            and receipt.execution_bundle.total_provider_call_count
            <= receipt.request.execution_budget.max_provider_calls_total
            for receipt in (first, second)
        ),
        "first_trial_is_not_enough": first_dynamic.sufficient_matched_evidence is False,
        "second_trial_closes_matched_evidence": (
            second_dynamic.sufficient_matched_evidence is True
            and second_dynamic.matched_pair_count == 2
            and second_dynamic.unique_source_count == 2
        ),
        "feedback_sources_are_independent": (
            first.admitted_records[0].source_result_hash
            != second.admitted_records[0].source_result_hash
        ),
        "restart_replay_valid": restarted.verify_replay()["valid"],
        "restart_restores_four_records": restarted.verify_replay()["record_count"] == 4,
        "selector_reads_feedback_without_manual_records": (
            downstream_selection.kernel_decision.selected_policy_id == "DYNAMIC_TEAM"
            and downstream_selection.kernel_decision.activation_mode == "AUTHORIZED_PROJECT_SCOPED"
        ),
        "no_global_or_production_authority": all(
            receipt.as_dict()["global_policy_authority"] is False
            and receipt.as_dict()["production_activation"] is False
            for receipt in (first, second)
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "selection-execution-feedback-bridge-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "gates": gates,
        "initial_selection": initial_selection.as_dict(),
        "first_feedback": first.as_dict(),
        "second_feedback": second.as_dict(),
        "downstream_selection": downstream_selection.as_dict(),
        "restart_replay": restarted.verify_replay(),
        "execution_provider_call_count": len(recordings_one) + len(recordings_two),
        "selector_provider_call_count": len(policy_provider.tasks) + len(downstream_provider.tasks),
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "selection_execution_feedback_smoke_result.json", result)
    _manifest(output_dir, status)
    _return_pack(output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_smoke(args.output_dir)
        print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)}
        _write_json(args.output_dir / "selection_execution_feedback_smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
