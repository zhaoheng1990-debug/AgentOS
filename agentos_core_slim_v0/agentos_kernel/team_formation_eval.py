"""Deterministic counterfactual evaluation for cognitive team formation trials."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


TEAM_FORMATION_EVAL_VERSION = "team_formation_counterfactual_eval_v0_1"

ARM_BEST_MEMBER = "BEST_MEMBER"
ARM_FIXED_TEAM = "FIXED_TEAM"
ARM_DYNAMIC_TEAM = "DYNAMIC_TEAM"
TRIAL_ARMS = {ARM_BEST_MEMBER, ARM_FIXED_TEAM, ARM_DYNAMIC_TEAM}

VERDICT_OUTPERFORMS = "OUTPERFORMS"
VERDICT_PARITY = "AT_PARITY"
VERDICT_UNDERPERFORMS = "UNDERPERFORMS"


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _unit(name: str, value: Any) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name}_outside_unit_interval")


@dataclass(frozen=True)
class TeamTrialObservation:
    observation_id: str
    trial_id: str
    arm: str
    subject_id: str
    agent_ids: tuple[str, ...]
    quality_score: float
    observed_cbit_gain: float
    errors_exposed: int
    errors_corrected: int
    negative_transfer_opportunities: int
    negative_transfer_intercepts: int
    normalized_cost: float
    convergence_steps: int
    evidence_refs: tuple[str, ...]
    harness_protocol_id: str
    budget_hash: str
    harness_receipt_ref: str
    semantic_assessment_receipt_ref: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.observation_id,
                self.trial_id,
                self.subject_id,
                self.agent_ids,
                self.evidence_refs,
                self.harness_protocol_id,
                self.budget_hash,
                self.harness_receipt_ref,
                self.semantic_assessment_receipt_ref,
            )
        ):
            raise ValueError("team_trial_observation_identity_incomplete")
        if self.arm not in TRIAL_ARMS:
            raise ValueError(f"unknown_team_trial_arm:{self.arm}")
        if len(set(self.agent_ids)) != len(self.agent_ids):
            raise ValueError("team_trial_agent_ids_not_unique")
        if self.arm == ARM_BEST_MEMBER and len(self.agent_ids) != 1:
            raise ValueError("best_member_arm_requires_one_agent")
        if self.arm != ARM_BEST_MEMBER and len(self.agent_ids) < 2:
            raise ValueError("team_arm_requires_plural_agents")
        for name in ("quality_score", "observed_cbit_gain", "normalized_cost"):
            _unit(name, getattr(self, name))
        for name in (
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
            "convergence_steps",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name}_must_be_nonnegative_integer")
        if self.errors_corrected > self.errors_exposed:
            raise ValueError("team_trial_errors_corrected_exceed_exposed")
        if self.negative_transfer_intercepts > self.negative_transfer_opportunities:
            raise ValueError("team_trial_intercepts_exceed_opportunities")

    @property
    def effectiveness_score(self) -> float:
        correction = self.errors_corrected / self.errors_exposed if self.errors_exposed else 0.0
        interception = (
            self.negative_transfer_intercepts / self.negative_transfer_opportunities
            if self.negative_transfer_opportunities
            else 0.0
        )
        score = (
            0.45 * self.quality_score
            + 0.35 * self.observed_cbit_gain
            + 0.10 * correction
            + 0.10 * interception
            - 0.15 * self.normalized_cost
        )
        return round(max(0.0, min(1.0, score)), 12)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "trial_id": self.trial_id,
            "arm": self.arm,
            "subject_id": self.subject_id,
            "agent_ids": list(self.agent_ids),
            "quality_score": self.quality_score,
            "observed_cbit_gain": self.observed_cbit_gain,
            "errors_exposed": self.errors_exposed,
            "errors_corrected": self.errors_corrected,
            "negative_transfer_opportunities": self.negative_transfer_opportunities,
            "negative_transfer_intercepts": self.negative_transfer_intercepts,
            "normalized_cost": self.normalized_cost,
            "convergence_steps": self.convergence_steps,
            "evidence_refs": list(self.evidence_refs),
            "harness_protocol_id": self.harness_protocol_id,
            "budget_hash": self.budget_hash,
            "harness_receipt_ref": self.harness_receipt_ref,
            "semantic_assessment_receipt_ref": self.semantic_assessment_receipt_ref,
            "effectiveness_score": self.effectiveness_score,
        }


@dataclass(frozen=True)
class TeamCounterfactualEvaluation:
    evaluation_id: str
    trial_id: str
    best_member_subject_id: str
    fixed_team_subject_id: str
    dynamic_team_subject_id: str
    best_member_score: float
    fixed_team_score: float
    dynamic_team_score: float
    delta_dynamic_vs_best_member: float
    delta_dynamic_vs_fixed_team: float
    verdict_vs_best_member: str
    verdict_vs_fixed_team: str
    dynamic_cost_delta_vs_fixed: float
    dynamic_convergence_delta_vs_fixed: int
    evidence_refs: tuple[str, ...]
    evaluation_hash: str
    frozen: bool = True
    route_selection_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "trial_id": self.trial_id,
            "best_member_subject_id": self.best_member_subject_id,
            "fixed_team_subject_id": self.fixed_team_subject_id,
            "dynamic_team_subject_id": self.dynamic_team_subject_id,
            "best_member_score": self.best_member_score,
            "fixed_team_score": self.fixed_team_score,
            "dynamic_team_score": self.dynamic_team_score,
            "delta_dynamic_vs_best_member": self.delta_dynamic_vs_best_member,
            "delta_dynamic_vs_fixed_team": self.delta_dynamic_vs_fixed_team,
            "verdict_vs_best_member": self.verdict_vs_best_member,
            "verdict_vs_fixed_team": self.verdict_vs_fixed_team,
            "dynamic_cost_delta_vs_fixed": self.dynamic_cost_delta_vs_fixed,
            "dynamic_convergence_delta_vs_fixed": self.dynamic_convergence_delta_vs_fixed,
            "evidence_refs": list(self.evidence_refs),
            "evaluation_hash": self.evaluation_hash,
            "frozen": self.frozen,
            "route_selection_authority": self.route_selection_authority,
        }


class TeamCounterfactualEvalHarness:
    """Compare a dynamic team with equal-protocol best-member and fixed-team arms."""

    module_id = TEAM_FORMATION_EVAL_VERSION
    capabilities = ("team_formation_counterfactual_evaluation",)

    def __init__(self, *, improvement_threshold: float = 0.02) -> None:
        if not math.isfinite(improvement_threshold) or improvement_threshold < 0.0:
            raise ValueError("team_improvement_threshold_invalid")
        self.improvement_threshold = float(improvement_threshold)

    def evaluate(
        self,
        evaluation_id: str,
        observations: tuple[TeamTrialObservation, ...],
    ) -> TeamCounterfactualEvaluation:
        if not evaluation_id:
            raise ValueError("team_counterfactual_evaluation_id_required")
        if len(observations) != 3 or {item.arm for item in observations} != TRIAL_ARMS:
            raise ValueError("team_counterfactual_requires_exactly_three_arms")
        if len({item.observation_id for item in observations}) != 3:
            raise ValueError("team_counterfactual_observation_ids_not_unique")
        if len({item.subject_id for item in observations}) != 3:
            raise ValueError("team_counterfactual_subject_ids_not_unique")
        if len({item.trial_id for item in observations}) != 1:
            raise ValueError("team_counterfactual_trial_id_mismatch")
        if len({item.harness_protocol_id for item in observations}) != 1:
            raise ValueError("team_counterfactual_harness_protocol_mismatch")
        if len({item.budget_hash for item in observations}) != 1:
            raise ValueError("team_counterfactual_budget_mismatch")
        evidence_sets = {tuple(sorted(item.evidence_refs)) for item in observations}
        if len(evidence_sets) != 1:
            raise ValueError("team_counterfactual_evidence_mismatch")

        by_arm = {item.arm: item for item in observations}
        member = by_arm[ARM_BEST_MEMBER]
        fixed = by_arm[ARM_FIXED_TEAM]
        dynamic = by_arm[ARM_DYNAMIC_TEAM]
        delta_member = round(dynamic.effectiveness_score - member.effectiveness_score, 12)
        delta_fixed = round(dynamic.effectiveness_score - fixed.effectiveness_score, 12)
        committed = {
            "evaluation_id": evaluation_id,
            "observation_hashes": [_hash_payload(item.as_dict()) for item in observations],
            "delta_dynamic_vs_best_member": delta_member,
            "delta_dynamic_vs_fixed_team": delta_fixed,
        }
        return TeamCounterfactualEvaluation(
            evaluation_id=evaluation_id,
            trial_id=dynamic.trial_id,
            best_member_subject_id=member.subject_id,
            fixed_team_subject_id=fixed.subject_id,
            dynamic_team_subject_id=dynamic.subject_id,
            best_member_score=member.effectiveness_score,
            fixed_team_score=fixed.effectiveness_score,
            dynamic_team_score=dynamic.effectiveness_score,
            delta_dynamic_vs_best_member=delta_member,
            delta_dynamic_vs_fixed_team=delta_fixed,
            verdict_vs_best_member=self._verdict(delta_member),
            verdict_vs_fixed_team=self._verdict(delta_fixed),
            dynamic_cost_delta_vs_fixed=round(dynamic.normalized_cost - fixed.normalized_cost, 12),
            dynamic_convergence_delta_vs_fixed=dynamic.convergence_steps - fixed.convergence_steps,
            evidence_refs=dynamic.evidence_refs,
            evaluation_hash=_hash_payload(committed),
        )

    def _verdict(self, delta: float) -> str:
        if delta > self.improvement_threshold:
            return VERDICT_OUTPERFORMS
        if delta < -self.improvement_threshold:
            return VERDICT_UNDERPERFORMS
        return VERDICT_PARITY
