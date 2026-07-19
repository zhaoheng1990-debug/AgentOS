import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(CORE_ROOT / "tests"))

from agentos_kernel import (  # noqa: E402
    PROBLEM_STRUCTURE_DIMENSIONS,
    AgentDescriptor,
    AgentRegistry,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
)
from agentos_runtime import (  # noqa: E402
    ContextualOrganizationPolicyRuntime,
    ProblemDefinitionStructureAdapter,
    ProblemStructureAdmissionRuntime,
)
from test_endogenous_problem_runtime import runtime as build_problem_runtime  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


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
    def __init__(self, *, mutate=None):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-problem-structure-provider",
            model_id="fixture-problem-structure-model",
            task_kinds=("problem_structure_dimension_assessment",),
            max_timeout_seconds=120,
        )
        self.mutate = mutate
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        candidate = task.inputs["problem_structure_candidate"]
        refs = [task.allowed_evidence[0]]
        result = {
            "candidate_hash": candidate["candidate_hash"],
            "dimension_assessments": [
                {
                    "dimension": dimension,
                    "score": _SCORES[dimension],
                    "uncertainty": 0.2,
                    "support_status": "CONSISTENT",
                    "rationale": f"bounded support for {dimension}",
                    "evidence_refs": refs,
                    "source_signal_names": _SIGNALS[dimension],
                }
                for dimension in PROBLEM_STRUCTURE_DIMENSIONS
            ],
            "global_uncertainty": 0.2,
            "evidence_refs": refs,
        }
        if self.mutate:
            self.mutate(result)
        return {
            "result": result,
            "usage": {"total_tokens": 30},
            "provenance_refs": refs,
        }


class PolicyProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-policy-provider",
            model_id="fixture-policy-model",
            task_kinds=("contextual_organization_policy_assessment",),
            max_timeout_seconds=120,
        )

    def invoke(self, task):
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
                    "rationale": "fixture bounded policy assessment",
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


def admission_runtime(tmp_path, provider=None):
    provider = provider or StructureProvider()
    return (
        ProblemStructureAdmissionRuntime(
            runtime_id="problem-structure-admission-test",
            project_scope="project://fixture",
            provider_router=ProviderTaskRouter([provider]),
            workspace_root=tmp_path,
        ),
        provider,
    )


def ready_problem_runtime(tmp_path):
    runtime, _ = build_problem_runtime(tmp_path)
    result = runtime.run_to_candidate()
    assert result.stage == "CANDIDATE"
    return runtime


def registry() -> AgentRegistry:
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


def test_existing_four_role_problem_runtime_admits_structure_and_feeds_selector(tmp_path):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    engine, structure_provider = admission_runtime(tmp_path / "admission")

    receipt = engine.admit_from_problem_runtime(
        admission_id="structure-admission-1",
        problem_runtime=source_runtime,
        context_key="ctx-admitted-problem",
        kernel_authorization_ref="kernel://problem-structure/admit-1",
    )

    assert receipt.decision.candidate_state == "ADMITTED_PROBLEM_STRUCTURE_PROJECT_SCOPED"
    assert receipt.problem_structure.structure_receipt_hash == receipt.decision.decision_hash
    assert receipt.problem_structure.premise_uncertainty == 0.8
    assert receipt.as_dict()["execution_authorized"] is False
    assert len(structure_provider.tasks) == 1
    assert engine.verify_replay()["valid"] is True

    selector = ContextualOrganizationPolicyRuntime(
        runtime_id="selector-from-admitted-problem",
        project_scope="project://fixture",
        registry=registry(),
        provider_router=ProviderTaskRouter([PolicyProvider()]),
        workspace_root=tmp_path / "selector",
        problem_source=engine,
    )
    selection = selector.select_policy(
        selection_id="selection-from-admitted-problem",
        problem_admission_id="structure-admission-1",
        evidence_tier="SCRIPTED_FIXTURE",
        budget=OrganizationBudgetEnvelope(
            budget_ref="budget://admitted-problem",
            max_roles=4,
            max_provider_calls=5,
            max_coordination_steps=4,
            max_normalized_cost=0.8,
        ),
        risk=OrganizationRiskEnvelope(
            risk_ref="risk://admitted-problem",
            max_residual_risk=0.5,
            max_provider_uncertainty=0.4,
            max_anti_additive_signal=0.5,
            matched_evidence_required_above_risk=0.4,
            allow_unmatched_exploration=True,
            exploration_max_roles=4,
        ),
        kernel_authorization_ref="kernel://selector/admitted-problem",
    )
    assert selection.kernel_decision.selected_policy_id == "FIXED_TEAM"
    assert selection.kernel_decision.activation_mode == "EXPLORATORY_TRIAL_ONLY"
    assert selection.kernel_decision.problem_structure_hash == receipt.problem_structure.as_dict()[
        "problem_structure_hash"
    ]


