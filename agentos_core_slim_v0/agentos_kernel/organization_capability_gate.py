"""Kernel gate for registry-bound, evidence-backed organization assignments."""

from __future__ import annotations

from .agent_registry import AgentRegistry
from .organization_capability_models import (
    AgentCapabilityEvidence,
    OrganizationAgentBinding,
    OrganizationCapabilityBindingReceipt,
    OrganizationCapabilityPolicy,
)
from .organization_evolution_models import OrganizationEvolutionTask, OrganizationGenome


class OrganizationCapabilityBindingGate:
    """Validate role bindings and classify evidence support without choosing an agent."""

    def evaluate(
        self,
        *,
        task: OrganizationEvolutionTask,
        genome: OrganizationGenome,
        registry: AgentRegistry,
        role_contract_capabilities: dict[str, tuple[str, ...]],
        evidence: tuple[AgentCapabilityEvidence, ...],
        policy: OrganizationCapabilityPolicy,
        evidence_required_agent_ids: tuple[str, ...] = (),
    ) -> OrganizationCapabilityBindingReceipt:
        failures: list[str] = []
        role_by_id = {item.role_id: item for item in genome.roles}
        binding_by_role = {item.role_id: item for item in genome.agent_bindings}
        if set(binding_by_role) != set(role_by_id) or len(binding_by_role) != len(genome.agent_bindings):
            failures.append("organization_capability_binding_surface_incomplete")
        resolved = []
        for role_id, role in role_by_id.items():
            binding = binding_by_role.get(role_id)
            if binding is None:
                continue
            try:
                descriptor = registry.get(binding.agent_id)
            except KeyError:
                failures.append(f"organization_capability_agent_unregistered:{binding.agent_id}")
                continue
            expected = OrganizationAgentBinding.from_descriptor(descriptor)
            if binding.binding_hash != expected.binding_hash or descriptor.role != role_id or not descriptor.enabled:
                failures.append(f"organization_capability_registry_binding_mismatch:{binding.agent_id}")
                continue
            required = set(role_contract_capabilities.get(role.contract_id, ()))
            if not required.issubset(descriptor.capabilities):
                failures.append(f"organization_capability_requirement_missing:{binding.agent_id}")
            scopes = set(descriptor.allowed_evidence_scopes)
            if task.project_scope not in scopes and "*" not in scopes:
                failures.append(f"organization_capability_scope_forbidden:{binding.agent_id}")
            resolved.append(binding)
        if policy.require_distinct_agents and len({item.agent_id for item in resolved}) != len(resolved):
            failures.append("organization_capability_agent_reuse_forbidden")
        if policy.require_distinct_contexts and len({item.context_isolation_key for item in resolved}) != len(resolved):
            failures.append("organization_capability_context_reuse_forbidden")
        if policy.require_distinct_providers and len({item.provider_id for item in resolved}) != len(resolved):
            failures.append("organization_capability_provider_reuse_forbidden")

        admitted_evidence: list[AgentCapabilityEvidence] = []
        exploratory = False
        for agent_id in dict.fromkeys(evidence_required_agent_ids):
            binding = next((item for item in resolved if item.agent_id == agent_id), None)
            if binding is None:
                failures.append(f"organization_capability_required_agent_not_bound:{agent_id}")
                continue
            role = role_by_id[binding.role_id]
            required = set(role_contract_capabilities.get(role.contract_id, ()))
            matches = tuple(
                item
                for item in evidence
                if item.project_scope == task.project_scope
                and item.context_key == task.context_key
                and item.agent_id == agent_id
                and item.role_id == binding.role_id
                and item.replay_valid
                and required.issubset(item.required_capabilities)
                and set(item.evidence_refs).issubset(task.evidence_refs)
            )
            independent_trials = sum(item.independent_trials for item in matches)
            if independent_trials < policy.minimum_independent_trials:
                if policy.allow_exploratory_rebinding:
                    exploratory = True
                else:
                    failures.append(f"organization_capability_evidence_insufficient:{agent_id}")
            admitted_evidence.extend(matches)

        mode = "BLOCKED" if failures else "EXPLORATORY_TRIAL_ONLY" if exploratory else "SUPPORTED"
        return OrganizationCapabilityBindingReceipt.create(
            genome_hash=genome.genome_hash,
            mode=mode,
            binding_hashes=tuple(sorted(item.binding_hash for item in resolved)),
            capability_evidence_hashes=tuple(sorted({item.evidence_hash for item in admitted_evidence})),
            failures=tuple(dict.fromkeys(failures)),
        )
