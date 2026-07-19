"""Deterministic end-to-end smoke for problem-structure admission."""

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
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    PROBLEM_STRUCTURE_DIMENSIONS,
    AgentDescriptor,
    AgentRegistry,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    methodology_candidate_commitment,
)
from agentos_runtime import (  # noqa: E402
    AgentAdapterResult,
    AntiAdditiveCalibrationRuntime,
    AntiAdditiveMethodologyRuntime,
    CognitiveAgent,
    ContextualOrganizationPolicyRuntime,
    EndogenousProblemRuntime,
    ProblemDefinitionStructureAdapter,
    ProblemStructureAdmissionRuntime,
    standard_role_contract,
)


RETURN_PACK_NAME = "AgentOS_ProblemStructureAdmission_ReturnPack_v0_1.zip"
SCOPE = "project://problem-structure-admission-smoke"
EVIDENCE_REF = "evidence://problem-structure-admission-smoke/source"
CONTEXT_KEY = "ctx-problem-structure-admission-smoke"


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _hash_payload(payload: Any) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _problem_payload(role: str) -> dict[str, Any]:
    candidates = [
        {
            "problem_id": "problem-negative-control-mechanism",
            "question": "Which mechanism explains the failed negative-control family?",
            "research_object": "negative_control_failure",
            "scope": SCOPE,
            "triggering_anomaly": "Local comparison survives while the family gate fails.",
            "rival_explanations": ["metric artifact", "scope-local effect"],
            "falsifier": "Independent family-level revalidation finds no failure.",
            "evidence_refs": [EVIDENCE_REF],
            "expected_cbit_gain": 0.8,
            "urgency": 0.7,
            "novelty": 0.6,
        },
        {
            "problem_id": "problem-local-rule-transfer",
            "question": "Under which scopes do local rules transfer?",
            "research_object": "local_rule_transfer",
            "scope": SCOPE,
            "triggering_anomaly": "Local rules survive without global retention support.",
            "rival_explanations": ["overfitting", "bounded transfer"],
            "falsifier": "No preregistered held-out scope preserves either rule.",
            "evidence_refs": [EVIDENCE_REF],
            "expected_cbit_gain": 0.7,
            "urgency": 0.5,
            "novelty": 0.8,
        },
    ]
    if role == "PROBLEM_FRAMER":
        return {
            "problem_candidates": candidates,
            "generation_rationale": "Residual contradictions define distinct research objects.",
            "coverage_notes": ["mechanism", "transfer boundary"],
            "evidence_refs": [EVIDENCE_REF],
        }
    if role == "PROBLEM_CRITIC":
        return {
            "candidate_reviews": [
                {
                    "problem_id": item["problem_id"],
                    "premise_risk": 0.2 if index == 0 else 0.3,
                    "redundancy_risk": 0.1 if index == 0 else 0.2,
                    "negative_transfer_risk": 0.1 if index == 0 else 0.2,
                    "challenge": "Separate the candidate from threshold or transfer assumptions.",
                    "evidence_refs": [EVIDENCE_REF],
                }
                for index, item in enumerate(candidates)
            ],
            "surviving_problem_ids": [item["problem_id"] for item in candidates],
            "minority_objections": ["The anomaly may be a frozen-threshold artifact."],
            "evidence_refs": [EVIDENCE_REF],
        }
    if role == "RESEARCHABILITY_ASSESSOR":
        return {
            "assessments": [
                {
                    "problem_id": item["problem_id"],
                    "operationalization": (
                        "Re-run each negative-control member against frozen thresholds."
                        if index == 0
                        else "Pre-register held-out scopes and test both local rules."
                    ),
                    "falsifiability": 0.9 if index == 0 else 0.8,
                    "tractability": 0.8 if index == 0 else 0.6,
                    "normalized_cost": 0.3 if index == 0 else 0.5,
                    "required_harnesses": [
                        "independent_experiment_harness"
                        if index == 0
                        else "heldout_evaluation_harness"
                    ],
                    "evidence_refs": [EVIDENCE_REF],
                }
                for index, item in enumerate(candidates)
            ],
            "researchable_problem_ids": [item["problem_id"] for item in candidates],
            "missing_capabilities": [],
            "evidence_refs": [EVIDENCE_REF],
        }
    return {
        "decision": "SELECT",
        "selected_problem_id": candidates[0]["problem_id"],
        "selection_rationale": "Resolve the contradiction with the strongest falsifier first.",
        "rejected_problem_ids": [candidates[1]["problem_id"]],
        "unresolved_conflicts": ["Threshold artifact remains a rival."],
        "evidence_refs": [EVIDENCE_REF],
        "expected_cbit_gain": 0.8,
        "stop_condition": "Stop if family-level revalidation removes the anomaly.",
    }


