"""Kernel-owned authorization effects for consumed Selector calibration state."""

from __future__ import annotations

from .contextual_policy_calibration import ContextualPolicyCalibrationControl


class ContextualPolicyCalibrationGate:
    """Apply calibration restrictions without selecting or ranking a policy."""

    @staticmethod
    def hard_failures(control: ContextualPolicyCalibrationControl) -> tuple[str, ...]:
        if control.control_mode == "BLOCKED":
            return ("selector_calibration_drifted",)
        return ()

    @staticmethod
    def eligibility(
        *,
        hard_failures: tuple[str, ...],
        sufficient_matched_evidence: bool,
        control: ContextualPolicyCalibrationControl,
    ) -> str:
        if hard_failures:
            return "BLOCKED"
        if control.control_mode == "EXPLORATION_ONLY":
            return "EXPLORATION_ELIGIBLE"
        if sufficient_matched_evidence:
            return "AUTHORIZED_ELIGIBLE"
        return "EXPLORATION_ELIGIBLE"
