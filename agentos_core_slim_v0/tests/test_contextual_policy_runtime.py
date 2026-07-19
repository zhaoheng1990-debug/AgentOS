import hashlib
import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class ContextualPolicyProvider:
    def __init__(self, result_factory=None):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-organization-provider",
            model_id="fixture-contextual-policy-model",
            task_kinds=("contextual_organization_policy_assessment",),
            max_timeout_seconds=120,
        )
        self.result_factory = result_factory or provider_result
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        result = self.result_factory(task)
        return {
            "result": result,
            "usage": {"total_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def provider_result(task):
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
    return {
        "recommended_policy_id": "DYNAMIC_TEAM",
        "policy_assessments": assessments,
        "global_uncertainty": 0.25,
        "evidence_refs": refs,
    }


def registry(*, include_coordinator: bool = True, shared_provider: bool = False) -> AgentRegistry:
    result = AgentRegistry()
    role_ids = (
        ("generator", "HYPOTHESIS_GENERATOR"),
        ("reviewer", "ADVERSARIAL_REVIEWER"),
        ("replicator", "REPLICATOR"),
        ("synthesizer", "SYNTHESIZER"),
        ("coordinator", "COORDINATOR"),
    )
    for index, (agent_id, role) in enumerate(role_ids):
        if role == "COORDINATOR" and not include_coordinator:
            continue
        result.register(
            AgentDescriptor(
                agent_id=agent_id,
                role=role,
                capabilities=("bounded-cognitive-work",),
                runner_id=f"runner-{agent_id}",
                harness_id=f"harness-{agent_id}",
                provider_id="shared-provider" if shared_provider else f"provider-{index}",
                model_id=f"model-{index}",
                context_isolation_key=f"context-{agent_id}",
                allowed_evidence_scopes=("INTERNAL_PROJECT",),
            )
        )
    return result


def trial_record(
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
        context_key="ctx-runtime",
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
        execution_result_hash=digest(f"execution-{group_id}-{policy_id}"),
        source_result_hash=digest(source_id),
        replay_valid=True,
    )


def matched_records() -> tuple[OrganizationTrialRecord, ...]:
    records = []
    for index in (1, 2):
        source = f"runtime-source-{index}"
        group = f"runtime-group-{index}"
        records.extend(
            (
                trial_record(
                    "DYNAMIC_TEAM", group, source, effectiveness=0.70, cbit=0.60, cost=0.70
                ),
                trial_record(
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


def problem() -> ContextualProblemStructure:
    return ContextualProblemStructure(
        problem_id="problem-runtime-1",
        context_key="ctx-runtime",
        project_scope="project://contextual-runtime-test",
        objective="Challenge uncertain premises, replicate independently, and coordinate the bounded team.",
        premise_uncertainty=0.8,
        evidence_conflict=0.2,
        replication_need=0.8,
        synthesis_need=0.2,
        coordination_complexity=0.8,
        novelty_need=0.5,
        evidence_refs=("evidence://problem-runtime",),
        structure_receipt_ref="provider-receipt://problem-runtime",
        structure_receipt_hash=digest("problem-runtime-structure"),
    )


def budget() -> OrganizationBudgetEnvelope:
    return OrganizationBudgetEnvelope(
        budget_ref="budget://contextual-runtime-test",
        max_roles=4,
        max_provider_calls=5,
        max_coordination_steps=4,
        max_normalized_cost=0.8,
    )


def risk(**overrides) -> OrganizationRiskEnvelope:
    values = {
        "risk_ref": "risk://contextual-runtime-test",
        "max_residual_risk": 0.5,
        "max_provider_uncertainty": 0.4,
        "max_anti_additive_signal": 0.5,
        "matched_evidence_required_above_risk": 0.4,
        "allow_unmatched_exploration": True,
        "exploration_max_roles": 2,
    }
    values.update(overrides)
    return OrganizationRiskEnvelope(**values)


def runtime(tmp_path, *, adapter=None, agents=None):
    adapter = adapter or ContextualPolicyProvider()
    return (
        ContextualOrganizationPolicyRuntime(
            runtime_id="contextual-policy-runtime-fixture",
            project_scope="project://contextual-runtime-test",
            registry=agents or registry(),
            provider_router=ProviderTaskRouter([adapter]),
            workspace_root=tmp_path,
        ),
        adapter,
    )


def select(engine, *, selection_id="selection-1", risk_value=None):
    return engine.select_policy(
        selection_id=selection_id,
        problem=problem(),
        records=matched_records(),
        evidence_tier="LIVE_PROJECT",
        budget=budget(),
        risk=risk_value or risk(),
        kernel_authorization_ref="kernel://contextual-runtime-test",
    )


def test_runtime_keeps_provider_advisory_and_kernel_selects_feasible_policy(tmp_path):
    engine, adapter = runtime(tmp_path)

    receipt = select(engine)

    assert receipt.provider_advice.recommended_policy_id == "DYNAMIC_TEAM"
    assert receipt.kernel_decision.selected_policy_id == "DYNAMIC_NO_SYNTHESIZER"
    assert tuple(agent.role for agent in receipt.assignment.agents) == (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "COORDINATOR",
    )
    assert receipt.assignment.execution_authorized is True
    assert receipt.as_dict()["global_policy_authority"] is False
    assert len(adapter.tasks) == 1
    assert engine.verify_replay()["valid"] is True


def test_runtime_recovers_selection_and_hash_after_restart(tmp_path):
    engine, _ = runtime(tmp_path)
    receipt = select(engine)

    restarted, _ = runtime(tmp_path)
    recovered = restarted.selection(receipt.selection_id)

    assert recovered is not None
    assert recovered.receipt_hash == receipt.receipt_hash
    assert restarted.verify_replay()["valid"] is True


def test_provider_nested_contract_failure_is_blocked_and_replayable(tmp_path):
    def incomplete(task):
        result = provider_result(task)
        del result["policy_assessments"][0]["residual_risk"]
        return result

    engine, _ = runtime(tmp_path, adapter=ContextualPolicyProvider(incomplete))

    with pytest.raises(ValueError, match="contextual_policy_provider_assessment_schema_invalid"):
        select(engine)

    assert engine.verify_replay()["valid"] is True
    events_path = engine.public_store_path / "events.jsonl"
    assert "CONTEXTUAL_POLICY_PROVIDER_BLOCKED" in events_path.read_text(encoding="utf-8")


def test_out_of_scope_provider_evidence_fails_closed(tmp_path):
    def out_of_scope(task):
        result = provider_result(task)
        result["evidence_refs"] = ["evidence://not-allowed"]
        return result

    engine, _ = runtime(tmp_path, adapter=ContextualPolicyProvider(out_of_scope))

    with pytest.raises(ValueError, match="contextual_policy_provider_evidence_invalid"):
        select(engine)

    assert engine.verify_replay()["valid"] is True


def test_missing_required_registry_role_forces_kernel_abstention(tmp_path):
    engine, _ = runtime(tmp_path, agents=registry(include_coordinator=False))

    receipt = select(engine)

    assert receipt.kernel_decision.activation_mode == "ABSTAIN"
    assert receipt.assignment is None
    assert receipt.kernel_decision.execution_authorized is False


def test_distinct_provider_gate_is_enforced_by_registry_feasibility(tmp_path):
    engine, _ = runtime(tmp_path, agents=registry(shared_provider=True))

    receipt = select(engine, risk_value=risk(require_distinct_provider=True))

    assert receipt.kernel_decision.activation_mode == "ABSTAIN"
    assert all(
        "no_context_isolated_registered_assignment" in item.hard_gate_failures
        or "problem_required_role_missing" in item.hard_gate_failures
        for item in receipt.kernel_decision.candidate_evaluations
    )


def test_tampered_public_event_chain_is_rejected_on_restart(tmp_path):
    engine, _ = runtime(tmp_path)
    select(engine)
    events_path = engine.public_store_path / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[-1])
    record["payload"]["selection"]["context_key"] = "ctx-tampered"
    lines[-1] = json.dumps(record, sort_keys=True)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="contextual_policy_replay_invalid"):
        runtime(tmp_path)
