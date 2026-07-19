"""Profiles, decisions, and receipts for Anti-Additive prediction calibration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .anti_additive_base import ANTI_ADDITIVE_CHANGE_KINDS, require_anti_additive_id
from .anti_additive_calibration_observation import AntiAdditiveCalibrationObservation, _require_hash
from .anti_additive_control import ANTI_ADDITIVE_CALIBRATION_STATES
from .contextual_policy_models import hash_payload, require_text, require_unit


ANTI_ADDITIVE_CALIBRATION_VERSION = "anti_additive_prediction_outcome_calibration_v0_1"


@dataclass(frozen=True)
class AntiAdditiveCalibrationThresholds:
    threshold_ref: str = "calibration://anti-additive/default-v0.1"
    minimum_observations: int = 2
    mean_absolute_error_watch: float = 0.15
    mean_absolute_error_drift: float = 0.30
    margin_survival_watch_minimum: float = 0.75
    margin_survival_drift_minimum: float = 0.50

    def __post_init__(self) -> None:
        require_text("anti_additive_calibration_threshold_ref", self.threshold_ref)
        if not isinstance(self.minimum_observations, int) or self.minimum_observations < 2:
            raise ValueError("anti_additive_calibration_minimum_observations_invalid")
        for name in (
            "mean_absolute_error_watch", "mean_absolute_error_drift",
            "margin_survival_watch_minimum", "margin_survival_drift_minimum",
        ):
            require_unit(f"anti_additive_calibration_{name}", getattr(self, name))
        if self.mean_absolute_error_watch >= self.mean_absolute_error_drift:
            raise ValueError("anti_additive_calibration_error_threshold_order_invalid")
        if self.margin_survival_drift_minimum >= self.margin_survival_watch_minimum:
            raise ValueError("anti_additive_calibration_survival_threshold_order_invalid")

    def as_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["threshold_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class AntiAdditiveCalibrationProfile:
    profile_id: str
    project_scope: str
    change_kind: str
    target_type: str
    observation_count: int
    independent_source_count: int
    mean_absolute_cbit_error: float
    mean_absolute_complexity_error: float
    mean_absolute_object_upgrade_error: float
    mean_absolute_abstraction_error: float
    effective_margin_survival_rate: float
    object_upgrade_margin_survival_rate: float
    mechanical_state: str
    observation_hashes: tuple[str, ...]
    outcome_source_hashes: tuple[str, ...]
    threshold_hash: str
    profile_hash: str

    def __post_init__(self) -> None:
        require_anti_additive_id("anti_additive_calibration_profile_id", self.profile_id)
        if not self.project_scope.startswith("project://"):
            raise ValueError("anti_additive_calibration_profile_scope_invalid")
        if self.change_kind not in ANTI_ADDITIVE_CHANGE_KINDS:
            raise ValueError("anti_additive_calibration_profile_change_kind_invalid")
        require_text("anti_additive_calibration_profile_target_type", self.target_type)
        if self.mechanical_state not in ANTI_ADDITIVE_CALIBRATION_STATES[2:]:
            raise ValueError("anti_additive_calibration_profile_state_invalid")
        for name in ("observation_count", "independent_source_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"anti_additive_calibration_profile_{name}_invalid")
        if self.independent_source_count > self.observation_count:
            raise ValueError("anti_additive_calibration_profile_source_count_invalid")
        for name in (
            "mean_absolute_cbit_error", "mean_absolute_complexity_error",
            "mean_absolute_object_upgrade_error", "mean_absolute_abstraction_error",
            "effective_margin_survival_rate", "object_upgrade_margin_survival_rate",
        ):
            require_unit(f"anti_additive_calibration_profile_{name}", getattr(self, name))
        if len(self.observation_hashes) != self.observation_count:
            raise ValueError("anti_additive_calibration_profile_observation_count_mismatch")
        if len(self.outcome_source_hashes) != self.independent_source_count:
            raise ValueError("anti_additive_calibration_profile_source_count_mismatch")
        for value in (*self.observation_hashes, *self.outcome_source_hashes, self.threshold_hash):
            _require_hash("anti_additive_calibration_profile_hash_ref", value)
        if self.profile_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_calibration_profile_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveCalibrationProfile":
        committed = {
            **values,
            "observation_hashes": list(values["observation_hashes"]),
            "outcome_source_hashes": list(values["outcome_source_hashes"]),
        }
        return cls(**values, profile_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        payload = {key: value for key, value in self.__dict__.items() if key != "profile_hash"}
        payload["observation_hashes"] = list(self.observation_hashes)
        payload["outcome_source_hashes"] = list(self.outcome_source_hashes)
        return payload

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "profile_hash": self.profile_hash}


@dataclass(frozen=True)
class AntiAdditiveCalibrationDecision:
    calibration_id: str
    project_scope: str
    change_kind: str
    target_type: str
    profile_hash: str
    state: str
    reason: str
    kernel_authorization_ref: str
    decision_hash: str

    def __post_init__(self) -> None:
        require_anti_additive_id("anti_additive_calibration_id", self.calibration_id)
        if not self.project_scope.startswith("project://"):
            raise ValueError("anti_additive_calibration_decision_scope_invalid")
        if self.change_kind not in ANTI_ADDITIVE_CHANGE_KINDS:
            raise ValueError("anti_additive_calibration_decision_change_kind_invalid")
        require_text("anti_additive_calibration_decision_target_type", self.target_type)
        _require_hash("anti_additive_calibration_decision_profile_hash", self.profile_hash)
        if self.state not in ANTI_ADDITIVE_CALIBRATION_STATES[2:]:
            raise ValueError("anti_additive_calibration_decision_state_invalid")
        require_text("anti_additive_calibration_decision_reason", self.reason)
        if not self.kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("anti_additive_calibration_kernel_authorization_required")
        if self.decision_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_calibration_decision_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveCalibrationDecision":
        return cls(**values, decision_hash=hash_payload(values))

    def _committed_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if key != "decision_hash"}

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "decision_hash": self.decision_hash}


@dataclass(frozen=True)
class AntiAdditiveCalibrationReceipt:
    observation: AntiAdditiveCalibrationObservation
    profile: AntiAdditiveCalibrationProfile
    decision: AntiAdditiveCalibrationDecision
    created_at: str
    receipt_hash: str

    def __post_init__(self) -> None:
        if self.observation.observation_hash not in self.profile.observation_hashes:
            raise ValueError("anti_additive_calibration_receipt_observation_binding_invalid")
        if self.decision.profile_hash != self.profile.profile_hash:
            raise ValueError("anti_additive_calibration_receipt_profile_binding_invalid")
        scope = (self.observation.project_scope, self.observation.change_kind, self.observation.target_type)
        if scope != (self.profile.project_scope, self.profile.change_kind, self.profile.target_type) or scope != (
            self.decision.project_scope, self.decision.change_kind, self.decision.target_type,
        ):
            raise ValueError("anti_additive_calibration_receipt_scope_binding_invalid")
        if self.receipt_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_calibration_receipt_hash_mismatch")

    @classmethod
    def create(cls, *, observation, profile, decision) -> "AntiAdditiveCalibrationReceipt":
        created_at = datetime.now(timezone.utc).astimezone().isoformat()
        committed = {
            "observation": observation.as_dict(),
            "profile": profile.as_dict(),
            "decision": decision.as_dict(),
            "created_at": created_at,
        }
        return cls(
            observation=observation,
            profile=profile,
            decision=decision,
            created_at=created_at,
            receipt_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "observation": self.observation.as_dict(),
            "profile": self.profile.as_dict(),
            "decision": self.decision.as_dict(),
            "created_at": self.created_at,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "receipt_hash": self.receipt_hash}
