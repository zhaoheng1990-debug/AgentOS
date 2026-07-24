"""Pure contracts for bounded cognitive-organization evolution."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .organization_capability_models import OrganizationAgentBinding


ORGANIZATION_EVOLUTION_VERSION = "organization_evolution_v0_1"
ORGANIZATION_EVOLUTION_OPERATOR_IDS = (
    "ADD_ROLE",
    "REMOVE_ROLE",
    "ADD_EDGE",
    "REMOVE_EDGE",
    "SPECIALIZE_ROLE",
    "REBIND_ROLE_AGENT",
)
ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES = {
    "ADD_ROLE": "EXPLORATION",
    "ADD_EDGE": "EXPLORATION",
    "REMOVE_ROLE": "EXPLOITATION",
    "REMOVE_EDGE": "EXPLOITATION",
    "SPECIALIZE_ROLE": "EXPLOITATION",
    "REBIND_ROLE_AGENT": "EXPLORATION",
}

_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def organization_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require_id(name: str, value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name}_invalid")
    return value


def _require_refs(name: str, refs: tuple[str, ...]) -> tuple[str, ...]:
    if not refs or len(refs) != len(set(refs)) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError(f"{name}_invalid")
    return refs


def _require_nonnegative(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{name}_invalid")
    return float(value)


@dataclass(frozen=True)
class OrganizationEvolutionTask:
    task_id: str
    stage_id: str
    project_scope: str
    context_key: str
    objective: str
    evidence_refs: tuple[str, ...]
    anchor_task_ids: tuple[str, ...]
    task_hash: str

    def __post_init__(self) -> None:
        _require_id("organization_evolution_task_id", self.task_id)
        _require_id("organization_evolution_stage_id", self.stage_id)
        if not self.project_scope.startswith("project://"):
            raise ValueError("organization_evolution_project_scope_invalid")
        if not self.context_key or not self.objective.strip():
            raise ValueError("organization_evolution_task_text_invalid")
        _require_refs("organization_evolution_task_evidence_refs", self.evidence_refs)
        if len(self.anchor_task_ids) != len(set(self.anchor_task_ids)):
            raise ValueError("organization_evolution_anchor_task_ids_invalid")
        for anchor in self.anchor_task_ids:
            _require_id("organization_evolution_anchor_task_id", anchor)
        if self.task_hash != organization_hash(self._commitment()):
            raise ValueError("organization_evolution_task_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationEvolutionTask":
        committed = dict(values)
        committed["evidence_refs"] = list(committed["evidence_refs"])
        committed["anchor_task_ids"] = list(committed.get("anchor_task_ids", ()))
        return cls(**values, task_hash=organization_hash(committed))

    def _commitment(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "stage_id": self.stage_id,
            "project_scope": self.project_scope,
            "context_key": self.context_key,
            "objective": self.objective,
            "evidence_refs": list(self.evidence_refs),
            "anchor_task_ids": list(self.anchor_task_ids),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "task_hash": self.task_hash}


@dataclass(frozen=True)
class OrganizationRole:
    role_id: str
    contract_id: str

    def __post_init__(self) -> None:
        _require_id("organization_role_id", self.role_id)
        _require_id("organization_role_contract_id", self.contract_id)

    def as_dict(self) -> dict[str, str]:
        return {"role_id": self.role_id, "contract_id": self.contract_id}


@dataclass(frozen=True)
class OrganizationEdge:
    source_role: str
    target_role: str
    channel: str = "PUBLIC_RECEIPT"

    def __post_init__(self) -> None:
        _require_id("organization_edge_source", self.source_role)
        _require_id("organization_edge_target", self.target_role)
        _require_id("organization_edge_channel", self.channel)
        if self.source_role == self.target_role:
            raise ValueError("organization_edge_self_loop_forbidden")

    def as_dict(self) -> dict[str, str]:
        return {
            "source_role": self.source_role,
            "target_role": self.target_role,
            "channel": self.channel,
        }


@dataclass(frozen=True)
class OrganizationGenome:
    genome_id: str
    task_hash: str
    roles: tuple[OrganizationRole, ...]
    edges: tuple[OrganizationEdge, ...]
    max_rounds: int
    stop_policy: str
    generation: int
    parent_genome_hash: str
    mutation_operator_id: str
    mutation_proposal_hash: str
    genome_hash: str
    agent_bindings: tuple[OrganizationAgentBinding, ...] = ()

    def __post_init__(self) -> None:
        _require_id("organization_genome_id", self.genome_id)
        if not _SHA256.fullmatch(self.task_hash):
            raise ValueError("organization_genome_task_hash_invalid")
        if not self.roles or len({item.role_id for item in self.roles}) != len(self.roles):
            raise ValueError("organization_genome_roles_invalid")
        if len({tuple(item.as_dict().values()) for item in self.edges}) != len(self.edges):
            raise ValueError("organization_genome_edges_duplicate")
        role_ids = {item.role_id for item in self.roles}
        if any(edge.source_role not in role_ids or edge.target_role not in role_ids for edge in self.edges):
            raise ValueError("organization_genome_edge_role_unknown")
        if self.agent_bindings:
            binding_roles = [item.role_id for item in self.agent_bindings]
            if len(binding_roles) != len(set(binding_roles)) or set(binding_roles) != role_ids:
                raise ValueError("organization_genome_agent_bindings_invalid")
        if not isinstance(self.max_rounds, int) or isinstance(self.max_rounds, bool) or self.max_rounds < 1:
            raise ValueError("organization_genome_max_rounds_invalid")
        _require_id("organization_genome_stop_policy", self.stop_policy)
        if not isinstance(self.generation, int) or isinstance(self.generation, bool) or self.generation < 0:
            raise ValueError("organization_genome_generation_invalid")
        if self.generation == 0:
            if self.parent_genome_hash or self.mutation_operator_id or self.mutation_proposal_hash:
                raise ValueError("organization_baseline_lineage_invalid")
        else:
            if not _SHA256.fullmatch(self.parent_genome_hash):
                raise ValueError("organization_genome_parent_hash_invalid")
            if self.mutation_operator_id not in ORGANIZATION_EVOLUTION_OPERATOR_IDS:
                raise ValueError("organization_genome_operator_invalid")
            if not _SHA256.fullmatch(self.mutation_proposal_hash):
                raise ValueError("organization_genome_proposal_hash_invalid")
        if self.genome_hash != organization_hash(self._commitment()):
            raise ValueError("organization_genome_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationGenome":
        committed = dict(values)
        bindings = tuple(committed.get("agent_bindings", ()))
        values["agent_bindings"] = bindings
        committed["roles"] = [item.as_dict() for item in committed["roles"]]
        committed["edges"] = [item.as_dict() for item in committed["edges"]]
        if bindings:
            committed["agent_bindings"] = [item.as_dict() for item in bindings]
        else:
            committed.pop("agent_bindings", None)
        return cls(**values, genome_hash=organization_hash(committed))

    def _commitment(self) -> dict[str, Any]:
        commitment = {
            "genome_id": self.genome_id,
            "task_hash": self.task_hash,
            "roles": [item.as_dict() for item in self.roles],
            "edges": [item.as_dict() for item in self.edges],
            "max_rounds": self.max_rounds,
            "stop_policy": self.stop_policy,
            "generation": self.generation,
            "parent_genome_hash": self.parent_genome_hash,
            "mutation_operator_id": self.mutation_operator_id,
            "mutation_proposal_hash": self.mutation_proposal_hash,
        }
        if self.agent_bindings:
            commitment["agent_bindings"] = [item.as_dict() for item in self.agent_bindings]
        return commitment

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "genome_hash": self.genome_hash}


@dataclass(frozen=True)
class OrganizationEvolutionBudget:
    max_generations: int
    max_candidates_per_generation: int
    max_roles: int
    max_edges: int
    max_provider_calls: int
    max_normalized_cost: float
    patience_generations: int = 2

    def __post_init__(self) -> None:
        for name in (
            "max_generations",
            "max_candidates_per_generation",
            "max_roles",
            "max_provider_calls",
            "patience_generations",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"organization_evolution_{name}_invalid")
        if not isinstance(self.max_edges, int) or isinstance(self.max_edges, bool) or self.max_edges < 0:
            raise ValueError("organization_evolution_max_edges_invalid")
        _require_nonnegative("organization_evolution_max_normalized_cost", self.max_normalized_cost)

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_generations": self.max_generations,
            "max_candidates_per_generation": self.max_candidates_per_generation,
            "max_roles": self.max_roles,
            "max_edges": self.max_edges,
            "max_provider_calls": self.max_provider_calls,
            "max_normalized_cost": self.max_normalized_cost,
            "patience_generations": self.patience_generations,
        }


@dataclass(frozen=True)
class OrganizationMutationProposal:
    proposal_id: str
    parent_genome_hash: str
    operator_id: str
    parameters: dict[str, Any]
    rationale: str
    evidence_refs: tuple[str, ...]
    provider_invocation_receipt: dict[str, Any]
    proposal_hash: str

    def __post_init__(self) -> None:
        _require_id("organization_mutation_proposal_id", self.proposal_id)
        if not _SHA256.fullmatch(self.parent_genome_hash):
            raise ValueError("organization_mutation_parent_hash_invalid")
        if self.operator_id not in ORGANIZATION_EVOLUTION_OPERATOR_IDS:
            raise ValueError("organization_mutation_operator_invalid")
        if not isinstance(self.parameters, dict) or not self.parameters:
            raise ValueError("organization_mutation_parameters_invalid")
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise ValueError("organization_mutation_rationale_invalid")
        _require_refs("organization_mutation_evidence_refs", self.evidence_refs)
        if not isinstance(self.provider_invocation_receipt, dict) or not self.provider_invocation_receipt.get(
            "receipt_hash"
        ):
            raise ValueError("organization_mutation_provider_receipt_invalid")
        if self.proposal_hash != organization_hash(self._commitment()):
            raise ValueError("organization_mutation_proposal_hash_invalid")

    @classmethod
    def create(cls, **values: Any) -> "OrganizationMutationProposal":
        committed = dict(values)
        committed["evidence_refs"] = list(committed["evidence_refs"])
        return cls(**values, proposal_hash=organization_hash(committed))

    def _commitment(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "parent_genome_hash": self.parent_genome_hash,
            "operator_id": self.operator_id,
            "parameters": self.parameters,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "provider_invocation_receipt": self.provider_invocation_receipt,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._commitment(), "proposal_hash": self.proposal_hash}