@pytest.mark.parametrize(
    ("mutate", "error"),
    (
        (
            lambda result: result["dimension_assessments"][0].update(
                support_status="CONFLICT"
            ),
            "dimension_support_not_consistent",
        ),
        (
            lambda result: (
                result["dimension_assessments"][0].update(uncertainty=0.7),
                result.update(global_uncertainty=0.7),
            ),
            "global_uncertainty_exceeded",
        ),
        (
            lambda result: result["dimension_assessments"][0].update(
                source_signal_names=["novelty"]
            ),
            "dimension_source_signal_required:premise_uncertainty",
        ),
    ),
)
def test_kernel_blocks_conflicted_uncertain_or_unbound_dimensions(tmp_path, mutate, error):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    engine, _ = admission_runtime(tmp_path / "admission", StructureProvider(mutate=mutate))

    with pytest.raises(ValueError, match=error):
        engine.admit_from_problem_runtime(
            admission_id="structure-admission-blocked",
            problem_runtime=source_runtime,
            context_key="ctx-admitted-problem",
            kernel_authorization_ref="kernel://problem-structure/blocked",
        )

    assert engine.snapshot().receipts == ()
    assert "PROBLEM_STRUCTURE_ADMISSION_BLOCKED" in (
        engine.public_store_path / "events.jsonl"
    ).read_text(encoding="utf-8")


def test_revision_requires_exact_latest_receipt_and_survives_restart(tmp_path):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    engine, _ = admission_runtime(tmp_path / "admission")
    first = engine.admit_from_problem_runtime(
        admission_id="structure-admission-1",
        problem_runtime=source_runtime,
        context_key="ctx-admitted-problem",
        kernel_authorization_ref="kernel://problem-structure/admit-1",
    )

    with pytest.raises(ValueError, match="revision_binding_required"):
        engine.admit_from_problem_runtime(
            admission_id="structure-admission-unbound-revision",
            problem_runtime=source_runtime,
            context_key="ctx-admitted-problem",
            kernel_authorization_ref="kernel://problem-structure/unbound-revision",
        )

    second = engine.admit_from_problem_runtime(
        admission_id="structure-admission-2",
        problem_runtime=source_runtime,
        context_key="ctx-admitted-problem",
        supersedes_receipt_hash=first.receipt_hash,
        kernel_authorization_ref="kernel://problem-structure/admit-2",
    )
    assert second.decision.candidate_state == "ADMITTED_REVISION_PROJECT_SCOPED"
    assert second.decision.supersedes_receipt_hash == first.receipt_hash

    restarted, _ = admission_runtime(tmp_path / "admission")
    assert restarted.verify_replay()["valid"] is True
    assert len(restarted.snapshot().receipts) == 2
    assert restarted.latest_receipt(
        context_key="ctx-admitted-problem",
        source_problem_id=first.candidate.source_problem_id,
    ).receipt_hash == second.receipt_hash


