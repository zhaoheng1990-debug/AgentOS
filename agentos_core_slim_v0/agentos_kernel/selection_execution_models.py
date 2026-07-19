"""Pure request contracts for selected-policy execution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .contextual_policy_models import (
    CONTEXTUAL_POLICY_ROLE_MAP,
    hash_payload,
    require_refs,
    require_text,
    require_unit,
)


SELECTION_EXECUTION_FEEDBACK_VERSION = "selection_execution_feedback_kernel_v0_1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_id(name: str, value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"{name}_invalid")


def _require_nonnegative_int(name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class SelectionExecutionBudget:
    budget_ref: str
    max_protocol_runs: int
    max_provider_calls_total: int
    max_normalized_cost_per_protocol: float
    budget_hash: str

    def __post_init__(self) -> None:
        require_text("selection_execution_budget_ref", self.budget_ref)
        for name in ("max_protocol_runs", "max_provider_calls_total"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"selection_execution_budget_{name}_invalid")
        require_unit(
            "selection_execution_budget_max_normalized_cost_per_protocol",
            self.max_normalized_cost_per_protocol,
        )
        if self.budget_hash != hash_payload(self._committed_dict()):
            raise ValueError("selection_execution_budget_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        budget_ref: str,
        max_protocol_runs: int,
        max_provider_calls_total: int,
        max_normalized_cost_per_protocol: float,
    ) -> "SelectionExecutionBudget":
        committed = {
            "budget_ref": budget_ref,
            "max_protocol_runs": max_protocol_runs,
            "max_provider_calls_total": max_provider_calls_total,
            "max_normalized_cost_per_protocol": float(max_normalized_cost_per_protocol),
        }
        return cls(**committed, budget_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "budget_ref": self.budget_ref,
            "max_protocol_runs": self.max_protocol_runs,
            "max_provider_calls_total": self.max_provider_calls_total,
            "max_normalized_cost_per_protocol": self.max_normalized_cost_per_protocol,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "budget_hash": self.budget_hash}


@dataclass(frozen=True)
class SelectionExecutionRequest:
    bridge_run_id: str
    selection_receipt_hash: str
    project_scope: str
    context_key: str
    evidence_tier: str
    trial_group_id: str
    trial_id: str
    selected_policy_id: str
    selected_agent_ids: tuple[str, ...]
    selected_roles: tuple[str, ...]
    selected_agent_binding_hash: str
    trial_evidence_refs: tuple[str, ...]
    execution_budget: SelectionExecutionBudget
    kernel_execution_authorization_ref: str
    trial_surface_hash: str
    request_hash: str

    def __post_init__(self) -> None:
        for name in ("bridge_run_id", "trial_group_id", "trial_id"):
            _require_id(f"selection_execution_{name}", getattr(self, name))
        if self.selected_policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("selection_execution_policy_invalid")
        if self.selected_roles != CONTEXTUAL_POLICY_ROLE_MAP[self.selected_policy_id]:
            raise ValueError("selection_execution_role_policy_binding_invalid")
        if len(self.selected_agent_ids) != len(self.selected_roles):
            raise ValueError("selection_execution_assignment_cardinality_invalid")
        if len(self.selected_agent_ids) != len(set(self.selected_agent_ids)):
            raise ValueError("selection_execution_duplicate_agent")
        if not self.project_scope.startswith("project://"):
            raise ValueError("selection_execution_project_scope_invalid")
        require_text("selection_execution_context_key", self.context_key)
        require_text("selection_execution_evidence_tier", self.evidence_tier)
        require_refs("selection_execution_trial_evidence_refs", self.trial_evidence_refs)
        if not self.kernel_execution_authorization_ref.startswith("kernel://"):
            raise ValueError("selection_execution_kernel_authorization_required")
        for name in (
            "selection_receipt_hash",
            "selected_agent_binding_hash",
            "trial_surface_hash",
            "request_hash",
        ):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise ValueError(f"selection_execution_{name}_invalid")
        if self.trial_surface_hash != hash_payload(self._surface_dict()):
            raise ValueError("selection_execution_trial_surface_hash_mismatch")
        if self.request_hash != hash_payload(self._committed_dict()):
            raise ValueError("selection_execution_request_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        bridge_run_id: str,
        selection_receipt_hash: str,
        project_scope: str,
        context_key: str,
        evidence_tier: str,
        trial_group_id: str,
        trial_id: str,
        selected_policy_id: str,
        selected_agent_ids: tuple[str, ...],
        selected_roles: tuple[str, ...],
        selected_agent_binding_hash: str,
        trial_evidence_refs: tuple[str, ...],
        execution_budget: SelectionExecutionBudget,
        kernel_execution_authorization_ref: str,
    ) -> "SelectionExecutionRequest":
        surface = {
            "project_scope": project_scope,
            "context_key": context_key,
            "evidence_tier": evidence_tier,
            "trial_group_id": trial_group_id,
            "trial_id": trial_id,
            "trial_evidence_refs": list(trial_evidence_refs),
        }
        trial_surface_hash = hash_payload(surface)
        committed = {
            "bridge_run_id": bridge_run_id,
            "selection_receipt_hash": selection_receipt_hash,
            **surface,
            "selected_policy_id": selected_policy_id,
            "selected_agent_ids": list(selected_agent_ids),
            "selected_roles": list(selected_roles),
            "selected_agent_binding_hash": selected_agent_binding_hash,
            "execution_budget": execution_budget.as_dict(),
            "kernel_execution_authorization_ref": kernel_execution_authorization_ref,
            "trial_surface_hash": trial_surface_hash,
        }
        return cls(
            bridge_run_id=bridge_run_id,
            selection_receipt_hash=selection_receipt_hash,
            project_scope=project_scope,
            context_key=context_key,
            evidence_tier=evidence_tier,
            trial_group_id=trial_group_id,
            trial_id=trial_id,
            selected_policy_id=selected_policy_id,
            selected_agent_ids=selected_agent_ids,
            selected_roles=selected_roles,
            selected_agent_binding_hash=selected_agent_binding_hash,
            trial_evidence_refs=trial_evidence_refs,
            execution_budget=execution_budget,
            kernel_execution_authorization_ref=kernel_execution_authorization_ref,
            trial_surface_hash=trial_surface_hash,
            request_hash=hash_payload(committed),
        )

    def _surface_dict(self) -> dict[str, Any]:
        return {
            "project_scope": self.project_scope,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "trial_group_id": self.trial_group_id,
            "trial_id": self.trial_id,
            "trial_evidence_refs": list(self.trial_evidence_refs),
        }

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "bridge_run_id": self.bridge_run_id,
            "selection_receipt_hash": self.selection_receipt_hash,
            **self._surface_dict(),
            "selected_policy_id": self.selected_policy_id,
            "selected_agent_ids": list(self.selected_agent_ids),
            "selected_roles": list(self.selected_roles),
            "selected_agent_binding_hash": self.selected_agent_binding_hash,
            "execution_budget": self.execution_budget.as_dict(),
            "kernel_execution_authorization_ref": self.kernel_execution_authorization_ref,
            "trial_surface_hash": self.trial_surface_hash,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "request_hash": self.request_hash}
