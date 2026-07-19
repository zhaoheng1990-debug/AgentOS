"""Thin Runtime facade for context-conditioned organization policy selection."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from agentos_kernel import (
    AgentRegistry,
    AgentRoleRequirement,
    ContextualMatchedEvidenceEvaluator,
    ContextualOrganizationPolicySelector,
    ContextualProblemStructure,
    ContextualRolePolicy,
    EnsembleAssignment,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    OrganizationTrialRecord,
    ProviderTaskRouter,
    default_contextual_role_policies,
)

from .contextual_policy_contracts import (
    CONTEXTUAL_ORGANIZATION_POLICY_RUNTIME_VERSION,
    ContextualOrganizationPolicySnapshot,
    ContextualOrganizationSelectionReceipt,
)
from .contextual_policy_provider import ContextualOrganizationProviderAdvisor
from .contextual_policy_repository import ContextualPolicyRepository
from .organization_record_source import OrganizationTrialRecordSource, collect_organization_records


class ContextualOrganizationPolicyRuntime:
    """Coordinate evidence, Provider advice, Kernel selection, and assignment."""

    module_id = CONTEXTUAL_ORGANIZATION_POLICY_RUNTIME_VERSION
    capabilities = (
        "contextual_role_policy_selection",
        "exact_context_matched_evidence",
        "budget_and_risk_gating",
        "provider_supported_kernel_authorized_assignment",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        registry: AgentRegistry,
        provider_router: ProviderTaskRouter,
        workspace_root: str | Path,
        policies: tuple[ContextualRolePolicy, ...] | None = None,
        evidence_evaluator: ContextualMatchedEvidenceEvaluator | None = None,
        kernel_selector: ContextualOrganizationPolicySelector | None = None,
        record_source: OrganizationTrialRecordSource | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("contextual_policy_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("contextual_policy_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.registry = registry
        self.policies = policies or default_contextual_role_policies()
        self.evidence_evaluator = evidence_evaluator or ContextualMatchedEvidenceEvaluator()
        self.kernel_selector = kernel_selector or ContextualOrganizationPolicySelector()
        self.record_source = record_source
        self._repository = ContextualPolicyRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )
        self._provider_advisor = ContextualOrganizationProviderAdvisor(
            runtime_id=runtime_id,
            provider_router=provider_router,
            event_sink=self._repository.persist_event,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def select_policy(
        self,
        *,
        selection_id: str,
        problem: ContextualProblemStructure,
        records: tuple[OrganizationTrialRecord, ...] = (),
        evidence_tier: str,
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        kernel_authorization_ref: str,
    ) -> ContextualOrganizationSelectionReceipt:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", selection_id):
            raise ValueError("contextual_policy_selection_id_invalid")
        if self._repository.selection(selection_id) is not None:
            raise ValueError(f"duplicate_contextual_policy_selection:{selection_id}")
        if problem.project_scope != self.project_scope:
            raise ValueError("contextual_policy_problem_scope_mismatch")
        admitted_records = collect_organization_records(
            source=self.record_source,
            project_scope=self.project_scope,
            context_key=problem.context_key,
            evidence_tier=evidence_tier,
            explicit=records,
        )
        matched_evidence = self.evidence_evaluator.evaluate(
            admitted_records,
            context_key=problem.context_key,
            evidence_tier=evidence_tier,
        )
        assignments = self._feasible_assignments(selection_id, risk)
        provider_advice = self._provider_advisor.assess(
            selection_id=selection_id,
            problem=problem,
            policies=self.policies,
            matched_evidence=matched_evidence,
            budget=budget,
            risk=risk,
            public_agent_profiles=self._public_agent_profiles(),
        )
        decision = self.kernel_selector.select(
            decision_id=f"{selection_id}-kernel",
            problem=problem,
            budget=budget,
            risk=risk,
            policies=self.policies,
            matched_evidence=matched_evidence,
            provider_assessments=provider_advice.policy_assessments,
            provider_advice_hash=provider_advice.advice_hash,
            feasible_policy_ids=tuple(assignments),
            kernel_authorization_ref=kernel_authorization_ref,
        )
        assignment = self._authorized_assignment(decision.selected_policy_id, decision.execution_authorized, assignments)
        receipt = ContextualOrganizationSelectionReceipt.create(
            selection_id=selection_id,
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            context_key=problem.context_key,
            evidence_tier=evidence_tier,
            provider_advice=provider_advice,
            matched_evidence=matched_evidence,
            kernel_decision=decision,
            assignment=assignment,
        )
        self._repository.save_selection(receipt)
        return receipt

    def selection(self, selection_id: str) -> ContextualOrganizationSelectionReceipt | None:
        return self._repository.selection(selection_id)

    def snapshot(self) -> ContextualOrganizationPolicySnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, Any]:
        return self._repository.verify_replay()

    def _feasible_assignments(
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
    def _authorized_assignment(
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

    def _public_agent_profiles(self) -> tuple[dict[str, Any], ...]:
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
