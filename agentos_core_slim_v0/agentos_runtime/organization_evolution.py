"""Thin orchestration facade for bounded organization workflow optimization."""

from __future__ import annotations
import re
from dataclasses import replace
from pathlib import Path
from agentos_kernel import ProviderTaskRouter
from agentos_kernel.organization_capability_models import OrganizationCapabilityBindingReceipt
from agentos_kernel.organization_evolution_eval import (
    OrganizationEvolutionDecision,
    OrganizationEvolutionGate,
    OrganizationFitnessPolicy,
    OrganizationHarnessOutcome,
)
from agentos_kernel.organization_evolution_models import (
    OrganizationEvolutionBudget,
    OrganizationEvolutionTask,
    OrganizationGenome,
)

from .organization_evolution_contracts import (
    ORGANIZATION_EVOLUTION_RUNTIME_VERSION,
    OrganizationEvolutionHarness,
    OrganizationEvolutionSnapshot,
    OrganizationGenerationReceipt,
)
from .organization_capability_support import OrganizationCapabilityRuntimeSupport
from .organization_evolution_control import generation_stop_reason, validate_harness_outcome
from .organization_evolution_operators import OrganizationEvolutionOperatorRegistry
from .organization_evolution_provider import OrganizationEvolutionProviderAdvisor
from .organization_evolution_repository import OrganizationEvolutionRepository
from .organization_evolution_strategy import OrganizationEvolutionStrategy

