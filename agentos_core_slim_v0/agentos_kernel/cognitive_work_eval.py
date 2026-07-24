"""Kernel-owned evaluation of cognitive-work trajectories."""

from __future__ import annotations

from dataclasses import dataclass

from .cognitive_work_models import (
    CognitiveWorkBudget,
    CognitiveWorkControlDecision,
    CognitiveWorkRoundObservation,
    CognitiveWorkSemanticAssessment,
)


@dataclass(frozen=True)
class CognitiveWorkThresholds:
    sufficient_cbit: float = 0.80
    minimum_marginal_cbit: float = 0.03
    minimum_cognitive_efficiency: float = 0.00001
    redundancy_ceiling: float = 0.70
    problem_drift_ceiling: float = 0.45
    error_correlation_ceiling: float = 0.75
    escalation_uncertainty_threshold: float = 0.60
    minimum_rounds_before_escalation: int = 2


class CognitiveWorkEvaluator:
    """Turn admitted mechanical and semantic receipts into a bounded action."""

    def __init__(self, thresholds: CognitiveWorkThresholds | None = None) -> None:
        self.thresholds = thresholds or CognitiveWorkThresholds()

    def evaluate(
        self,
        *,
        decision_id: str,
        observations: tuple[CognitiveWorkRoundObservation, ...],
        assessments: tuple[CognitiveWorkSemanticAssessment, ...],
        provider_receipt_hashes: tuple[str, ...],
        budget: CognitiveWorkBudget,
        kernel_authorization_ref: str,
    ) -> CognitiveWorkControlDecision:
        if not observations or len(observations) != len(assessments):
            raise ValueError("cognitive_work_trajectory_alignment_invalid")
        if len(provider_receipt_hashes) != len(observations):
            raise ValueError("cognitive_work_provider_receipt_alignment_invalid")
        if [item.round_index for item in observations] != list(range(1, len(observations) + 1)):
            raise ValueError("cognitive_work_round_sequence_invalid")
        if len({item.trajectory_id for item in observations}) != 1:
            raise ValueError("cognitive_work_trajectory_id_mismatch")
        if len({(item.project_scope, item.context_key) for item in observations}) != 1:
            raise ValueError("cognitive_work_scope_or_context_mismatch")
        if any(not set(item.evidence_refs).issubset(observation.evidence_refs)
               for observation, item in zip(observations, assessments)):
            raise ValueError("cognitive_work_semantic_evidence_outside_observation")

        totals = self._totals(observations)
        marginal = observations[-1].observed_cbit_gain
        cumulative = min(1.0, sum(item.observed_cbit_gain for item in observations))
        efficiency = round(cumulative / max(1, totals["total_tokens"]), 12)
        action, reason = self._action(
            observations=observations,
            assessments=assessments,
            budget=budget,
            totals=totals,
            marginal=marginal,
            cumulative=cumulative,
            efficiency=efficiency,
        )
        sufficient = action == "STOP_SUFFICIENT"
        return CognitiveWorkControlDecision.create(
            decision_id=decision_id,
            trajectory_id=observations[0].trajectory_id,
            project_scope=observations[0].project_scope,
            context_key=observations[0].context_key,
            action=action,
            allow_additional_round=action in {"CONTINUE", "REORGANIZE", "ESCALATE"},
            allow_organization_expansion=action in {"CONTINUE", "REORGANIZE"},
            allow_direct_sro_reuse=sufficient and assessments[-1].problem_drift <= self.thresholds.problem_drift_ceiling,
            retention_eligible=sufficient,
            operator_memory_eligible=sufficient and len(observations) >= 2,
            marginal_cbit_gain=round(marginal, 12),
            cognitive_efficiency=efficiency,
            cumulative_cbit_gain=round(cumulative, 12),
            round_count=len(observations),
            reason=reason,
            observation_hashes=tuple(item.observation_hash for item in observations),
            provider_receipt_hashes=provider_receipt_hashes,
            budget_hash=budget.as_dict()["budget_hash"],
            kernel_authorization_ref=kernel_authorization_ref,
            **totals,
        )

    def _action(self, *, observations, assessments, budget, totals, marginal, cumulative, efficiency):
        latest = assessments[-1]
        if self._budget_exceeded(len(observations), totals, budget):
            return "BLOCK_BUDGET", "cognitive_work_budget_exhausted"
        if cumulative >= self.thresholds.sufficient_cbit:
            return "STOP_SUFFICIENT", "required_effective_cbit_reached"
        if self._budget_exhausted(len(observations), totals, budget):
            return "BLOCK_BUDGET", "cognitive_work_budget_exhausted"
        if latest.problem_drift > self.thresholds.problem_drift_ceiling:
            return "REORGANIZE", "problem_drift_requires_topology_or_object_reorganization"
        if latest.error_correlation > self.thresholds.error_correlation_ceiling:
            return "REORGANIZE", "correlated_errors_require_independent_cognitive_source"
        if (
            latest.uncertainty >= self.thresholds.escalation_uncertainty_threshold
            and len(observations) >= self.thresholds.minimum_rounds_before_escalation
            and latest.recommended_action == "ESCALATE"
        ):
            return "ESCALATE", "residual_uncertainty_requires_capability_escalation"
        if (
            marginal < self.thresholds.minimum_marginal_cbit
            and latest.redundancy >= self.thresholds.redundancy_ceiling
        ) or efficiency < self.thresholds.minimum_cognitive_efficiency:
            return "STOP_LOW_MARGINAL", "marginal_cbit_does_not_cover_redundant_work"
        return "CONTINUE", "positive_marginal_cbit_within_budget"

    @staticmethod
    def _totals(observations):
        return {
            "total_tokens": sum(item.total_tokens for item in observations),
            "total_provider_calls": sum(item.provider_calls for item in observations),
            "total_tool_calls": sum(item.tool_calls for item in observations),
            "total_latency_ms": sum(item.latency_ms for item in observations),
            "total_api_cost": round(sum(item.api_cost for item in observations), 12),
            "total_tool_cost": round(sum(item.tool_cost for item in observations), 12),
        }

    @staticmethod
    def _budget_exceeded(round_count, totals, budget):
        return any((
            round_count > budget.max_rounds,
            totals["total_tokens"] > budget.max_total_tokens,
            totals["total_provider_calls"] > budget.max_provider_calls,
            totals["total_tool_calls"] > budget.max_tool_calls,
            totals["total_latency_ms"] > budget.max_latency_ms,
            totals["total_api_cost"] > budget.max_api_cost,
            totals["total_tool_cost"] > budget.max_tool_cost,
        ))

    @staticmethod
    def _budget_exhausted(round_count, totals, budget):
        return any((
            round_count >= budget.max_rounds,
            totals["total_tokens"] >= budget.max_total_tokens,
            totals["total_provider_calls"] >= budget.max_provider_calls,
            totals["total_tool_calls"] >= budget.max_tool_calls,
            totals["total_latency_ms"] >= budget.max_latency_ms,
            totals["total_api_cost"] >= budget.max_api_cost if budget.max_api_cost else False,
            totals["total_tool_cost"] >= budget.max_tool_cost if budget.max_tool_cost else False,
        ))
