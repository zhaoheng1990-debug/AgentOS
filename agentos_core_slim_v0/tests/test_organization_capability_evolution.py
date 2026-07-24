from __future__ import annotations

import json

import pytest

from agentos_kernel import (
    AgentCapabilityEvidence,
    AgentDescriptor,
    AgentRegistry,
    OrganizationAgentBinding,
    OrganizationCapabilityPolicy,
    OrganizationEvolutionBudget,
    OrganizationEvolutionTask,
    OrganizationFitnessPolicy,
    OrganizationGenome,
    OrganizationHarnessOutcome,
    OrganizationRole,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    organization_hash,
)
from agentos_runtime import OrganizationCapabilityRuntimeSupport, OrganizationEvolutionRuntime


SCOPE = "project://capability-evolution-test"
EVIDENCE = ("evidence://task-structure", "evidence://strong-agent-trials")
CONTRACT = "problem-framer.structure"
CAPABILITY = "structure_elicitation"


class RebindProvider:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.tasks = []
        self.profile = ProviderCapabilityProfile(
            provider_id="organization-advisor",
            model_id="advisor-model",
            task_kinds=("organization_evolution_proposal",),
            max_timeout_seconds=60,
        )

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": {
                "proposals": [
                    {
                        "proposal_id": "rebind-strong",
                        "operator_id": "REBIND_ROLE_AGENT",
                        "parameters": {"role_id": "PROBLEM_FRAMER", "agent_id": self.agent_id},
                        "rationale": "Test the capability-supported executor on the same frozen workflow.",
                        "evidence_refs": list(EVIDENCE),
                    }
                ],
                "global_rationale": "Hold workflow structure fixed and vary executor capability.",
                "uncertainty": 0.15,
                "evidence_refs": list(EVIDENCE),
            },
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "provenance_refs": list(EVIDENCE),
        }


class BindingHarness:
    harness_id = "binding-aware-harness"

    def __init__(self, *, candidate_anchor: float = 0.90):
        self.calls = 0
        self.candidate_anchor = candidate_anchor

    def evaluate(self, *, task, genome, max_normalized_cost):
        self.calls += 1
        agent_id = genome.agent_bindings[0].agent_id
        strong = agent_id == "framer-strong"
        return OrganizationHarnessOutcome.create(
            outcome_id=f"binding-outcome-{self.calls}",
            genome_hash=genome.genome_hash,
            task_hash=task.task_hash,
            stage_id=task.stage_id,
            primary_score=0.82 if strong else 0.52,
            observed_cbit_gain=0.62 if strong else 0.20,
            normalized_cost=0.12 if strong else 0.08,
            errors_exposed=4,
            errors_corrected=3 if strong else 1,
            anchor_scores={"prior-stage": self.candidate_anchor if strong else 0.90},
            evidence_refs=task.evidence_refs,
            source_result_hash=organization_hash(
                {"agent_id": agent_id, "call": self.calls, "genome_hash": genome.genome_hash}
            ),
            replay_valid=True,
        )


def descriptor(agent_id: str, *, role: str = "PROBLEM_FRAMER", capabilities=(CAPABILITY,)):
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=capabilities,
        runner_id=f"runner-{agent_id}",
        harness_id="binding-aware-harness",
        provider_id=f"provider-{agent_id}",
        model_id="deepseek-r1-32b" if agent_id == "framer-strong" else "local-small",
        context_isolation_key=f"context-{agent_id}",
        allowed_evidence_scopes=(SCOPE,),
    )


def registry(*, include_wrong=False):
    result = AgentRegistry()
    result.register(descriptor("framer-weak"))
    result.register(descriptor("framer-strong"))
    if include_wrong:
        result.register(descriptor("critic-wrong", role="PROBLEM_CRITIC", capabilities=("critique",)))
    return result


def task():
    return OrganizationEvolutionTask.create(
        task_id="structure-holdout",
        stage_id="problem-structure",
        project_scope=SCOPE,
        context_key="fresh-structure-context",
        objective="Recover the hidden object structure under a frozen workflow.",
        evidence_refs=EVIDENCE,
        anchor_task_ids=("prior-stage",),
    )


