import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    AgentDescriptor,
    AgentRegistry,
    CONTEXTUAL_POLICY_ROLE_MAP,
    EnsembleAssignment,
    SelectionExecutionFeedbackGate,
    SelectionExecutionBudget,
    SelectionExecutionRequest,
)
from agentos_kernel.contextual_policy_models import hash_payload  # noqa: E402
from agentos_runtime import AblationExecutionPolicyAdapter  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def descriptor(agent_id: str, role: str, index: int) -> AgentDescriptor:
    return AgentDescriptor(
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


def fixture_runtime():
    registry = AgentRegistry()
    agents = (
        descriptor("generator", "HYPOTHESIS_GENERATOR", 0),
        descriptor("reviewer", "ADVERSARIAL_REVIEWER", 1),
        descriptor("replicator", "REPLICATOR", 2),
        descriptor("synthesizer", "SYNTHESIZER", 3),
    )
    coordinator = descriptor("coordinator", "COORDINATOR", 4)
    for agent in agents:
        registry.register(agent)
    results = (
        SimpleNamespace(
            protocol_id="DYNAMIC_TEAM",
            agent_ids=tuple(item.agent_id for item in agents),
            coordinator_agent_id=coordinator.agent_id,
            provider_call_count=5,
            result_hash=digest("dynamic-result"),
        ),
        SimpleNamespace(
            protocol_id="DYNAMIC_NO_SYNTHESIZER",
            agent_ids=tuple(item.agent_id for item in agents[:-1]),
            coordinator_agent_id=coordinator.agent_id,
            provider_call_count=4,
            result_hash=digest("no-synth-result"),
        ),
    )

    def receipt(protocol_id):
        return SimpleNamespace(
            trial_id="ablation-trial",
            evidence_refs=("evidence://ablation",),
            observed_cbit_gain=0.78 if "NO_" in protocol_id else 0.60,
            normalized_cost=0.55 if "NO_" in protocol_id else 0.70,
            convergence_steps=4,
            errors_exposed=2,
            errors_corrected=1,
            negative_transfer_opportunities=2,
            negative_transfer_intercepts=1,
            receipt_hash=digest(f"receipt-{protocol_id}"),
            harness_owned=True,
            semantic_provider_used=False,
        )

    observations = tuple(
        SimpleNamespace(
            protocol_id=item.protocol_id,
            effectiveness_score=0.84 if "NO_" in item.protocol_id else 0.70,
            harness_receipt=receipt(item.protocol_id),
        )
        for item in results
    )

    class Snapshot:
        def __init__(self, protocol_results, observation_values):
            self.protocol_results = protocol_results
            self.observations = observation_values

        def as_dict(self):
            return {
                "protocols": [item.protocol_id for item in self.protocol_results],
                "observations": [item.protocol_id for item in self.observations],
            }

    class Runtime:
        trial_spec = SimpleNamespace(
            trial_id="ablation-trial",
            project_scope="project://ablation-adapter",
            evidence_refs=("evidence://ablation",),
        )
        experiment_plan = SimpleNamespace(
            selected_variants=("DYNAMIC_NO_SYNTHESIZER",),
            budget={"max_provider_calls_per_run": 10},
        )

        def __init__(self):
            self.registry = registry
            self.executed = False

        def execute_protocols(self):
            self.executed = True

        def evaluate_protocols(self):
            assert self.executed
            return Snapshot(results, observations)

        def verify_replay(self):
            return {"valid": True}

        def verify_protocol_replays(self):
            return {
                "DYNAMIC_TEAM": {"valid": True},
                "DYNAMIC_NO_SYNTHESIZER": {"valid": True},
            }

    return Runtime(), agents, coordinator


def request(agents, coordinator, *, execution_budget=None):
    selected_agents = (*agents[:-1], coordinator)
    assignment = EnsembleAssignment(
        team_id="selected-no-synth",
        agents=selected_agents,
        context_isolated=True,
    )
    return SelectionExecutionRequest.create(
        bridge_run_id="ablation-bridge-run",
        selection_receipt_hash=digest("selection"),
        project_scope="project://ablation-adapter",
        context_key="ctx-ablation-adapter",
        evidence_tier="SCRIPTED_FIXTURE",
        trial_group_id="ablation-group",
        trial_id="ablation-trial",
        selected_policy_id="DYNAMIC_NO_SYNTHESIZER",
        selected_agent_ids=tuple(item.agent_id for item in selected_agents),
        selected_roles=CONTEXTUAL_POLICY_ROLE_MAP["DYNAMIC_NO_SYNTHESIZER"],
        selected_agent_binding_hash=hash_payload(assignment.as_dict()["agents"]),
        trial_evidence_refs=("evidence://ablation",),
        execution_budget=execution_budget
        or SelectionExecutionBudget.create(
            budget_ref="budget://ablation-adapter",
            max_protocol_runs=2,
            max_provider_calls_total=20,
            max_normalized_cost_per_protocol=0.8,
        ),
        kernel_execution_authorization_ref="kernel://ablation-adapter/run",
    )


def test_ablation_adapter_executes_selected_variant_and_dynamic_comparator():
    runtime, agents, coordinator = fixture_runtime()
    execution_request = request(agents, coordinator)
    adapter = AblationExecutionPolicyAdapter(
        adapter_id="ablation-adapter",
        runtime=runtime,
        coordinator_descriptors={
            "DYNAMIC_TEAM": coordinator,
            "DYNAMIC_NO_SYNTHESIZER": coordinator,
        },
    )

    bundle = adapter.execute(execution_request)
    records = SelectionExecutionFeedbackGate().admit(
        request=execution_request,
        bundle=bundle,
    )

    assert {item.protocol_id for item in bundle.outcomes} == {
        "DYNAMIC_TEAM",
        "DYNAMIC_NO_SYNTHESIZER",
    }
    assert {item.protocol_id for item in records} == {
        "DYNAMIC_TEAM",
        "DYNAMIC_NO_SYNTHESIZER",
    }
    assert all(item.replay_valid for item in records)
    assert bundle.executed_protocol_ids == (
        "DYNAMIC_TEAM",
        "DYNAMIC_NO_SYNTHESIZER",
    )
    assert bundle.total_provider_call_count == 9


def test_ablation_adapter_requires_explicit_coordinator_identity_binding():
    runtime, agents, coordinator = fixture_runtime()
    adapter = AblationExecutionPolicyAdapter(adapter_id="ablation-adapter", runtime=runtime)

    with pytest.raises(ValueError, match="coordinator_binding_missing"):
        adapter.execute(request(agents, coordinator))


def test_ablation_adapter_blocks_before_execution_when_budget_cannot_cover_plan():
    runtime, agents, coordinator = fixture_runtime()
    execution_request = request(
        agents,
        coordinator,
        execution_budget=SelectionExecutionBudget.create(
            budget_ref="budget://ablation-adapter-too-small",
            max_protocol_runs=1,
            max_provider_calls_total=10,
            max_normalized_cost_per_protocol=0.8,
        ),
    )
    adapter = AblationExecutionPolicyAdapter(
        adapter_id="ablation-adapter",
        runtime=runtime,
        coordinator_descriptors={
            "DYNAMIC_TEAM": coordinator,
            "DYNAMIC_NO_SYNTHESIZER": coordinator,
        },
    )

    with pytest.raises(ValueError, match="protocol_budget_insufficient"):
        adapter.execute(execution_request)

    assert runtime.executed is False
