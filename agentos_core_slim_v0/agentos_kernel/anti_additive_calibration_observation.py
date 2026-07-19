"""Prediction-outcome observation for Anti-Additive Methodology calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .anti_additive_base import ANTI_ADDITIVE_CHANGE_KINDS, require_anti_additive_id
from .contextual_policy_models import hash_payload, require_refs, require_text, require_unit


def _require_hash(name: str, value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name}_invalid")


def _require_signed_unit(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not -1 <= value <= 1:
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class AntiAdditiveCalibrationObservation:
    observation_id: str
    project_scope: str
    change_kind: str
    target_type: str
    methodology_receipt_hash: str
    methodology_decision_hash: str
    provider_judgment_hash: str
    candidate_hash: str
    candidate_payload_hash: str
    outcome_source_hash: str
    harness_receipt_hash: str
    predicted_effective_cbit_gain: float
    observed_effective_cbit_gain: float
    cbit_error: float
    predicted_complexity_cost: float
    observed_complexity_cost: float
    complexity_error: float
    predicted_object_upgrade_gain: float
    observed_object_upgrade_gain: float
    object_upgrade_error: float
    predicted_abstraction_cost: float
    observed_abstraction_cost: float
    abstraction_error: float
    object_lift_attempted: bool
    effective_margin_survived: bool
    object_upgrade_margin_survived: bool
    evidence_refs: tuple[str, ...]
    observation_hash: str

    def __post_init__(self) -> None:
        require_anti_additive_id("anti_additive_calibration_observation_id", self.observation_id)
        if not self.project_scope.startswith("project://"):
            raise ValueError("anti_additive_calibration_scope_invalid")
        if self.change_kind not in ANTI_ADDITIVE_CHANGE_KINDS:
            raise ValueError("anti_additive_calibration_change_kind_invalid")
        require_text("anti_additive_calibration_target_type", self.target_type)
        for name in (
            "methodology_receipt_hash", "methodology_decision_hash", "provider_judgment_hash",
            "candidate_hash", "candidate_payload_hash", "outcome_source_hash", "harness_receipt_hash",
            "observation_hash",
        ):
            _require_hash(f"anti_additive_calibration_{name}", getattr(self, name))
        for name in (
            "predicted_effective_cbit_gain", "observed_effective_cbit_gain",
            "predicted_complexity_cost", "observed_complexity_cost",
            "predicted_object_upgrade_gain", "observed_object_upgrade_gain",
            "predicted_abstraction_cost", "observed_abstraction_cost",
        ):
            require_unit(f"anti_additive_calibration_{name}", getattr(self, name))
        for name in ("cbit_error", "complexity_error", "object_upgrade_error", "abstraction_error"):
            _require_signed_unit(f"anti_additive_calibration_{name}", getattr(self, name))
        expected_errors = {
            "cbit_error": self.observed_effective_cbit_gain - self.predicted_effective_cbit_gain,
            "complexity_error": self.observed_complexity_cost - self.predicted_complexity_cost,
            "object_upgrade_error": self.observed_object_upgrade_gain - self.predicted_object_upgrade_gain,
            "abstraction_error": self.observed_abstraction_cost - self.predicted_abstraction_cost,
        }
        if any(abs(getattr(self, name) - expected) > 1e-9 for name, expected in expected_errors.items()):
            raise ValueError("anti_additive_calibration_error_mismatch")
        for name in ("object_lift_attempted", "effective_margin_survived", "object_upgrade_margin_survived"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"anti_additive_calibration_{name}_invalid")
        if self.effective_margin_survived != (
            self.observed_effective_cbit_gain > self.observed_complexity_cost
        ):
            raise ValueError("anti_additive_calibration_effective_margin_state_invalid")
        expected_upgrade = (
            not self.object_lift_attempted
            or self.observed_object_upgrade_gain > self.observed_abstraction_cost
        )
        if self.object_upgrade_margin_survived != expected_upgrade:
            raise ValueError("anti_additive_calibration_upgrade_margin_state_invalid")
        require_refs("anti_additive_calibration_evidence_refs", self.evidence_refs)
        if self.observation_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_calibration_observation_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveCalibrationObservation":
        committed = {**values, "evidence_refs": list(values["evidence_refs"])}
        return cls(**values, observation_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            key: (list(value) if key == "evidence_refs" else value)
            for key, value in self.__dict__.items()
            if key != "observation_hash"
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "observation_hash": self.observation_hash}
