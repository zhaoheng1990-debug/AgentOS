"""Thin prediction-outcome calibration Runtime for Anti-Additive Methodology."""

from __future__ import annotations

import re
from pathlib import Path

from agentos_kernel import (
    ANTI_ADDITIVE_OBJECT_LEVELS,
    AntiAdditiveCalibrationEvaluator,
    AntiAdditiveCalibrationObservation,
    AntiAdditiveCalibrationReceipt,
    AntiAdditiveCalibrationThresholds,
    AntiAdditiveMethodologyReceipt,
)

from .anti_additive_calibration_repository import AntiAdditiveCalibrationRepository


class AntiAdditiveCalibrationRuntime:
    module_id = "anti_additive_prediction_outcome_calibration_runtime_v0_1"

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        workspace_root: str | Path,
        thresholds: AntiAdditiveCalibrationThresholds | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("anti_additive_calibration_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("anti_additive_calibration_runtime_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.thresholds = thresholds or AntiAdditiveCalibrationThresholds()
        self._evaluator = AntiAdditiveCalibrationEvaluator()
        self._repository = AntiAdditiveCalibrationRepository(
            runtime_id=runtime_id, project_scope=project_scope, workspace_root=workspace_root
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def record_outcome(
        self,
        *,
        calibration_id: str,
        observation_id: str,
        methodology_receipt: AntiAdditiveMethodologyReceipt,
        outcome_source_hash: str,
        harness_receipt_hash: str,
        observed_effective_cbit_gain: float,
        observed_complexity_cost: float,
        observed_object_upgrade_gain: float,
        observed_abstraction_cost: float,
        evidence_refs: tuple[str, ...],
        kernel_authorization_ref: str,
    ) -> AntiAdditiveCalibrationReceipt:
        candidate = methodology_receipt.candidate
        judgment = methodology_receipt.provider_judgment
        if candidate.project_scope != self.project_scope:
            raise ValueError("anti_additive_calibration_cross_scope_receipt")
        if methodology_receipt.decision.allowed is not True:
            raise ValueError("anti_additive_calibration_requires_executed_allowed_change")
        if not set(candidate.evidence_refs).issubset(evidence_refs):
            raise ValueError("anti_additive_calibration_outcome_must_preserve_evidence")
        if methodology_receipt.receipt_hash in {
            item.methodology_receipt_hash for item in self._repository.observations()
        }:
            raise ValueError("anti_additive_calibration_duplicate_methodology_receipt")
        lift = ANTI_ADDITIVE_OBJECT_LEVELS.index(candidate.proposed_object_level) > ANTI_ADDITIVE_OBJECT_LEVELS.index(candidate.current_object_level)
        observation = AntiAdditiveCalibrationObservation.create(
            observation_id=observation_id,
            project_scope=candidate.project_scope,
            change_kind=candidate.change_kind,
            target_type=candidate.target_type,
            methodology_receipt_hash=methodology_receipt.receipt_hash,
            methodology_decision_hash=methodology_receipt.decision.decision_hash,
            provider_judgment_hash=judgment.judgment_hash,
            candidate_hash=candidate.candidate_hash,
            candidate_payload_hash=candidate.candidate_payload_hash,
            outcome_source_hash=outcome_source_hash,
            harness_receipt_hash=harness_receipt_hash,
            predicted_effective_cbit_gain=judgment.expected_effective_cbit_gain,
            observed_effective_cbit_gain=observed_effective_cbit_gain,
            cbit_error=observed_effective_cbit_gain - judgment.expected_effective_cbit_gain,
            predicted_complexity_cost=judgment.complexity_cost,
            observed_complexity_cost=observed_complexity_cost,
            complexity_error=observed_complexity_cost - judgment.complexity_cost,
            predicted_object_upgrade_gain=judgment.object_upgrade_gain,
            observed_object_upgrade_gain=observed_object_upgrade_gain,
            object_upgrade_error=observed_object_upgrade_gain - judgment.object_upgrade_gain,
            predicted_abstraction_cost=judgment.abstraction_cost,
            observed_abstraction_cost=observed_abstraction_cost,
            abstraction_error=observed_abstraction_cost - judgment.abstraction_cost,
            object_lift_attempted=lift,
            effective_margin_survived=observed_effective_cbit_gain > observed_complexity_cost,
            object_upgrade_margin_survived=(not lift or observed_object_upgrade_gain > observed_abstraction_cost),
            evidence_refs=evidence_refs,
        )
        prior = tuple(
            item for item in self._repository.observations()
            if (item.project_scope, item.change_kind, item.target_type)
            == (candidate.project_scope, candidate.change_kind, candidate.target_type)
        )
        profile, decision = self._evaluator.evaluate(
            calibration_id=calibration_id,
            observations=(*prior, observation),
            thresholds=self.thresholds,
            kernel_authorization_ref=kernel_authorization_ref,
        )
        receipt = AntiAdditiveCalibrationReceipt.create(
            observation=observation, profile=profile, decision=decision
        )
        self._repository.save(receipt)
        return receipt

    def latest_calibration_receipt(self, **scope):
        return self._repository.latest_calibration_receipt(**scope)

    def verify_replay(self):
        return self._repository.verify_replay()
