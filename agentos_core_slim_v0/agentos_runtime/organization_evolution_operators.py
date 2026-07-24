"""Deterministic, bounded operators for cognitive-organization genomes."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel.agent_registry import AgentRegistry
from agentos_kernel.organization_capability_models import OrganizationAgentBinding

from agentos_kernel.organization_evolution_models import (
    ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES,
    OrganizationEvolutionBudget,
    OrganizationEdge,
    OrganizationGenome,
    OrganizationMutationProposal,
    OrganizationRole,
)


class OrganizationEvolutionOperatorRegistry:
    """Apply Provider-proposed mutations through an explicit mechanical registry."""

    def __init__(
        self,
        *,
        role_contract_catalog: dict[str, tuple[str, ...]],
        agent_registry: AgentRegistry | None = None,
        role_contract_capabilities: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        if not role_contract_catalog:
            raise ValueError("organization_evolution_role_catalog_required")
        self.role_contract_catalog = {
            role_id: tuple(dict.fromkeys(contracts)) for role_id, contracts in role_contract_catalog.items()
        }
        if any(not role_id or not contracts for role_id, contracts in self.role_contract_catalog.items()):
            raise ValueError("organization_evolution_role_catalog_invalid")
        self.agent_registry = agent_registry
        self.role_contract_capabilities = role_contract_capabilities or {}
        if agent_registry is not None:
            registered_contracts = {item for contracts in self.role_contract_catalog.values() for item in contracts}
            missing = registered_contracts - set(self.role_contract_capabilities)
            if missing:
                raise ValueError(f"organization_evolution_contract_capabilities_required:{sorted(missing)}")
        self._operators: dict[str, Callable] = {
            "ADD_ROLE": self._add_role,
            "REMOVE_ROLE": self._remove_role,
            "ADD_EDGE": self._add_edge,
            "REMOVE_EDGE": self._remove_edge,
            "SPECIALIZE_ROLE": self._specialize_role,
            "REBIND_ROLE_AGENT": self._rebind_role_agent,
        }

    def validate_genome(self, genome: OrganizationGenome) -> None:
        for role in genome.roles:
            allowed = self.role_contract_catalog.get(role.role_id)
            if allowed is None or role.contract_id not in allowed:
                raise ValueError(f"organization_evolution_role_contract_unregistered:{role.role_id}")
        if self.agent_registry is not None:
            if len(genome.agent_bindings) != len(genome.roles):
                raise ValueError("organization_evolution_registry_bindings_required")
            roles = {item.role_id: item for item in genome.roles}
            for binding in genome.agent_bindings:
                descriptor = self.agent_registry.get(binding.agent_id)
                if OrganizationAgentBinding.from_descriptor(descriptor) != binding:
                    raise ValueError("organization_evolution_registry_binding_mismatch")
                role = roles.get(binding.role_id)
                required = set(self.role_contract_capabilities.get(role.contract_id, ())) if role else set()
                if descriptor.role != binding.role_id or not descriptor.enabled or not required.issubset(descriptor.capabilities):
                    raise ValueError("organization_evolution_registry_binding_ineligible")

    def operator_surface(self, operator_ids: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
        unknown = set(operator_ids) - set(self._operators)
        if unknown:
            raise ValueError(f"organization_evolution_operator_unknown:{sorted(unknown)}")
        schemas = {
            "ADD_ROLE": {
                "required": ["role_id", "contract_id"],
                "optional": ["incoming_from_role", "outgoing_to_role", "channel", "agent_id"],
            },
            "REMOVE_ROLE": {"required": ["role_id"], "optional": []},
            "ADD_EDGE": {"required": ["source_role", "target_role"], "optional": ["channel"]},
            "REMOVE_EDGE": {"required": ["source_role", "target_role"], "optional": ["channel"]},
            "SPECIALIZE_ROLE": {"required": ["role_id", "contract_id"], "optional": []},
            "REBIND_ROLE_AGENT": {"required": ["role_id", "agent_id"], "optional": []},
        }
        return tuple(
            {
                "operator_id": operator_id,
                "family": ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES[operator_id],
                "parameter_schema": schemas[operator_id],
            }
            for operator_id in operator_ids
        )

    def applicable_operator_ids(
        self, parent: OrganizationGenome, budget: OrganizationEvolutionBudget
    ) -> tuple[str, ...]:
        role_ids = {item.role_id for item in parent.roles}
        missing_roles = set(self.role_contract_catalog) - role_ids
        possible_edges = len(role_ids) * max(0, len(role_ids) - 1)
        has_alternate_contract = any(
            len(self.role_contract_catalog.get(item.role_id, ())) > 1 for item in parent.roles
        )
        applicable = []
        if missing_roles and len(parent.roles) < budget.max_roles and len(parent.edges) < budget.max_edges:
            applicable.append("ADD_ROLE")
        if len(parent.roles) > 1:
            applicable.append("REMOVE_ROLE")
        if len(parent.edges) < min(budget.max_edges, possible_edges):
            applicable.append("ADD_EDGE")
        if parent.edges:
            applicable.append("REMOVE_EDGE")
        if has_alternate_contract:
            applicable.append("SPECIALIZE_ROLE")
        if self.agent_registry is not None and any(
            any(
                candidate.agent_id != binding.agent_id
                and candidate.role == binding.role_id
                and candidate.enabled
                for candidate in self.agent_registry.registered_agents()
            )
            for binding in parent.agent_bindings
        ):
            applicable.append("REBIND_ROLE_AGENT")
        return tuple(applicable)

    def apply(self, parent: OrganizationGenome, proposal: OrganizationMutationProposal) -> OrganizationGenome:
        self.validate_genome(parent)
        if proposal.parent_genome_hash != parent.genome_hash:
            raise ValueError("organization_evolution_operator_parent_mismatch")
        operator = self._operators.get(proposal.operator_id)
        if operator is None:
            raise ValueError("organization_evolution_operator_unregistered")
        roles, edges, bindings = operator(parent, proposal.parameters)
        candidate = OrganizationGenome.create(
            genome_id=f"{parent.genome_id}.g{parent.generation + 1}.{proposal.proposal_id}",
            task_hash=parent.task_hash,
            roles=tuple(sorted(roles, key=lambda item: item.role_id)),
            edges=tuple(sorted(edges, key=lambda item: (item.source_role, item.target_role, item.channel))),
            max_rounds=parent.max_rounds,
            stop_policy=parent.stop_policy,
            generation=parent.generation + 1,
            parent_genome_hash=parent.genome_hash,
            mutation_operator_id=proposal.operator_id,
            mutation_proposal_hash=proposal.proposal_hash,
            agent_bindings=tuple(sorted(bindings, key=lambda item: item.role_id)),
        )
        self.validate_genome(candidate)
        if self._surface(parent) == self._surface(candidate):
            raise ValueError("organization_evolution_operator_noop")
        return candidate

    @staticmethod
    def _surface(genome: OrganizationGenome) -> tuple[Any, ...]:
        return (
            tuple(tuple(item.as_dict().items()) for item in genome.roles),
            tuple(tuple(item.as_dict().items()) for item in genome.edges),
            tuple(item.binding_hash for item in genome.agent_bindings),
        )

    def _add_role(
        self, parent: OrganizationGenome, parameters: dict[str, Any]
    ) -> tuple[tuple[OrganizationRole, ...], tuple[OrganizationEdge, ...], tuple[OrganizationAgentBinding, ...]]:
        self._keys(
            parameters,
            {"role_id", "contract_id"},
            {"incoming_from_role", "outgoing_to_role", "channel", "agent_id"},
        )
        role_id, contract_id = parameters["role_id"], parameters["contract_id"]
        if role_id in {item.role_id for item in parent.roles}:
            raise ValueError("organization_evolution_add_role_duplicate")
        self._validate_contract(role_id, contract_id)
        incoming, outgoing = parameters.get("incoming_from_role"), parameters.get("outgoing_to_role")
        existing = {item.role_id for item in parent.roles}
        if incoming not in existing and outgoing not in existing:
            raise ValueError("organization_evolution_add_role_connection_required")
        channel = parameters.get("channel", "PUBLIC_RECEIPT")
        edges = list(parent.edges)
        if incoming in existing:
            edges.append(OrganizationEdge(incoming, role_id, channel))
        if outgoing in existing:
            edges.append(OrganizationEdge(role_id, outgoing, channel))
        bindings = parent.agent_bindings
        if self.agent_registry is not None:
            agent_id = parameters.get("agent_id")
            if not agent_id:
                raise ValueError("organization_evolution_add_role_agent_required")
            bindings = (*bindings, self._binding_for(role_id, contract_id, agent_id))
        return (*parent.roles, OrganizationRole(role_id, contract_id)), tuple(edges), bindings

    def _remove_role(
        self,
        parent: OrganizationGenome, parameters: dict[str, Any]
    ) -> tuple[tuple[OrganizationRole, ...], tuple[OrganizationEdge, ...], tuple[OrganizationAgentBinding, ...]]:
        OrganizationEvolutionOperatorRegistry._keys(parameters, {"role_id"}, set())
        role_id = parameters["role_id"]
        if len(parent.roles) == 1:
            raise ValueError("organization_evolution_remove_last_role_forbidden")
        if role_id not in {item.role_id for item in parent.roles}:
            raise ValueError("organization_evolution_remove_role_unknown")
        roles = tuple(item for item in parent.roles if item.role_id != role_id)
        edges = tuple(
            item for item in parent.edges if item.source_role != role_id and item.target_role != role_id
        )
        return roles, edges, tuple(item for item in parent.agent_bindings if item.role_id != role_id)

    def _add_edge(
        self,
        parent: OrganizationGenome, parameters: dict[str, Any]
    ) -> tuple[tuple[OrganizationRole, ...], tuple[OrganizationEdge, ...], tuple[OrganizationAgentBinding, ...]]:
        OrganizationEvolutionOperatorRegistry._keys(parameters, {"source_role", "target_role"}, {"channel"})
        edge = OrganizationEdge(
            parameters["source_role"], parameters["target_role"], parameters.get("channel", "PUBLIC_RECEIPT")
        )
        role_ids = {item.role_id for item in parent.roles}
        if edge.source_role not in role_ids or edge.target_role not in role_ids:
            raise ValueError("organization_evolution_add_edge_role_unknown")
        if edge in parent.edges:
            raise ValueError("organization_evolution_add_edge_duplicate")
        return parent.roles, (*parent.edges, edge), parent.agent_bindings

    def _remove_edge(
        self,
        parent: OrganizationGenome, parameters: dict[str, Any]
    ) -> tuple[tuple[OrganizationRole, ...], tuple[OrganizationEdge, ...], tuple[OrganizationAgentBinding, ...]]:
        OrganizationEvolutionOperatorRegistry._keys(parameters, {"source_role", "target_role"}, {"channel"})
        edge = OrganizationEdge(
            parameters["source_role"], parameters["target_role"], parameters.get("channel", "PUBLIC_RECEIPT")
        )
        if edge not in parent.edges:
            raise ValueError("organization_evolution_remove_edge_unknown")
        return parent.roles, tuple(item for item in parent.edges if item != edge), parent.agent_bindings

    def _specialize_role(
        self, parent: OrganizationGenome, parameters: dict[str, Any]
    ) -> tuple[tuple[OrganizationRole, ...], tuple[OrganizationEdge, ...], tuple[OrganizationAgentBinding, ...]]:
        self._keys(parameters, {"role_id", "contract_id"}, set())
        role_id, contract_id = parameters["role_id"], parameters["contract_id"]
        self._validate_contract(role_id, contract_id)
        current = next((item for item in parent.roles if item.role_id == role_id), None)
        if current is None:
            raise ValueError("organization_evolution_specialize_role_unknown")
        if current.contract_id == contract_id:
            raise ValueError("organization_evolution_specialize_role_noop")
        roles = tuple(OrganizationRole(role_id, contract_id) if item.role_id == role_id else item for item in parent.roles)
        if self.agent_registry is not None:
            binding = next(item for item in parent.agent_bindings if item.role_id == role_id)
            self._binding_for(role_id, contract_id, binding.agent_id)
        return roles, parent.edges, parent.agent_bindings

    def _rebind_role_agent(
        self, parent: OrganizationGenome, parameters: dict[str, Any]
    ) -> tuple[tuple[OrganizationRole, ...], tuple[OrganizationEdge, ...], tuple[OrganizationAgentBinding, ...]]:
        self._keys(parameters, {"role_id", "agent_id"}, set())
        if self.agent_registry is None:
            raise ValueError("organization_evolution_rebind_registry_required")
        role_id, agent_id = parameters["role_id"], parameters["agent_id"]
        role = next((item for item in parent.roles if item.role_id == role_id), None)
        current = next((item for item in parent.agent_bindings if item.role_id == role_id), None)
        if role is None or current is None:
            raise ValueError("organization_evolution_rebind_role_unknown")
        if current.agent_id == agent_id:
            raise ValueError("organization_evolution_rebind_noop")
        replacement = self._binding_for(role_id, role.contract_id, agent_id)
        bindings = tuple(replacement if item.role_id == role_id else item for item in parent.agent_bindings)
        return parent.roles, parent.edges, bindings

    def _binding_for(self, role_id: str, contract_id: str, agent_id: str) -> OrganizationAgentBinding:
        assert self.agent_registry is not None
        descriptor = self.agent_registry.get(agent_id)
        required = set(self.role_contract_capabilities.get(contract_id, ()))
        if descriptor.role != role_id or not descriptor.enabled or not required.issubset(descriptor.capabilities):
            raise ValueError("organization_evolution_agent_binding_ineligible")
        return OrganizationAgentBinding.from_descriptor(descriptor)

    def _validate_contract(self, role_id: str, contract_id: str) -> None:
        if contract_id not in self.role_contract_catalog.get(role_id, ()):
            raise ValueError("organization_evolution_role_contract_unregistered")

    @staticmethod
    def _keys(parameters: dict[str, Any], required: set[str], optional: set[str]) -> None:
        if not isinstance(parameters, dict) or not required.issubset(parameters) or set(parameters) - required - optional:
            raise ValueError("organization_evolution_operator_parameters_invalid")
        if any(not isinstance(value, str) or not value for value in parameters.values()):
            raise ValueError("organization_evolution_operator_parameter_text_invalid")