def baseline(bound_task, bound_registry):
    return OrganizationGenome.create(
        genome_id="weak-bound-baseline",
        task_hash=bound_task.task_hash,
        roles=(OrganizationRole("PROBLEM_FRAMER", CONTRACT),),
        edges=(),
        max_rounds=4,
        stop_policy="MARGINAL_CBIT",
        generation=0,
        parent_genome_hash="",
        mutation_operator_id="",
        mutation_proposal_hash="",
        agent_bindings=(OrganizationAgentBinding.from_descriptor(bound_registry.get("framer-weak")),),
    )


def capability_evidence(bound_task):
    return AgentCapabilityEvidence.create(
        evidence_id="strong-agent-fresh-holdout",
        project_scope=SCOPE,
        context_key=bound_task.context_key,
        evidence_tier="fresh_holdout",
        agent_id="framer-strong",
        role_id="PROBLEM_FRAMER",
        required_capabilities=(CAPABILITY,),
        independent_trials=2,
        mean_effectiveness=0.81,
        mean_observed_cbit=0.58,
        mean_normalized_cost=0.12,
        replay_valid=True,
        evidence_refs=("evidence://strong-agent-trials",),
    )


def runtime(tmp_path, provider, support, runtime_id="capability-evolution"):
    return OrganizationEvolutionRuntime(
        runtime_id=runtime_id,
        project_scope=SCOPE,
        provider_router=ProviderTaskRouter([provider]),
        role_contract_catalog={"PROBLEM_FRAMER": (CONTRACT,)},
        workspace_root=tmp_path,
        capability_support=support,
    )


def budget():
    return OrganizationEvolutionBudget(
        max_generations=1,
        max_candidates_per_generation=1,
        max_roles=1,
        max_edges=0,
        max_provider_calls=1,
        max_normalized_cost=1.0,
        patience_generations=1,
    )


def support(bound_registry, *, evidence=(), allow_exploration=True):
    return OrganizationCapabilityRuntimeSupport(
        agent_registry=bound_registry,
        role_contract_capabilities={CONTRACT: (CAPABILITY,)},
        evidence=evidence,
        policy=OrganizationCapabilityPolicy(allow_exploratory_rebinding=allow_exploration),
    )


