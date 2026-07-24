"""Provider-backed semantic matcher for one bound witness-task pair."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import (
    GradedSROCompatibilityGate,
    CognitiveWorkControlDecision,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    SerialSelectionWitness,
)
from agentos_kernel.provider_cognition_layer import (
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .sro_retention_contracts import (
    SROCalibrationContract,
    SRORetentionRouteReceipt,
    SRORetentionTask,
    hash_payload,
    utc_now,
)


_PASS_PROVIDER_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}


class ProviderBackedSROMatcher:
    """Own Provider invocation, semantic audit, and receipt construction."""

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        matcher_router: ProviderTaskRouter,
        compatibility_gate: GradedSROCompatibilityGate,
        event_sink: Callable[[str, dict[str, Any]], None],
    ) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.matcher_router = matcher_router
        self.compatibility_gate = compatibility_gate
        self.event_sink = event_sink
        self._cognition = ProviderBackedRuntimeCognitionLayer()

    def route(
        self,
        witness: SerialSelectionWitness,
        task: SRORetentionTask,
        calibration: SROCalibrationContract,
        *,
        route_sequence: int,
        cognitive_work_control: CognitiveWorkControlDecision | None = None,
    ) -> SRORetentionRouteReceipt:
        allowed_evidence = tuple(
            dict.fromkeys((*witness.evidence_refs, *task.evidence_refs, *calibration.evidence_refs))
        )
        provider_task = self._build_task(witness, task, calibration, allowed_evidence, route_sequence)
        envelope = self.matcher_router.route(provider_task)
        semantic = self._require_semantic_result(envelope, allowed_evidence)
        provider_audit = self._audit_semantic_result(semantic, calibration, envelope)
        invocation = self._verify_invocation(envelope, provider_task, semantic)
        matcher_receipt = self._build_matcher_receipt(
            witness,
            task,
            calibration,
            semantic,
            provider_audit,
            invocation["receipt_hash"],
        )
        decision = self.compatibility_gate.evaluate(
            matcher_receipt,
            witness=witness,
            task_commitment_hash=task.task_commitment_hash,
            provider_invocation_receipt_hash=invocation["receipt_hash"],
            cognitive_work_control=cognitive_work_control,
        )
        route_id = f"sro-route-{hash_payload([witness.witness_id, task.task_id, invocation['receipt_hash']])[:16]}"
        return SRORetentionRouteReceipt(
            route_receipt_id=route_id,
            witness_id=witness.witness_id,
            witness_hash=witness.as_dict()["record_hash"],
            task_id=task.task_id,
            task_commitment_hash=task.task_commitment_hash,
            calibration_hash=calibration.as_dict()["calibration_hash"],
            provider_invocation_receipt=invocation,
            provider_audit=provider_audit,
            matcher_receipt=matcher_receipt,
            decision=decision.as_dict(),
            evidence_refs=tuple(semantic["evidence_refs"]),
            created_at=utc_now(),
        )

    def _build_task(
        self,
        witness: SerialSelectionWitness,
        task: SRORetentionTask,
        calibration: SROCalibrationContract,
        allowed_evidence: tuple[str, ...],
        route_sequence: int,
    ) -> ProviderCognitiveTask:
        return ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-sro-route-{route_sequence}",
            task_kind="graded_sro_retention_candidate_routing",
            objective=(
                "Estimate query-conditioned SRO compatibility for exactly one bound witness-task pair. Return "
                "calibrated five-route probabilities and semantic metrics only. Do not claim route authority, "
                "memory-write authority, production activation, or alter the supplied witness/task identities. "
                "confidence must equal the largest route probability. Cite only admitted evidence refs."
            ),
            inputs={
                "witness": witness.as_dict(),
                "target_task": task.as_dict(),
                "calibration_contract": calibration.as_dict(),
                "runtime_project_scope": self.project_scope,
            },
            allowed_evidence=list(allowed_evidence),
            expected_schema=self.provider_schema(),
            failure_semantics="block_sro_route_without_bound_provider_support",
        )

    def _require_semantic_result(self, envelope: Any, allowed_evidence: tuple[str, ...]) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._blocked(envelope)
            raise RuntimeError(f"sro_retention_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        if set(semantic) != set(self.provider_schema()["required"]):
            self._blocked(envelope)
            raise ValueError("sro_retention_provider_field_set_invalid")
        provider_refs = semantic.get("evidence_refs")
        if (
            not isinstance(provider_refs, list)
            or not provider_refs
            or len(provider_refs) != len(set(provider_refs))
            or not set(provider_refs).issubset(allowed_evidence)
        ):
            self._blocked(envelope)
            raise ValueError("sro_retention_provider_evidence_invalid")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(allowed_evidence):
            self._blocked(envelope)
            raise ValueError("sro_retention_provider_provenance_invalid")
        return semantic

    def _audit_semantic_result(
        self,
        semantic: dict[str, Any],
        calibration: SROCalibrationContract,
        envelope: Any,
    ) -> dict[str, Any]:
        support_receipt = dict(semantic)
        support_receipt["evidence_scope"] = calibration.evidence_scope
        provider_audit = self._cognition.audit_operation(
            "graded_sro_retention_candidate_routing",
            {
                "operation_id": "graded_sro_retention_candidate_routing",
                "provider_support_receipt": support_receipt,
                "provider_support_receipt_hash": hash_payload(support_receipt),
            },
        )
        if provider_audit.get("status") not in _PASS_PROVIDER_AUDITS:
            self._blocked(envelope, provider_audit=provider_audit)
            raise ValueError(f"sro_retention_provider_audit_failed:{provider_audit.get('status')}")
        return provider_audit

    def _verify_invocation(
        self,
        envelope: Any,
        provider_task: ProviderCognitiveTask,
        semantic: dict[str, Any],
    ) -> dict[str, Any]:
        invocation = envelope.invocation_receipt.as_dict()
        if (
            invocation.get("input_hash") != provider_task.contract_hash()
            or invocation.get("output_hash") != hash_payload(semantic)
        ):
            self._blocked(envelope)
            raise ValueError("sro_retention_provider_invocation_binding_invalid")
        return invocation

    def _build_matcher_receipt(
        self,
        witness: SerialSelectionWitness,
        task: SRORetentionTask,
        calibration: SROCalibrationContract,
        semantic: dict[str, Any],
        provider_audit: dict[str, Any],
        invocation_hash: str,
    ) -> dict[str, Any]:
        return {
            "matcher_id": calibration.matcher_id,
            "matcher_version": calibration.matcher_version,
            "task_id": task.task_id,
            "task_commitment_hash": task.task_commitment_hash,
            "witness_id": witness.witness_id,
            "witness_hash": witness.as_dict()["record_hash"],
            "project_scope_ref": self.project_scope,
            "scope": "project_scoped",
            "evidence_refs": semantic["evidence_refs"],
            "calibration_ref": calibration.calibration_ref,
            "calibration_status": calibration.calibration_status,
            "evidence_scope": calibration.evidence_scope,
            "provider_support_receipt_ref": f"provider-receipt://{invocation_hash}",
            "provider_invocation_receipt_hash": invocation_hash,
            "cognition_audit_hash": hash_payload(provider_audit),
            "replayable_evidence": True,
            **{key: value for key, value in semantic.items() if key != "evidence_refs"},
        }

    def _blocked(self, envelope: Any, *, provider_audit: dict[str, Any] | None = None) -> None:
        payload = {"provider_envelope": envelope.as_dict()}
        if provider_audit is not None:
            payload["provider_audit"] = provider_audit
        self.event_sink("SRO_PROVIDER_ROUTE_BLOCKED", payload)

    @staticmethod
    def provider_schema() -> dict[str, Any]:
        required = [
            "route_probabilities",
            "uncertainty",
            "drift_risk",
            "negative_transfer_risk",
            "structural_compatibility",
            "role_compatibility",
            "boundary_compatibility",
            "interface_compatibility",
            "trace_sufficiency",
            "calibration_error",
            "validity_state",
            "confidence",
            "evidence_refs",
        ]
        return {
            "type": "object",
            "required": required,
            "properties": {
                "route_probabilities": {"type": "object"},
                **{name: {"type": "number"} for name in required[1:10]},
                "validity_state": {"type": "string"},
                "confidence": {"type": "number"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
