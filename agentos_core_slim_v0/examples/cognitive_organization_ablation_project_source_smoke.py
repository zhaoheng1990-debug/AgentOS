"""Matched cognitive-organization ablation smoke over frozen project sources."""

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
REPO_ROOT = CORE_ROOT.parent
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import ProviderTaskRouter  # noqa: E402
from agentos_runtime import (  # noqa: E402
    AgentAdapterResult,
    CognitiveAgent,
    CognitiveCoordinationRuntime,
    CognitiveOrganizationAblationRuntime,
    OrganizationExperimentPlan,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)
from examples.cognitive_team_execution_project_source_smoke import (  # noqa: E402
    HIDDEN_KEYS,
    ProjectTrialCase,
    _build_runtime,
    _candidate,
    _case_loader,
    _descriptor,
    _hash_bytes,
    _hash_payload,
    _recording_live,
    _recording_static,
)


RETURN_PACK_NAME = "AgentOS_CognitiveOrganizationAblation_ReturnPack_v0_1.zip"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _contains_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in forbidden for key in value):
            return True
        return any(_contains_key(item, forbidden) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, forbidden) for item in value)
    return False


def load_authorized_experiment_plan(path: Path) -> OrganizationExperimentPlan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise ValueError("ablation_learning_result_must_pass")
    item = payload.get("experiment_authorization") or payload.get("next_experiment_authorization")
    if not isinstance(item, dict):
        raise ValueError("ablation_learning_authorization_missing")
    return OrganizationExperimentPlan(
        plan_id=item["plan_id"],
        context_key=item["context_key"],
        evidence_tier=item["evidence_tier"],
        selected_variants=tuple(item["selected_variants"]),
        rationale_refs=tuple(item["rationale_refs"]),
        policy_ref=item["policy_ref"],
        budget=dict(item["budget"]),
        budget_hash=item["budget_hash"],
        kernel_authorization_ref=item["kernel_authorization_ref"],
        created_at=item["created_at"],
        plan_hash=item["plan_hash"],
        candidate_state=item["candidate_state"],
        execution_authorized=item["execution_authorized"],
    )


class ScriptedAblationCoordinatorAdapter:
    def __init__(self, coordinator: CognitiveAgent) -> None:
        self.adapter_id = f"scripted-ablation-coordinator-{coordinator.agent_id}"
        self.coordinator = coordinator

    def invoke(self, cognitive_agent: Any, work_order: Any, context_view: Any, private_workspace: Any) -> Any:
        candidates = context_view.coordination_state["admissible_progression_candidates"]
        if not candidates:
            raise RuntimeError("scripted_ablation_coordinator_no_admissible_progression")
        selected = candidates[0]
        payload = {
            "route_action": selected["route_action"],
            "target_role": selected["target_role"],
            "rationale": "Follow the Kernel-admissible progression for this authorized ablation.",
            "unresolved_questions": ["Which public findings survive?"],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": list(work_order.allowed_evidence_refs),
            "expected_cbit_gain": 0.0 if selected["route_action"] == "FINALIZE_CANDIDATE" else 0.4,
            "stop_condition": "Stop after bounded synthesis.",
        }
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.coordinator.descriptor.provider_id,
            model_id=self.coordinator.model_id,
            invocation_receipt_ref=f"fixture-provider://{work_order.work_order_id}",
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


