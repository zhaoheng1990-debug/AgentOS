"""Observable evaluation harness for bounded group-cognition trials.

The harness measures whether an ensemble improves on its best observed member.
It does not schedule agents, judge claims, or promote cognitive assets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


GROUP_COGNITION_EVAL_VERSION = "group_cognition_eval_v0_1"

VERDICT_GROUP_OUTPERFORMS = "GROUP_OUTPERFORMS_BEST_MEMBER"
VERDICT_GROUP_PARITY = "GROUP_AT_PARITY_WITH_BEST_MEMBER"
VERDICT_GROUP_UNDERPERFORMS = "GROUP_UNDERPERFORMS_BEST_MEMBER"


def _require_unit_interval(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name}_outside_unit_interval")


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name}_must_be_non_negative")


@dataclass(frozen=True)
class CognitionRunObservation:
    """One bounded run observed through explicit, replayable proxies."""

    subject_id: str
    quality_score: float
    hypotheses: tuple[str, ...] = ()
    errors_exposed: int = 0
    errors_corrected: int = 0
    candidates_admitted: int = 0
    candidates_survived: int = 0
    negative_transfer_opportunities: int = 0
    negative_transfer_intercepts: int = 0
    convergence_steps: int = 0
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject_id:
            raise ValueError("subject_id_required")
        _require_unit_interval("quality_score", self.quality_score)
        for name in (
            "errors_exposed",
            "errors_corrected",
            "candidates_admitted",
            "candidates_survived",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
            "convergence_steps",
        ):
            _require_non_negative(name, getattr(self, name))
        if self.errors_corrected > self.errors_exposed:
            raise ValueError("errors_corrected_exceeds_errors_exposed")
        if self.candidates_survived > self.candidates_admitted:
            raise ValueError("candidates_survived_exceeds_candidates_admitted")
        if self.negative_transfer_intercepts > self.negative_transfer_opportunities:
            raise ValueError("negative_transfer_intercepts_exceed_opportunities")


@dataclass(frozen=True)
class GroupCognitionEvaluation:
    trial_id: str
    member_count: int
    best_member_id: str
    best_member_quality: float
    group_quality: float
    group_delta_vs_best_member: float
    error_correction_rate: float
    candidate_survival_rate: float
    hypothesis_diversity: float
    convergence_steps: int
    negative_transfer_intercept_rate: float
    verdict: str
    evidence_refs: tuple[str, ...]
    proxy_boundary: str = "observable_trial_metrics_do_not_establish_group_cognition_ontology"

    def as_dict(self) -> dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "member_count": self.member_count,
            "best_member_id": self.best_member_id,
            "best_member_quality": self.best_member_quality,
            "group_quality": self.group_quality,
            "group_delta_vs_best_member": self.group_delta_vs_best_member,
            "error_correction_rate": self.error_correction_rate,
            "candidate_survival_rate": self.candidate_survival_rate,
            "hypothesis_diversity": self.hypothesis_diversity,
            "convergence_steps": self.convergence_steps,
            "negative_transfer_intercept_rate": self.negative_transfer_intercept_rate,
            "verdict": self.verdict,
            "evidence_refs": list(self.evidence_refs),
            "proxy_boundary": self.proxy_boundary,
        }


class GroupCognitionEvalHarness:
    """Deterministic P0 metric adapter with no scheduling or write authority."""

    module_id = GROUP_COGNITION_EVAL_VERSION
    capabilities = ("group_cognition_evaluation",)

    def __init__(self, *, improvement_threshold: float = 0.0) -> None:
        if improvement_threshold < 0.0:
            raise ValueError("improvement_threshold_must_be_non_negative")
        self.improvement_threshold = improvement_threshold

    def evaluate(
        self,
        trial_id: str,
        members: tuple[CognitionRunObservation, ...],
        group: CognitionRunObservation,
    ) -> GroupCognitionEvaluation:
        if not trial_id:
            raise ValueError("trial_id_required")
        if not members:
            raise ValueError("at_least_one_member_observation_required")
        member_ids = [member.subject_id for member in members]
        if len(set(member_ids)) != len(member_ids):
            raise ValueError("duplicate_member_subject_id")
        if group.subject_id in member_ids:
            raise ValueError("group_subject_id_must_be_distinct")

        best_member = max(members, key=lambda member: member.quality_score)
        delta = group.quality_score - best_member.quality_score
        if delta > self.improvement_threshold:
            verdict = VERDICT_GROUP_OUTPERFORMS
        elif delta < -self.improvement_threshold:
            verdict = VERDICT_GROUP_UNDERPERFORMS
        else:
            verdict = VERDICT_GROUP_PARITY

        total_hypotheses = sum(len(member.hypotheses) for member in members)
        distinct_hypotheses = len({hypothesis for member in members for hypothesis in member.hypotheses})
        evidence_refs = tuple(
            dict.fromkeys(ref for observation in (*members, group) for ref in observation.evidence_refs)
        )

        return GroupCognitionEvaluation(
            trial_id=trial_id,
            member_count=len(members),
            best_member_id=best_member.subject_id,
            best_member_quality=best_member.quality_score,
            group_quality=group.quality_score,
            group_delta_vs_best_member=round(delta, 12),
            error_correction_rate=self._rate(group.errors_corrected, group.errors_exposed),
            candidate_survival_rate=self._rate(group.candidates_survived, group.candidates_admitted),
            hypothesis_diversity=self._rate(distinct_hypotheses, total_hypotheses),
            convergence_steps=group.convergence_steps,
            negative_transfer_intercept_rate=self._rate(
                group.negative_transfer_intercepts,
                group.negative_transfer_opportunities,
            ),
            verdict=verdict,
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 12) if denominator else 0.0
