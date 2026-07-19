"""Pure outcome and execution-footprint contracts for selection feedback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contextual_policy_evidence import CONTEXTUAL_POLICY_COMPARATORS
from .contextual_policy_models import (
    CONTEXTUAL_POLICY_ROLE_MAP,
    hash_payload,
    require_refs,
    require_text,
    require_unit,
)
from .selection_execution_models import _SHA256, _require_id, _require_nonnegative_int


@dataclass(frozen=True)
class PolicyExecutionOutcome:
    outcome_id: str
    protocol_id: str
    agent_ids: tuple[str, ...]
    roles: tuple[str, ...]
    agent_binding_hash: str
    project_scope: str
    context_key: str
    evidence_tier: str
    trial_group_id: str
    trial_id: str
    trial_surface_hash: str
    evidence_refs: tuple[str, ...]
    effectiveness_score: float
    observed_cbit_gain: float
    normalized_cost: float
    provider_call_count: int
    convergence_steps: int
    errors_exposed: int
    errors_corrected: int
    negative_transfer_opportunities: int
    negative_transfer_intercepts: int
    harness_receipt_ref: str
    harness_receipt_hash: str
    execution_result_hash: str
    source_result_hash: str
    replay_valid: bool
    outcome_hash: str

    def __post_init__(self) -> None:
        _require_id("policy_execution_outcome_id", self.outcome_id)
        if self.protocol_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("policy_execution_outcome_protocol_invalid")
        if self.roles != CONTEXTUAL_POLICY_ROLE_MAP[self.protocol_id]:
            raise ValueError("policy_execution_outcome_roles_invalid")
        if len(self.agent_ids) != len(self.roles) or len(self.agent_ids) != len(set(self.agent_ids)):
            raise ValueError("policy_execution_outcome_assignment_invalid")
        if not self.project_scope.startswith("project://"):
            raise ValueError("policy_execution_outcome_scope_invalid")
        for name in ("context_key", "evidence_tier", "harness_receipt_ref"):
            require_text(f"policy_execution_outcome_{name}", getattr(self, name))
        for name in ("trial_group_id", "trial_id"):
            _require_id(f"policy_execution_outcome_{name}", getattr(self, name))
        require_refs("policy_execution_outcome_evidence_refs", self.evidence_refs)
        for name in ("effectiveness_score", "observed_cbit_gain", "normalized_cost"):
            require_unit(f"policy_execution_outcome_{name}", getattr(self, name))
        for name in (
            "convergence_steps",
            "provider_call_count",
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
        ):
            _require_nonnegative_int(f"policy_execution_outcome_{name}", getattr(self, name))
        if self.convergence_steps < 1:
            raise ValueError("policy_execution_outcome_convergence_required")
        if self.errors_corrected > self.errors_exposed:
            raise ValueError("policy_execution_outcome_error_counts_invalid")
        if self.negative_transfer_intercepts > self.negative_transfer_opportunities:
            raise ValueError("policy_execution_outcome_transfer_counts_invalid")
        for name in (
            "trial_surface_hash",
            "agent_binding_hash",
            "harness_receipt_hash",
            "execution_result_hash",
            "source_result_hash",
            "outcome_hash",
        ):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise ValueError(f"policy_execution_outcome_{name}_invalid")
        if self.replay_valid is not True:
            raise ValueError("policy_execution_outcome_replay_required")
        if self.outcome_hash != hash_payload(self._committed_dict()):
            raise ValueError("policy_execution_outcome_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "PolicyExecutionOutcome":
        committed = {
            **values,
            "agent_ids": list(values["agent_ids"]),
            "roles": list(values["roles"]),
            "evidence_refs": list(values["evidence_refs"]),
        }
        return cls(**values, outcome_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "protocol_id": self.protocol_id,
            "agent_ids": list(self.agent_ids),
            "roles": list(self.roles),
            "agent_binding_hash": self.agent_binding_hash,
            "project_scope": self.project_scope,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "trial_group_id": self.trial_group_id,
            "trial_id": self.trial_id,
            "trial_surface_hash": self.trial_surface_hash,
            "evidence_refs": list(self.evidence_refs),
            "effectiveness_score": self.effectiveness_score,
            "observed_cbit_gain": self.observed_cbit_gain,
            "normalized_cost": self.normalized_cost,
            "provider_call_count": self.provider_call_count,
            "convergence_steps": self.convergence_steps,
            "errors_exposed": self.errors_exposed,
            "errors_corrected": self.errors_corrected,
            "negative_transfer_opportunities": self.negative_transfer_opportunities,
            "negative_transfer_intercepts": self.negative_transfer_intercepts,
            "harness_receipt_ref": self.harness_receipt_ref,
            "harness_receipt_hash": self.harness_receipt_hash,
            "execution_result_hash": self.execution_result_hash,
            "source_result_hash": self.source_result_hash,
            "replay_valid": self.replay_valid,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "outcome_hash": self.outcome_hash}


@dataclass(frozen=True)
class ExecutedProtocolFootprint:
    protocol_id: str
    provider_call_count: int
    normalized_cost: float
    execution_result_hash: str
    harness_receipt_hash: str
    footprint_hash: str

    def __post_init__(self) -> None:
        if self.protocol_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("executed_protocol_footprint_protocol_invalid")
        _require_nonnegative_int(
            "executed_protocol_footprint_provider_call_count", self.provider_call_count
        )
        require_unit("executed_protocol_footprint_normalized_cost", self.normalized_cost)
        for name in ("execution_result_hash", "harness_receipt_hash", "footprint_hash"):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise ValueError(f"executed_protocol_footprint_{name}_invalid")
        if self.footprint_hash != hash_payload(self._committed_dict()):
            raise ValueError("executed_protocol_footprint_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ExecutedProtocolFootprint":
        return cls(**values, footprint_hash=hash_payload(values))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "provider_call_count": self.provider_call_count,
            "normalized_cost": self.normalized_cost,
            "execution_result_hash": self.execution_result_hash,
            "harness_receipt_hash": self.harness_receipt_hash,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "footprint_hash": self.footprint_hash}


@dataclass(frozen=True)
class PolicyExecutionBundle:
    bridge_run_id: str
    selection_receipt_hash: str
    selected_policy_id: str
    execution_adapter_id: str
    outcomes: tuple[PolicyExecutionOutcome, ...]
    executed_protocols: tuple[ExecutedProtocolFootprint, ...]
    execution_replay: dict[str, Any]
    bundle_hash: str

    def __post_init__(self) -> None:
        _require_id("policy_execution_bundle_run_id", self.bridge_run_id)
        require_text("policy_execution_adapter_id", self.execution_adapter_id)
        if self.selected_policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("policy_execution_bundle_selected_policy_invalid")
        protocols = tuple(item.protocol_id for item in self.outcomes)
        required = {self.selected_policy_id, CONTEXTUAL_POLICY_COMPARATORS[self.selected_policy_id]}
        if len(protocols) != len(set(protocols)) or set(protocols) != required:
            raise ValueError("policy_execution_bundle_protocol_surface_invalid")
        executed_ids = self.executed_protocol_ids
        if (
            not executed_ids
            or len(executed_ids) != len(set(executed_ids))
            or not required.issubset(executed_ids)
        ):
            raise ValueError("policy_execution_bundle_executed_protocols_invalid")
        footprints = {item.protocol_id: item for item in self.executed_protocols}
        for outcome in self.outcomes:
            footprint = footprints[outcome.protocol_id]
            if (
                footprint.provider_call_count != outcome.provider_call_count
                or footprint.normalized_cost != outcome.normalized_cost
                or footprint.execution_result_hash != outcome.execution_result_hash
                or footprint.harness_receipt_hash != outcome.harness_receipt_hash
            ):
                raise ValueError("policy_execution_bundle_outcome_footprint_mismatch")
        if not self.execution_replay.get("valid"):
            raise ValueError("policy_execution_bundle_replay_invalid")
        if len({item.source_result_hash for item in self.outcomes}) != 1:
            raise ValueError("policy_execution_bundle_source_surface_mismatch")
        if len({item.trial_surface_hash for item in self.outcomes}) != 1:
            raise ValueError("policy_execution_bundle_trial_surface_mismatch")
        if len({item.evidence_refs for item in self.outcomes}) != 1:
            raise ValueError("policy_execution_bundle_evidence_surface_mismatch")
        if not _SHA256.fullmatch(self.selection_receipt_hash):
            raise ValueError("policy_execution_bundle_selection_hash_invalid")
        if self.bundle_hash != hash_payload(self._committed_dict()):
            raise ValueError("policy_execution_bundle_hash_mismatch")

    @property
    def executed_protocol_ids(self) -> tuple[str, ...]:
        return tuple(item.protocol_id for item in self.executed_protocols)

    @property
    def total_provider_call_count(self) -> int:
        return sum(item.provider_call_count for item in self.executed_protocols)

    @classmethod
    def create(
        cls,
        *,
        bridge_run_id: str,
        selection_receipt_hash: str,
        selected_policy_id: str,
        execution_adapter_id: str,
        outcomes: tuple[PolicyExecutionOutcome, ...],
        executed_protocols: tuple[ExecutedProtocolFootprint, ...],
        execution_replay: dict[str, Any],
    ) -> "PolicyExecutionBundle":
        committed = {
            "bridge_run_id": bridge_run_id,
            "selection_receipt_hash": selection_receipt_hash,
            "selected_policy_id": selected_policy_id,
            "execution_adapter_id": execution_adapter_id,
            "outcomes": [item.as_dict() for item in outcomes],
            "executed_protocols": [item.as_dict() for item in executed_protocols],
            "execution_replay": execution_replay,
        }
        return cls(
            bridge_run_id=bridge_run_id,
            selection_receipt_hash=selection_receipt_hash,
            selected_policy_id=selected_policy_id,
            execution_adapter_id=execution_adapter_id,
            outcomes=outcomes,
            executed_protocols=executed_protocols,
            execution_replay=execution_replay,
            bundle_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "bridge_run_id": self.bridge_run_id,
            "selection_receipt_hash": self.selection_receipt_hash,
            "selected_policy_id": self.selected_policy_id,
            "execution_adapter_id": self.execution_adapter_id,
            "outcomes": [item.as_dict() for item in self.outcomes],
            "executed_protocols": [item.as_dict() for item in self.executed_protocols],
            "execution_replay": self.execution_replay,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "bundle_hash": self.bundle_hash}
