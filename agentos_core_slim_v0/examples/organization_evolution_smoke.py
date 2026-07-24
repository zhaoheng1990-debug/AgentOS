"""Deterministic end-to-end smoke for bounded organization evolution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
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
from agentos_runtime import OrganizationEvolutionRuntime  # noqa: E402


class SmokeProvider:
    profile = ProviderCapabilityProfile(
        provider_id="smoke-provider",
        model_id="deterministic-smoke-model",
        task_kinds=("organization_evolution_proposal",),
        max_timeout_seconds=60,
    )

    def invoke(self, task):
        evidence_ref = task.allowed_evidence[0]
        return {
            "result": {
                "proposals": [
                    {
                        "proposal_id": "add-reviewer",
                        "operator_id": "ADD_ROLE",
                        "parameters": {
                            "role_id": "REVIEWER",
                            "contract_id": "reviewer.adversarial",
                            "incoming_from_role": "GENERATOR",
                        },
                        "rationale": "Add an adversarial review path for the conflict-bearing task.",
                        "evidence_refs": [evidence_ref],
                    },
                    {
                        "proposal_id": "specialize-generator",
                        "operator_id": "SPECIALIZE_ROLE",
                        "parameters": {
                            "role_id": "GENERATOR",
                            "contract_id": "generator.constraint-aware",
                        },
                        "rationale": "Test a narrower generator contract without adding a role.",
                        "evidence_refs": [evidence_ref],
                    },
                ],
                "global_rationale": "Compare structural expansion with contract specialization.",
                "uncertainty": 0.20,
                "evidence_refs": [evidence_ref],
            },
            "usage": {"input_tokens": 20, "output_tokens": 20},
            "provenance_refs": [evidence_ref],
        }


class SmokeHarness:
    harness_id = "deterministic-organization-evolution-smoke"

    def __init__(self):
        self.calls = 0

    def evaluate(self, *, task, genome, max_normalized_cost):
        self.calls += 1
        metrics = {
            "": (0.50, 0.20, 0.10),
            "ADD_ROLE": (0.78, 0.60, 0.12),
            "SPECIALIZE_ROLE": (0.64, 0.35, 0.08),
        }[genome.mutation_operator_id]
        primary, cbit, cost = metrics
        if cost > max_normalized_cost:
            raise RuntimeError("smoke_harness_budget_exceeded")
        return OrganizationHarnessOutcome.create(
            outcome_id=f"smoke-outcome-{self.calls}",
            genome_hash=genome.genome_hash,
            task_hash=task.task_hash,
            stage_id=task.stage_id,
            primary_score=primary,
            observed_cbit_gain=cbit,
            normalized_cost=cost,
            errors_exposed=2,
            errors_corrected=1,
            anchor_scores={anchor: 0.80 for anchor in task.anchor_task_ids},
            evidence_refs=task.evidence_refs,
            source_result_hash=organization_hash(
                {"genome_hash": genome.genome_hash, "call": self.calls, "kind": "smoke"}
            ),
            replay_valid=True,
        )


def run_smoke(output_dir: str | Path) -> dict:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence_refs = ("evidence://organization-evolution-smoke-task",)
    task = OrganizationEvolutionTask.create(
        task_id="organization-evolution-smoke",
        stage_id="stage-2",
        project_scope="project://organization-evolution-smoke",
        context_key="ctx-smoke",
        objective="Improve a conflict-bearing reasoning workflow under a fixed budget.",
        evidence_refs=evidence_refs,
        anchor_task_ids=("stage-1-anchor",),
    )
    baseline = OrganizationGenome.create(
        genome_id="smoke-baseline",
        task_hash=task.task_hash,
        roles=(OrganizationRole("GENERATOR", "generator.base"),),
        edges=(),
        max_rounds=4,
        stop_policy="MARGINAL_CBIT",
        generation=0,
        parent_genome_hash="",
        mutation_operator_id="",
        mutation_proposal_hash="",
    )
    harness = SmokeHarness()
    runtime = OrganizationEvolutionRuntime(
        runtime_id="organization-evolution-smoke",
        project_scope=task.project_scope,
        provider_router=ProviderTaskRouter([SmokeProvider()]),
        role_contract_catalog={
            "GENERATOR": ("generator.base", "generator.constraint-aware"),
            "REVIEWER": ("reviewer.adversarial",),
        },
        workspace_root=output / "runtime",
    )
    runtime.start(
        task=task,
        baseline=baseline,
        budget=OrganizationEvolutionBudget(
            max_generations=1,
            max_candidates_per_generation=2,
            max_roles=3,
            max_edges=4,
            max_provider_calls=1,
            max_normalized_cost=1.0,
            patience_generations=1,
        ),
        fitness=OrganizationFitnessPolicy(),
        harness=harness,
    )
    snapshot = runtime.optimize(harness=harness)
    replay = runtime.verify_replay()
    result = {
        "status": "PASS" if snapshot.state == "STOPPED" and replay["valid"] else "FAIL",
        "baseline_genome_hash": baseline.genome_hash,
        "retained_genome_hash": snapshot.incumbent.genome_hash,
        "retained_operator": snapshot.incumbent.mutation_operator_id,
        "generation_count": len(snapshot.generation_receipts),
        "spent_provider_calls": snapshot.spent_provider_calls,
        "spent_normalized_cost": snapshot.spent_normalized_cost,
        "stop_reason": snapshot.stop_reason,
        "replay": replay,
        "snapshot": snapshot.as_dict(),
    }
    result_path = output / "smoke_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "smoke_result": str(result_path),
        "smoke_result_sha256": organization_hash(result),
        "event_store": str(runtime.public_store_path),
        "rollback_pointer": {
            "from_genome_hash": snapshot.incumbent.genome_hash,
            "to_genome_hash": baseline.genome_hash,
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = run_smoke(args.output_dir)
    print(json.dumps({key: value for key, value in result.items() if key != "snapshot"}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
