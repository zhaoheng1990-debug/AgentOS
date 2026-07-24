"""Capability-conditioned agent binding contracts for organization evolution."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .agent_registry import AgentDescriptor


ORGANIZATION_CAPABILITY_BINDING_VERSION = "organization_capability_binding_v0_1"
CAPABILITY_BINDING_MODES = {"SUPPORTED", "EXPLORATORY_TRIAL_ONLY", "BLOCKED"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def capability_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _unit(name: str, value: float) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name}_invalid")
    return float(value)


@dataclass(frozen=True)
class OrganizationAgentBinding:
    role_id: str
    agent_id: str
    capabilities: tuple[str, ...]
    runner_id: str
    harness_id: str
    provider_id: str
    model_id: str
    context_isolation_key: str
    allowed_evidence_scopes: tuple[str, ...]
    binding_hash: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.role_id,
                self.agent_id,
                self.capabilities,
                self.runner_id,
                self.harness_id,
                self.provider_id,
                self.context_isolation_key,
                self.allowed_evidence_scopes,
            )
        ):
            raise ValueError("organization_agent_binding_fields_required")
        if len(self.capabilities) != len(set(self.capabilities)):
            raise ValueError("organization_agent_binding_capabilities_duplicate")
        if self.binding_hash != capability_hash(self._commitment()):
            raise ValueError("organization_agent_binding_hash_invalid")

    @classmethod
    def from_descriptor(cls, descriptor: AgentDescriptor) -> "OrganizationAgentBinding":
        committed = {
            "role_id": descriptor.role,
            "agent_id": descriptor.agent_id,
            "capabilities": list(descriptor.capabilities),
            "runner_id": descriptor.runner_id,
            "harness_id": descriptor.harness_id,
            "provider_id": descriptor.provider_id,
            "model_id": descriptor.model_id,
            "context_isolation_key": descriptor.context_isolation_key,
            "allowed_evidence_scopes": list(descriptor.allowed_evidence_scopes),
        }
        return cls(
            role_id=descriptor.role,
            agent_id=descriptor.agent_id,
            capabilities=descriptor.capabilities,
            runner_id=descriptor.runner_id,
            harness_id=descriptor.harness_id,
            provider_id=descriptor.provider_id,
            model_id=descriptor.model_id,
            context_isolation_key=descriptor.context_isolation_key,
            allowed_evidence_scopes=descriptor.allowed_evidence_scopes,
            binding_hash=capability_hash(committed),
        )

    def _commitment(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "agent_id": self.agent_id,
            "capabilities": list(self.capabilities),
            "runner_id": self.runner_id,
            "harness_id": self.harness_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "context_isolation_key": self.context_isolation_key,
            "allowed_evidence_scopes": list(self.allowed_evidence_scopes),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "binding_hash": self.binding_hash}


@dataclass(frozen=True)
class AgentCapabilityEvidence:
    evidence_id: str
    project_scope: str
    context_key: str
    evidence_tier: str
    agent_id: str
    role_id: str
    required_capabilities: tuple[str, ...]
    independent_trials: int
    mean_effectiveness: float
    mean_observed_cbit: float
    mean_normalized_cost: float
    replay_valid: bool
    evidence_refs: tuple[str, ...]
    evidence_hash: str

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.project_scope.startswith("project://") or not self.context_key:
            raise ValueError("agent_capability_evidence_identity_invalid")
        if not self.agent_id or not self.role_id or not self.evidence_tier:
            raise ValueError("agent_capability_evidence_binding_invalid")
        if not isinstance(self.independent_trials, int) or isinstance(self.independent_trials, bool) or self.independent_trials < 1:
            raise ValueError("agent_capability_evidence_trials_invalid")
        _unit("agent_capability_evidence_effectiveness", self.mean_effectiveness)
        if not -1.0 <= float(self.mean_observed_cbit) <= 1.0:
            raise ValueError("agent_capability_evidence_cbit_invalid")
        if not math.isfinite(float(self.mean_normalized_cost)) or self.mean_normalized_cost < 0:
            raise ValueError("agent_capability_evidence_cost_invalid")
        if not self.evidence_refs or len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("agent_capability_evidence_refs_invalid")
        if self.evidence_hash != capability_hash(self._commitment()):
            raise ValueError("agent_capability_evidence_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "AgentCapabilityEvidence":
        committed = dict(values)
        committed["required_capabilities"] = list(committed["required_capabilities"])
        committed["evidence_refs"] = list(committed["evidence_refs"])
        return cls(**values, evidence_hash=capability_hash(committed))

    def _commitment(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "project_scope": self.project_scope,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "agent_id": self.agent_id,
            "role_id": self.role_id,
            "required_capabilities": list(self.required_capabilities),
            "independent_trials": self.independent_trials,
            "mean_effectiveness": self.mean_effectiveness,
            "mean_observed_cbit": self.mean_observed_cbit,
            "mean_normalized_cost": self.mean_normalized_cost,
            "replay_valid": self.replay_valid,
            "evidence_refs": list(self.evidence_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "evidence_hash": self.evidence_hash}


@dataclass(frozen=True)
class OrganizationCapabilityPolicy:
    minimum_independent_trials: int = 2
    allow_exploratory_rebinding: bool = True
    require_distinct_agents: bool = True
    require_distinct_contexts: bool = True
    require_distinct_providers: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.minimum_independent_trials, int)
            or isinstance(self.minimum_independent_trials, bool)
            or self.minimum_independent_trials < 1
        ):
            raise ValueError("organization_capability_minimum_trials_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {
            "minimum_independent_trials": self.minimum_independent_trials,
            "allow_exploratory_rebinding": self.allow_exploratory_rebinding,
            "require_distinct_agents": self.require_distinct_agents,
            "require_distinct_contexts": self.require_distinct_contexts,
            "require_distinct_providers": self.require_distinct_providers,
        }


@dataclass(frozen=True)
class OrganizationCapabilityBindingReceipt:
    genome_hash: str
    mode: str
    binding_hashes: tuple[str, ...]
    capability_evidence_hashes: tuple[str, ...]
    failures: tuple[str, ...]
    receipt_hash: str

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.genome_hash) or self.mode not in CAPABILITY_BINDING_MODES:
            raise ValueError("organization_capability_receipt_identity_invalid")
        if self.mode == "BLOCKED" and not self.failures:
            raise ValueError("organization_capability_blocked_failures_required")
        if self.mode != "BLOCKED" and self.failures:
            raise ValueError("organization_capability_pass_failures_forbidden")
        if self.receipt_hash != capability_hash(self._commitment()):
            raise ValueError("organization_capability_receipt_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationCapabilityBindingReceipt":
        committed = dict(values)
        for name in ("binding_hashes", "capability_evidence_hashes", "failures"):
            committed[name] = list(committed[name])
        return cls(**values, receipt_hash=capability_hash(committed))

    def _commitment(self) -> dict[str, Any]:
        return {
            "genome_hash": self.genome_hash,
            "mode": self.mode,
            "binding_hashes": list(self.binding_hashes),
            "capability_evidence_hashes": list(self.capability_evidence_hashes),
            "failures": list(self.failures),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "receipt_hash": self.receipt_hash}
