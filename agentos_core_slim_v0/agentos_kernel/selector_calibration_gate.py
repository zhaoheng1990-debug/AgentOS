"""Kernel-owned final state gate for Selector calibration and drift."""

from __future__ import annotations

from .contextual_policy_models import hash_payload
from .provider_cognition_layer import (
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
)
from .selector_calibration_models import (
    SelectorCalibrationDecision,
    SelectorCalibrationProfile,
    SelectorCalibrationProviderJudgment,
    SelectorCalibrationThresholds,
)


class SelectorCalibrationGate:
    """Combine frozen metrics and Provider diagnosis without delegating state authority."""

    def decide(
        self,
        *,
        decision_id: str,
        profile: SelectorCalibrationProfile,
        judgment: SelectorCalibrationProviderJudgment,
        thresholds: SelectorCalibrationThresholds,
        kernel_authorization_ref: str,
    ) -> SelectorCalibrationDecision:
        failures = self.failures(profile=profile, judgment=judgment, thresholds=thresholds)
        if failures:
            raise ValueError("selector_calibration_gate_blocked:" + ";".join(failures))
        final_state = self._final_state(profile.mechanical_state, judgment.diagnostic_state)
        action = {
            "INSUFFICIENT_HISTORY": "COLLECT_MORE",
            "CALIBRATED": "KEEP_CURRENT_CALIBRATION",
            "WATCH": "REASSESS_CONTEXT_POLICY",
            "DRIFTED": "SUSPEND_PREDICTION_TRUST",
        }[final_state]
        return SelectorCalibrationDecision.create(
            decision_id=decision_id,
            final_state=final_state,
            prediction_trusted=final_state == "CALIBRATED",
            recalibration_required=final_state in {"WATCH", "DRIFTED"},
            action=action,
            reason=f"kernel_combined_{profile.mechanical_state.lower()}_{judgment.diagnostic_state.lower()}",
            kernel_authorization_ref=kernel_authorization_ref,
            profile_hash=profile.profile_hash,
            provider_judgment_hash=judgment.judgment_hash,
            threshold_hash=thresholds.as_dict()["threshold_hash"],
        )

    @staticmethod
    def failures(
        *,
        profile: SelectorCalibrationProfile,
        judgment: SelectorCalibrationProviderJudgment,
        thresholds: SelectorCalibrationThresholds,
    ) -> tuple[str, ...]:
        failures = []
        if judgment.profile_hash != profile.profile_hash:
            failures.append("provider_profile_hash_mismatch")
        if profile.threshold_hash != thresholds.as_dict()["threshold_hash"]:
            failures.append("threshold_hash_mismatch")
        if profile.evidence_ref not in judgment.evidence_refs:
            failures.append("provider_profile_evidence_missing")
        if judgment.uncertainty > thresholds.provider_uncertainty_ceiling:
            failures.append("provider_uncertainty_ceiling_exceeded")
        if judgment.provider_audit.get("status") not in {
            PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
            PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
        }:
            failures.append("provider_audit_not_passed")
        insufficient = profile.mechanical_state == "INSUFFICIENT_HISTORY"
        if insufficient != (judgment.diagnostic_state == "INSUFFICIENT_HISTORY"):
            failures.append("provider_history_state_inconsistent")
        invocation = judgment.provider_invocation_receipt
        if invocation.get("output_hash") != hash_payload(
            {
                "diagnostic_state": judgment.diagnostic_state,
                "drift_drivers": list(judgment.drift_drivers),
                "recommended_action": judgment.recommended_action,
                "uncertainty": judgment.uncertainty,
                "rationale": judgment.rationale,
                "evidence_refs": list(judgment.evidence_refs),
            }
        ):
            failures.append("provider_output_binding_invalid")
        return tuple(failures)

    @staticmethod
    def _final_state(mechanical_state: str, diagnostic_state: str) -> str:
        if mechanical_state == "INSUFFICIENT_HISTORY":
            return "INSUFFICIENT_HISTORY"
        if mechanical_state == "DRIFTED":
            return "DRIFTED"
        if mechanical_state == "WATCH" or diagnostic_state in {
            "POSSIBLE_SEMANTIC_DRIFT",
            "MATERIAL_SEMANTIC_DRIFT",
        }:
            return "WATCH"
        return "CALIBRATED"
