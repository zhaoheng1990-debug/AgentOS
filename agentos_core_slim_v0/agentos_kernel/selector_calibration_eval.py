"""Mechanical aggregation for exact-scope Selector calibration observations."""

from __future__ import annotations

from statistics import fmean

from .selector_calibration_models import (
    SelectorCalibrationObservation,
    SelectorCalibrationProfile,
    SelectorCalibrationThresholds,
)


class SelectorCalibrationEvaluator:
    """Aggregate predictions and outcomes without performing semantic diagnosis."""

    def evaluate(
        self,
        *,
        profile_id: str,
        observations: tuple[SelectorCalibrationObservation, ...],
        thresholds: SelectorCalibrationThresholds,
    ) -> SelectorCalibrationProfile:
        if not observations:
            raise ValueError("selector_calibration_observations_required")
        first = observations[0]
        binding = (first.project_scope, first.context_key, first.evidence_tier, first.policy_id)
        if any(
            (item.project_scope, item.context_key, item.evidence_tier, item.policy_id) != binding
            for item in observations
        ):
            raise ValueError("selector_calibration_cross_scope_pooling_forbidden")
        if len({item.observation_hash for item in observations}) != len(observations):
            raise ValueError("selector_calibration_duplicate_observation")
        sources = tuple(sorted({item.source_result_hash for item in observations}))
        cbit_mae = fmean(abs(item.cbit_error) for item in observations)
        cost_mae = fmean(abs(item.cost_error) for item in observations)
        cbit_bias = fmean(item.cbit_error for item in observations)
        cost_bias = fmean(item.cost_error for item in observations)
        coverage = fmean(float(item.cbit_within_uncertainty) for item in observations)
        residual_errors = tuple(
            item.observed_negative_transfer_rate - item.predicted_residual_risk
            for item in observations
            if item.observed_negative_transfer_rate is not None
        )
        state = self._mechanical_state(
            observation_count=len(observations),
            independent_source_count=len(sources),
            cbit_mae=cbit_mae,
            cost_mae=cost_mae,
            cbit_bias=cbit_bias,
            cost_bias=cost_bias,
            coverage=coverage,
            thresholds=thresholds,
        )
        return SelectorCalibrationProfile.create(
            profile_id=profile_id,
            project_scope=first.project_scope,
            context_key=first.context_key,
            evidence_tier=first.evidence_tier,
            policy_id=first.policy_id,
            observation_count=len(observations),
            independent_source_count=len(sources),
            mean_absolute_cbit_error=cbit_mae,
            mean_cbit_bias=cbit_bias,
            mean_absolute_cost_error=cost_mae,
            mean_cost_bias=cost_bias,
            cbit_uncertainty_coverage=coverage,
            mean_residual_risk_error=fmean(residual_errors) if residual_errors else None,
            mechanical_state=state,
            observation_hashes=tuple(item.observation_hash for item in observations),
            source_result_hashes=sources,
            threshold_hash=thresholds.as_dict()["threshold_hash"],
        )

    @staticmethod
    def _mechanical_state(
        *,
        observation_count: int,
        independent_source_count: int,
        cbit_mae: float,
        cost_mae: float,
        cbit_bias: float,
        cost_bias: float,
        coverage: float,
        thresholds: SelectorCalibrationThresholds,
    ) -> str:
        if (
            observation_count < thresholds.minimum_observations
            or independent_source_count < thresholds.minimum_observations
        ):
            return "INSUFFICIENT_HISTORY"
        if (
            cbit_mae >= thresholds.cbit_mae_drift
            or cost_mae >= thresholds.cost_mae_drift
            or abs(cbit_bias) >= thresholds.absolute_bias_drift
            or abs(cost_bias) >= thresholds.absolute_bias_drift
            or coverage < thresholds.coverage_drift_minimum
        ):
            return "DRIFTED"
        if (
            cbit_mae >= thresholds.cbit_mae_watch
            or cost_mae >= thresholds.cost_mae_watch
            or abs(cbit_bias) >= thresholds.absolute_bias_watch
            or abs(cost_bias) >= thresholds.absolute_bias_watch
            or coverage < thresholds.coverage_watch_minimum
        ):
            return "WATCH"
        return "CALIBRATED"
