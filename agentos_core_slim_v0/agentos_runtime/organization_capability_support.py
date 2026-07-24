"""Capability-binding support for the Organization Evolution facade."""

from __future__ import annotations

from agentos_kernel.agent_registry import AgentRegistry
from agentos_kernel.organization_capability_gate import OrganizationCapabilityBindingGate
from agentos_kernel.organization_capability_models import (
    AgentCapabilityEvidence,
    OrganizationCapabilityBindingReceipt,
    OrganizationCapabilityPolicy,
)
from agentos_kernel.organization_evolution_models import OrganizationEvolutionTask, OrganizationGenome


class OrganizationCapabilityRuntimeSupport:
    """Own capability evidence and binding gates outside the orchestration facade."""

    def __init__(
        self,
        *,
        agent_registry: AgentRegistry,
        role_contract_capabilities: dict[str, tuple[str, ...]],
        evidence: tuple[AgentCapabilityEvidence, ...] = (),
        policy: OrganizationCapabilityPolicy | None = None,
        gate: OrganizationCapabilityBindingGate | None = None,
    ) -> None:
        self.registry = agent_registry
        self.role_contract_capabilities = role_contract_capabilities
        self.evidence = evidence
        self.policy = policy or OrganizationCapabilityPolicy()
        self.gate = gate or OrganizationCapabilityBindingGate()

    def evaluate(
        self,
        *,
        task: OrganizationEvolutionTask,
        genome: OrganizationGenome,
        incumbent: OrganizationGenome | None = None,
    ) -> OrganizationCapabilityBindingReceipt:
        return self.gate.evaluate(
            task=task,
            genome=genome,
            registry=self.registry,
            role_contract_capabilities=self.role_contract_capabilities,
            evidence=self.evidence,
            policy=self.policy,
            evidence_required_agent_ids=self.changed_agent_ids(incumbent, genome) if incumbent else (),
        )

    @staticmethod
    def changed_agent_ids(
        incumbent: OrganizationGenome, candidate: OrganizationGenome
    ) -> tuple[str, ...]:
        incumbent_by_role = {item.role_id: item.agent_id for item in incumbent.agent_bindings}
        incumbent_contracts = {item.role_id: item.contract_id for item in incumbent.roles}
        candidate_contracts = {item.role_id: item.contract_id for item in candidate.roles}
        return tuple(
            item.agent_id
            for item in candidate.agent_bindings
            if incumbent_by_role.get(item.role_id) != item.agent_id
            or incumbent_contracts.get(item.role_id) != candidate_contracts.get(item.role_id)
        )