def test_selector_with_admission_source_rejects_direct_problem_bypass(tmp_path):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    engine, _ = admission_runtime(tmp_path / "admission")
    receipt = engine.admit_from_problem_runtime(
        admission_id="structure-admission-1",
        problem_runtime=source_runtime,
        context_key="ctx-admitted-problem",
        kernel_authorization_ref="kernel://problem-structure/admit-1",
    )
    selector = ContextualOrganizationPolicyRuntime(
        runtime_id="selector-no-direct-bypass",
        project_scope="project://fixture",
        registry=registry(),
        provider_router=ProviderTaskRouter([PolicyProvider()]),
        workspace_root=tmp_path / "selector",
        problem_source=engine,
    )

    with pytest.raises(ValueError, match="direct_problem_forbidden"):
        selector.select_policy(
            selection_id="selection-direct-bypass",
            problem=receipt.problem_structure,
            evidence_tier="SCRIPTED_FIXTURE",
            budget=OrganizationBudgetEnvelope(
                "budget://bypass", 4, 5, 4, 0.8
            ),
            risk=OrganizationRiskEnvelope(
                "risk://bypass", 0.5, 0.4, 0.5, 0.4, True, 4
            ),
            kernel_authorization_ref="kernel://selector/direct-bypass",
        )


def test_selector_revalidates_receipt_identity_returned_by_source(tmp_path):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    engine, _ = admission_runtime(tmp_path / "admission")
    receipt = engine.admit_from_problem_runtime(
        admission_id="structure-admission-1",
        problem_runtime=source_runtime,
        context_key="ctx-admitted-problem",
        kernel_authorization_ref="kernel://problem-structure/admit-1",
    )

    class WrongReceiptSource:
        def problem_structure_admission_receipt(self, **_):
            return receipt

    selector = ContextualOrganizationPolicyRuntime(
        runtime_id="selector-wrong-receipt-id",
        project_scope="project://fixture",
        registry=registry(),
        provider_router=ProviderTaskRouter([PolicyProvider()]),
        workspace_root=tmp_path / "selector",
        problem_source=WrongReceiptSource(),
    )

    with pytest.raises(ValueError, match="problem_admission_receipt_invalid"):
        selector.select_policy(
            selection_id="selection-wrong-receipt-id",
            problem_admission_id="different-admission-id",
            evidence_tier="SCRIPTED_FIXTURE",
            budget=OrganizationBudgetEnvelope(
                "budget://wrong-receipt", 4, 5, 4, 0.8
            ),
            risk=OrganizationRiskEnvelope(
                "risk://wrong-receipt", 0.5, 0.4, 0.5, 0.4, True, 4
            ),
            kernel_authorization_ref="kernel://selector/wrong-receipt",
        )


def test_tampered_source_message_is_rejected_before_provider_call(tmp_path):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    provider = StructureProvider()
    engine, _ = admission_runtime(tmp_path / "admission", provider)
    message = source_runtime._messages[0]
    source_runtime._messages[0] = replace(message, payload={**message.payload, "tampered": True})

    with pytest.raises(ValueError, match="source_message_hash_invalid"):
        engine.admit_from_problem_runtime(
            admission_id="structure-admission-tampered",
            problem_runtime=source_runtime,
            context_key="ctx-admitted-problem",
            kernel_authorization_ref="kernel://problem-structure/tampered",
        )

    assert provider.tasks == []


def test_tampered_admission_event_chain_is_rejected_on_restart(tmp_path):
    source_runtime = ready_problem_runtime(tmp_path / "problem")
    engine, _ = admission_runtime(tmp_path / "admission")
    engine.admit_from_problem_runtime(
        admission_id="structure-admission-1",
        problem_runtime=source_runtime,
        context_key="ctx-admitted-problem",
        kernel_authorization_ref="kernel://problem-structure/admit-1",
    )
    events_path = engine.public_store_path / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[-1])
    event["payload"]["receipt"]["candidate"]["context_key"] = "ctx-tampered"
    lines[-1] = json.dumps(event, sort_keys=True)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="problem_structure_admission_replay_invalid"):
        admission_runtime(tmp_path / "admission")
