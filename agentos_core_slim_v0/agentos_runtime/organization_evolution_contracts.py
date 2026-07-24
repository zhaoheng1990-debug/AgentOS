"""Runtime receipts and reconstruction for organization evolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from agentos_kernel.organization_evolution_eval import (
    OrganizationEvolutionDecision,
    OrganizationFitnessPolicy,
    OrganizationHarnessOutcome,
    OrganizationOperatorCredit,
)
from agentos_kernel.organization_capability_models import (
    OrganizationAgentBinding,
    OrganizationCapabilityBindingReceipt,
)
from agentos_kernel.organization_evolution_models import (
    OrganizationEdge,
    OrganizationEvolutionBudget,
    OrganizationEvolutionTask,
    OrganizationGenome,
    OrganizationMutationProposal,
    OrganizationRole,
    organization_hash,
)


ORGANIZATION_EVOLUTION_RUNTIME_VERSION = "organization_evolution_runtime_v0_1"
ORGANIZATION_EVOLUTION_STATES = {"INITIALIZED", "RUNNING", "STOPPED", "BLOCKED"}


class OrganizationEvolutionHarness(Protocol):
    harness_id: str

    def evaluate(
        self,
        *,
        task: OrganizationEvolutionTask,
        genome: OrganizationGenome,
        max_normalized_cost: float,
    ) -> OrganizationHarnessOutcome:
        """Execute one frozen organization genome and return a replay-valid outcome."""


@dataclass(frozen=True)
class OrganizationGenerationReceipt:
    generation_id: str
    generation: int
    incumbent_before_hash: str
    incumbent_before_outcome_hash: str
    proposals: tuple[OrganizationMutationProposal, ...]
    candidates: tuple[OrganizationGenome, ...]
    outcomes: tuple[OrganizationHarnessOutcome, ...]
    decisions: tuple[OrganizationEvolutionDecision, ...]
    retained_genome_hash: str
    retained_outcome_hash: str
    provider_calls: int
    evaluated_normalized_cost: float
    receipt_hash: str
    capability_receipts: tuple[OrganizationCapabilityBindingReceipt, ...] = ()

    def __post_init__(self) -> None:
        size = len(self.proposals)
        if not size or len(self.candidates) != size or len(self.outcomes) != size or len(self.decisions) != size:
            raise ValueError("organization_generation_surface_invalid")
        if self.provider_calls != 1:
            raise ValueError("organization_generation_provider_calls_invalid")
        if self.retained_genome_hash not in {self.incumbent_before_hash, *(item.genome_hash for item in self.candidates)}:
            raise ValueError("organization_generation_retained_genome_invalid")
        pairs = {
            self.incumbent_before_hash: self.incumbent_before_outcome_hash,
            **{genome.genome_hash: outcome.outcome_hash for genome, outcome in zip(self.candidates, self.outcomes, strict=True)},
        }
        if pairs[self.retained_genome_hash] != self.retained_outcome_hash:
            raise ValueError("organization_generation_retained_outcome_invalid")
        for proposal, genome, outcome, decision in zip(
            self.proposals, self.candidates, self.outcomes, self.decisions, strict=True
        ):
            if (
                genome.mutation_proposal_hash != proposal.proposal_hash
                or outcome.genome_hash != genome.genome_hash
                or decision.proposal_hash != proposal.proposal_hash
                or decision.candidate_genome_hash != genome.genome_hash
                or decision.outcome_hash != outcome.outcome_hash
            ):
                raise ValueError("organization_generation_candidate_binding_invalid")
        if self.capability_receipts:
            if len(self.capability_receipts) != size:
                raise ValueError("organization_generation_capability_surface_invalid")
            for genome, decision, capability in zip(
                self.candidates, self.decisions, self.capability_receipts, strict=True
            ):
                if (
                    capability.genome_hash != genome.genome_hash
                    or decision.capability_receipt_hash != capability.receipt_hash
                    or decision.capability_mode != capability.mode
                ):
                    raise ValueError("organization_generation_capability_binding_invalid")
        if self.receipt_hash != organization_hash(self._commitment()):
            raise ValueError("organization_generation_receipt_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationGenerationReceipt":
        committed = cls._commitment_from_values(values)
        return cls(**values, receipt_hash=organization_hash(committed))

    @staticmethod
    def _commitment_from_values(values: dict[str, Any]) -> dict[str, Any]:
        commitment = {
            "generation_id": values["generation_id"],
            "generation": values["generation"],
            "incumbent_before_hash": values["incumbent_before_hash"],
            "incumbent_before_outcome_hash": values["incumbent_before_outcome_hash"],
            "proposals": [item.as_dict() for item in values["proposals"]],
            "candidates": [item.as_dict() for item in values["candidates"]],
            "outcomes": [item.as_dict() for item in values["outcomes"]],
            "decisions": [item.as_dict() for item in values["decisions"]],
            "retained_genome_hash": values["retained_genome_hash"],
            "retained_outcome_hash": values["retained_outcome_hash"],
            "provider_calls": values["provider_calls"],
            "evaluated_normalized_cost": values["evaluated_normalized_cost"],
        }
        capability_receipts = values.get("capability_receipts", ())
        if capability_receipts:
            commitment["capability_receipts"] = [item.as_dict() for item in capability_receipts]
        return commitment

    def _commitment(self) -> dict[str, Any]:
        return self._commitment_from_values(self.__dict__)

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "receipt_hash": self.receipt_hash}


@dataclass(frozen=True)
class OrganizationEvolutionSnapshot:
    runtime_id: str
    project_scope: str
    state: str
    task: OrganizationEvolutionTask | None
    budget: OrganizationEvolutionBudget | None
    fitness: OrganizationFitnessPolicy | None
    incumbent: OrganizationGenome | None
    incumbent_outcome: OrganizationHarnessOutcome | None
    generation_receipts: tuple[OrganizationGenerationReceipt, ...]
    operator_credits: tuple[OrganizationOperatorCredit, ...]
    spent_provider_calls: int
    spent_normalized_cost: float
    no_improvement_generations: int
    stop_reason: str

    def __post_init__(self) -> None:
        if self.state not in ORGANIZATION_EVOLUTION_STATES:
            raise ValueError("organization_evolution_snapshot_state_invalid")
        if self.state in {"RUNNING", "STOPPED"} and not all(
            (self.task, self.budget, self.fitness, self.incumbent, self.incumbent_outcome)
        ):
            raise ValueError("organization_evolution_snapshot_session_incomplete")
        if len({item.operator_id for item in self.operator_credits}) != len(self.operator_credits):
            raise ValueError("organization_evolution_snapshot_credit_duplicate")
        if self.state in {"RUNNING", "STOPPED"}:
            assert self.incumbent and self.incumbent_outcome
            if self.incumbent_outcome.genome_hash != self.incumbent.genome_hash:
                raise ValueError("organization_evolution_snapshot_incumbent_binding_invalid")
            if self.spent_provider_calls != sum(item.provider_calls for item in self.generation_receipts):
                raise ValueError("organization_evolution_snapshot_provider_accounting_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "state": self.state,
            "task": self.task.as_dict() if self.task else None,
            "budget": self.budget.as_dict() if self.budget else None,
            "fitness": self.fitness.as_dict() if self.fitness else None,
            "incumbent": self.incumbent.as_dict() if self.incumbent else None,
            "incumbent_outcome": self.incumbent_outcome.as_dict() if self.incumbent_outcome else None,
            "generation_receipts": [item.as_dict() for item in self.generation_receipts],
            "operator_credits": [item.as_dict() for item in self.operator_credits],
            "spent_provider_calls": self.spent_provider_calls,
            "spent_normalized_cost": self.spent_normalized_cost,
            "no_improvement_generations": self.no_improvement_generations,
            "stop_reason": self.stop_reason,
        }


def task_from_dict(payload: dict[str, Any]) -> OrganizationEvolutionTask:
    return OrganizationEvolutionTask(
        task_id=payload["task_id"],
        stage_id=payload["stage_id"],
        project_scope=payload["project_scope"],
        context_key=payload["context_key"],
        objective=payload["objective"],
        evidence_refs=tuple(payload["evidence_refs"]),
        anchor_task_ids=tuple(payload["anchor_task_ids"]),
        task_hash=payload["task_hash"],
    )


def genome_from_dict(payload: dict[str, Any]) -> OrganizationGenome:
    return OrganizationGenome(
        genome_id=payload["genome_id"],
        task_hash=payload["task_hash"],
        roles=tuple(OrganizationRole(**item) for item in payload["roles"]),
        edges=tuple(OrganizationEdge(**item) for item in payload["edges"]),
        max_rounds=payload["max_rounds"],
        stop_policy=payload["stop_policy"],
        generation=payload["generation"],
        parent_genome_hash=payload["parent_genome_hash"],
        mutation_operator_id=payload["mutation_operator_id"],
        mutation_proposal_hash=payload["mutation_proposal_hash"],
        genome_hash=payload["genome_hash"],
        agent_bindings=tuple(binding_from_dict(item) for item in payload.get("agent_bindings", ())),
    )


def binding_from_dict(payload: dict[str, Any]) -> OrganizationAgentBinding:
    item = dict(payload)
    item["capabilities"] = tuple(item["capabilities"])
    item["allowed_evidence_scopes"] = tuple(item["allowed_evidence_scopes"])
    return OrganizationAgentBinding(**item)


def outcome_from_dict(payload: dict[str, Any]) -> OrganizationHarnessOutcome:
    item = dict(payload)
    item["evidence_refs"] = tuple(item["evidence_refs"])
    return OrganizationHarnessOutcome(**item)


def proposal_from_dict(payload: dict[str, Any]) -> OrganizationMutationProposal:
    item = dict(payload)
    item["evidence_refs"] = tuple(item["evidence_refs"])
    return OrganizationMutationProposal(**item)


def decision_from_dict(payload: dict[str, Any]) -> OrganizationEvolutionDecision:
    item = dict(payload)
    item["gate_failures"] = tuple(item["gate_failures"])
    return OrganizationEvolutionDecision(**item)


def capability_receipt_from_dict(payload: dict[str, Any]) -> OrganizationCapabilityBindingReceipt:
    item = dict(payload)
    for name in ("binding_hashes", "capability_evidence_hashes", "failures"):
        item[name] = tuple(item[name])
    return OrganizationCapabilityBindingReceipt(**item)


def generation_from_dict(payload: dict[str, Any]) -> OrganizationGenerationReceipt:
    return OrganizationGenerationReceipt(
        generation_id=payload["generation_id"],
        generation=payload["generation"],
        incumbent_before_hash=payload["incumbent_before_hash"],
        incumbent_before_outcome_hash=payload["incumbent_before_outcome_hash"],
        proposals=tuple(proposal_from_dict(item) for item in payload["proposals"]),
        candidates=tuple(genome_from_dict(item) for item in payload["candidates"]),
        outcomes=tuple(outcome_from_dict(item) for item in payload["outcomes"]),
        decisions=tuple(decision_from_dict(item) for item in payload["decisions"]),
        retained_genome_hash=payload["retained_genome_hash"],
        retained_outcome_hash=payload["retained_outcome_hash"],
        provider_calls=payload["provider_calls"],
        evaluated_normalized_cost=payload["evaluated_normalized_cost"],
        receipt_hash=payload["receipt_hash"],
        capability_receipts=tuple(
            capability_receipt_from_dict(item) for item in payload.get("capability_receipts", ())
        ),
    )


def snapshot_from_dict(payload: dict[str, Any]) -> OrganizationEvolutionSnapshot:
    task = task_from_dict(payload["task"]) if payload.get("task") else None
    budget = OrganizationEvolutionBudget(**payload["budget"]) if payload.get("budget") else None
    fitness = OrganizationFitnessPolicy(**payload["fitness"]) if payload.get("fitness") else None
    incumbent = genome_from_dict(payload["incumbent"]) if payload.get("incumbent") else None
    incumbent_outcome = outcome_from_dict(payload["incumbent_outcome"]) if payload.get("incumbent_outcome") else None
    credits = tuple(
        OrganizationOperatorCredit(
            operator_id=item["operator_id"],
            trials=item["trials"],
            retained=item["retained"],
            cumulative_utility_delta=item["cumulative_utility_delta"],
            cumulative_normalized_cost=item["cumulative_normalized_cost"],
        )
        for item in payload["operator_credits"]
    )
    return OrganizationEvolutionSnapshot(
        runtime_id=payload["runtime_id"],
        project_scope=payload["project_scope"],
        state=payload["state"],
        task=task,
        budget=budget,
        fitness=fitness,
        incumbent=incumbent,
        incumbent_outcome=incumbent_outcome,
        generation_receipts=tuple(generation_from_dict(item) for item in payload["generation_receipts"]),
        operator_credits=credits,
        spent_provider_calls=payload["spent_provider_calls"],
        spent_normalized_cost=payload["spent_normalized_cost"],
        no_improvement_generations=payload["no_improvement_generations"],
        stop_reason=payload["stop_reason"],
    )
