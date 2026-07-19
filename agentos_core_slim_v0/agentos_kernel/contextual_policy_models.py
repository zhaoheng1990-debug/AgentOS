"""Pure contracts for context-conditioned cognitive organization selection."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


CONTEXTUAL_POLICY_ROLE_MAP = {
    "SOLO": ("HYPOTHESIS_GENERATOR",),
    "FIXED_TEAM": (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "SYNTHESIZER",
    ),
    "DYNAMIC_TEAM": (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "SYNTHESIZER",
        "COORDINATOR",
    ),
    "DYNAMIC_NO_COORDINATOR": (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "SYNTHESIZER",
    ),
    "DYNAMIC_NO_REVIEWER": (
        "HYPOTHESIS_GENERATOR",
        "REPLICATOR",
        "SYNTHESIZER",
        "COORDINATOR",
    ),
    "DYNAMIC_NO_REPLICATOR": (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "SYNTHESIZER",
        "COORDINATOR",
    ),
    "DYNAMIC_NO_SYNTHESIZER": (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "COORDINATOR",
    ),
}
CONTEXTUAL_POLICY_IDS = tuple(CONTEXTUAL_POLICY_ROLE_MAP)
POLICY_ACTIVATION_MODES = {
    "AUTHORIZED_PROJECT_SCOPED",
    "EXPLORATORY_TRIAL_ONLY",
    "ABSTAIN",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def require_unit(name: str, value: Any) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name}_outside_unit_interval")
    return float(value)


def require_positive_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name}_must_be_positive_integer")
    return value


def require_refs(name: str, refs: tuple[str, ...]) -> tuple[str, ...]:
    if not refs or len(refs) != len(set(refs)) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError(f"{name}_must_be_unique_nonempty_refs")
    return refs


@dataclass(frozen=True)
class ContextualRolePolicy:
    policy_id: str
    roles: tuple[str, ...]
    provider_call_ceiling: int
    coordination_step_ceiling: int

    def __post_init__(self) -> None:
        if self.policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError(f"contextual_policy_id_invalid:{self.policy_id}")
        if self.roles != CONTEXTUAL_POLICY_ROLE_MAP[self.policy_id]:
            raise ValueError("contextual_policy_role_binding_invalid")
        require_positive_int("contextual_policy_provider_call_ceiling", self.provider_call_ceiling)
        if (
            not isinstance(self.coordination_step_ceiling, int)
            or isinstance(self.coordination_step_ceiling, bool)
            or self.coordination_step_ceiling < 0
        ):
            raise ValueError("contextual_policy_coordination_step_ceiling_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "roles": list(self.roles),
            "provider_call_ceiling": self.provider_call_ceiling,
            "coordination_step_ceiling": self.coordination_step_ceiling,
        }


def default_contextual_role_policies() -> tuple[ContextualRolePolicy, ...]:
    return tuple(
        ContextualRolePolicy(
            policy_id=policy_id,
            roles=roles,
            provider_call_ceiling=len(roles) + 1,
            coordination_step_ceiling=(len(roles) if "COORDINATOR" in roles else max(0, len(roles) - 1)),
        )
        for policy_id, roles in CONTEXTUAL_POLICY_ROLE_MAP.items()
    )


@dataclass(frozen=True)
class ContextualProblemStructure:
    problem_id: str
    context_key: str
    project_scope: str
    objective: str
    premise_uncertainty: float
    evidence_conflict: float
    replication_need: float
    synthesis_need: float
    coordination_complexity: float
    novelty_need: float
    evidence_refs: tuple[str, ...]
    structure_receipt_ref: str
    structure_receipt_hash: str

    def __post_init__(self) -> None:
        for name in (
            "problem_id",
            "context_key",
            "project_scope",
            "objective",
            "structure_receipt_ref",
        ):
            require_text(name, getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("contextual_problem_scope_must_be_project_uri")
        for name in (
            "premise_uncertainty",
            "evidence_conflict",
            "replication_need",
            "synthesis_need",
            "coordination_complexity",
            "novelty_need",
        ):
            require_unit(name, getattr(self, name))
        require_refs("contextual_problem_evidence_refs", self.evidence_refs)
        if not _SHA256.fullmatch(self.structure_receipt_hash):
            raise ValueError("contextual_problem_structure_receipt_hash_invalid")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "problem_id": self.problem_id,
            "context_key": self.context_key,
            "project_scope": self.project_scope,
            "objective": self.objective,
            "premise_uncertainty": self.premise_uncertainty,
            "evidence_conflict": self.evidence_conflict,
            "replication_need": self.replication_need,
            "synthesis_need": self.synthesis_need,
            "coordination_complexity": self.coordination_complexity,
            "novelty_need": self.novelty_need,
            "evidence_refs": list(self.evidence_refs),
            "structure_receipt_ref": self.structure_receipt_ref,
            "structure_receipt_hash": self.structure_receipt_hash,
        }
        payload["problem_structure_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class OrganizationBudgetEnvelope:
    budget_ref: str
    max_roles: int
    max_provider_calls: int
    max_coordination_steps: int
    max_normalized_cost: float

    def __post_init__(self) -> None:
        require_text("organization_budget_ref", self.budget_ref)
        for name in ("max_roles", "max_provider_calls", "max_coordination_steps"):
            require_positive_int(name, getattr(self, name))
        require_unit("max_normalized_cost", self.max_normalized_cost)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "budget_ref": self.budget_ref,
            "max_roles": self.max_roles,
            "max_provider_calls": self.max_provider_calls,
            "max_coordination_steps": self.max_coordination_steps,
            "max_normalized_cost": self.max_normalized_cost,
        }
        payload["budget_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class OrganizationRiskEnvelope:
    risk_ref: str
    max_residual_risk: float
    max_provider_uncertainty: float
    max_anti_additive_signal: float
    matched_evidence_required_above_risk: float
    allow_unmatched_exploration: bool
    exploration_max_roles: int
    block_adverse_matched_evidence: bool = True
    require_distinct_provider: bool = False

    def __post_init__(self) -> None:
        require_text("organization_risk_ref", self.risk_ref)
        for name in (
            "max_residual_risk",
            "max_provider_uncertainty",
            "max_anti_additive_signal",
            "matched_evidence_required_above_risk",
        ):
            require_unit(name, getattr(self, name))
        require_positive_int("exploration_max_roles", self.exploration_max_roles)
        for name in (
            "allow_unmatched_exploration",
            "block_adverse_matched_evidence",
            "require_distinct_provider",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name}_must_be_boolean")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "risk_ref": self.risk_ref,
            "max_residual_risk": self.max_residual_risk,
            "max_provider_uncertainty": self.max_provider_uncertainty,
            "max_anti_additive_signal": self.max_anti_additive_signal,
            "matched_evidence_required_above_risk": self.matched_evidence_required_above_risk,
            "allow_unmatched_exploration": self.allow_unmatched_exploration,
            "exploration_max_roles": self.exploration_max_roles,
            "block_adverse_matched_evidence": self.block_adverse_matched_evidence,
            "require_distinct_provider": self.require_distinct_provider,
        }
        payload["risk_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class MatchedPolicyEvidence:
    policy_id: str
    context_key: str
    evidence_tier: str
    comparator_policy_id: str
    minimum_matched_pairs: int
    matched_pair_count: int
    unique_source_count: int
    sufficient_matched_evidence: bool
    mean_effectiveness: float | None
    mean_observed_cbit: float | None
    mean_normalized_cost: float | None
    mean_effectiveness_delta: float | None
    mean_cbit_delta: float | None
    mean_cost_delta: float | None
    mean_negative_transfer_interception: float | None
    matched_trial_group_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    record_hashes: tuple[str, ...]
    evidence_hash: str

    def __post_init__(self) -> None:
        if self.policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("contextual_matched_evidence_policy_invalid")
        if self.comparator_policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("contextual_matched_evidence_comparator_invalid")
        require_text("contextual_matched_evidence_context_key", self.context_key)
        require_text("contextual_matched_evidence_tier", self.evidence_tier)
        require_positive_int("contextual_matched_evidence_minimum_pairs", self.minimum_matched_pairs)
        if self.minimum_matched_pairs < 2:
            raise ValueError("contextual_matched_evidence_minimum_pairs_invalid")
        for name in ("matched_pair_count", "unique_source_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"contextual_matched_evidence_{name}_invalid")
        if self.matched_pair_count != len(self.matched_trial_group_ids):
            raise ValueError("contextual_matched_evidence_group_count_mismatch")
        if self.unique_source_count > self.matched_pair_count:
            raise ValueError("contextual_matched_evidence_source_count_invalid")
        if self.sufficient_matched_evidence != (
            self.matched_pair_count >= self.minimum_matched_pairs
            and self.unique_source_count >= self.minimum_matched_pairs
        ):
            raise ValueError("contextual_matched_evidence_sufficiency_invalid")
        if len(self.record_hashes) != self.matched_pair_count * 2:
            raise ValueError("contextual_matched_evidence_record_count_mismatch")
        if len(self.matched_trial_group_ids) != len(set(self.matched_trial_group_ids)):
            raise ValueError("contextual_matched_evidence_duplicate_group")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("contextual_matched_evidence_duplicate_ref")
        if any(not _SHA256.fullmatch(item) for item in self.record_hashes):
            raise ValueError("contextual_matched_evidence_record_hash_invalid")
        for name in (
            "mean_effectiveness",
            "mean_observed_cbit",
            "mean_normalized_cost",
            "mean_negative_transfer_interception",
        ):
            value = getattr(self, name)
            if value is not None:
                require_unit(f"contextual_matched_evidence_{name}", value)
        for name in ("mean_effectiveness_delta", "mean_cbit_delta", "mean_cost_delta"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or not -1.0 <= float(value) <= 1.0
            ):
                raise ValueError(f"contextual_matched_evidence_{name}_invalid")
        if self.matched_pair_count == 0:
            metrics = (
                self.mean_effectiveness,
                self.mean_observed_cbit,
                self.mean_normalized_cost,
                self.mean_effectiveness_delta,
                self.mean_cbit_delta,
                self.mean_cost_delta,
                self.mean_negative_transfer_interception,
            )
            if any(value is not None for value in metrics) or self.evidence_refs or self.record_hashes:
                raise ValueError("contextual_matched_evidence_empty_state_invalid")
        if self.evidence_hash != hash_payload(self._committed_dict()):
            raise ValueError("contextual_matched_evidence_hash_mismatch")

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "comparator_policy_id": self.comparator_policy_id,
            "matched_trial_group_ids": list(self.matched_trial_group_ids),
            "record_hashes": list(self.record_hashes),
            "minimum_matched_pairs": self.minimum_matched_pairs,
            "mean_effectiveness": self.mean_effectiveness,
            "mean_observed_cbit": self.mean_observed_cbit,
            "mean_normalized_cost": self.mean_normalized_cost,
            "mean_effectiveness_delta": self.mean_effectiveness_delta,
            "mean_cbit_delta": self.mean_cbit_delta,
            "mean_cost_delta": self.mean_cost_delta,
            "mean_negative_transfer_interception": self.mean_negative_transfer_interception,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "comparator_policy_id": self.comparator_policy_id,
            "minimum_matched_pairs": self.minimum_matched_pairs,
            "matched_pair_count": self.matched_pair_count,
            "unique_source_count": self.unique_source_count,
            "sufficient_matched_evidence": self.sufficient_matched_evidence,
            "mean_effectiveness": self.mean_effectiveness,
            "mean_observed_cbit": self.mean_observed_cbit,
            "mean_normalized_cost": self.mean_normalized_cost,
            "mean_effectiveness_delta": self.mean_effectiveness_delta,
            "mean_cbit_delta": self.mean_cbit_delta,
            "mean_cost_delta": self.mean_cost_delta,
            "mean_negative_transfer_interception": self.mean_negative_transfer_interception,
            "matched_trial_group_ids": list(self.matched_trial_group_ids),
            "evidence_refs": list(self.evidence_refs),
            "record_hashes": list(self.record_hashes),
            "evidence_hash": self.evidence_hash,
        }


@dataclass(frozen=True)
class ContextualProviderPolicyAssessment:
    policy_id: str
    structure_fit: float
    expected_cbit_gain: float
    estimated_normalized_cost: float
    residual_risk: float
    anti_additive_signal: float
    uncertainty: float
    rationale: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("contextual_provider_policy_id_invalid")
        for name in (
            "structure_fit",
            "expected_cbit_gain",
            "estimated_normalized_cost",
            "residual_risk",
            "anti_additive_signal",
            "uncertainty",
        ):
            require_unit(name, getattr(self, name))
        require_text("contextual_provider_rationale", self.rationale)
        require_refs("contextual_provider_evidence_refs", self.evidence_refs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "structure_fit": self.structure_fit,
            "expected_cbit_gain": self.expected_cbit_gain,
            "estimated_normalized_cost": self.estimated_normalized_cost,
            "residual_risk": self.residual_risk,
            "anti_additive_signal": self.anti_additive_signal,
            "uncertainty": self.uncertainty,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ContextualPolicyCandidateEvaluation:
    policy_id: str
    roles: tuple[str, ...]
    eligibility: str
    hard_gate_failures: tuple[str, ...]
    rank_vector: tuple[float, ...]
    matched_evidence_hash: str
    provider_assessment: ContextualProviderPolicyAssessment

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "roles": list(self.roles),
            "eligibility": self.eligibility,
            "hard_gate_failures": list(self.hard_gate_failures),
            "rank_vector": list(self.rank_vector),
            "matched_evidence_hash": self.matched_evidence_hash,
            "provider_assessment": self.provider_assessment.as_dict(),
        }


@dataclass(frozen=True)
class ContextualOrganizationPolicyDecision:
    decision_id: str
    selected_policy_id: str
    selected_roles: tuple[str, ...]
    activation_mode: str
    execution_authorized: bool
    trial_authorized: bool
    kernel_authorization_ref: str
    required_roles: tuple[str, ...]
    candidate_evaluations: tuple[ContextualPolicyCandidateEvaluation, ...]
    reason: str
    problem_structure_hash: str
    budget_hash: str
    risk_hash: str
    provider_advice_hash: str
    evidence_refs: tuple[str, ...]
    decision_hash: str

    def __post_init__(self) -> None:
        require_text("contextual_policy_decision_id", self.decision_id)
        if self.activation_mode not in POLICY_ACTIVATION_MODES:
            raise ValueError("contextual_policy_activation_mode_invalid")
        if not self.kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("contextual_policy_kernel_authorization_required")
        if self.activation_mode == "ABSTAIN":
            if self.selected_policy_id or self.selected_roles or self.execution_authorized or self.trial_authorized:
                raise ValueError("contextual_policy_abstain_state_invalid")
        else:
            if self.selected_policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
                raise ValueError("contextual_policy_selected_policy_invalid")
            if self.selected_roles != CONTEXTUAL_POLICY_ROLE_MAP[self.selected_policy_id]:
                raise ValueError("contextual_policy_selected_roles_invalid")
            if not self.trial_authorized:
                raise ValueError("contextual_policy_selected_trial_authority_required")
        if self.execution_authorized != (self.activation_mode == "AUTHORIZED_PROJECT_SCOPED"):
            raise ValueError("contextual_policy_execution_authority_invalid")
        require_refs("contextual_policy_decision_evidence_refs", self.evidence_refs)
        for name in (
            "problem_structure_hash",
            "budget_hash",
            "risk_hash",
            "provider_advice_hash",
            "decision_hash",
        ):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise ValueError(f"contextual_policy_{name}_invalid")
        if self.decision_hash != hash_payload(self._committed_dict()):
            raise ValueError("contextual_policy_decision_hash_mismatch")

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "selected_policy_id": self.selected_policy_id,
            "selected_roles": list(self.selected_roles),
            "activation_mode": self.activation_mode,
            "execution_authorized": self.execution_authorized,
            "trial_authorized": self.trial_authorized,
            "kernel_authorization_ref": self.kernel_authorization_ref,
            "required_roles": list(self.required_roles),
            "candidate_evaluations": [item.as_dict() for item in self.candidate_evaluations],
            "reason": self.reason,
            "problem_structure_hash": self.problem_structure_hash,
            "budget_hash": self.budget_hash,
            "risk_hash": self.risk_hash,
            "provider_advice_hash": self.provider_advice_hash,
            "evidence_refs": list(self.evidence_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "decision_hash": self.decision_hash,
            "global_policy_authority": False,
            "production_activation": False,
        }
