"""Strong receipt binding from Selector prediction to admitted execution outcome."""

from __future__ import annotations

from agentos_kernel import SelectorCalibrationObservation
from agentos_kernel.contextual_policy_models import hash_payload

from .contextual_policy_contracts import ContextualOrganizationSelectionReceipt
from .selection_feedback_contracts import SelectionExecutionFeedbackReceipt


class SelectorCalibrationObservationAdapter:
    """Construct one mechanical observation from two already immutable receipts."""

    adapter_id = "selector_calibration_observation_adapter_v0_1"

    def build(
        self,
        *,
        observation_id: str,
        selection: ContextualOrganizationSelectionReceipt,
        feedback: SelectionExecutionFeedbackReceipt,
    ) -> SelectorCalibrationObservation:
        self._validate_binding(selection, feedback)
        policy_id = selection.kernel_decision.selected_policy_id
        advice = next(item for item in selection.provider_advice.policy_assessments if item.policy_id == policy_id)
        evaluation = next(
            item for item in selection.kernel_decision.candidate_evaluations if item.policy_id == policy_id
        )
        if evaluation.provider_assessment.as_dict() != advice.as_dict():
            raise ValueError("selector_calibration_decision_assessment_binding_invalid")
        outcome = next(item for item in feedback.execution_bundle.outcomes if item.protocol_id == policy_id)
        record = next(item for item in feedback.admitted_records if item.protocol_id == policy_id)
        self._validate_record_outcome(record, outcome)
        transfer_rate = None
        if outcome.negative_transfer_opportunities:
            transfer_rate = (
                outcome.negative_transfer_opportunities - outcome.negative_transfer_intercepts
            ) / outcome.negative_transfer_opportunities
        cbit_error = outcome.observed_cbit_gain - advice.expected_cbit_gain
        cost_error = outcome.normalized_cost - advice.estimated_normalized_cost
        evidence_refs = tuple(
            dict.fromkeys(
                (
                    *selection.kernel_decision.evidence_refs,
                    *outcome.evidence_refs,
                    outcome.harness_receipt_ref,
                )
            )
        )
        return SelectorCalibrationObservation.create(
            observation_id=observation_id,
            project_scope=selection.project_scope,
            context_key=selection.context_key,
            evidence_tier=selection.evidence_tier,
            policy_id=policy_id,
            selection_id=selection.selection_id,
            selection_receipt_hash=selection.receipt_hash,
            provider_advice_hash=selection.provider_advice.advice_hash,
            provider_assessment_hash=hash_payload(advice.as_dict()),
            feedback_receipt_hash=feedback.receipt_hash,
            request_hash=feedback.request.request_hash,
            execution_bundle_hash=feedback.execution_bundle.bundle_hash,
            outcome_hash=outcome.outcome_hash,
            selected_agent_binding_hash=feedback.request.selected_agent_binding_hash,
            trial_group_id=feedback.request.trial_group_id,
            trial_id=feedback.request.trial_id,
            trial_surface_hash=feedback.request.trial_surface_hash,
            source_result_hash=outcome.source_result_hash,
            harness_receipt_ref=outcome.harness_receipt_ref,
            harness_receipt_hash=outcome.harness_receipt_hash,
            execution_result_hash=outcome.execution_result_hash,
            predicted_cbit_gain=advice.expected_cbit_gain,
            observed_cbit_gain=outcome.observed_cbit_gain,
            cbit_error=cbit_error,
            estimated_normalized_cost=advice.estimated_normalized_cost,
            observed_normalized_cost=outcome.normalized_cost,
            cost_error=cost_error,
            provider_uncertainty=advice.uncertainty,
            cbit_within_uncertainty=abs(cbit_error) <= advice.uncertainty + 1e-12,
            predicted_residual_risk=advice.residual_risk,
            observed_negative_transfer_rate=transfer_rate,
            evidence_refs=evidence_refs,
        )

    @staticmethod
    def _validate_binding(
        selection: ContextualOrganizationSelectionReceipt,
        feedback: SelectionExecutionFeedbackReceipt,
    ) -> None:
        request = feedback.request
        bundle = feedback.execution_bundle
        policy_id = selection.kernel_decision.selected_policy_id
        if not policy_id or selection.assignment is None or not selection.kernel_decision.trial_authorized:
            raise ValueError("selector_calibration_selected_trial_required")
        if request.selection_receipt_hash != selection.receipt_hash:
            raise ValueError("selector_calibration_selection_receipt_hash_mismatch")
        if bundle.selection_receipt_hash != selection.receipt_hash:
            raise ValueError("selector_calibration_bundle_selection_hash_mismatch")
        if request.selected_policy_id != policy_id or bundle.selected_policy_id != policy_id:
            raise ValueError("selector_calibration_selected_policy_mismatch")
        if (
            request.project_scope != selection.project_scope
            or request.context_key != selection.context_key
            or request.evidence_tier != selection.evidence_tier
        ):
            raise ValueError("selector_calibration_scope_binding_mismatch")
        assignment_hash = hash_payload(selection.assignment.as_dict()["agents"])
        assignment_ids = tuple(item.agent_id for item in selection.assignment.agents)
        assignment_roles = tuple(item.role for item in selection.assignment.agents)
        if (
            request.selected_agent_ids != assignment_ids
            or request.selected_roles != assignment_roles
        ):
            raise ValueError("selector_calibration_assignment_identity_mismatch")
        if request.selected_agent_binding_hash != assignment_hash:
            raise ValueError("selector_calibration_assignment_binding_mismatch")
        if not bundle.execution_replay.get("valid"):
            raise ValueError("selector_calibration_execution_replay_invalid")

    @staticmethod
    def _validate_record_outcome(record, outcome) -> None:
        bindings = (
            (record.trial_group_id, outcome.trial_group_id),
            (record.context_key, outcome.context_key),
            (record.evidence_tier, outcome.evidence_tier),
            (record.protocol_id, outcome.protocol_id),
            (record.effectiveness_score, outcome.effectiveness_score),
            (record.observed_cbit_gain, outcome.observed_cbit_gain),
            (record.normalized_cost, outcome.normalized_cost),
            (record.convergence_steps, outcome.convergence_steps),
            (record.errors_exposed, outcome.errors_exposed),
            (record.errors_corrected, outcome.errors_corrected),
            (record.negative_transfer_opportunities, outcome.negative_transfer_opportunities),
            (record.negative_transfer_intercepts, outcome.negative_transfer_intercepts),
            (record.evidence_refs, outcome.evidence_refs),
            (record.harness_receipt_ref, outcome.harness_receipt_ref),
            (record.execution_result_hash, outcome.execution_result_hash),
            (record.source_result_hash, outcome.source_result_hash),
        )
        if any(left != right for left, right in bindings) or record.replay_valid is not True:
            raise ValueError("selector_calibration_admitted_record_outcome_mismatch")
