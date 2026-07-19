"""Kernel contracts for consuming project-scoped Selector calibration state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contextual_policy_models import (
    CONTEXTUAL_POLICY_ROLE_MAP,
    hash_payload,
    require_text,
)
from .selector_calibration_base import SELECTOR_CALIBRATION_STATES, require_calibration_hash
from .selector_calibration_models import SelectorCalibrationReceipt


CONTEXTUAL_CALIBRATION_STATES = (
    "UNMONITORED",
    "NO_OBSERVATION",
    *SELECTOR_CALIBRATION_STATES,
)
CONTEXTUAL_CALIBRATION_CONTROL_MODES = (
    "LEGACY_COMPATIBLE",
    "EXPLORATION_ONLY",
    "TRUSTED",
    "BLOCKED",
)


@dataclass(frozen=True)
class ContextualPolicyCalibrationControl:
    project_scope: str
    context_key: str
    evidence_tier: str
    policy_id: str
    source_configured: bool
    calibration_state: str
    control_mode: str
    prediction_trusted: bool
    calibration_receipt_ref: str
    calibration_receipt_hash: str
    calibration_decision_hash: str
    calibration_profile_hash: str
    observation_count: int
    independent_source_count: int
    reason: str
    control_hash: str

    def __post_init__(self) -> None:
        if not self.project_scope.startswith("project://"):
            raise ValueError("contextual_calibration_project_scope_invalid")
        for name in ("context_key", "evidence_tier", "reason"):
            require_text(f"contextual_calibration_{name}", getattr(self, name))
        if self.policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("contextual_calibration_policy_invalid")
        if not isinstance(self.source_configured, bool):
            raise ValueError("contextual_calibration_source_configured_invalid")
        if self.calibration_state not in CONTEXTUAL_CALIBRATION_STATES:
            raise ValueError("contextual_calibration_state_invalid")
        if self.control_mode not in CONTEXTUAL_CALIBRATION_CONTROL_MODES:
            raise ValueError("contextual_calibration_control_mode_invalid")
        if not isinstance(self.prediction_trusted, bool):
            raise ValueError("contextual_calibration_prediction_trust_invalid")
        for name in ("observation_count", "independent_source_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"contextual_calibration_{name}_invalid")
        if self.independent_source_count > self.observation_count:
            raise ValueError("contextual_calibration_source_count_invalid")
        self._validate_state_contract()
        require_calibration_hash("contextual_calibration_control_hash", self.control_hash)
        if self.control_hash != hash_payload(self._committed_dict()):
            raise ValueError("contextual_calibration_control_hash_mismatch")

    def _validate_state_contract(self) -> None:
        empty_binding = not any(
            (
                self.calibration_receipt_ref,
                self.calibration_receipt_hash,
                self.calibration_decision_hash,
                self.calibration_profile_hash,
            )
        )
        if self.calibration_state in {"UNMONITORED", "NO_OBSERVATION"}:
            expected = {
                "UNMONITORED": (False, "LEGACY_COMPATIBLE"),
                "NO_OBSERVATION": (True, "EXPLORATION_ONLY"),
            }[self.calibration_state]
            if (
                (self.source_configured, self.control_mode) != expected
                or self.prediction_trusted
                or not empty_binding
                or self.observation_count
                or self.independent_source_count
            ):
                raise ValueError("contextual_calibration_empty_state_contract_invalid")
            return
        if not self.source_configured or empty_binding:
            raise ValueError("contextual_calibration_receipt_binding_required")
        for name in (
            "calibration_receipt_hash",
            "calibration_decision_hash",
            "calibration_profile_hash",
        ):
            require_calibration_hash(f"contextual_calibration_{name}", getattr(self, name))
        expected_ref = f"calibration://selector-receipt/{self.calibration_receipt_hash}"
        if self.calibration_receipt_ref != expected_ref:
            raise ValueError("contextual_calibration_receipt_ref_mismatch")
        expected_mode = {
            "INSUFFICIENT_HISTORY": "EXPLORATION_ONLY",
            "CALIBRATED": "TRUSTED",
            "WATCH": "EXPLORATION_ONLY",
            "DRIFTED": "BLOCKED",
        }[self.calibration_state]
        if self.control_mode != expected_mode:
            raise ValueError("contextual_calibration_state_mode_mismatch")
        if self.prediction_trusted != (self.calibration_state == "CALIBRATED"):
            raise ValueError("contextual_calibration_state_trust_mismatch")
        if self.observation_count < 1 or self.independent_source_count < 1:
            raise ValueError("contextual_calibration_observation_history_required")

    @classmethod
    def create(cls, **values: Any) -> "ContextualPolicyCalibrationControl":
        return cls(**values, control_hash=hash_payload(values))

    @classmethod
    def unmonitored(
        cls, *, project_scope: str, context_key: str, evidence_tier: str, policy_id: str
    ) -> "ContextualPolicyCalibrationControl":
        return cls._empty(
            project_scope=project_scope,
            context_key=context_key,
            evidence_tier=evidence_tier,
            policy_id=policy_id,
            source_configured=False,
            calibration_state="UNMONITORED",
            control_mode="LEGACY_COMPATIBLE",
            reason="calibration_source_not_configured",
        )

    @classmethod
    def no_observation(
        cls, *, project_scope: str, context_key: str, evidence_tier: str, policy_id: str
    ) -> "ContextualPolicyCalibrationControl":
        return cls._empty(
            project_scope=project_scope,
            context_key=context_key,
            evidence_tier=evidence_tier,
            policy_id=policy_id,
            source_configured=True,
            calibration_state="NO_OBSERVATION",
            control_mode="EXPLORATION_ONLY",
            reason="no_exact_scope_calibration_observation",
        )

    @classmethod
    def from_receipt(cls, receipt: SelectorCalibrationReceipt) -> "ContextualPolicyCalibrationControl":
        observation = receipt.observation
        decision = receipt.kernel_decision
        profile = receipt.profile
        return cls.create(
            project_scope=observation.project_scope,
            context_key=observation.context_key,
            evidence_tier=observation.evidence_tier,
            policy_id=observation.policy_id,
            source_configured=True,
            calibration_state=decision.final_state,
            control_mode={
                "INSUFFICIENT_HISTORY": "EXPLORATION_ONLY",
                "CALIBRATED": "TRUSTED",
                "WATCH": "EXPLORATION_ONLY",
                "DRIFTED": "BLOCKED",
            }[decision.final_state],
            prediction_trusted=decision.prediction_trusted,
            calibration_receipt_ref=f"calibration://selector-receipt/{receipt.receipt_hash}",
            calibration_receipt_hash=receipt.receipt_hash,
            calibration_decision_hash=decision.decision_hash,
            calibration_profile_hash=profile.profile_hash,
            observation_count=profile.observation_count,
            independent_source_count=profile.independent_source_count,
            reason=f"selector_calibration_{decision.final_state.lower()}",
        )

    @classmethod
    def _empty(cls, **values: Any) -> "ContextualPolicyCalibrationControl":
        return cls.create(
            **values,
            prediction_trusted=False,
            calibration_receipt_ref="",
            calibration_receipt_hash="",
            calibration_decision_hash="",
            calibration_profile_hash="",
            observation_count=0,
            independent_source_count=0,
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if key != "control_hash"}

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "control_hash": self.control_hash}
