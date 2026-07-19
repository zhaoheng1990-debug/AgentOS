"""Calibration control consumed by Anti-Additive Methodology decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .anti_additive_base import ANTI_ADDITIVE_CHANGE_KINDS
from .contextual_policy_models import hash_payload, require_text


ANTI_ADDITIVE_CALIBRATION_STATES = (
    "UNMONITORED",
    "NO_OBSERVATION",
    "INSUFFICIENT_HISTORY",
    "CALIBRATED",
    "WATCH",
    "DRIFTED",
)
ANTI_ADDITIVE_CONTROL_MODES = (
    "LEGACY_COMPATIBLE",
    "EXPLORATION_ONLY",
    "TRUSTED",
    "BLOCKED",
)


@dataclass(frozen=True)
class AntiAdditiveCalibrationControl:
    project_scope: str
    change_kind: str
    target_type: str
    source_configured: bool
    calibration_state: str
    control_mode: str
    calibration_receipt_hash: str
    profile_hash: str
    decision_hash: str
    observation_count: int
    independent_source_count: int
    reason: str
    control_hash: str

    def __post_init__(self) -> None:
        if not self.project_scope.startswith("project://"):
            raise ValueError("anti_additive_control_scope_invalid")
        if self.change_kind not in ANTI_ADDITIVE_CHANGE_KINDS:
            raise ValueError("anti_additive_control_change_kind_invalid")
        require_text("anti_additive_control_target_type", self.target_type)
        if not isinstance(self.source_configured, bool):
            raise ValueError("anti_additive_control_source_configured_invalid")
        if self.calibration_state not in ANTI_ADDITIVE_CALIBRATION_STATES:
            raise ValueError("anti_additive_control_state_invalid")
        if self.control_mode not in ANTI_ADDITIVE_CONTROL_MODES:
            raise ValueError("anti_additive_control_mode_invalid")
        for name in ("observation_count", "independent_source_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"anti_additive_control_{name}_invalid")
        for name in ("calibration_receipt_hash", "profile_hash", "decision_hash"):
            value = getattr(self, name)
            if value and (len(value) != 64 or any(char not in "0123456789abcdef" for char in value)):
                raise ValueError(f"anti_additive_control_{name}_invalid")
        if self.source_configured is False and (
            self.calibration_state != "UNMONITORED"
            or self.control_mode != "LEGACY_COMPATIBLE"
        ):
            raise ValueError("anti_additive_control_legacy_state_invalid")
        if self.source_configured and self.calibration_state == "UNMONITORED":
            raise ValueError("anti_additive_control_configured_state_invalid")
        expected_mode = {
            "UNMONITORED": "LEGACY_COMPATIBLE",
            "NO_OBSERVATION": "EXPLORATION_ONLY",
            "INSUFFICIENT_HISTORY": "EXPLORATION_ONLY",
            "CALIBRATED": "TRUSTED",
            "WATCH": "EXPLORATION_ONLY",
            "DRIFTED": "BLOCKED",
        }[self.calibration_state]
        if self.control_mode != expected_mode:
            raise ValueError("anti_additive_control_mode_state_mismatch")
        require_text("anti_additive_control_reason", self.reason)
        if self.control_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_control_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveCalibrationControl":
        return cls(**values, control_hash=hash_payload(values))

    @classmethod
    def unmonitored(cls, *, project_scope: str, change_kind: str, target_type: str):
        return cls.create(
            project_scope=project_scope,
            change_kind=change_kind,
            target_type=target_type,
            source_configured=False,
            calibration_state="UNMONITORED",
            control_mode="LEGACY_COMPATIBLE",
            calibration_receipt_hash="",
            profile_hash="",
            decision_hash="",
            observation_count=0,
            independent_source_count=0,
            reason="no_calibration_source_configured",
        )

    @classmethod
    def no_observation(cls, *, project_scope: str, change_kind: str, target_type: str):
        return cls.create(
            project_scope=project_scope,
            change_kind=change_kind,
            target_type=target_type,
            source_configured=True,
            calibration_state="NO_OBSERVATION",
            control_mode="EXPLORATION_ONLY",
            calibration_receipt_hash="",
            profile_hash="",
            decision_hash="",
            observation_count=0,
            independent_source_count=0,
            reason="configured_calibration_source_has_no_exact_scope_receipt",
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if key != "control_hash"}

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "control_hash": self.control_hash}