class ScriptedProblemRoleAdapter:
    def __init__(self, agent: CognitiveAgent) -> None:
        self.adapter_id = f"scripted-{agent.agent_id}"
        self.agent = agent

    def invoke(self, cognitive_agent, work_order, context_view, private_workspace):
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=_problem_payload(self.agent.role),
            provider_id=self.agent.descriptor.provider_id,
            model_id=self.agent.model_id,
            invocation_receipt_ref=f"provider-receipt://{work_order.work_order_id}",
        )


_SIGNALS = {
    "premise_uncertainty": ["premise_risk"],
    "evidence_conflict": ["negative_transfer_risk"],
    "replication_need": ["falsifiability"],
    "synthesis_need": ["premise_risk"],
    "coordination_complexity": ["normalized_cost"],
    "novelty_need": ["novelty"],
}
_SCORES = {
    "premise_uncertainty": 0.8,
    "evidence_conflict": 0.2,
    "replication_need": 0.8,
    "synthesis_need": 0.2,
    "coordination_complexity": 0.2,
    "novelty_need": 0.6,
}


class StructureProvider:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-structure-provider",
            model_id="scripted-structure-model",
            task_kinds=("problem_structure_dimension_assessment",),
            max_timeout_seconds=120,
        )
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        candidate = task.inputs["problem_structure_candidate"]
        refs = [task.allowed_evidence[0]]
        return {
            "result": {
                "candidate_hash": candidate["candidate_hash"],
                "dimension_assessments": [
                    {
                        "dimension": dimension,
                        "score": _SCORES[dimension],
                        "uncertainty": 0.2,
                        "support_status": "CONSISTENT",
                        "rationale": f"source-bound assessment for {dimension}",
                        "evidence_refs": refs,
                        "source_signal_names": _SIGNALS[dimension],
                    }
                    for dimension in PROBLEM_STRUCTURE_DIMENSIONS
                ],
                "global_uncertainty": 0.2,
                "evidence_refs": refs,
            },
            "usage": {"total_tokens": 30},
            "provenance_refs": refs,
        }


class MethodologyProvider:
    profile = ProviderCapabilityProfile(
        provider_id="scripted-problem-methodology-provider",
        model_id="scripted-problem-methodology-model",
        task_kinds=("anti_additive_methodology_assessment",),
        max_timeout_seconds=120,
    )

    def invoke(self, task):
        return {
            "result": {
                "current_object_adequacy": "UNDERPOWERED",
                "trigger_assessments": [
                    {
                        "trigger_id": trigger_id,
                        "triggered": trigger_id == "PATCH_PRESERVES_OBJECT_WITHOUT_CBIT_GAIN",
                        "rationale": f"bounded smoke assessment for {trigger_id}",
                        "evidence_refs": [EVIDENCE_REF],
                    }
                    for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
                ],
                "expected_effective_cbit_gain": 0.8,
                "complexity_cost": 0.2,
                "object_upgrade_gain": 0.7,
                "abstraction_cost": 0.2,
                "uncertainty": 0.2,
                "recommended_action": "UPGRADE_OBJECT",
                "rationale": "the admitted problem structure replaces a local proxy",
                "evidence_refs": [EVIDENCE_REF],
            },
            "usage": {},
            "provenance_refs": [EVIDENCE_REF],
        }


class PolicyProvider:
    def __init__(self) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-policy-provider",
            model_id="scripted-policy-model",
            task_kinds=("contextual_organization_policy_assessment",),
            max_timeout_seconds=120,
        )
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        refs = [task.allowed_evidence[0]]
        assessments = []
        for policy in task.inputs["registered_policies"]:
            preferred = policy["policy_id"] == "FIXED_TEAM"
            assessments.append(
                {
                    "policy_id": policy["policy_id"],
                    "structure_fit": 0.9 if preferred else 0.5,
                    "expected_cbit_gain": 0.7 if preferred else 0.4,
                    "estimated_normalized_cost": 0.6,
                    "residual_risk": 0.2,
                    "anti_additive_signal": 0.1,
                    "uncertainty": 0.2,
                    "rationale": "bounded policy assessment over admitted structure",
                    "evidence_refs": refs,
                }
            )
        return {
            "result": {
                "recommended_policy_id": "FIXED_TEAM",
                "policy_assessments": assessments,
                "global_uncertainty": 0.2,
                "evidence_refs": refs,
            },
            "usage": {"total_tokens": 20},
            "provenance_refs": refs,
        }