class OrganizationEvolutionRuntime:
    """Optimize one task-bound organization while preserving Kernel authority."""

    module_id = ORGANIZATION_EVOLUTION_RUNTIME_VERSION
    capabilities = (
        "provider_supported_organization_mutation",
        "harness_evaluated_workflow_optimization",
        "kernel_owned_fitness_and_cross_stage_stability",
        "adaptive_operator_credit",
        "capability_conditioned_agent_rebinding",
        "budgeted_stop_and_replay",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        provider_router: ProviderTaskRouter,
        role_contract_catalog: dict[str, tuple[str, ...]],
        workspace_root: str | Path,
        gate: OrganizationEvolutionGate | None = None,
        capability_support: OrganizationCapabilityRuntimeSupport | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("organization_evolution_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("organization_evolution_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.capability_support = capability_support
        self.operator_registry = OrganizationEvolutionOperatorRegistry(
            role_contract_catalog=role_contract_catalog,
            agent_registry=capability_support.registry if capability_support else None,
            role_contract_capabilities=(capability_support.role_contract_capabilities if capability_support else None),
        )
        self.gate = gate or OrganizationEvolutionGate()
        self.strategy = OrganizationEvolutionStrategy()
        self._repository = OrganizationEvolutionRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )
        self._provider_advisor = OrganizationEvolutionProviderAdvisor(
            runtime_id=runtime_id,
            provider_router=provider_router,
            operator_registry=self.operator_registry,
            event_sink=self._repository.persist_event,
            capability_evidence=capability_support.evidence if capability_support else (),
            capability_policy=capability_support.policy if capability_support else None,
        )
        snapshot = self._repository.snapshot()
        if snapshot.incumbent is not None:
            self.operator_registry.validate_genome(snapshot.incumbent)

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def start(
        self,
        *,
        task: OrganizationEvolutionTask,
        baseline: OrganizationGenome,
        budget: OrganizationEvolutionBudget,
        fitness: OrganizationFitnessPolicy,
        harness: OrganizationEvolutionHarness,
    ) -> OrganizationEvolutionSnapshot:
        snapshot = self._repository.snapshot()
        if snapshot.state != "INITIALIZED":
            raise RuntimeError("organization_evolution_session_already_started")
        if task.project_scope != self.project_scope or baseline.task_hash != task.task_hash:
            raise ValueError("organization_evolution_start_scope_or_task_mismatch")
        if baseline.generation != 0:
            raise ValueError("organization_evolution_baseline_generation_invalid")
        self.operator_registry.validate_genome(baseline)
        if len(baseline.roles) > budget.max_roles or len(baseline.edges) > budget.max_edges:
            raise ValueError("organization_evolution_baseline_structure_budget_exceeded")
        baseline_capability = None
        try:
            baseline_capability = self.capability_support.evaluate(task=task, genome=baseline) if self.capability_support else None
            if baseline_capability is not None and baseline_capability.mode == "BLOCKED":
                raise ValueError("organization_evolution_baseline_capability_blocked")
            outcome = harness.evaluate(
                task=task,
                genome=baseline,
                max_normalized_cost=budget.max_normalized_cost,
            )
            validate_harness_outcome(task, baseline, outcome, budget.max_normalized_cost)
        except Exception as exc:
            blocked = replace(snapshot, state="BLOCKED", stop_reason="BASELINE_EVALUATION_BLOCKED")
            self._repository.save(
                "ORGANIZATION_EVOLUTION_RUNTIME_BLOCKED",
                blocked,
                {
                    "stage": "BASELINE", "error_type": type(exc).__name__, "error": str(exc)[:500],
                    "capability_receipt": baseline_capability.as_dict() if baseline_capability else None,
                },
            )
            raise
        started = replace(
            snapshot,
            state="RUNNING",
            task=task,
            budget=budget,
            fitness=fitness,
            incumbent=baseline,
            incumbent_outcome=outcome,
            spent_normalized_cost=outcome.normalized_cost,
        )
        self._repository.save(
            "ORGANIZATION_EVOLUTION_SESSION_STARTED",
            started,
            {
                "harness_id": harness.harness_id,
                "baseline_outcome_hash": outcome.outcome_hash,
                "capability_receipt": baseline_capability.as_dict() if baseline_capability else None,
            },
        )
        if outcome.normalized_cost >= budget.max_normalized_cost:
            return self._stop("NORMALIZED_COST_BUDGET_EXHAUSTED")
        return started

    def run_generation(self, *, harness: OrganizationEvolutionHarness) -> OrganizationGenerationReceipt:
        snapshot = self._repository.snapshot()
        if snapshot.state != "RUNNING":
            raise RuntimeError("organization_evolution_generation_requires_running_session")
        task, budget, fitness = snapshot.task, snapshot.budget, snapshot.fitness
        incumbent, incumbent_outcome = snapshot.incumbent, snapshot.incumbent_outcome
        assert task and budget and fitness and incumbent and incumbent_outcome
        stop_reason = generation_stop_reason(snapshot)
        if stop_reason:
            self._stop(stop_reason)
            raise RuntimeError(f"organization_evolution_session_stopped:{stop_reason}")
        applicable = self.operator_registry.applicable_operator_ids(incumbent, budget)
        if not applicable:
            self._stop("NO_APPLICABLE_OPERATORS")
            raise RuntimeError("organization_evolution_session_stopped:NO_APPLICABLE_OPERATORS")
        operator_ids = self.strategy.operator_window(
            applicable=applicable,
            credits=snapshot.operator_credits,
            limit=budget.max_candidates_per_generation,
        )
        generation = incumbent.generation + 1
        generation_id = f"{self.runtime_id}-generation-{generation}"
        provider_call_charged = False
        evaluated_cost = 0.0
        blocked_capability = None
        try:
            provider_call_charged = True
            proposals = self._provider_advisor.propose(
                generation_id=generation_id,
                task=task,
                incumbent=incumbent,
                budget=budget,
                operator_ids=operator_ids,
                credits=snapshot.operator_credits,
                max_candidates=min(budget.max_candidates_per_generation, len(operator_ids)),
            )
            candidates = tuple(self.operator_registry.apply(incumbent, item) for item in proposals)
            if len({item.genome_hash for item in candidates}) != len(candidates):
                raise ValueError("organization_evolution_duplicate_candidate")
            if any(len(item.roles) > budget.max_roles or len(item.edges) > budget.max_edges for item in candidates):
                raise ValueError("organization_evolution_candidate_structure_budget_exceeded")
            outcomes: list[OrganizationHarnessOutcome] = []
            decisions: list[OrganizationEvolutionDecision] = []
            capability_receipts: list[OrganizationCapabilityBindingReceipt] = []
            source_hashes = {incumbent_outcome.source_result_hash}
            for index, (proposal, candidate) in enumerate(zip(proposals, candidates, strict=True)):
                capability_receipt = (
                    self.capability_support.evaluate(task=task, genome=candidate, incumbent=incumbent)
                    if self.capability_support else None
                )
                blocked_capability = capability_receipt
                if capability_receipt is not None and capability_receipt.mode == "BLOCKED":
                    raise ValueError("organization_evolution_candidate_capability_blocked")
                remaining_cost = budget.max_normalized_cost - snapshot.spent_normalized_cost - evaluated_cost
                if remaining_cost < 0:
                    raise RuntimeError("organization_evolution_cost_budget_exhausted_before_candidate")
                outcome = harness.evaluate(
                    task=task,
                    genome=candidate,
                    max_normalized_cost=remaining_cost,
                )
                validate_harness_outcome(task, candidate, outcome, remaining_cost)
                if outcome.source_result_hash in source_hashes:
                    raise ValueError("organization_evolution_duplicate_outcome_source")
                source_hashes.add(outcome.source_result_hash)
                decision = self.gate.evaluate(
                    decision_id=f"{generation_id}-candidate-{index + 1}",
                    task=task,
                    incumbent=incumbent,
                    candidate=candidate,
                    proposal=proposal,
                    incumbent_outcome=incumbent_outcome,
                    candidate_outcome=outcome,
                    budget=budget,
                    fitness=fitness,
                    spent_cost_before_candidate=snapshot.spent_normalized_cost + evaluated_cost,
                    capability_receipt=capability_receipt,
                )
                outcomes.append(outcome)
                decisions.append(decision)
                if capability_receipt is not None:
                    capability_receipts.append(capability_receipt)
                evaluated_cost += outcome.normalized_cost
        except Exception as exc:
            blocked = replace(
                snapshot,
                state="BLOCKED",
                spent_provider_calls=snapshot.spent_provider_calls + int(provider_call_charged),
                spent_normalized_cost=snapshot.spent_normalized_cost + evaluated_cost,
                stop_reason="GENERATION_BLOCKED",
            )
            self._repository.save(
                "ORGANIZATION_EVOLUTION_RUNTIME_BLOCKED",
                blocked,
                {
                    "generation_id": generation_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                    "capability_receipt": blocked_capability.as_dict() if blocked_capability else None,
                },
            )
            raise

        winner_index = self.strategy.winner_index(tuple(decisions))
        retained = candidates[winner_index] if winner_index is not None else incumbent
        retained_outcome = outcomes[winner_index] if winner_index is not None else incumbent_outcome
        credits = self.strategy.updated_credits(
            credits=snapshot.operator_credits,
            proposals=proposals,
            outcomes=tuple(outcomes),
            decisions=tuple(decisions),
            winner_index=winner_index,
        )
        receipt = OrganizationGenerationReceipt.create(
            generation_id=generation_id,
            generation=generation,
            incumbent_before_hash=incumbent.genome_hash,
            incumbent_before_outcome_hash=incumbent_outcome.outcome_hash,
            proposals=proposals,
            candidates=candidates,
            outcomes=tuple(outcomes),
            decisions=tuple(decisions),
            retained_genome_hash=retained.genome_hash,
            retained_outcome_hash=retained_outcome.outcome_hash,
            provider_calls=1,
            evaluated_normalized_cost=evaluated_cost,
            capability_receipts=tuple(capability_receipts),
        )
        next_snapshot = replace(
            snapshot,
            incumbent=retained,
            incumbent_outcome=retained_outcome,
            generation_receipts=(*snapshot.generation_receipts, receipt),
            operator_credits=credits,
            spent_provider_calls=snapshot.spent_provider_calls + 1,
            spent_normalized_cost=snapshot.spent_normalized_cost + evaluated_cost,
            no_improvement_generations=(0 if winner_index is not None else snapshot.no_improvement_generations + 1),
        )
        stop_reason = generation_stop_reason(next_snapshot)
        if stop_reason:
            next_snapshot = replace(next_snapshot, state="STOPPED", stop_reason=stop_reason)
        self._repository.save(
            "ORGANIZATION_EVOLUTION_GENERATION_COMPLETED",
            next_snapshot,
            {"generation_receipt_hash": receipt.receipt_hash, "harness_id": harness.harness_id},
        )
        return receipt

    def optimize(self, *, harness: OrganizationEvolutionHarness) -> OrganizationEvolutionSnapshot:
        while self._repository.snapshot().state == "RUNNING":
            self.run_generation(harness=harness)
        return self._repository.snapshot()

    def snapshot(self) -> OrganizationEvolutionSnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, object]:
        return self._repository.verify_replay()

    def _stop(self, reason: str) -> OrganizationEvolutionSnapshot:
        stopped = replace(self._repository.snapshot(), state="STOPPED", stop_reason=reason)
        self._repository.save("ORGANIZATION_EVOLUTION_SESSION_STOPPED", stopped, {"reason": reason})
        return stopped
