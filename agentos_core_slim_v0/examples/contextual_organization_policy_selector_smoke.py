"""Deterministic smoke for context-conditioned organization policy selection."""

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
    AgentDescriptor,
    AgentRegistry,
    ContextualProblemStructure,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    OrganizationTrialRecord,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
)
from agentos_runtime import ContextualOrganizationPolicyRuntime  # noqa: E402


RETURN_PACK_NAME = "AgentOS_ContextualOrganizationPolicySelector_ReturnPack_v0_1.zip"


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(data)


def _digest(label: str) -> str:
    return _hash_bytes(label.encode("utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


class StaticOrganizationProvider:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-organization-provider",
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
            preferred = policy_id == "DYNAMIC_NO_SYNTHESIZER"
            assessments.append(
                {
                    "policy_id": policy_id,
                    "structure_fit": 0.95 if preferred else 0.55,
                    "expected_cbit_gain": 0.82 if preferred else 0.50,
                    "estimated_normalized_cost": 0.55 if preferred else 0.70,
                    "residual_risk": 0.20,
                    "anti_additive_signal": 0.18,
                    "uncertainty": 0.22 if preferred else 0.25,
                    "rationale": f"bounded exact-context assessment for {policy_id}",
                    "evidence_refs": refs,
                }
            )
        result = {
            "recommended_policy_id": "DYNAMIC_TEAM",
            "policy_assessments": assessments,
            "global_uncertainty": 0.25,
            "evidence_refs": refs,
        }
        return {
            "result": result,
            "usage": {"total_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def _registry() -> AgentRegistry:
    registry = AgentRegistry()
    roles = (
        ("generator", "HYPOTHESIS_GENERATOR"),
        ("reviewer", "ADVERSARIAL_REVIEWER"),
        ("replicator", "REPLICATOR"),
        ("synthesizer", "SYNTHESIZER"),
        ("coordinator", "COORDINATOR"),
    )
    for index, (agent_id, role) in enumerate(roles):
        registry.register(
            AgentDescriptor(
                agent_id=agent_id,
                role=role,
                capabilities=("bounded-cognitive-work",),
                runner_id=f"runner-{agent_id}",
                harness_id=f"harness-{agent_id}",
                provider_id=f"provider-{index}",
                model_id=f"model-{index}",
                context_isolation_key=f"context-{agent_id}",
                allowed_evidence_scopes=("INTERNAL_PROJECT",),
            )
        )
    return registry


def _trial_record(
    policy_id: str,
    group_id: str,
    source_id: str,
    *,
    effectiveness: float,
    cbit: float,
    cost: float,
) -> OrganizationTrialRecord:
    refs = (f"evidence://{source_id}",)
    return OrganizationTrialRecord.create(
        record_id=f"record-{group_id}-{policy_id.lower()}",
        trial_group_id=group_id,
        context_key="ctx-selector-smoke",
        evidence_tier="LIVE_PROJECT",
        protocol_id=policy_id,
        effectiveness_score=effectiveness,
        observed_cbit_gain=cbit,
        normalized_cost=cost,
        convergence_steps=4,
        errors_exposed=2,
        errors_corrected=1,
        negative_transfer_opportunities=2,
        negative_transfer_intercepts=1,
        evidence_refs=refs,
        harness_receipt_ref=f"harness://{source_id}/{policy_id}",
        execution_result_hash=_digest(f"execution-{group_id}-{policy_id}"),
        source_result_hash=_digest(source_id),
        replay_valid=True,
    )


def _records() -> tuple[OrganizationTrialRecord, ...]:
    records = []
    for index in (1, 2):
        source = f"selector-source-{index}"
        group = f"selector-group-{index}"
        records.extend(
            (
                _trial_record(
                    "DYNAMIC_TEAM", group, source, effectiveness=0.70, cbit=0.60, cost=0.70
                ),
                _trial_record(
                    "DYNAMIC_NO_SYNTHESIZER",
                    group,
                    source,
                    effectiveness=0.84,
                    cbit=0.78,
                    cost=0.55,
                ),
            )
        )
    return tuple(records)


def _problem() -> ContextualProblemStructure:
    return ContextualProblemStructure(
        problem_id="problem-selector-smoke",
        context_key="ctx-selector-smoke",
        project_scope="project://contextual-policy-selector-smoke",
        objective="Challenge uncertain premises, replicate independently, and coordinate a bounded team.",
        premise_uncertainty=0.8,
        evidence_conflict=0.2,
        replication_need=0.8,
        synthesis_need=0.2,
        coordination_complexity=0.8,
        novelty_need=0.5,
        evidence_refs=("evidence://selector-smoke/problem",),
        structure_receipt_ref="provider-receipt://selector-smoke/problem-structure",
        structure_receipt_hash=_digest("selector-smoke-problem-structure"),
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
    provider = StaticOrganizationProvider()
    router = ProviderTaskRouter([provider])
    runtime = ContextualOrganizationPolicyRuntime(
        runtime_id="contextual-policy-selector-smoke",
        project_scope="project://contextual-policy-selector-smoke",
        registry=_registry(),
        provider_router=router,
        workspace_root=output_dir / "runtime",
    )
    receipt = runtime.select_policy(
        selection_id="selector-smoke-1",
        problem=_problem(),
        records=_records(),
        evidence_tier="LIVE_PROJECT",
        budget=OrganizationBudgetEnvelope(
            budget_ref="budget://selector-smoke",
            max_roles=4,
            max_provider_calls=5,
            max_coordination_steps=4,
            max_normalized_cost=0.8,
        ),
        risk=OrganizationRiskEnvelope(
            risk_ref="risk://selector-smoke",
            max_residual_risk=0.5,
            max_provider_uncertainty=0.4,
            max_anti_additive_signal=0.5,
            matched_evidence_required_above_risk=0.4,
            allow_unmatched_exploration=True,
            exploration_max_roles=2,
            require_distinct_provider=True,
        ),
        kernel_authorization_ref="kernel://selector-smoke/select",
    )
    restarted = ContextualOrganizationPolicyRuntime(
        runtime_id="contextual-policy-selector-smoke",
        project_scope="project://contextual-policy-selector-smoke",
        registry=_registry(),
        provider_router=router,
        workspace_root=output_dir / "runtime",
    )
    recovered = restarted.selection(receipt.selection_id)
    replay = restarted.verify_replay()
    selected_roles = tuple(agent.role for agent in receipt.assignment.agents) if receipt.assignment else ()
    gates = {
        "provider_remained_advisory": receipt.provider_advice.recommended_policy_id == "DYNAMIC_TEAM",
        "kernel_selected_budget_feasible_policy": (
            receipt.kernel_decision.selected_policy_id == "DYNAMIC_NO_SYNTHESIZER"
        ),
        "problem_required_roles_preserved": selected_roles
        == (
            "HYPOTHESIS_GENERATOR",
            "ADVERSARIAL_REVIEWER",
            "REPLICATOR",
            "COORDINATOR",
        ),
        "matched_evidence_authorized_project_scope": (
            receipt.kernel_decision.activation_mode == "AUTHORIZED_PROJECT_SCOPED"
        ),
        "assignment_execution_matches_kernel": (
            receipt.assignment is not None and receipt.assignment.execution_authorized
        ),
        "restart_receipt_hash_matches": (
            recovered is not None and recovered.receipt_hash == receipt.receipt_hash
        ),
        "restart_replay_valid": replay["valid"],
        "provider_called_once": len(provider.tasks) == 1,
        "no_global_or_production_authority": (
            receipt.as_dict()["global_policy_authority"] is False
            and receipt.as_dict()["production_activation"] is False
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "contextual-organization-policy-selector-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "gates": gates,
        "selection_receipt": receipt.as_dict(),
        "restart_replay": replay,
        "provider_task_count": len(provider.tasks),
        "manifest_path": str(output_dir / "manifest.json"),
        "return_pack": str(output_dir / RETURN_PACK_NAME),
    }
    _write_json(output_dir / "contextual_policy_selector_smoke_result.json", result)
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
        _write_json(args.output_dir / "contextual_policy_selector_smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
