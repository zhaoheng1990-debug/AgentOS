"""Thin Runtime facade for context-conditioned organization policy selection."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentos_kernel import (
    AgentRegistry,
    ContextualMatchedEvidenceEvaluator,
    ContextualOrganizationPolicySelector,
    ContextualProblemStructure,
    ContextualRolePolicy,
    CognitiveWorkControlDecision,
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
from .contextual_policy_assignment import ContextualPolicyAssignmentPlanner
from .contextual_policy_calibration_source import (
    SelectorCalibrationControlSource,
    resolve_calibration_controls,
)
from .organization_record_source import OrganizationTrialRecordSource, collect_organization_records
from .problem_structure_source import AdmittedProblemStructureSource, resolve_problem_structure


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
        problem_source: AdmittedProblemStructureSource | None = None,
        calibration_source: SelectorCalibrationControlSource | None = None,
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
        self.record_source, self.problem_source = record_source, problem_source
        self.calibration_source = calibration_source
        self._assignment_planner = ContextualPolicyAssignmentPlanner(
            registry=registry,
            policies=self.policies,
        )
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
        problem: ContextualProblemStructure | None = None,
        problem_admission_id: str = "",
        records: tuple[OrganizationTrialRecord, ...] = (),
        evidence_tier: str,
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        kernel_authorization_ref: str,
        cognitive_work_control: CognitiveWorkControlDecision | None = None,
    ) -> ContextualOrganizationSelectionReceipt:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", selection_id):
            raise ValueError("contextual_policy_selection_id_invalid")
        if self._repository.selection(selection_id) is not None:
            raise ValueError(f"duplicate_contextual_policy_selection:{selection_id}")
        problem = resolve_problem_structure(source=self.problem_source, project_scope=self.project_scope,
            admission_id=problem_admission_id, direct_problem=problem,
        )
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
        calibration_controls = resolve_calibration_controls(
            source=self.calibration_source,
            project_scope=self.project_scope,
            context_key=problem.context_key,
            evidence_tier=evidence_tier,
        )
        assignments = self._assignment_planner.feasible_assignments(selection_id, risk)
        provider_advice = self._provider_advisor.assess(
            selection_id=selection_id,
            problem=problem,
            policies=self.policies,
            matched_evidence=matched_evidence,
            budget=budget,
            risk=risk,
            public_agent_profiles=self._assignment_planner.public_agent_profiles(),
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
            calibration_controls=calibration_controls,
            cognitive_work_control=cognitive_work_control,
        )
        assignment = self._assignment_planner.authorized_assignment(
            decision.selected_policy_id,
            decision.execution_authorized,
            assignments,
        )
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
