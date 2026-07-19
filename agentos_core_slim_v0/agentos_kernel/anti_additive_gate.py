"""Kernel-owned Anti-Additive Methodology decision gate."""

from __future__ import annotations

from .anti_additive_models import (
    ANTI_ADDITIVE_OBJECT_LEVELS,
    AntiAdditiveChangeCandidate,
    AntiAdditiveMethodologyDecision,
    AntiAdditiveMethodologyPolicy,
    AntiAdditiveMethodologyReceipt,
    AntiAdditiveProviderJudgment,
)
from .anti_additive_control import AntiAdditiveCalibrationControl


class AntiAdditiveMethodologyGate:
    """Prevent patch accumulation while allowing evidence-backed object upgrades."""

    def review(
        self,
        *,
        candidate: AntiAdditiveChangeCandidate,
        judgment: AntiAdditiveProviderJudgment,
        policy: AntiAdditiveMethodologyPolicy,
        kernel_authorization_ref: str,
        calibration_control: AntiAdditiveCalibrationControl | None = None,
    ) -> AntiAdditiveMethodologyReceipt:
        if judgment.candidate_hash != candidate.candidate_hash:
            raise ValueError("anti_additive_candidate_judgment_mismatch")
        if not set(judgment.evidence_refs).issubset(candidate.evidence_refs):
            raise ValueError("anti_additive_judgment_evidence_outside_candidate")
        control = calibration_control or AntiAdditiveCalibrationControl.unmonitored(
            project_scope=candidate.project_scope,
            change_kind=candidate.change_kind,
            target_type=candidate.target_type,
        )
        if (
            control.project_scope != candidate.project_scope
            or control.change_kind != candidate.change_kind
            or control.target_type != candidate.target_type
        ):
            raise ValueError("anti_additive_calibration_control_binding_invalid")
        state, reason = self._state(candidate, judgment, policy)
        if state == "ALLOW_BOUNDED_CHANGE" and control.control_mode == "EXPLORATION_ONLY":
            state, reason = (
                "REQUIRE_CALIBRATED_VALIDATION",
                "anti_additive_prediction_history_not_trusted_for_durable_change",
            )
        elif state == "ALLOW_BOUNDED_CHANGE" and control.control_mode == "BLOCKED":
            state, reason = (
                "BLOCK_CALIBRATION_DRIFT",
                "anti_additive_prediction_calibration_drifted",
            )
        active = tuple(item.trigger_id for item in judgment.trigger_assessments if item.triggered)
        decision = AntiAdditiveMethodologyDecision.create(
            audit_id=candidate.audit_id,
            project_scope=candidate.project_scope,
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            candidate_payload_hash=candidate.candidate_payload_hash,
            provider_judgment_hash=judgment.judgment_hash,
            policy_hash=policy.as_dict()["policy_hash"],
            state=state,
            allowed=state == "ALLOW_BOUNDED_CHANGE",
            candidate_only_allowed=state in {
                "ALLOW_BOUNDED_CHANGE",
                "REQUIRE_CALIBRATED_VALIDATION",
            },
            reason=reason,
            active_trigger_ids=active,
            effective_cbit_margin=round(
                judgment.expected_effective_cbit_gain - judgment.complexity_cost, 12
            ),
            object_upgrade_margin=round(judgment.object_upgrade_gain - judgment.abstraction_cost, 12),
            kernel_authorization_ref=kernel_authorization_ref,
            calibration_control=control,
        )
        return AntiAdditiveMethodologyReceipt.create(
            candidate=candidate,
            provider_judgment=judgment,
            decision=decision,
        )

    @staticmethod
    def _state(
        candidate: AntiAdditiveChangeCandidate,
        judgment: AntiAdditiveProviderJudgment,
        policy: AntiAdditiveMethodologyPolicy,
    ) -> tuple[str, str]:
        if judgment.uncertainty > policy.max_provider_uncertainty:
            return (
                "REQUIRE_FIRST_PRINCIPLES_REFRAMING",
                "provider_uncertainty_exceeds_methodology_boundary",
            )
        if judgment.expected_effective_cbit_gain <= judgment.complexity_cost:
            return (
                "BLOCK_PATCH_ACCUMULATION",
                "effective_cbit_gain_does_not_exceed_complexity_cost",
            )
        current_rank = ANTI_ADDITIVE_OBJECT_LEVELS.index(candidate.current_object_level)
        proposed_rank = ANTI_ADDITIVE_OBJECT_LEVELS.index(candidate.proposed_object_level)
        active = any(item.triggered for item in judgment.trigger_assessments)
        if active and judgment.current_object_adequacy in {"UNDERPOWERED", "WRONG_OBJECT"}:
            if proposed_rank <= current_rank:
                return (
                    "REQUIRE_OBJECT_UPGRADE",
                    "active_anti_additive_trigger_requires_higher_resolution_object",
                )
        if proposed_rank > current_rank and judgment.object_upgrade_gain <= judgment.abstraction_cost:
            return (
                "BLOCK_ABSTRACTION_FOG",
                "object_upgrade_gain_does_not_exceed_abstraction_cost",
            )
        if judgment.current_object_adequacy == "UNCERTAIN" or judgment.recommended_action == "ABSTAIN":
            return (
                "REQUIRE_FIRST_PRINCIPLES_REFRAMING",
                "object_adequacy_not_resolved_for_bounded_change",
            )
        return "ALLOW_BOUNDED_CHANGE", "anti_additive_methodology_gates_passed"
