"""Provider semantic support for Selector calibration drift diagnosis."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import (
    SELECTOR_CALIBRATION_ACTIONS,
    SELECTOR_DIAGNOSTIC_STATES,
    SELECTOR_DRIFT_DRIVERS,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    SelectorCalibrationObservation,
    SelectorCalibrationProfile,
    SelectorCalibrationProviderJudgment,
)
from agentos_kernel.contextual_policy_models import hash_payload, require_unit
from agentos_kernel.provider_cognition_layer import (
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED


_PASS_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}
_FIELDS = {
    "diagnostic_state",
    "drift_drivers",
    "recommended_action",
    "uncertainty",
    "rationale",
    "evidence_refs",
}


class SelectorCalibrationProviderAdvisor:
    """Diagnose semantic drift while withholding calibration state authority."""

    def __init__(
        self,
        *,
        runtime_id: str,
        provider_router: ProviderTaskRouter,
        event_sink: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self.runtime_id = runtime_id
        self.provider_router = provider_router
        self.event_sink = event_sink
        self._cognition = ProviderBackedRuntimeCognitionLayer()

    def assess(
        self,
        *,
        calibration_id: str,
        profile: SelectorCalibrationProfile,
        observations: tuple[SelectorCalibrationObservation, ...],
    ) -> SelectorCalibrationProviderJudgment:
        allowed = tuple(
            dict.fromkeys(
                (
                    profile.evidence_ref,
                    *(ref for item in observations for ref in item.evidence_refs),
                )
            )
        )
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-{calibration_id}-drift-assessment",
            task_kind="selector_calibration_drift_assessment",
            objective=(
                "Diagnose whether this exact project/context/evidence-tier/policy calibration profile shows "
                "semantic scope, evidence, model, Harness, Cbit, cost, or residual-risk drift. Use only the "
                "frozen observations and profile. Return advisory diagnosis; do not alter metrics, thresholds, "
                "Kernel state, Selector policy, or execution authority."
            ),
            inputs={
                "calibration_profile": profile.as_dict(),
                "observations": [item.as_dict() for item in observations],
            },
            allowed_evidence=list(allowed),
            expected_schema=self.provider_schema(),
            failure_semantics="keep_selector_calibration_pending_without_provider_diagnosis",
            budget={"max_provider_calls": 1},
        )
        envelope = self.provider_router.route(task)
        semantic = self._semantic(envelope, profile, allowed)
        audit = self._cognition.audit_operation(
            "selector_calibration_drift_assessment",
            {
                "operation_id": "selector_calibration_drift_assessment",
                "provider_support_receipt": semantic,
                "provider_support_receipt_hash": hash_payload(semantic),
            },
        )
        if audit.get("status") not in _PASS_AUDITS:
            self._blocked(envelope, provider_audit=audit)
            raise ValueError(f"selector_calibration_provider_audit_failed:{audit.get('status')}")
        invocation = envelope.invocation_receipt.as_dict()
        if invocation.get("input_hash") != task.contract_hash() or invocation.get("output_hash") != hash_payload(semantic):
            self._blocked(envelope, provider_audit=audit)
            raise ValueError("selector_calibration_provider_invocation_binding_invalid")
        return SelectorCalibrationProviderJudgment.create(
            profile_hash=profile.profile_hash,
            diagnostic_state=semantic["diagnostic_state"],
            drift_drivers=tuple(semantic["drift_drivers"]),
            recommended_action=semantic["recommended_action"],
            uncertainty=float(semantic["uncertainty"]),
            rationale=semantic["rationale"],
            evidence_refs=tuple(semantic["evidence_refs"]),
            provider_invocation_receipt=invocation,
            provider_audit=audit,
        )

    def _semantic(
        self,
        envelope: Any,
        profile: SelectorCalibrationProfile,
        allowed: tuple[str, ...],
    ) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._blocked(envelope)
            raise RuntimeError(f"selector_calibration_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        if set(semantic) != _FIELDS:
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_field_set_invalid")
        if semantic.get("diagnostic_state") not in SELECTOR_DIAGNOSTIC_STATES:
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_diagnostic_state_invalid")
        drivers = semantic.get("drift_drivers")
        if (
            not isinstance(drivers, list)
            or len(drivers) != len(set(drivers))
            or not set(drivers).issubset(SELECTOR_DRIFT_DRIVERS)
        ):
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_drift_drivers_invalid")
        if semantic.get("recommended_action") not in SELECTOR_CALIBRATION_ACTIONS:
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_action_invalid")
        try:
            require_unit("selector_calibration_provider_uncertainty", semantic.get("uncertainty"))
        except ValueError:
            self._blocked(envelope)
            raise
        refs = semantic.get("evidence_refs")
        if not self._refs_valid(refs, allowed) or profile.evidence_ref not in refs:
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_evidence_invalid")
        if not isinstance(semantic.get("rationale"), str) or not semantic["rationale"].strip():
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_rationale_required")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(allowed):
            self._blocked(envelope)
            raise ValueError("selector_calibration_provider_provenance_invalid")
        return semantic

    def _blocked(self, envelope: Any, *, provider_audit: dict[str, Any] | None = None) -> None:
        payload = {"provider_envelope": envelope.as_dict()}
        if provider_audit is not None:
            payload["provider_audit"] = provider_audit
        self.event_sink("SELECTOR_CALIBRATION_PROVIDER_BLOCKED", payload)

    @staticmethod
    def _refs_valid(refs: Any, allowed: tuple[str, ...]) -> bool:
        return bool(
            isinstance(refs, list)
            and refs
            and len(refs) == len(set(refs))
            and set(refs).issubset(allowed)
        )

    @staticmethod
    def provider_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": sorted(_FIELDS),
            "properties": {
                "diagnostic_state": {"type": "string"},
                "drift_drivers": {"type": "array", "items": {"type": "string"}},
                "recommended_action": {"type": "string"},
                "uncertainty": {"type": "number"},
                "rationale": {"type": "string"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
