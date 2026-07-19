"""Mechanical aggregation and state selection for Anti-Additive calibration."""

from __future__ import annotations

from statistics import fmean

from .anti_additive_calibration_models import (
    AntiAdditiveCalibrationDecision,
    AntiAdditiveCalibrationProfile,
    AntiAdditiveCalibrationThresholds,
)
from .anti_additive_calibration_observation import AntiAdditiveCalibrationObservation


class AntiAdditiveCalibrationEvaluator:
    def evaluate(
        self,
        *,
        calibration_id: str,
        observations: tuple[AntiAdditiveCalibrationObservation, ...],
        thresholds: AntiAdditiveCalibrationThresholds,
        kernel_authorization_ref: str,
    ) -> tuple[AntiAdditiveCalibrationProfile, AntiAdditiveCalibrationDecision]:
        if not observations:
            raise ValueError("anti_additive_calibration_observations_required")
        first = observations[0]
        binding = (first.project_scope, first.change_kind, first.target_type)
        if any((item.project_scope, item.change_kind, item.target_type) != binding for item in observations):
            raise ValueError("anti_additive_calibration_cross_scope_pooling_forbidden")
        if len({item.observation_hash for item in observations}) != len(observations):
            raise ValueError("anti_additive_calibration_duplicate_observation")
        sources = tuple(sorted({item.outcome_source_hash for item in observations}))
        metrics = {
            "mean_absolute_cbit_error": fmean(abs(item.cbit_error) for item in observations),
            "mean_absolute_complexity_error": fmean(abs(item.complexity_error) for item in observations),
            "mean_absolute_object_upgrade_error": fmean(abs(item.object_upgrade_error) for item in observations),
            "mean_absolute_abstraction_error": fmean(abs(item.abstraction_error) for item in observations),
            "effective_margin_survival_rate": fmean(float(item.effective_margin_survived) for item in observations),
            "object_upgrade_margin_survival_rate": fmean(float(item.object_upgrade_margin_survived) for item in observations),
        }
        state = self._state(len(observations), len(sources), metrics, thresholds)
        profile = AntiAdditiveCalibrationProfile.create(
            profile_id=f"profile-{calibration_id}",
            project_scope=first.project_scope,
            change_kind=first.change_kind,
            target_type=first.target_type,
            observation_count=len(observations),
            independent_source_count=len(sources),
            mechanical_state=state,
            observation_hashes=tuple(item.observation_hash for item in observations),
            outcome_source_hashes=sources,
            threshold_hash=thresholds.as_dict()["threshold_hash"],
            **metrics,
        )
        decision = AntiAdditiveCalibrationDecision.create(
            calibration_id=calibration_id,
            project_scope=first.project_scope,
            change_kind=first.change_kind,
            target_type=first.target_type,
            profile_hash=profile.profile_hash,
            state=state,
            reason=f"anti_additive_prediction_outcome_profile_{state.lower()}",
            kernel_authorization_ref=kernel_authorization_ref,
        )
        return profile, decision

    @staticmethod
    def _state(count, source_count, metrics, thresholds):
        if count < thresholds.minimum_observations or source_count < thresholds.minimum_observations:
            return "INSUFFICIENT_HISTORY"
        errors = (
            metrics["mean_absolute_cbit_error"],
            metrics["mean_absolute_complexity_error"],
            metrics["mean_absolute_object_upgrade_error"],
            metrics["mean_absolute_abstraction_error"],
        )
        survivals = (
            metrics["effective_margin_survival_rate"],
            metrics["object_upgrade_margin_survival_rate"],
        )
        if max(errors) >= thresholds.mean_absolute_error_drift or min(survivals) < thresholds.margin_survival_drift_minimum:
            return "DRIFTED"
        if max(errors) >= thresholds.mean_absolute_error_watch or min(survivals) < thresholds.margin_survival_watch_minimum:
            return "WATCH"
        return "CALIBRATED"