def _build_return_pack(output_dir: Path) -> Path:
    path = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def run_case(
    case: ProjectTrialCase,
    output_dir: Path,
    experiment_plan: OrganizationExperimentPlan,
    *,
    provider_mode: str = "scripted",
    bundle_id: str = "bundle-1",
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    base_runtime, recordings = _build_runtime(case, output_dir / "base", provider_mode, True)

    def coordinator_factory(protocol_id, workspace_root, omitted_roles, authorization_ref):
        descriptor = _descriptor(
            case,
            f"ablation-coordinator-{protocol_id.lower()}",
            "COORDINATOR",
            "route_proposal",
            "deepseek",
            "deepseek-v4-flash",
        )
        coordinator = CognitiveAgent(
            descriptor,
            standard_role_contract("COORDINATOR"),
            model_id=descriptor.model_id,
            private_memory_namespace=f"coord-{_hash_payload([case.case_id, protocol_id])[:16]}",
            harness_capabilities=("formal_receipt_read", "route_proposal"),
            credit_subject_id=f"credit-{protocol_id.lower()}-ablation-coordinator",
        )
        if provider_mode == "live":
            provider = _recording_live(
                recordings,
                "deepseek",
                "deepseek-v4-flash",
                "cognitive_deliberation_coordination",
                1800,
            )
            adapter: Any = ProviderCognitiveAgentAdapter(
                f"live-ablation-coordinator-{protocol_id.lower()}",
                ProviderTaskRouter([provider]),
            )
        else:
            adapter = ScriptedAblationCoordinatorAdapter(coordinator)
        active_role_count = 4 - len(omitted_roles)
        return CognitiveCoordinationRuntime(
            coordinator=coordinator,
            adapter=adapter,
            workspace_root=workspace_root,
            max_cycles=active_role_count + 1,
            max_role_executions_per_role=1,
            authorized_omitted_roles=omitted_roles,
            ablation_authorization_ref=(authorization_ref if omitted_roles else ""),
        )

    dynamic_synthesizer_id = next(
        agent_id
        for agent_id in base_runtime.formation_runtime.snapshot().proposal.selected_agent_ids
        if base_runtime.registry.get(agent_id).role == "SYNTHESIZER"
    )
    dynamic_generator_id = next(
        agent_id
        for agent_id in base_runtime.formation_runtime.snapshot().proposal.selected_agent_ids
        if base_runtime.registry.get(agent_id).role == "HYPOTHESIS_GENERATOR"
    )
    generator_descriptor = base_runtime.registry.get(dynamic_generator_id)
    if provider_mode == "live":
        generator_projection = _recording_live(
            recordings,
            generator_descriptor.provider_id,
            generator_descriptor.model_id,
            "team_trial_output_normalization",
            3200,
        )
    else:
        generator_projection = _recording_static(
            recordings,
            generator_descriptor.provider_id,
            generator_descriptor.model_id,
            "team_trial_output_normalization",
            lambda task: _candidate(case, "partial"),
        )
    runtime = CognitiveOrganizationAblationRuntime(
        runtime_id=f"{case.case_id}-organization-ablation-{bundle_id}",
        experiment_plan=experiment_plan,
        formation_runtime=base_runtime.formation_runtime,
        registry=base_runtime.registry,
        trial_spec=base_runtime.trial_spec,
        team_adapters=base_runtime.team_adapters,
        normalization_router=base_runtime.normalization_routers[dynamic_synthesizer_id],
        unsynthesized_normalization_router=ProviderTaskRouter([generator_projection]),
        semantic_assessment_router=base_runtime.formation_runtime.trial_assessment_router,
        trial_harness=base_runtime.trial_harness,
        workspace_root=output_dir / "ablation-runtime",
        coordination_runtime_factory=coordinator_factory,
    )
    runtime.execute_protocols()
    snapshot = runtime.evaluate_protocols()
    task_audit = [
        {
            "task_kind": task.task_kind,
            "task_id": task.task_id,
            "inputs_hash": _hash_payload(task.inputs),
            "hidden_truth_key_present": _contains_key(task.inputs, HIDDEN_KEYS),
            "protocol_identity_present": (
                "DYNAMIC_NO_" in json.dumps(task.inputs, sort_keys=True)
                or "protocol_id" in task.inputs
                or "agent_ids" in task.inputs
            ),
        }
        for adapter in recordings
        for task in adapter.tasks
    ]
    assessment_tasks = [item for item in task_audit if item["task_kind"] == "team_trial_semantic_assessment"]
    by_protocol = {item.protocol_id: item for item in snapshot.protocol_results}
    expected_protocols = {"DYNAMIC_TEAM", *experiment_plan.selected_variants}
    gates = {
        "authorized_protocols_completed": set(by_protocol) == expected_protocols,
        "all_protocol_replays_valid": all(item["valid"] for item in runtime.verify_protocol_replays().values()),
        "ablation_replay_valid": runtime.verify_replay()["valid"],
        "harness_owns_observed_cbit": all(
            item.harness_receipt.harness_owned and not item.harness_receipt.semantic_provider_used
            for item in snapshot.observations
        ),
        "hidden_truth_absent_from_provider_inputs": bool(task_audit)
        and not any(item["hidden_truth_key_present"] for item in task_audit),
        "semantic_assessment_blinded": len(assessment_tasks) == len(expected_protocols)
        and not any(item["protocol_identity_present"] for item in assessment_tasks),
        "one_component_omitted_per_variant": all(
            len(by_protocol[variant].omitted_components) == 1
            for variant in experiment_plan.selected_variants
        ),
        "evidence_surface_equal": all(
            item.evidence_refs == case.evidence_refs for item in snapshot.observations
        ),
        "provider_budget_respected": all(
            item.provider_call_count <= base_runtime.trial_spec.budget["max_provider_calls_per_arm"]
            for item in snapshot.protocol_results
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": f"{case.case_id}-organization-ablation-{provider_mode}",
        "bundle_id": bundle_id,
        "status": status,
        "created_at": _utc_now(),
        "provider_mode": provider_mode,
        "context_key": experiment_plan.context_key,
        "evidence_tier": experiment_plan.evidence_tier,
        "selected_variants": list(experiment_plan.selected_variants),
        "experiment_authorization": experiment_plan.as_dict(),
        "source_inventory": list(case.source_inventory),
        "gates": gates,
        "ablation_observations": [item.as_dict() for item in snapshot.observations],
        "protocol_results": [item.as_dict() for item in snapshot.protocol_results],
        "provider_task_count": len(task_audit),
        "measurement_boundary": (
            "Each bundle compares one full dynamic baseline with one-component omissions under one frozen trial. "
            "Causal attribution requires at least two independent passing bundles."
        ),
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "ablation_snapshot.json", snapshot.as_dict())
    _write_json(output_dir / "provider_task_audit.json", task_audit)
    _write_json(output_dir / "ablation_result.json", result)
    _manifest(output_dir, status)
    _build_return_pack(output_dir)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("life-cog3r", "math-cbit1", "ocs1r2"), required=True)
    parser.add_argument("--learning-result", type=Path, required=True)
    parser.add_argument("--provider-mode", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--bundle-id", default="bundle-1")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_case(
            _case_loader(args.case),
            args.output_dir,
            load_authorized_experiment_plan(args.learning_result),
            provider_mode=args.provider_mode,
            bundle_id=args.bundle_id,
        )
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:1000]}
        _write_json(args.output_dir / "ablation_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
