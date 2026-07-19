"""Agent assignment planning for contextual organization policies."""

from __future__ import annotations

from dataclasses import replace

from agentos_kernel import (
    AgentRegistry,
    AgentRoleRequirement,
    ContextualRolePolicy,
    EnsembleAssignment,
    OrganizationRiskEnvelope,
)


class ContextualPolicyAssignmentPlanner:
    """Own registry feasibility, public profiles, and authority projection."""

    def __init__(self, *, registry: AgentRegistry, policies: tuple[ContextualRolePolicy, ...]) -> None:
        self.registry = registry
        self.policies = policies

    def feasible_assignments(
        self,
        selection_id: str,
        risk: OrganizationRiskEnvelope,
    ) -> dict[str, EnsembleAssignment]:
        assignments = {}
        for policy in self.policies:
            requirements = tuple(
                AgentRoleRequirement(
                    role=role,
                    require_distinct_provider=risk.require_distinct_provider,
                )
                for role in policy.roles
            )
            try:
                assignments[policy.policy_id] = self.registry.form_team(
                    f"{selection_id}-{policy.policy_id.lower()}",
                    requirements,
                )
            except ValueError as exc:
                if str(exc) != "no_context_isolated_team_satisfies_requirements":
                    raise
        return assignments

    @staticmethod
    def authorized_assignment(
        selected_policy_id: str,
        execution_authorized: bool,
        assignments: dict[str, EnsembleAssignment],
    ) -> EnsembleAssignment | None:
        if not selected_policy_id:
            return None
        assignment = assignments.get(selected_policy_id)
        if assignment is None:
            raise ValueError("contextual_policy_selected_assignment_missing")
        return replace(assignment, execution_authorized=execution_authorized)

    def public_agent_profiles(self) -> tuple[dict, ...]:
        return tuple(
            {
                "agent_id": agent.agent_id,
                "role": agent.role,
                "capabilities": list(agent.capabilities),
                "runner_id": agent.runner_id,
                "harness_id": agent.harness_id,
                "provider_id": agent.provider_id,
                "model_id": agent.model_id,
                "context_isolation_key": agent.context_isolation_key,
                "allowed_evidence_scopes": list(agent.allowed_evidence_scopes),
                "enabled": agent.enabled,
            }
            for agent in self.registry.registered_agents()
        )
