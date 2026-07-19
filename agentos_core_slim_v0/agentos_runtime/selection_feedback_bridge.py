"""Thin selection-to-execution feedback bridge."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ContextualMatchedEvidenceEvaluator,
    OrganizationTrialRecord,
    SelectionExecutionFeedbackGate,
    SelectionExecutionBudget,
    SelectionExecutionRequest,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .contextual_policy_contracts import ContextualOrganizationSelectionReceipt
from .selection_execution_adapters import SelectionPolicyExecutionAdapter
from .selection_feedback_contracts import (
    SELECTION_EXECUTION_FEEDBACK_RUNTIME_VERSION,
    SelectionExecutionFeedbackReceipt,
    SelectionExecutionFeedbackSnapshot,
)
from .selection_feedback_repository import SelectionFeedbackRepository


class SelectionExecutionFeedbackBridge:
    """Execute one selected policy surface and persist admitted learning evidence."""

    module_id = SELECTION_EXECUTION_FEEDBACK_RUNTIME_VERSION
    capabilities = (
        "selector_receipt_execution_binding",
        "harness_outcome_admission",
        "organization_trial_feedback",
        "exact_context_matched_evidence_source",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        workspace_root: str | Path,
        feedback_gate: SelectionExecutionFeedbackGate | None = None,
        evidence_evaluator: ContextualMatchedEvidenceEvaluator | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("selection_feedback_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("selection_feedback_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.feedback_gate = feedback_gate or SelectionExecutionFeedbackGate()
        self.evidence_evaluator = evidence_evaluator or ContextualMatchedEvidenceEvaluator()
        self._repository = SelectionFeedbackRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def execute_and_admit(
        self,
        *,
        bridge_run_id: str,
        selection: ContextualOrganizationSelectionReceipt,
        executor: SelectionPolicyExecutionAdapter,
        trial_group_id: str,
        trial_id: str,
        trial_evidence_refs: tuple[str, ...],
        execution_budget: SelectionExecutionBudget,
        kernel_execution_authorization_ref: str,
    ) -> SelectionExecutionFeedbackReceipt:
        self._validate_selection(selection)
        if not set(trial_evidence_refs).issubset(selection.kernel_decision.evidence_refs):
            raise ValueError("selection_feedback_trial_evidence_not_selected")
        if self._repository.receipt(bridge_run_id) is not None:
            raise ValueError(f"duplicate_selection_feedback_run:{bridge_run_id}")
        if self._repository.has_trial_group(
            context_key=selection.context_key,
            evidence_tier=selection.evidence_tier,
            trial_group_id=trial_group_id,
        ):
            raise ValueError("duplicate_selection_feedback_trial_group")
        assignment = selection.assignment
        assert assignment is not None
        request = SelectionExecutionRequest.create(
            bridge_run_id=bridge_run_id,
            selection_receipt_hash=selection.receipt_hash,
            project_scope=selection.project_scope,
            context_key=selection.context_key,
            evidence_tier=selection.evidence_tier,
            trial_group_id=trial_group_id,
            trial_id=trial_id,
            selected_policy_id=selection.kernel_decision.selected_policy_id,
            selected_agent_ids=tuple(item.agent_id for item in assignment.agents),
            selected_roles=tuple(item.role for item in assignment.agents),
            selected_agent_binding_hash=hash_payload(assignment.as_dict()["agents"]),
            trial_evidence_refs=trial_evidence_refs,
            execution_budget=execution_budget,
            kernel_execution_authorization_ref=kernel_execution_authorization_ref,
        )
        try:
            bundle = executor.execute(request)
            records = self.feedback_gate.admit(request=request, bundle=bundle)
            combined = (*self._repository.all_records(), *records)
            matched = self.evidence_evaluator.evaluate(
                combined,
                context_key=selection.context_key,
                evidence_tier=selection.evidence_tier,
            )
            receipt = SelectionExecutionFeedbackReceipt.create(
                request=request,
                execution_bundle=bundle,
                admitted_records=records,
                matched_evidence=matched,
            )
            self._repository.save(receipt)
            return receipt
        except Exception as exc:
            self._repository.persist_blocked(
                {
                    "bridge_run_id": bridge_run_id,
                    "selection_receipt_hash": selection.receipt_hash,
                    "execution_adapter_id": getattr(executor, "adapter_id", "unknown"),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            raise

    def organization_records(
        self,
        *,
        project_scope: str,
        context_key: str,
        evidence_tier: str,
    ) -> tuple[OrganizationTrialRecord, ...]:
        if project_scope != self.project_scope:
            raise ValueError("selection_feedback_record_source_scope_mismatch")
        return tuple(
            item
            for item in self._repository.all_records()
            if item.context_key == context_key and item.evidence_tier == evidence_tier
        )

    def matched_evidence(self, *, context_key: str, evidence_tier: str):
        return self.evidence_evaluator.evaluate(
            self.organization_records(
                project_scope=self.project_scope,
                context_key=context_key,
                evidence_tier=evidence_tier,
            ),
            context_key=context_key,
            evidence_tier=evidence_tier,
        )

    def receipt(self, bridge_run_id: str) -> SelectionExecutionFeedbackReceipt | None:
        return self._repository.receipt(bridge_run_id)

    def snapshot(self) -> SelectionExecutionFeedbackSnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, Any]:
        return self._repository.verify_replay()

    def _validate_selection(self, selection: ContextualOrganizationSelectionReceipt) -> None:
        if selection.project_scope != self.project_scope:
            raise ValueError("selection_feedback_selection_scope_mismatch")
        if (
            selection.assignment is None
            or not selection.kernel_decision.selected_policy_id
            or selection.kernel_decision.trial_authorized is not True
        ):
            raise ValueError("selection_feedback_requires_trial_authorized_selection")
