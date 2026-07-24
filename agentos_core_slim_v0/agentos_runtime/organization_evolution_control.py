"""Mechanical execution checks and stop policy for organization evolution."""

from agentos_kernel.organization_evolution_eval import OrganizationHarnessOutcome
from agentos_kernel.organization_evolution_models import OrganizationEvolutionTask, OrganizationGenome

from .organization_evolution_contracts import OrganizationEvolutionSnapshot


def validate_harness_outcome(
    task: OrganizationEvolutionTask,
    genome: OrganizationGenome,
    outcome: OrganizationHarnessOutcome,
    remaining_cost: float,
) -> None:
    if outcome.task_hash != task.task_hash or outcome.genome_hash != genome.genome_hash:
        raise ValueError("organization_evolution_harness_binding_invalid")
    if outcome.stage_id != task.stage_id or set(outcome.anchor_scores) != set(task.anchor_task_ids):
        raise ValueError("organization_evolution_harness_stage_or_anchor_invalid")
    if not outcome.replay_valid:
        raise ValueError("organization_evolution_harness_replay_invalid")
    if outcome.normalized_cost > remaining_cost:
        raise ValueError("organization_evolution_harness_cost_limit_exceeded")


def generation_stop_reason(snapshot: OrganizationEvolutionSnapshot) -> str:
    assert snapshot.budget
    if len(snapshot.generation_receipts) >= snapshot.budget.max_generations:
        return "GENERATION_BUDGET_EXHAUSTED"
    if snapshot.spent_provider_calls >= snapshot.budget.max_provider_calls:
        return "PROVIDER_CALL_BUDGET_EXHAUSTED"
    if snapshot.spent_normalized_cost >= snapshot.budget.max_normalized_cost:
        return "NORMALIZED_COST_BUDGET_EXHAUSTED"
    if snapshot.no_improvement_generations >= snapshot.budget.patience_generations:
        return "NO_IMPROVEMENT_PATIENCE_EXHAUSTED"
    return ""
