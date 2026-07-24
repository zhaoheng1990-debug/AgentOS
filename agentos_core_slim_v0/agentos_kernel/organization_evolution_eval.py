"""Kernel-owned evaluation and stability gates for organization evolution."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .organization_capability_models import OrganizationCapabilityBindingReceipt
from .organization_evolution_models import (
    ORGANIZATION_EVOLUTION_OPERATOR_IDS,
    OrganizationEvolutionBudget,
    OrganizationEvolutionTask,
    OrganizationGenome,
    OrganizationMutationProposal,
    organization_hash,
)


def _finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name}_invalid")
    return float(value)


def _unit(name: str, value: float) -> float:
    result = _finite(name, value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{name}_outside_unit_interval")
    return result


@dataclass(frozen=True)
class OrganizationHarnessOutcome:
    outcome_id: str
    genome_hash: str
    task_hash: str
    stage_id: str
    primary_score: float
    observed_cbit_gain: float
    normalized_cost: float
    errors_exposed: int
    errors_corrected: int
    anchor_scores: dict[str, float]
    evidence_refs: tuple[str, ...]
    source_result_hash: str
    replay_valid: bool
    outcome_hash: str

    def __post_init__(self) -> None:
        if not self.outcome_id or not self.stage_id:
            raise ValueError("organization_outcome_identity_invalid")
        if len(self.genome_hash) != 64 or len(self.task_hash) != 64 or len(self.source_result_hash) != 64:
            raise ValueError("organization_outcome_binding_hash_invalid")
        _unit("organization_outcome_primary_score", self.primary_score)
        cbit = _finite("organization_outcome_cbit_gain", self.observed_cbit_gain)
        if not -1.0 <= cbit <= 1.0:
            raise ValueError("organization_outcome_cbit_gain_outside_interval")
        if _finite("organization_outcome_normalized_cost", self.normalized_cost) < 0:
            raise ValueError("organization_outcome_cost_negative")
        for name in ("errors_exposed", "errors_corrected"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"organization_outcome_{name}_invalid")
        if self.errors_corrected > self.errors_exposed:
            raise ValueError("organization_outcome_corrections_exceed_exposed")
        if not isinstance(self.anchor_scores, dict):
            raise ValueError("organization_outcome_anchor_scores_invalid")
        for value in self.anchor_scores.values():
            _unit("organization_outcome_anchor_score", value)
        if not self.evidence_refs or len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("organization_outcome_evidence_refs_invalid")
        if self.outcome_hash != organization_hash(self._commitment()):
            raise ValueError("organization_outcome_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationHarnessOutcome":
        committed = dict(values)
        committed["evidence_refs"] = list(committed["evidence_refs"])
        return cls(**values, outcome_hash=organization_hash(committed))

    def correction_rate(self) -> float:
        return self.errors_corrected / self.errors_exposed if self.errors_exposed else 0.0

    def _commitment(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "genome_hash": self.genome_hash,
            "task_hash": self.task_hash,
            "stage_id": self.stage_id,
            "primary_score": self.primary_score,
            "observed_cbit_gain": self.observed_cbit_gain,
            "normalized_cost": self.normalized_cost,
            "errors_exposed": self.errors_exposed,
            "errors_corrected": self.errors_corrected,
            "anchor_scores": self.anchor_scores,
            "evidence_refs": list(self.evidence_refs),
            "source_result_hash": self.source_result_hash,
            "replay_valid": self.replay_valid,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "outcome_hash": self.outcome_hash}


@dataclass(frozen=True)
class OrganizationFitnessPolicy:
    primary_score_weight: float = 1.0
    cbit_weight: float = 0.25
    correction_weight: float = 0.10
    cost_weight: float = 0.20
    minimum_primary_gain: float = 0.0
    minimum_utility_gain: float = 0.01
    maximum_anchor_regression: float = 0.02

    def __post_init__(self) -> None:
        for name in (
            "primary_score_weight",
            "cbit_weight",
            "correction_weight",
            "cost_weight",
            "minimum_utility_gain",
            "maximum_anchor_regression",
        ):
            if _finite(f"organization_fitness_{name}", getattr(self, name)) < 0:
                raise ValueError(f"organization_fitness_{name}_negative")
        _finite("organization_fitness_minimum_primary_gain", self.minimum_primary_gain)
        if self.primary_score_weight + self.cbit_weight + self.correction_weight <= 0:
            raise ValueError("organization_fitness_positive_signal_required")

    def score(self, outcome: OrganizationHarnessOutcome) -> float:
        return (
            self.primary_score_weight * outcome.primary_score
            + self.cbit_weight * outcome.observed_cbit_gain
            + self.correction_weight * outcome.correction_rate()
            - self.cost_weight * outcome.normalized_cost
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "primary_score_weight": self.primary_score_weight,
            "cbit_weight": self.cbit_weight,
            "correction_weight": self.correction_weight,
            "cost_weight": self.cost_weight,
            "minimum_primary_gain": self.minimum_primary_gain,
            "minimum_utility_gain": self.minimum_utility_gain,
            "maximum_anchor_regression": self.maximum_anchor_regression,
        }


@dataclass(frozen=True)
class OrganizationEvolutionDecision:
    decision_id: str
    incumbent_genome_hash: str
    candidate_genome_hash: str
    proposal_hash: str
    outcome_hash: str
    incumbent_utility: float
    candidate_utility: float
    utility_delta: float
    primary_score_delta: float
    anchor_regressions: dict[str, float]
    gate_failures: tuple[str, ...]
    accepted: bool
    decision_hash: str
    capability_receipt_hash: str = ""
    capability_mode: str = ""

    def __post_init__(self) -> None:
        committed = self._commitment()
        if self.decision_hash != organization_hash(committed):
            raise ValueError("organization_evolution_decision_hash_invalid")
        if self.accepted != (not self.gate_failures):
            raise ValueError("organization_evolution_decision_state_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationEvolutionDecision":
        committed = dict(values)
        committed["gate_failures"] = list(committed["gate_failures"])
        if not committed.get("capability_receipt_hash"):
            committed.pop("capability_receipt_hash", None)
            committed.pop("capability_mode", None)
        return cls(**values, decision_hash=organization_hash(committed))

    def _commitment(self) -> dict[str, Any]:
        commitment = {
            "decision_id": self.decision_id,
            "incumbent_genome_hash": self.incumbent_genome_hash,
            "candidate_genome_hash": self.candidate_genome_hash,
            "proposal_hash": self.proposal_hash,
            "outcome_hash": self.outcome_hash,
            "incumbent_utility": self.incumbent_utility,
            "candidate_utility": self.candidate_utility,
            "utility_delta": self.utility_delta,
            "primary_score_delta": self.primary_score_delta,
            "anchor_regressions": self.anchor_regressions,
            "gate_failures": list(self.gate_failures),
            "accepted": self.accepted,
        }
        if self.capability_receipt_hash:
            commitment["capability_receipt_hash"] = self.capability_receipt_hash
            commitment["capability_mode"] = self.capability_mode
        return commitment

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "decision_hash": self.decision_hash}


@dataclass(frozen=True)
class OrganizationOperatorCredit:
    operator_id: str
    trials: int = 0
    retained: int = 0
    cumulative_utility_delta: float = 0.0
    cumulative_normalized_cost: float = 0.0

    def __post_init__(self) -> None:
        if self.operator_id not in ORGANIZATION_EVOLUTION_OPERATOR_IDS:
            raise ValueError("organization_operator_credit_id_invalid")
        if self.trials < 0 or self.retained < 0 or self.retained > self.trials:
            raise ValueError("organization_operator_credit_counts_invalid")
        _finite("organization_operator_credit_utility", self.cumulative_utility_delta)
        if _finite("organization_operator_credit_cost", self.cumulative_normalized_cost) < 0:
            raise ValueError("organization_operator_credit_cost_negative")

    def update(self, *, utility_delta: float, cost: float, retained: bool) -> "OrganizationOperatorCredit":
        return OrganizationOperatorCredit(
            operator_id=self.operator_id,
            trials=self.trials + 1,
            retained=self.retained + int(retained),
            cumulative_utility_delta=self.cumulative_utility_delta + utility_delta,
            cumulative_normalized_cost=self.cumulative_normalized_cost + cost,
        )

    def mean_reward(self) -> float:
        if not self.trials:
            return 0.0
        return self.cumulative_utility_delta / self.trials

    def as_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "trials": self.trials,
            "retained": self.retained,
            "cumulative_utility_delta": self.cumulative_utility_delta,
            "cumulative_normalized_cost": self.cumulative_normalized_cost,
            "mean_reward": self.mean_reward(),
        }


class OrganizationEvolutionGate:
    """Apply structural, evidence, cost, utility, and anchor-stability gates."""

    def evaluate(
        self,
        *,
        decision_id: str,
        task: OrganizationEvolutionTask,
        incumbent: OrganizationGenome,
        candidate: OrganizationGenome,
        proposal: OrganizationMutationProposal,
        incumbent_outcome: OrganizationHarnessOutcome,
        candidate_outcome: OrganizationHarnessOutcome,
        budget: OrganizationEvolutionBudget,
        fitness: OrganizationFitnessPolicy,
        spent_cost_before_candidate: float,
        capability_receipt: OrganizationCapabilityBindingReceipt | None = None,
    ) -> OrganizationEvolutionDecision:
        failures: list[str] = []
        if candidate.task_hash != task.task_hash or incumbent.task_hash != task.task_hash:
            failures.append("organization_evolution_task_binding_mismatch")
        if candidate.parent_genome_hash != incumbent.genome_hash or candidate.generation != incumbent.generation + 1:
            failures.append("organization_evolution_lineage_invalid")
        if candidate.mutation_operator_id != proposal.operator_id or candidate.mutation_proposal_hash != proposal.proposal_hash:
            failures.append("organization_evolution_proposal_binding_invalid")
        if proposal.parent_genome_hash != incumbent.genome_hash:
            failures.append("organization_evolution_proposal_parent_mismatch")
        if candidate.genome_hash == incumbent.genome_hash:
            failures.append("organization_evolution_noop_candidate")
        if capability_receipt is not None:
            if capability_receipt.genome_hash != candidate.genome_hash:
                failures.append("organization_evolution_capability_binding_mismatch")
            if capability_receipt.mode == "BLOCKED":
                failures.append("organization_evolution_capability_blocked")
        if len(candidate.roles) > budget.max_roles or len(candidate.edges) > budget.max_edges:
            failures.append("organization_evolution_structure_budget_exceeded")
        if candidate_outcome.genome_hash != candidate.genome_hash or candidate_outcome.task_hash != task.task_hash:
            failures.append("organization_evolution_outcome_binding_invalid")
        if incumbent_outcome.genome_hash != incumbent.genome_hash or incumbent_outcome.task_hash != task.task_hash:
            failures.append("organization_evolution_incumbent_outcome_binding_invalid")
        if candidate_outcome.stage_id != task.stage_id or incumbent_outcome.stage_id != task.stage_id:
            failures.append("organization_evolution_stage_binding_invalid")
        if not candidate_outcome.replay_valid:
            failures.append("organization_evolution_outcome_replay_invalid")
        if candidate_outcome.source_result_hash == incumbent_outcome.source_result_hash:
            failures.append("organization_evolution_outcome_independence_invalid")
        expected_anchors = set(task.anchor_task_ids)
        if set(candidate_outcome.anchor_scores) != expected_anchors or set(incumbent_outcome.anchor_scores) != expected_anchors:
            failures.append("organization_evolution_anchor_surface_mismatch")
        total_cost = spent_cost_before_candidate + candidate_outcome.normalized_cost
        if total_cost > budget.max_normalized_cost:
            failures.append("organization_evolution_cost_budget_exceeded")

        incumbent_utility = fitness.score(incumbent_outcome)
        candidate_utility = fitness.score(candidate_outcome)
        utility_delta = candidate_utility - incumbent_utility
        primary_delta = candidate_outcome.primary_score - incumbent_outcome.primary_score
        anchor_regressions = {
            anchor: incumbent_outcome.anchor_scores[anchor] - candidate_outcome.anchor_scores[anchor]
            for anchor in expected_anchors
        }
        if primary_delta < fitness.minimum_primary_gain:
            failures.append("organization_evolution_primary_gain_insufficient")
        if utility_delta < fitness.minimum_utility_gain:
            failures.append("organization_evolution_utility_gain_insufficient")
        if any(value > fitness.maximum_anchor_regression for value in anchor_regressions.values()):
            failures.append("organization_evolution_cross_stage_regression")
        return OrganizationEvolutionDecision.create(
            decision_id=decision_id,
            incumbent_genome_hash=incumbent.genome_hash,
            candidate_genome_hash=candidate.genome_hash,
            proposal_hash=proposal.proposal_hash,
            outcome_hash=candidate_outcome.outcome_hash,
            incumbent_utility=incumbent_utility,
            candidate_utility=candidate_utility,
            utility_delta=utility_delta,
            primary_score_delta=primary_delta,
            anchor_regressions=anchor_regressions,
            gate_failures=tuple(dict.fromkeys(failures)),
            accepted=not failures,
            capability_receipt_hash=capability_receipt.receipt_hash if capability_receipt else "",
            capability_mode=capability_receipt.mode if capability_receipt else "",
        )
