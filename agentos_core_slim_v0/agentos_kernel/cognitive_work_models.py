"""Pure contracts for cognitive-work accounting and Kernel control."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


COGNITIVE_WORK_ACCOUNTING_VERSION = "cognitive_work_accounting_v0_1"
COGNITIVE_WORK_ACTIONS = (
    "CONTINUE",
    "STOP_SUFFICIENT",
    "STOP_LOW_MARGINAL",
    "REORGANIZE",
    "ESCALATE",
    "BLOCK_BUDGET",
)


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


def require_nonnegative(name: str, value: Any) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise ValueError(f"{name}_must_be_nonnegative")
    return float(value)


def require_refs(name: str, refs: tuple[str, ...]) -> tuple[str, ...]:
    if not refs or len(refs) != len(set(refs)) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError(f"{name}_must_be_unique_nonempty_refs")
    return refs


@dataclass(frozen=True)
class CognitiveWorkBudget:
    budget_id: str
    max_rounds: int
    max_total_tokens: int
    max_provider_calls: int
    max_tool_calls: int
    max_latency_ms: int
    max_api_cost: float
    max_tool_cost: float

    def __post_init__(self) -> None:
        require_text("cognitive_work_budget_id", self.budget_id)
        for name in (
            "max_rounds",
            "max_total_tokens",
            "max_provider_calls",
            "max_tool_calls",
            "max_latency_ms",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"cognitive_work_{name}_must_be_positive_integer")
        require_nonnegative("cognitive_work_max_api_cost", self.max_api_cost)
        require_nonnegative("cognitive_work_max_tool_cost", self.max_tool_cost)

    def as_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["budget_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class CognitiveWorkRoundObservation:
    observation_id: str
    trajectory_id: str
    project_scope: str
    context_key: str
    round_index: int
    stage: str
    topology_id: str
    agent_ids: tuple[str, ...]
    model_ids: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    provider_calls: int
    tool_calls: int
    latency_ms: int
    api_cost: float
    tool_cost: float
    observed_cbit_gain: float
    errors_exposed: int
    errors_corrected: int
    evidence_refs: tuple[str, ...]
    harness_receipt_ref: str

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "trajectory_id",
            "context_key",
            "stage",
            "topology_id",
            "harness_receipt_ref",
        ):
            require_text(f"cognitive_work_{name}", getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("cognitive_work_project_scope_invalid")
        if not isinstance(self.round_index, int) or isinstance(self.round_index, bool) or self.round_index < 1:
            raise ValueError("cognitive_work_round_index_invalid")
        if not self.agent_ids or len(self.agent_ids) != len(set(self.agent_ids)):
            raise ValueError("cognitive_work_agent_ids_invalid")
        if not self.model_ids or any(not isinstance(item, str) or not item for item in self.model_ids):
            raise ValueError("cognitive_work_model_ids_invalid")
        for name in (
            "input_tokens",
            "output_tokens",
            "cached_tokens",
            "provider_calls",
            "tool_calls",
            "latency_ms",
            "errors_exposed",
            "errors_corrected",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"cognitive_work_{name}_must_be_nonnegative_integer")
        if self.errors_corrected > self.errors_exposed:
            raise ValueError("cognitive_work_errors_corrected_exceed_exposed")
        require_nonnegative("cognitive_work_api_cost", self.api_cost)
        require_nonnegative("cognitive_work_tool_cost", self.tool_cost)
        require_unit("cognitive_work_observed_cbit_gain", self.observed_cbit_gain)
        require_refs("cognitive_work_evidence_refs", self.evidence_refs)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def as_dict(self) -> dict[str, Any]:
        payload = {
            **self.__dict__,
            "agent_ids": list(self.agent_ids),
            "model_ids": list(self.model_ids),
            "evidence_refs": list(self.evidence_refs),
            "total_tokens": self.total_tokens,
        }
        payload["observation_hash"] = hash_payload(payload)
        return payload

    @property
    def observation_hash(self) -> str:
        return self.as_dict()["observation_hash"]


@dataclass(frozen=True)
class CognitiveWorkSemanticAssessment:
    evidence_novelty: float
    constraint_coverage: float
    hypothesis_diversity: float
    redundancy: float
    error_correlation: float
    problem_drift: float
    uncertainty: float
    recommended_action: str
    rationale: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "evidence_novelty",
            "constraint_coverage",
            "hypothesis_diversity",
            "redundancy",
            "error_correlation",
            "problem_drift",
            "uncertainty",
        ):
            require_unit(f"cognitive_work_{name}", getattr(self, name))
        if self.recommended_action not in COGNITIVE_WORK_ACTIONS:
            raise ValueError("cognitive_work_recommended_action_invalid")
        require_text("cognitive_work_rationale", self.rationale)
        require_refs("cognitive_work_semantic_evidence_refs", self.evidence_refs)

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "evidence_refs": list(self.evidence_refs)}


@dataclass(frozen=True)
class CognitiveWorkControlDecision:
    decision_id: str
    trajectory_id: str
    project_scope: str
    context_key: str
    action: str
    allow_additional_round: bool
    allow_organization_expansion: bool
    allow_direct_sro_reuse: bool
    retention_eligible: bool
    operator_memory_eligible: bool
    marginal_cbit_gain: float
    cognitive_efficiency: float
    cumulative_cbit_gain: float
    total_tokens: int
    total_provider_calls: int
    total_tool_calls: int
    total_latency_ms: int
    total_api_cost: float
    total_tool_cost: float
    round_count: int
    reason: str
    observation_hashes: tuple[str, ...]
    provider_receipt_hashes: tuple[str, ...]
    budget_hash: str
    kernel_authorization_ref: str
    decision_hash: str

    def __post_init__(self) -> None:
        for name in ("decision_id", "trajectory_id", "context_key", "reason"):
            require_text(f"cognitive_work_{name}", getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("cognitive_work_control_scope_invalid")
        if self.action not in COGNITIVE_WORK_ACTIONS:
            raise ValueError("cognitive_work_control_action_invalid")
        for name in (
            "allow_additional_round",
            "allow_organization_expansion",
            "allow_direct_sro_reuse",
            "retention_eligible",
            "operator_memory_eligible",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"cognitive_work_control_{name}_must_be_boolean")
        require_unit("cognitive_work_control_marginal_cbit_gain", self.marginal_cbit_gain)
        require_unit("cognitive_work_control_cumulative_cbit_gain", self.cumulative_cbit_gain)
        require_nonnegative("cognitive_work_control_efficiency", self.cognitive_efficiency)
        for name in (
            "total_tokens",
            "total_provider_calls",
            "total_tool_calls",
            "total_latency_ms",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"cognitive_work_control_{name}_invalid")
        for name in ("total_api_cost", "total_tool_cost"):
            require_nonnegative(f"cognitive_work_control_{name}", getattr(self, name))
        if not isinstance(self.round_count, int) or isinstance(self.round_count, bool) or self.round_count < 1:
            raise ValueError("cognitive_work_control_round_count_invalid")
        if not self.kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("cognitive_work_kernel_authorization_required")
        if not self.observation_hashes or len(self.observation_hashes) != self.round_count:
            raise ValueError("cognitive_work_control_observation_lineage_invalid")
        if len(self.provider_receipt_hashes) != self.round_count:
            raise ValueError("cognitive_work_control_provider_lineage_invalid")
        for name, values in (
            ("observation", self.observation_hashes),
            ("provider_receipt", self.provider_receipt_hashes),
        ):
            if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in values):
                raise ValueError(f"cognitive_work_control_{name}_hash_invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", self.budget_hash):
            raise ValueError("cognitive_work_control_budget_hash_invalid")
        if self.allow_additional_round != (self.action in {"CONTINUE", "REORGANIZE", "ESCALATE"}):
            raise ValueError("cognitive_work_control_round_authority_inconsistent")
        if self.allow_organization_expansion != (self.action in {"CONTINUE", "REORGANIZE"}):
            raise ValueError("cognitive_work_control_expansion_authority_inconsistent")
        sufficient = self.action == "STOP_SUFFICIENT"
        if (self.allow_direct_sro_reuse or self.retention_eligible or self.operator_memory_eligible) and not sufficient:
            raise ValueError("cognitive_work_control_promotion_authority_inconsistent")
        if self.operator_memory_eligible and (not self.retention_eligible or self.round_count < 2):
            raise ValueError("cognitive_work_control_operator_memory_authority_invalid")
        if self.decision_hash != hash_payload(self._committed_dict()):
            raise ValueError("cognitive_work_control_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "CognitiveWorkControlDecision":
        committed = {
            **values,
            "observation_hashes": list(values["observation_hashes"]),
            "provider_receipt_hashes": list(values["provider_receipt_hashes"]),
        }
        return cls(**values, decision_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key != "decision_hash"},
            "observation_hashes": list(self.observation_hashes),
            "provider_receipt_hashes": list(self.provider_receipt_hashes),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "decision_hash": self.decision_hash,
            "global_policy_authority": False,
            "production_activation": False,
        }

    @property
    def evidence_ref(self) -> str:
        return f"cognitive-work://{self.decision_hash}"


def validate_control_binding(
    control: CognitiveWorkControlDecision,
    *,
    project_scope: str,
    context_key: str = "",
) -> None:
    if control.project_scope != project_scope:
        raise ValueError("cognitive_work_control_scope_mismatch")
    if context_key and control.context_key != context_key:
        raise ValueError("cognitive_work_control_context_mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", control.decision_hash):
        raise ValueError("cognitive_work_control_hash_invalid")