def test_supported_rebind_reaches_strong_ceiling_and_replays(tmp_path):
    bound_task, bound_registry = task(), registry()
    provider = RebindProvider("framer-strong")
    capability_support = support(bound_registry, evidence=(capability_evidence(bound_task),))
    harness = BindingHarness()
    system = runtime(tmp_path, provider, capability_support)
    system.start(
        task=bound_task,
        baseline=baseline(bound_task, bound_registry),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    snapshot = system.optimize(harness=harness)

    receipt = snapshot.generation_receipts[0]
    assert snapshot.incumbent.agent_bindings[0].agent_id == "framer-strong"
    assert receipt.capability_receipts[0].mode == "SUPPORTED"
    assert receipt.decisions[0].accepted is True
    assert receipt.decisions[0].capability_receipt_hash == receipt.capability_receipts[0].receipt_hash
    assert provider.tasks[0].inputs["agent_registry"][1]["model_id"] == "deepseek-r1-32b"
    assert system.verify_replay()["valid"] is True
    restarted = runtime(tmp_path, RebindProvider("framer-strong"), capability_support)
    assert restarted.snapshot().incumbent.genome_hash == snapshot.incumbent.genome_hash


def test_missing_capability_evidence_blocks_before_candidate_harness(tmp_path):
    bound_task, bound_registry = task(), registry()
    harness = BindingHarness()
    system = runtime(
        tmp_path,
        RebindProvider("framer-strong"),
        support(bound_registry, allow_exploration=False),
    )
    system.start(
        task=bound_task,
        baseline=baseline(bound_task, bound_registry),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )

    with pytest.raises(ValueError, match="organization_evolution_candidate_capability_blocked"):
        system.run_generation(harness=harness)
    assert harness.calls == 1
    assert system.snapshot().state == "BLOCKED"
    event = json.loads(system.public_store_path.joinpath("events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert event["payload"]["details"]["capability_receipt"]["mode"] == "BLOCKED"


def test_missing_evidence_can_remain_an_explicit_exploratory_trial(tmp_path):
    bound_task, bound_registry = task(), registry()
    harness = BindingHarness()
    system = runtime(tmp_path, RebindProvider("framer-strong"), support(bound_registry))
    system.start(
        task=bound_task,
        baseline=baseline(bound_task, bound_registry),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    receipt = system.run_generation(harness=harness)

    assert receipt.capability_receipts[0].mode == "EXPLORATORY_TRIAL_ONLY"
    assert receipt.decisions[0].capability_mode == "EXPLORATORY_TRIAL_ONLY"
    assert harness.calls == 2


def test_strong_rebind_cannot_bypass_cross_stage_regression(tmp_path):
    bound_task, bound_registry = task(), registry()
    harness = BindingHarness(candidate_anchor=0.70)
    system = runtime(
        tmp_path,
        RebindProvider("framer-strong"),
        support(bound_registry, evidence=(capability_evidence(bound_task),)),
    )
    original = baseline(bound_task, bound_registry)
    system.start(
        task=bound_task,
        baseline=original,
        budget=budget(),
        fitness=OrganizationFitnessPolicy(maximum_anchor_regression=0.02),
        harness=harness,
    )
    receipt = system.run_generation(harness=harness)

    assert receipt.capability_receipts[0].mode == "SUPPORTED"
    assert "organization_evolution_cross_stage_regression" in receipt.decisions[0].gate_failures
    assert system.snapshot().incumbent.genome_hash == original.genome_hash


def test_ineligible_agent_is_blocked_before_candidate_harness(tmp_path):
    bound_task, bound_registry = task(), registry(include_wrong=True)
    harness = BindingHarness()
    system = runtime(tmp_path, RebindProvider("critic-wrong"), support(bound_registry))
    system.start(
        task=bound_task,
        baseline=baseline(bound_task, bound_registry),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )

    with pytest.raises(ValueError, match="organization_evolution_agent_binding_ineligible"):
        system.run_generation(harness=harness)
    assert harness.calls == 1


def test_tampered_capability_receipt_is_rejected_on_restart(tmp_path):
    bound_task, bound_registry = task(), registry()
    capability_support = support(bound_registry, evidence=(capability_evidence(bound_task),))
    harness = BindingHarness()
    system = runtime(tmp_path, RebindProvider("framer-strong"), capability_support)
    system.start(
        task=bound_task,
        baseline=baseline(bound_task, bound_registry),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    system.run_generation(harness=harness)
    events_path = system.public_store_path / "events.jsonl"
    events = events_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(events[-1])
    event["payload"]["state"]["generation_receipts"][0]["capability_receipts"][0]["mode"] = "BLOCKED"
    events[-1] = json.dumps(event, sort_keys=True)
    events_path.write_text("\n".join(events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="organization_evolution_replay_invalid"):
        runtime(tmp_path, RebindProvider("framer-strong"), capability_support)


def test_contract_change_requires_fresh_capability_evidence_for_same_agent():
    bound_task, bound_registry = task(), registry()
    original = baseline(bound_task, bound_registry)
    candidate = OrganizationGenome.create(
        genome_id="specialized",
        task_hash=bound_task.task_hash,
        roles=(OrganizationRole("PROBLEM_FRAMER", "problem-framer.specialized"),),
        edges=(), max_rounds=4, stop_policy="MARGINAL_CBIT", generation=1,
        parent_genome_hash=original.genome_hash,
        mutation_operator_id="SPECIALIZE_ROLE", mutation_proposal_hash="a" * 64,
        agent_bindings=original.agent_bindings,
    )
    assert OrganizationCapabilityRuntimeSupport.changed_agent_ids(original, candidate) == ("framer-weak",)
