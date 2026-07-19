"""Kernel admission from selected-policy outcomes to organization evidence."""

from __future__ import annotations

from .organization_learning_eval import OrganizationTrialRecord
from .selection_execution_models import SelectionExecutionRequest
from .selection_execution_outcomes import PolicyExecutionBundle


class SelectionExecutionFeedbackGate:
    """Admit only strongly bound, Harness-owned, replay-valid outcomes."""

    def admit(
        self,
        *,
        request: SelectionExecutionRequest,
        bundle: PolicyExecutionBundle,
    ) -> tuple[OrganizationTrialRecord, ...]:
        failures = self.failures(request=request, bundle=bundle)
        if failures:
            raise ValueError("selection_execution_feedback_blocked:" + ";".join(failures))
        return tuple(
            OrganizationTrialRecord.create(
                record_id=f"record-{request.trial_group_id}-{item.protocol_id.lower()}",
                trial_group_id=request.trial_group_id,
                context_key=request.context_key,
                evidence_tier=request.evidence_tier,
                protocol_id=item.protocol_id,
                effectiveness_score=item.effectiveness_score,
                observed_cbit_gain=item.observed_cbit_gain,
                normalized_cost=item.normalized_cost,
                convergence_steps=item.convergence_steps,
                errors_exposed=item.errors_exposed,
                errors_corrected=item.errors_corrected,
                negative_transfer_opportunities=item.negative_transfer_opportunities,
                negative_transfer_intercepts=item.negative_transfer_intercepts,
                evidence_refs=item.evidence_refs,
                harness_receipt_ref=item.harness_receipt_ref,
                execution_result_hash=item.execution_result_hash,
                source_result_hash=item.source_result_hash,
                replay_valid=True,
            )
            for item in bundle.outcomes
        )

    @staticmethod
    def failures(
        *,
        request: SelectionExecutionRequest,
        bundle: PolicyExecutionBundle,
    ) -> tuple[str, ...]:
        failures = []
        if bundle.bridge_run_id != request.bridge_run_id:
            failures.append("bridge_run_id_mismatch")
        if bundle.selection_receipt_hash != request.selection_receipt_hash:
            failures.append("selection_receipt_hash_mismatch")
        if bundle.selected_policy_id != request.selected_policy_id:
            failures.append("selected_policy_mismatch")
        if len(bundle.executed_protocol_ids) > request.execution_budget.max_protocol_runs:
            failures.append("execution_protocol_run_budget_exceeded")
        if bundle.total_provider_call_count > request.execution_budget.max_provider_calls_total:
            failures.append("execution_provider_call_budget_exceeded")
        for footprint in bundle.executed_protocols:
            if footprint.normalized_cost > request.execution_budget.max_normalized_cost_per_protocol:
                failures.append(
                    f"execution_normalized_cost_budget_exceeded:{footprint.protocol_id}"
                )
        for outcome in bundle.outcomes:
            if (
                outcome.project_scope != request.project_scope
                or outcome.context_key != request.context_key
                or outcome.evidence_tier != request.evidence_tier
            ):
                failures.append(f"scope_binding_mismatch:{outcome.protocol_id}")
            if outcome.trial_group_id != request.trial_group_id or outcome.trial_id != request.trial_id:
                failures.append(f"trial_binding_mismatch:{outcome.protocol_id}")
            if outcome.trial_surface_hash != request.trial_surface_hash:
                failures.append(f"trial_surface_hash_mismatch:{outcome.protocol_id}")
            if outcome.evidence_refs != request.trial_evidence_refs:
                failures.append(f"evidence_surface_mismatch:{outcome.protocol_id}")
        selected = next(
            (item for item in bundle.outcomes if item.protocol_id == request.selected_policy_id),
            None,
        )
        if selected is None:
            failures.append("selected_outcome_missing")
        elif selected.agent_ids != request.selected_agent_ids or selected.roles != request.selected_roles:
            failures.append("selected_assignment_mismatch")
        elif selected.agent_binding_hash != request.selected_agent_binding_hash:
            failures.append("selected_agent_binding_hash_mismatch")
        return tuple(dict.fromkeys(failures))
