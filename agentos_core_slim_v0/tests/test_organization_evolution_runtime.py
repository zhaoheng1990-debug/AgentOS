from __future__ import annotations

import json

import pytest

from agentos_kernel import (
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
from agentos_runtime import OrganizationEvolutionRuntime


PROJECT_SCOPE = "project://organization-evolution-test"
EVIDENCE = ("evidence://task-structure",)
CATALOG = {
    "GENERATOR": ("generator.base", "generator.specialized"),
    "REVIEWER": ("reviewer.adversarial",),
    "SYNTHESIZER": ("synthesizer.base",),
}


class ScriptedProvider:
    def __init__(self, payloads: list[dict]):
        self.payloads = list(payloads)
        self.profile = ProviderCapabilityProfile(
            provider_id="scripted-provider",
            model_id="scripted-model",
            task_kinds=("organization_evolution_proposal",),
            max_timeout_seconds=60,
        )

    def invoke(self, task):
        if not self.payloads:
            raise RuntimeError("scripted_provider_exhausted")
        return {
            "result": self.payloads.pop(0),
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "provenance_refs": list(EVIDENCE),
        }


class ScoredHarness:
    harness_id = "scored-organization-harness"

    def __init__(self, scores: dict[str, dict[str, float]]):
        self.scores = scores
        self.calls = 0

    def evaluate(self, *, task, genome, max_normalized_cost):
        self.calls += 1
        key = genome.mutation_operator_id or "BASELINE"
        values = self.scores[key]
        anchor_score = values.get("anchor", 0.80)
        return OrganizationHarnessOutcome.create(
            outcome_id=f"outcome-{self.calls}",
            genome_hash=genome.genome_hash,
            task_hash=task.task_hash,
            stage_id=task.stage_id,
            primary_score=values["primary"],
            observed_cbit_gain=values["cbit"],
            normalized_cost=values["cost"],
            errors_exposed=2,
            errors_corrected=int(values.get("corrected", 1)),
            anchor_scores={anchor: anchor_score for anchor in task.anchor_task_ids},
            evidence_refs=task.evidence_refs,
            source_result_hash=organization_hash(
                {"genome_hash": genome.genome_hash, "harness_call": self.calls}
            ),
            replay_valid=True,
        )


def task():
    return OrganizationEvolutionTask.create(
        task_id="task-1",
        stage_id="stage-2",
        project_scope=PROJECT_SCOPE,
        context_key="ctx-organization-evolution",
        objective="Improve the task-bound cognitive workflow.",
        evidence_refs=EVIDENCE,
        anchor_task_ids=("stage-1-anchor",),
    )


def baseline(bound_task):
    return OrganizationGenome.create(
        genome_id="baseline",
        task_hash=bound_task.task_hash,
        roles=(OrganizationRole("GENERATOR", "generator.base"),),
        edges=(),
        max_rounds=4,
        stop_policy="MARGINAL_CBIT",
        generation=0,
        parent_genome_hash="",
        mutation_operator_id="",
        mutation_proposal_hash="",
    )


def budget(**overrides):
    values = {
        "max_generations": 1,
        "max_candidates_per_generation": 2,
        "max_roles": 4,
        "max_edges": 6,
        "max_provider_calls": 2,
        "max_normalized_cost": 1.0,
        "patience_generations": 2,
    }
    values.update(overrides)
    return OrganizationEvolutionBudget(**values)


def proposal_payload(*proposals):
    return {
        "proposals": list(proposals),
        "global_rationale": "Compare one structural expansion with one contract specialization.",
        "uncertainty": 0.25,
        "evidence_refs": list(EVIDENCE),
    }


def proposal(proposal_id, operator_id, parameters, **extra):
    return {
        "proposal_id": proposal_id,
        "operator_id": operator_id,
        "parameters": parameters,
        "rationale": f"Test {operator_id} against the frozen incumbent.",
        "evidence_refs": list(EVIDENCE),
        **extra,
    }


def runtime(tmp_path, payloads, runtime_id="evolution-test"):
    return OrganizationEvolutionRuntime(
        runtime_id=runtime_id,
        project_scope=PROJECT_SCOPE,
        provider_router=ProviderTaskRouter([ScriptedProvider(payloads)]),
        role_contract_catalog=CATALOG,
        workspace_root=tmp_path,
    )


def test_optimize_selects_best_generated_workflow_updates_credit_and_replays(tmp_path):
    bound_task = task()
    provider_payload = proposal_payload(
        proposal(
            "p-add-reviewer",
            "ADD_ROLE",
            {
                "role_id": "REVIEWER",
                "contract_id": "reviewer.adversarial",
                "incoming_from_role": "GENERATOR",
            },
        ),
        proposal(
            "p-specialize-generator",
            "SPECIALIZE_ROLE",
            {"role_id": "GENERATOR", "contract_id": "generator.specialized"},
        ),
    )
    harness = ScoredHarness(
        {
            "BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.10},
            "ADD_ROLE": {"primary": 0.75, "cbit": 0.55, "cost": 0.10},
            "SPECIALIZE_ROLE": {"primary": 0.62, "cbit": 0.35, "cost": 0.10},
        }
    )
    system = runtime(tmp_path, [provider_payload])
    system.start(
        task=bound_task,
        baseline=baseline(bound_task),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    snapshot = system.optimize(harness=harness)

    assert snapshot.state == "STOPPED"
    assert snapshot.stop_reason == "GENERATION_BUDGET_EXHAUSTED"
    assert snapshot.incumbent.mutation_operator_id == "ADD_ROLE"
    assert {item.role_id for item in snapshot.incumbent.roles} == {"GENERATOR", "REVIEWER"}
    assert snapshot.generation_receipts[0].retained_genome_hash == snapshot.incumbent.genome_hash
    assert snapshot.spent_provider_calls == 1
    assert snapshot.spent_normalized_cost == pytest.approx(0.30)
    add_role_credit = next(item for item in snapshot.operator_credits if item.operator_id == "ADD_ROLE")
    assert (add_role_credit.trials, add_role_credit.retained) == (1, 1)
    assert system.verify_replay()["valid"] is True

    restarted = runtime(tmp_path, [], runtime_id="evolution-test")
    assert restarted.snapshot().as_dict() == snapshot.as_dict()
    assert restarted.verify_replay()["valid"] is True


def test_cross_stage_regression_rejects_high_scoring_candidate(tmp_path):
    bound_task = task()
    provider_payload = proposal_payload(
        proposal(
            "p-add-reviewer",
            "ADD_ROLE",
            {
                "role_id": "REVIEWER",
                "contract_id": "reviewer.adversarial",
                "incoming_from_role": "GENERATOR",
            },
        )
    )
    harness = ScoredHarness(
        {
            "BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.10, "anchor": 0.90},
            "ADD_ROLE": {"primary": 0.90, "cbit": 0.80, "cost": 0.10, "anchor": 0.70},
        }
    )
    system = runtime(tmp_path, [provider_payload])
    original = baseline(bound_task)
    system.start(
        task=bound_task,
        baseline=original,
        budget=budget(max_generations=2, max_candidates_per_generation=1, patience_generations=1),
        fitness=OrganizationFitnessPolicy(maximum_anchor_regression=0.02),
        harness=harness,
    )
    receipt = system.run_generation(harness=harness)

    assert receipt.decisions[0].accepted is False
    assert "organization_evolution_cross_stage_regression" in receipt.decisions[0].gate_failures
    assert system.snapshot().incumbent.genome_hash == original.genome_hash
    assert system.snapshot().stop_reason == "NO_IMPROVEMENT_PATIENCE_EXHAUSTED"


def test_two_generations_adapt_operator_window_and_improve_topology(tmp_path):
    bound_task = task()
    first = proposal_payload(
        proposal(
            "p-add-reviewer",
            "ADD_ROLE",
            {
                "role_id": "REVIEWER",
                "contract_id": "reviewer.adversarial",
                "incoming_from_role": "GENERATOR",
            },
        ),
        proposal(
            "p-specialize-generator",
            "SPECIALIZE_ROLE",
            {"role_id": "GENERATOR", "contract_id": "generator.specialized"},
        ),
    )
    second = proposal_payload(
        proposal(
            "p-add-feedback-edge",
            "ADD_EDGE",
            {"source_role": "REVIEWER", "target_role": "GENERATOR"},
        ),
        proposal(
            "p-remove-forward-edge",
            "REMOVE_EDGE",
            {"source_role": "GENERATOR", "target_role": "REVIEWER"},
        ),
    )
    harness = ScoredHarness(
        {
            "BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.10},
            "ADD_ROLE": {"primary": 0.72, "cbit": 0.50, "cost": 0.10},
            "SPECIALIZE_ROLE": {"primary": 0.60, "cbit": 0.30, "cost": 0.10},
            "ADD_EDGE": {"primary": 0.84, "cbit": 0.65, "cost": 0.10},
            "REMOVE_EDGE": {"primary": 0.68, "cbit": 0.40, "cost": 0.10},
        }
    )
    system = runtime(tmp_path, [first, second])
    system.start(
        task=bound_task,
        baseline=baseline(bound_task),
        budget=budget(max_generations=2),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    snapshot = system.optimize(harness=harness)

    assert [item.retained_genome_hash for item in snapshot.generation_receipts] == [
        snapshot.generation_receipts[0].candidates[0].genome_hash,
        snapshot.generation_receipts[1].candidates[0].genome_hash,
    ]
    assert snapshot.incumbent.mutation_operator_id == "ADD_EDGE"
    assert {(item.source_role, item.target_role) for item in snapshot.incumbent.edges} == {
        ("GENERATOR", "REVIEWER"),
        ("REVIEWER", "GENERATOR"),
    }
    assert snapshot.spent_provider_calls == 2
    assert snapshot.stop_reason == "GENERATION_BUDGET_EXHAUSTED"


def test_provider_cannot_claim_candidate_authority(tmp_path):
    bound_task = task()
    provider_payload = proposal_payload(
        proposal(
            "p-authority",
            "SPECIALIZE_ROLE",
            {"role_id": "GENERATOR", "contract_id": "generator.specialized"},
            accepted=True,
        )
    )
    harness = ScoredHarness({"BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.10}})
    system = runtime(tmp_path, [provider_payload])
    system.start(
        task=bound_task,
        baseline=baseline(bound_task),
        budget=budget(max_candidates_per_generation=1),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )

    with pytest.raises(ValueError, match="organization_evolution_provider_authority_forbidden"):
        system.run_generation(harness=harness)
    assert system.snapshot().state == "BLOCKED"
    assert system.snapshot().spent_provider_calls == 1
    assert system.verify_replay()["valid"] is True


def test_harness_cannot_exceed_remaining_cost_budget(tmp_path):
    bound_task = task()
    provider_payload = proposal_payload(
        proposal(
            "p-add-reviewer",
            "ADD_ROLE",
            {
                "role_id": "REVIEWER",
                "contract_id": "reviewer.adversarial",
                "incoming_from_role": "GENERATOR",
            },
        )
    )
    harness = ScoredHarness(
        {
            "BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.90},
            "ADD_ROLE": {"primary": 0.80, "cbit": 0.60, "cost": 0.20},
        }
    )
    system = runtime(tmp_path, [provider_payload])
    system.start(
        task=bound_task,
        baseline=baseline(bound_task),
        budget=budget(max_candidates_per_generation=1),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )

    with pytest.raises(ValueError, match="organization_evolution_harness_cost_limit_exceeded"):
        system.run_generation(harness=harness)
    assert system.snapshot().state == "BLOCKED"


def test_invalid_operator_parameters_block_before_harness_execution(tmp_path):
    bound_task = task()
    provider_payload = proposal_payload(
        proposal(
            "p-add-reviewer",
            "ADD_ROLE",
            {"role_id": "REVIEWER", "contract_id": "reviewer.adversarial"},
        )
    )
    harness = ScoredHarness({"BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.10}})
    system = runtime(tmp_path, [provider_payload])
    system.start(
        task=bound_task,
        baseline=baseline(bound_task),
        budget=budget(max_candidates_per_generation=1),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )

    with pytest.raises(ValueError, match="organization_evolution_add_role_connection_required"):
        system.run_generation(harness=harness)
    assert harness.calls == 1
    assert system.snapshot().state == "BLOCKED"


def test_tampered_event_chain_is_rejected_on_restart(tmp_path):
    bound_task = task()
    harness = ScoredHarness({"BASELINE": {"primary": 0.50, "cbit": 0.20, "cost": 0.10}})
    system = runtime(tmp_path, [])
    system.start(
        task=bound_task,
        baseline=baseline(bound_task),
        budget=budget(),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    events_path = system.public_store_path / "events.jsonl"
    events = events_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(events[-1])
    event["payload"]["state"]["spent_normalized_cost"] = 0.0
    events[-1] = json.dumps(event, sort_keys=True)
    events_path.write_text("\n".join(events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="organization_evolution_replay_invalid"):
        runtime(tmp_path, [], runtime_id="evolution-test")
