"""Threshold and observation contracts for Selector calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contextual_policy_models import (
    CONTEXTUAL_POLICY_ROLE_MAP,
    hash_payload,
    require_refs,
    require_text,
    require_unit,
)
from .selector_calibration_base import require_calibration_hash, require_signed_unit


@dataclass(frozen=True)
class SelectorCalibrationThresholds:
    threshold_ref: str
    minimum_observations: int = 2
    cbit_mae_watch: float = 0.12
    cbit_mae_drift: float = 0.25
    cost_mae_watch: float = 0.12
    cost_mae_drift: float = 0.25
    absolute_bias_watch: float = 0.10
    absolute_bias_drift: float = 0.20
    coverage_watch_minimum: float = 0.75
    coverage_drift_minimum: float = 0.50
    provider_uncertainty_ceiling: float = 0.40

    def __post_init__(self) -> None:
        require_text("selector_calibration_threshold_ref", self.threshold_ref)
        if (
            not isinstance(self.minimum_observations, int)
            or isinstance(self.minimum_observations, bool)
            or self.minimum_observations < 2
        ):
            raise ValueError("selector_calibration_minimum_observations_invalid")
        for name in (
            "cbit_mae_watch",
            "cbit_mae_drift",
            "cost_mae_watch",
            "cost_mae_drift",
            "absolute_bias_watch",
            "absolute_bias_drift",
            "coverage_watch_minimum",
            "coverage_drift_minimum",
            "provider_uncertainty_ceiling",
        ):
            require_unit(f"selector_calibration_{name}", getattr(self, name))
        if self.cbit_mae_watch >= self.cbit_mae_drift:
            raise ValueError("selector_calibration_cbit_threshold_order_invalid")
        if self.cost_mae_watch >= self.cost_mae_drift:
            raise ValueError("selector_calibration_cost_threshold_order_invalid")
        if self.absolute_bias_watch >= self.absolute_bias_drift:
            raise ValueError("selector_calibration_bias_threshold_order_invalid")
        if self.coverage_drift_minimum >= self.coverage_watch_minimum:
            raise ValueError("selector_calibration_coverage_threshold_order_invalid")

    def as_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["threshold_hash"] = hash_payload(payload)
        return payload


@dataclass(frozen=True)
class SelectorCalibrationObservation:
    observation_id: str
    project_scope: str
    context_key: str
    evidence_tier: str
    policy_id: str
    selection_id: str
    selection_receipt_hash: str
    provider_advice_hash: str
    provider_assessment_hash: str
    feedback_receipt_hash: str
    request_hash: str
    execution_bundle_hash: str
    outcome_hash: str
    selected_agent_binding_hash: str
    trial_group_id: str
    trial_id: str
    trial_surface_hash: str
    source_result_hash: str
    harness_receipt_ref: str
    harness_receipt_hash: str
    execution_result_hash: str
    predicted_cbit_gain: float
    observed_cbit_gain: float
    cbit_error: float
    estimated_normalized_cost: float
    observed_normalized_cost: float
    cost_error: float
    provider_uncertainty: float
    cbit_within_uncertainty: bool
    predicted_residual_risk: float
    observed_negative_transfer_rate: float | None
    evidence_refs: tuple[str, ...]
    observation_hash: str

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "context_key",
            "evidence_tier",
            "selection_id",
            "trial_group_id",
            "trial_id",
            "harness_receipt_ref",
        ):
            require_text(f"selector_calibration_{name}", getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("selector_calibration_project_scope_invalid")
        if self.policy_id not in CONTEXTUAL_POLICY_ROLE_MAP:
            raise ValueError("selector_calibration_policy_id_invalid")
        for name in (
            "selection_receipt_hash",
            "provider_advice_hash",
            "provider_assessment_hash",
            "feedback_receipt_hash",
            "request_hash",
            "execution_bundle_hash",
            "outcome_hash",
            "selected_agent_binding_hash",
            "trial_surface_hash",
            "source_result_hash",
            "harness_receipt_hash",
            "execution_result_hash",
            "observation_hash",
        ):
            require_calibration_hash(f"selector_calibration_{name}", getattr(self, name))
        for name in (
            "predicted_cbit_gain",
            "observed_cbit_gain",
            "estimated_normalized_cost",
            "observed_normalized_cost",
            "provider_uncertainty",
            "predicted_residual_risk",
        ):
            require_unit(f"selector_calibration_{name}", getattr(self, name))
        require_signed_unit("selector_calibration_cbit_error", self.cbit_error)
        require_signed_unit("selector_calibration_cost_error", self.cost_error)
        if abs(self.cbit_error - (self.observed_cbit_gain - self.predicted_cbit_gain)) > 1e-9:
            raise ValueError("selector_calibration_cbit_error_mismatch")
        if abs(self.cost_error - (self.observed_normalized_cost - self.estimated_normalized_cost)) > 1e-9:
            raise ValueError("selector_calibration_cost_error_mismatch")
        expected_coverage = abs(self.cbit_error) <= self.provider_uncertainty + 1e-12
        if self.cbit_within_uncertainty != expected_coverage:
            raise ValueError("selector_calibration_uncertainty_coverage_mismatch")
        if self.observed_negative_transfer_rate is not None:
            require_unit(
                "selector_calibration_observed_negative_transfer_rate",
                self.observed_negative_transfer_rate,
            )
        if not isinstance(self.cbit_within_uncertainty, bool):
            raise ValueError("selector_calibration_uncertainty_coverage_invalid")
        require_refs("selector_calibration_observation_evidence_refs", self.evidence_refs)
        if self.observation_hash != hash_payload(self._committed_dict()):
            raise ValueError("selector_calibration_observation_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "SelectorCalibrationObservation":
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