def _problem_runtime(output_dir: Path) -> EndogenousProblemRuntime:
    roles = (
        "PROBLEM_FRAMER",
        "PROBLEM_CRITIC",
        "RESEARCHABILITY_ASSESSOR",
        "AGENDA_SYNTHESIZER",
    )
    agents = []
    adapters = {}
    for index, role in enumerate(roles, start=1):
        slug = role.lower().replace("_", "-")
        descriptor = AgentDescriptor(
            agent_id=slug,
            role=role,
            capabilities=("semantic_judgment", "source_read"),
            runner_id=f"problem-runner-{index}",
            harness_id=f"problem-harness-{index}",
            provider_id=f"problem-provider-{index}",
            model_id=f"problem-model-{index}",
            context_isolation_key=f"problem-context-{index}",
            allowed_evidence_scopes=(SCOPE,),
        )
        agent = CognitiveAgent(
            descriptor,
            standard_role_contract(role),
            model_id=descriptor.model_id,
            private_memory_namespace=f"problem-memory-{index}",
            harness_capabilities=("source_read", "formal_receipt_write"),
            credit_subject_id=f"problem-credit-{index}",
        )
        agents.append(agent)
        adapters[agent.agent_id] = ScriptedProblemRoleAdapter(agent)
    return EndogenousProblemRuntime(
        session_id="problem-structure-admission-smoke",
        discovery_objective="Discover the next falsifiable problem from unresolved evidence.",
        project_scope=SCOPE,
        evidence_refs=(EVIDENCE_REF,),
        evidence_payload={"unresolved_conflicts": ["negative-control family fails"]},
        agents=tuple(agents),
        adapters=adapters,
        workspace_root=output_dir / "problem-runtime",
        kernel_authorization_ref="kernel-authorization://problem-structure-smoke",
        minimum_priority=0.2,
    )


