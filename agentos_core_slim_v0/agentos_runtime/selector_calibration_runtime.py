"""Thin Runtime facade for Selector prediction calibration and drift monitoring."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ProviderTaskRouter,
    SelectorCalibrationEvaluator,
    SelectorCalibrationGate,
    SelectorCalibrationReceipt,
    SelectorCalibrationThresholds,
)

from .contextual_policy_contracts import ContextualOrganizationSelectionReceipt
from .selection_feedback_contracts import SelectionExecutionFeedbackReceipt
from .selector_calibration_adapter import SelectorCalibrationObservationAdapter
from .selector_calibration_contracts import (
    SELECTOR_CALIBRATION_RUNTIME_VERSION,
    SelectorCalibrationSnapshot,
)
from .selector_calibration_provider import SelectorCalibrationProviderAdvisor
from .selector_calibration_repository import SelectorCalibrationRepository


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class SelectorCalibrationRuntime:
    """Compose receipt binding, metrics, Provider diagnosis, Kernel state, and replay."""

    module_id = SELECTOR_CALIBRATION_RUNTIME_VERSION
    capabilities = (
        "selector_prediction_outcome_binding",
        "exact_scope_calibration_profiles",
        "provider_supported_drift_diagnosis",
        "kernel_owned_prediction_trust_state",
        "append_only_calibration_replay",
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        provider_router: ProviderTaskRouter,
        workspace_root: str | Path,
        thresholds: SelectorCalibrationThresholds | None = None,
        evaluator: SelectorCalibrationEvaluator | None = None,
        gate: SelectorCalibrationGate | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime_id):
            raise ValueError("selector_calibration_runtime_id_invalid")
        if not project_scope.startswith("project://"):
            raise ValueError("selector_calibration_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.thresholds = thresholds or SelectorCalibrationThresholds(
            threshold_ref="threshold://selector-calibration/default-v0-1"
        )
        self.evaluator = evaluator or SelectorCalibrationEvaluator()
        self.gate = gate or SelectorCalibrationGate()
        self._adapter = SelectorCalibrationObservationAdapter()
        self._repository = SelectorCalibrationRepository(
            runtime_id=runtime_id,
            project_scope=project_scope,
            workspace_root=workspace_root,
        )
        self._provider = SelectorCalibrationProviderAdvisor(
            runtime_id=runtime_id,
            provider_router=provider_router,
            event_sink=self._repository.persist_event,
        )

    @property
    def public_store_path(self) -> Path:
        return self._repository.public_store_path

    def observe(
        self,
        *,
        calibration_id: str,
        selection: ContextualOrganizationSelectionReceipt,
        feedback: SelectionExecutionFeedbackReceipt,
        kernel_authorization_ref: str,
    ) -> SelectorCalibrationReceipt:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", calibration_id):
            raise ValueError("selector_calibration_id_invalid")
        if self._repository.receipt(calibration_id) is not None:
            raise ValueError(f"duplicate_selector_calibration:{calibration_id}")
        if selection.project_scope != self.project_scope:
            raise ValueError("selector_calibration_selection_scope_mismatch")
        try:
            observation = self._adapter.build(
                observation_id=f"observation-{calibration_id}",
                selection=selection,
                feedback=feedback,
            )
            prior = self._repository.observations(
                context_key=observation.context_key,
                evidence_tier=observation.evidence_tier,
                policy_id=observation.policy_id,
            )
            latest = self._repository.latest(
                context_key=observation.context_key,
                evidence_tier=observation.evidence_tier,
                policy_id=observation.policy_id,
            )
            if (
                latest is not None
                and latest.profile.threshold_hash != self.thresholds.as_dict()["threshold_hash"]
            ):
                raise ValueError("selector_calibration_lineage_threshold_change_forbidden")
            observations = (*prior, observation)
            profile = self.evaluator.evaluate(
                profile_id=f"profile-{calibration_id}",
                observations=observations,
                thresholds=self.thresholds,
            )
            judgment = self._provider.assess(
                calibration_id=calibration_id,
                profile=profile,
                observations=observations,
            )
            decision = self.gate.decide(
                decision_id=f"{calibration_id}-kernel",
                profile=profile,
                judgment=judgment,
                thresholds=self.thresholds,
                kernel_authorization_ref=kernel_authorization_ref,
            )
            receipt = SelectorCalibrationReceipt.create(
                calibration_id=calibration_id,
                runtime_id=self.runtime_id,
                observation=observation,
                profile=profile,
                provider_judgment=judgment,
                kernel_decision=decision,
                supersedes_receipt_hash=latest.receipt_hash if latest else "",
                created_at=_utc_now(),
            )
            self._repository.save(receipt)
            return receipt
        except Exception as exc:
            self._repository.persist_blocked(
                {
                    "calibration_id": calibration_id,
                    "selection_receipt_hash": selection.receipt_hash,
                    "feedback_receipt_hash": feedback.receipt_hash,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            raise

    def receipt(self, calibration_id: str) -> SelectorCalibrationReceipt | None:
        return self._repository.receipt(calibration_id)

    def latest(self, *, context_key: str, evidence_tier: str, policy_id: str):
        return self._repository.latest(
            context_key=context_key,
            evidence_tier=evidence_tier,
            policy_id=policy_id,
        )

    def snapshot(self) -> SelectorCalibrationSnapshot:
        return self._repository.snapshot()

    def verify_replay(self) -> dict[str, Any]:
        return self._repository.verify_replay()
