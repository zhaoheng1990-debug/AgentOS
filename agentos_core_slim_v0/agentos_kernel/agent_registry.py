"""Registry and isolation contracts for plural cognitive agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


AGENT_REGISTRY_VERSION = "cognitive_agent_registry_v0_1"

AGENT_ROLES = {
    "HYPOTHESIS_GENERATOR",
    "ADVERSARIAL_REVIEWER",
    "REPLICATOR",
    "SYNTHESIZER",
    "AGENDA_SCOUT",
}


@dataclass(frozen=True)
class AgentDescriptor:
    agent_id: str
    role: str
    capabilities: tuple[str, ...]
    runner_id: str
    harness_id: str
    provider_id: str
    context_isolation_key: str
    allowed_evidence_scopes: tuple[str, ...]
    enabled: bool = True
    provider_support_mode: str = "required"

    def __post_init__(self) -> None:
        if self.role not in AGENT_ROLES:
            raise ValueError(f"unknown_agent_role:{self.role}")
        if not all(
            (
                self.agent_id,
                self.runner_id,
                self.harness_id,
                self.provider_id,
                self.context_isolation_key,
            )
        ):
            raise ValueError("agent_runtime_binding_required")
        if not self.capabilities:
            raise ValueError("agent_capabilities_required")
        if not self.allowed_evidence_scopes:
            raise ValueError("agent_evidence_scope_required")
        if self.provider_support_mode != "required":
            raise ValueError("cognitive_agent_provider_support_must_be_required")


@dataclass(frozen=True)
class AgentRoleRequirement:
    role: str
    required_capabilities: tuple[str, ...] = ()
    require_distinct_provider: bool = False

    def __post_init__(self) -> None:
        if self.role not in AGENT_ROLES:
            raise ValueError(f"unknown_agent_role:{self.role}")


@dataclass(frozen=True)
class EnsembleAssignment:
    team_id: str
    agents: tuple[AgentDescriptor, ...]
    context_isolated: bool
    execution_authorized: bool = False

    def by_role(self, role: str) -> AgentDescriptor:
        for agent in self.agents:
            if agent.role == role:
                return agent
        raise KeyError(f"role_not_assigned:{role}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "agents": [
                {
                    "agent_id": agent.agent_id,
                    "role": agent.role,
                    "capabilities": list(agent.capabilities),
                    "runner_id": agent.runner_id,
                    "harness_id": agent.harness_id,
                    "provider_id": agent.provider_id,
                    "context_isolation_key": agent.context_isolation_key,
                    "allowed_evidence_scopes": list(agent.allowed_evidence_scopes),
                }
                for agent in self.agents
            ],
            "context_isolated": self.context_isolated,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class AgentWorkOrder:
    work_order_id: str
    agent_id: str
    role: str
    objective: str
    input_receipt_refs: tuple[str, ...]
    output_schema: dict[str, Any]
    scope: str
    provider_required: bool = True


class AgentRuntimeAdapter(Protocol):
    """Pluggable runner/Harness execution boundary used outside the registry."""

    adapter_id: str

    def invoke(self, agent: AgentDescriptor, work_order: AgentWorkOrder) -> dict[str, Any]:
        """Return an execution receipt; final epistemic state remains Kernel-owned."""


class AgentRegistry:
    """P3 discovery and isolated-team assembly without execution authority."""

    module_id = AGENT_REGISTRY_VERSION
    capabilities = ("agent_registration", "role_discovery", "isolated_team_assembly")

    def __init__(self) -> None:
        self._agents: dict[str, AgentDescriptor] = {}

    def register(self, descriptor: AgentDescriptor) -> None:
        if descriptor.agent_id in self._agents:
            raise ValueError(f"duplicate_agent_id:{descriptor.agent_id}")
        self._agents[descriptor.agent_id] = descriptor

    def replace(self, descriptor: AgentDescriptor) -> None:
        if descriptor.agent_id not in self._agents:
            raise KeyError(f"agent_not_registered:{descriptor.agent_id}")
        self._agents[descriptor.agent_id] = descriptor

    def get(self, agent_id: str) -> AgentDescriptor:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"agent_not_registered:{agent_id}") from exc

    def candidates(self, requirement: AgentRoleRequirement) -> tuple[AgentDescriptor, ...]:
        required = set(requirement.required_capabilities)
        return tuple(
            agent
            for agent in self._agents.values()
            if agent.enabled and agent.role == requirement.role and required.issubset(agent.capabilities)
        )

    def form_team(
        self,
        team_id: str,
        requirements: tuple[AgentRoleRequirement, ...],
    ) -> EnsembleAssignment:
        if not team_id:
            raise ValueError("team_id_required")
        if not requirements:
            raise ValueError("team_requirements_required")
        roles = [requirement.role for requirement in requirements]
        if len(set(roles)) != len(roles):
            raise ValueError("duplicate_team_role_requirement")

        assignment = self._search(requirements, 0, (), set(), set(), set(), set())
        if assignment is None:
            raise ValueError("no_context_isolated_team_satisfies_requirements")
        return EnsembleAssignment(team_id=team_id, agents=assignment, context_isolated=True)

    def _search(
        self,
        requirements: tuple[AgentRoleRequirement, ...],
        index: int,
        selected: tuple[AgentDescriptor, ...],
        used_agent_ids: set[str],
        used_contexts: set[str],
        used_providers: set[str],
        exclusive_providers: set[str],
    ) -> tuple[AgentDescriptor, ...] | None:
        if index == len(requirements):
            return selected
        requirement = requirements[index]
        for agent in self.candidates(requirement):
            if agent.agent_id in used_agent_ids or agent.context_isolation_key in used_contexts:
                continue
            if agent.provider_id in exclusive_providers:
                continue
            if requirement.require_distinct_provider and agent.provider_id in used_providers:
                continue
            result = self._search(
                requirements,
                index + 1,
                (*selected, agent),
                used_agent_ids | {agent.agent_id},
                used_contexts | {agent.context_isolation_key},
                used_providers | {agent.provider_id},
                exclusive_providers | ({agent.provider_id} if requirement.require_distinct_provider else set()),
            )
            if result is not None:
                return result
        return None