def _selector_registry() -> AgentRegistry:
    result = AgentRegistry()
    for index, (agent_id, role) in enumerate(
        (
            ("generator", "HYPOTHESIS_GENERATOR"),
            ("reviewer", "ADVERSARIAL_REVIEWER"),
            ("replicator", "REPLICATOR"),
            ("synthesizer", "SYNTHESIZER"),
            ("coordinator", "COORDINATOR"),
        )
    ):
        result.register(
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
    return result


def _manifest(output_dir: Path, status: str) -> None:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {"manifest.json", RETURN_PACK_NAME}:
            data = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": len(data),
                    "sha256": sha256(data).hexdigest(),
                }
            )
    payload = {"status": status, "created_at": _utc_now(), "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    _write_json(output_dir / "manifest.json", payload)


def _return_pack(output_dir: Path) -> None:
    target = output_dir / RETURN_PACK_NAME
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != target:
                archive.write(path, path.relative_to(output_dir).as_posix())


def run_smoke(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    problem_runtime = _problem_runtime(output_dir)
    problem_snapshot = problem_runtime.run_to_candidate()
    problem_candidate = ProblemDefinitionStructureAdapter(
        problem_runtime,
        context_key=CONTEXT_KEY,
    ).build_candidate(candidate_id="candidate-problem-structure-admission-1")
    calibration = AntiAdditiveCalibrationRuntime(
        runtime_id="aa-cal",
        project_scope=SCOPE,
        workspace_root=output_dir / "aa-cal",
    )
    methodology_runtime = AntiAdditiveMethodologyRuntime(
        runtime_id="aa-problem",
        project_scope=SCOPE,
        provider_router=ProviderTaskRouter([MethodologyProvider()]),
        workspace_root=output_dir / "aa-method",
        calibration_source=calibration,
    )
    methodology_receipt = methodology_runtime.review_change(
        candidate=AntiAdditiveChangeCandidate.create(
            audit_id="audit-problem-structure-admission-1",
            candidate_id=problem_candidate.candidate_id,
            project_scope=SCOPE,
            change_kind="OBJECT",
            target_type="ProblemStructure",
            current_object_ref="object://problem-proxy",
            proposed_object_ref="object://problem-structure",
            current_object_level="PROXY",
            proposed_object_level="ONTOLOGY_OBJECT",
            prior_failure_count=2,
            prior_patch_count=2,
            candidate_payload_hash=methodology_candidate_commitment(problem_candidate.as_dict()),
            evidence_refs=(EVIDENCE_REF,),
        ),
        kernel_authorization_ref="kernel://problem-structure-smoke/methodology",
    )
    structure_provider = StructureProvider()
    admission = ProblemStructureAdmissionRuntime(
        runtime_id="problem-structure-admission-smoke",
        project_scope=SCOPE,
        provider_router=ProviderTaskRouter([structure_provider]),
        workspace_root=output_dir / "admission-runtime",
        anti_additive_source=methodology_runtime,
    )
    receipt = admission.admit_candidate(
        admission_id="problem-structure-admission-1",
        candidate=problem_candidate,
        kernel_authorization_ref="kernel://problem-structure-smoke/admit",
        methodology_audit_id="audit-problem-structure-admission-1",
    )
    restarted = ProblemStructureAdmissionRuntime(
        runtime_id="problem-structure-admission-smoke",
        project_scope=SCOPE,
        provider_router=ProviderTaskRouter([StructureProvider()]),
        workspace_root=output_dir / "admission-runtime",
    )
    policy_provider = PolicyProvider()
    selector = ContextualOrganizationPolicyRuntime(
        runtime_id="problem-structure-selector-smoke",
        project_scope=SCOPE,
        registry=_selector_registry(),
        provider_router=ProviderTaskRouter([policy_provider]),
        workspace_root=output_dir / "selector-runtime",
        problem_source=restarted,
    )
    selection = selector.select_policy(
        selection_id="selection-from-admitted-structure",
        problem_admission_id="problem-structure-admission-1",
        evidence_tier="SCRIPTED_FIXTURE",
        budget=OrganizationBudgetEnvelope(
            "budget://problem-structure-smoke", 4, 5, 4, 0.8
        ),
        risk=OrganizationRiskEnvelope(
            "risk://problem-structure-smoke", 0.5, 0.4, 0.5, 0.4, True, 4
        ),
        kernel_authorization_ref="kernel://problem-structure-smoke/select",
    )
    gates = {
        "plural_problem_runtime_reached_candidate": (
            problem_snapshot.stage == "CANDIDATE"
            and len(problem_snapshot.messages) == 4
            and problem_runtime.verify_replay()["valid"] is True
        ),
        "provider_assessed_exact_six_dimensions": (
            len(structure_provider.tasks) == 1
            and len(receipt.provider_judgment.dimension_assessments) == 6
        ),
        "kernel_admitted_project_scoped_structure": (
            receipt.decision.candidate_state == "ADMITTED_PROBLEM_STRUCTURE_PROJECT_SCOPED"
            and receipt.as_dict()["execution_authorized"] is False
        ),
        "anti_additive_candidate_authority_bound": (
            methodology_receipt.decision.state == "REQUIRE_CALIBRATED_VALIDATION"
            and receipt.decision.anti_additive_methodology_receipt_hash
            == methodology_receipt.receipt_hash
            and methodology_runtime.verify_replay()["valid"] is True
        ),
        "admission_restart_replay_valid": restarted.verify_replay()["valid"] is True,
        "selector_used_admitted_source": (
            selection.kernel_decision.problem_structure_hash
            == receipt.problem_structure.as_dict()["problem_structure_hash"]
            and selection.kernel_decision.selected_policy_id == "FIXED_TEAM"
            and selection.kernel_decision.activation_mode == "EXPLORATORY_TRIAL_ONLY"
        ),
        "no_global_or_production_authority": (
            receipt.as_dict()["global_policy_authority"] is False
            and receipt.as_dict()["production_activation"] is False
        ),
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "problem-structure-admission-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "gates": gates,
        "problem_definition": problem_snapshot.as_dict(),
        "admission_receipt": receipt.as_dict(),
        "methodology_receipt": methodology_receipt.as_dict(),
        "methodology_replay": methodology_runtime.verify_replay(),
        "admission_replay": restarted.verify_replay(),
        "selector_receipt": selection.as_dict(),
        "provider_call_count": len(structure_provider.tasks) + len(policy_provider.tasks),
    }
    _write_json(output_dir / "problem_structure_admission_smoke_result.json", result)
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
        _write_json(args.output_dir / "problem_structure_admission_smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
