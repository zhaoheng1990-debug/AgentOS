"""Deterministic comparison harness for provider-backed problem quality judgments."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


PROBLEM_QUALITY_EVAL_VERSION = "problem_quality_eval_harness_v0_1"

SOURCE_GROUP = "GROUP"
SOURCE_MEMBER = "MEMBER"
SOURCE_HUMAN_BASELINE = "HUMAN_BASELINE"
SOURCE_KINDS = {SOURCE_GROUP, SOURCE_MEMBER, SOURCE_HUMAN_BASELINE}

VERDICT_OUTPERFORMS = "OUTPERFORMS"
VERDICT_PARITY = "AT_PARITY"
VERDICT_UNDERPERFORMS = "UNDERPERFORMS"

QUALITY_DIMENSIONS = (
    "evidence_grounding",
    "premise_soundness",
    "novelty",
    "falsifiability",
    "discriminatory_power",
    "harness_feasibility",
    "expected_cbit_gain",
    "normalized_cost",
    "negative_transfer_risk",
)

_POSITIVE_WEIGHTS = {
    "evidence_grounding": 0.18,
    "premise_soundness": 0.14,
    "novelty": 0.10,
    "falsifiability": 0.16,
    "discriminatory_power": 0.16,
    "harness_feasibility": 0.10,
    "expected_cbit_gain": 0.16,
}
_RISK_WEIGHTS = {
    "normalized_cost": 0.10,
    "negative_transfer_risk": 0.15,
}


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require_unit_interval(name: str, value: Any) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name}_outside_unit_interval")


@dataclass(frozen=True)
class ProblemQualityObservation:
    """One prospective problem judgment admitted from a provider receipt."""

    observation_id: str
    candidate_id: str
    source_kind: str
    source_subject_id: str
    problem_statement: str
    scope: str
    evidence_refs: tuple[str, ...]
    provider_id: str
    model_id: str
    provider_support_receipt_ref: str
    evidence_grounding: float
    premise_soundness: float
    novelty: float
    falsifiability: float
    discriminatory_power: float
    harness_feasibility: float
    expected_cbit_gain: float
    normalized_cost: float
    negative_transfer_risk: float
    assessment_rationale: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.observation_id,
                self.candidate_id,
                self.source_subject_id,
                self.problem_statement,
                self.scope,
                self.provider_id,
                self.model_id,
                self.provider_support_receipt_ref,
                self.assessment_rationale,
            )
        ):
            raise ValueError("problem_quality_observation_identity_incomplete")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(f"unknown_problem_source_kind:{self.source_kind}")
        if not self.evidence_refs:
            raise ValueError("problem_quality_observation_evidence_required")
        for dimension in QUALITY_DIMENSIONS:
            _require_unit_interval(dimension, getattr(self, dimension))

    @property
    def quality_score(self) -> float:
        positive = sum(float(getattr(self, name)) * weight for name, weight in _POSITIVE_WEIGHTS.items())
        risks = sum(float(getattr(self, name)) * weight for name, weight in _RISK_WEIGHTS.items())
        return round(max(0.0, min(1.0, positive - risks)), 12)

    @property
    def observation_hash(self) -> str:
        return _hash_payload(self.as_dict(include_hash=False))

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "observation_id": self.observation_id,
            "candidate_id": self.candidate_id,
            "source_kind": self.source_kind,
            "source_subject_id": self.source_subject_id,
            "problem_statement": self.problem_statement,
            "scope": self.scope,
            "evidence_refs": list(self.evidence_refs),
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "provider_support_receipt_ref": self.provider_support_receipt_ref,
            **{name: getattr(self, name) for name in QUALITY_DIMENSIONS},
            "assessment_rationale": self.assessment_rationale,
            "quality_score": self.quality_score,
        }
        if include_hash:
            payload["observation_hash"] = _hash_payload(payload)
        return payload


@dataclass(frozen=True)
class ProblemQualityEvaluation:
    evaluation_id: str
    group_observation_id: str
    group_quality_score: float
    best_member_observation_id: str
    best_member_quality_score: float
    best_human_observation_id: str
    best_human_quality_score: float
    delta_vs_best_member: float
    delta_vs_human_baseline: float
    verdict_vs_best_member: str
    verdict_vs_human_baseline: str
    ranked_observation_ids: tuple[str, ...]
    admitted_evidence_refs: tuple[str, ...]
    group_trial_gate_passed: bool
    group_trial_gate_failures: tuple[str, ...]
    evaluation_hash: str
    frozen: bool = True
    execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "group_observation_id": self.group_observation_id,
            "group_quality_score": self.group_quality_score,
            "best_member_observation_id": self.best_member_observation_id,
            "best_member_quality_score": self.best_member_quality_score,
            "best_human_observation_id": self.best_human_observation_id,
            "best_human_quality_score": self.best_human_quality_score,
            "delta_vs_best_member": self.delta_vs_best_member,
            "delta_vs_human_baseline": self.delta_vs_human_baseline,
            "verdict_vs_best_member": self.verdict_vs_best_member,
            "verdict_vs_human_baseline": self.verdict_vs_human_baseline,
            "ranked_observation_ids": list(self.ranked_observation_ids),
            "admitted_evidence_refs": list(self.admitted_evidence_refs),
            "group_trial_gate_passed": self.group_trial_gate_passed,
            "group_trial_gate_failures": list(self.group_trial_gate_failures),
            "evaluation_hash": self.evaluation_hash,
            "frozen": self.frozen,
            "execution_authorized": self.execution_authorized,
        }


class ProblemQualityEvalHarness:
    """Compare problem candidates without making semantic judgments or authorizing trials."""

    module_id = PROBLEM_QUALITY_EVAL_VERSION
    capabilities = ("prospective_problem_quality_comparison",)

    def __init__(self, *, improvement_threshold: float = 0.02) -> None:
        if improvement_threshold < 0.0 or not math.isfinite(improvement_threshold):
            raise ValueError("improvement_threshold_must_be_finite_and_nonnegative")
        self.improvement_threshold = float(improvement_threshold)

    def evaluate(
        self,
        evaluation_id: str,
        observations: tuple[ProblemQualityObservation, ...],
    ) -> ProblemQualityEvaluation:
        if not evaluation_id:
            raise ValueError("problem_quality_evaluation_id_required")
        if len({item.observation_id for item in observations}) != len(observations):
            raise ValueError("duplicate_problem_quality_observation_id")
        scopes = {item.scope for item in observations}
        if len(scopes) != 1:
            raise ValueError("problem_quality_observation_scope_mismatch")

        groups = [item for item in observations if item.source_kind == SOURCE_GROUP]
        members = [item for item in observations if item.source_kind == SOURCE_MEMBER]
        humans = [item for item in observations if item.source_kind == SOURCE_HUMAN_BASELINE]
        if len(groups) != 1:
            raise ValueError("exactly_one_group_problem_observation_required")
        if not members:
            raise ValueError("member_problem_baseline_required")
        if not humans:
            raise ValueError("human_problem_baseline_required")

        group = groups[0]
        best_member = max(members, key=lambda item: (item.quality_score, item.observation_id))
        best_human = max(humans, key=lambda item: (item.quality_score, item.observation_id))
        delta_member = round(group.quality_score - best_member.quality_score, 12)
        delta_human = round(group.quality_score - best_human.quality_score, 12)
        ranked = tuple(
            item.observation_id
            for item in sorted(observations, key=lambda item: (-item.quality_score, item.observation_id))
        )
        evidence_refs = tuple(dict.fromkeys(ref for item in observations for ref in item.evidence_refs))
        gate_failures = self._trial_gate_failures(group)
        committed = {
            "evaluation_id": evaluation_id,
            "observation_hashes": [item.observation_hash for item in observations],
            "ranked_observation_ids": list(ranked),
            "delta_vs_best_member": delta_member,
            "delta_vs_human_baseline": delta_human,
            "group_trial_gate_failures": list(gate_failures),
        }
        return ProblemQualityEvaluation(
            evaluation_id=evaluation_id,
            group_observation_id=group.observation_id,
            group_quality_score=group.quality_score,
            best_member_observation_id=best_member.observation_id,
            best_member_quality_score=best_member.quality_score,
            best_human_observation_id=best_human.observation_id,
            best_human_quality_score=best_human.quality_score,
            delta_vs_best_member=delta_member,
            delta_vs_human_baseline=delta_human,
            verdict_vs_best_member=self._verdict(delta_member),
            verdict_vs_human_baseline=self._verdict(delta_human),
            ranked_observation_ids=ranked,
            admitted_evidence_refs=evidence_refs,
            group_trial_gate_passed=not gate_failures,
            group_trial_gate_failures=gate_failures,
            evaluation_hash=_hash_payload(committed),
        )

    def _verdict(self, delta: float) -> str:
        if delta > self.improvement_threshold:
            return VERDICT_OUTPERFORMS
        if delta < -self.improvement_threshold:
            return VERDICT_UNDERPERFORMS
        return VERDICT_PARITY

    @staticmethod
    def _trial_gate_failures(group: ProblemQualityObservation) -> tuple[str, ...]:
        failures: list[str] = []
        minimums = {
            "evidence_grounding": 0.5,
            "premise_soundness": 0.5,
            "falsifiability": 0.5,
            "discriminatory_power": 0.4,
            "harness_feasibility": 0.5,
        }
        for name, minimum in minimums.items():
            if getattr(group, name) < minimum:
                failures.append(f"group_problem_{name}_below_trial_floor")
        if group.negative_transfer_risk > 0.5:
            failures.append("group_problem_negative_transfer_risk_above_trial_ceiling")
        return tuple(failures)
