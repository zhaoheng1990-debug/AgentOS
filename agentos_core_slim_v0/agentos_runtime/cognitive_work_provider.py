"""Provider semantic support for one cognitive-work round."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import (
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
)
from agentos_kernel.cognitive_work_models import (
    COGNITIVE_WORK_ACTIONS,
    CognitiveWorkRoundObservation,
    CognitiveWorkSemanticAssessment,
    hash_payload,
)
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
    "evidence_novelty",
    "constraint_coverage",
    "hypothesis_diversity",
    "redundancy",
    "error_correlation",
    "problem_drift",
    "uncertainty",
    "recommended_action",
    "rationale",
    "evidence_refs",
}


class CognitiveWorkProviderAdvisor:
    """Supply bounded semantic diagnostics without stop or scheduling authority."""

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
        observation: CognitiveWorkRoundObservation,
        *,
        prior_control: dict[str, Any] | None,
    ) -> tuple[CognitiveWorkSemanticAssessment, dict[str, Any], dict[str, Any]]:
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-{observation.observation_id}-semantic",
            task_kind="cognitive_work_round_assessment",
            objective=(
                "Assess new evidence, constraint coverage, hypothesis diversity, redundancy, correlated error, "
                "problem drift, and uncertainty for one cognitive-work round. Recommend a bounded next action "
                "without claiming scheduling, retention, memory-write, or final Kernel authority."
            ),
            inputs={
                "mechanical_observation": observation.as_dict(),
                "prior_kernel_control": prior_control or {},
            },
            allowed_evidence=list(observation.evidence_refs),
            expected_schema=self.provider_schema(),
            budget={"max_provider_calls": 1},
            failure_semantics="block_round_accounting_without_semantic_support",
        )
        envelope = self.provider_router.route(task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._blocked(envelope)
            raise RuntimeError(f"cognitive_work_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        if set(semantic) != _FIELDS:
            self._blocked(envelope)
            raise ValueError("cognitive_work_provider_field_set_invalid")
        refs = semantic.get("evidence_refs")
        if not self._refs_valid(refs, observation.evidence_refs):
            self._blocked(envelope)
            raise ValueError("cognitive_work_provider_evidence_invalid")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(observation.evidence_refs):
            self._blocked(envelope)
            raise ValueError("cognitive_work_provider_provenance_invalid")
        if semantic.get("recommended_action") not in COGNITIVE_WORK_ACTIONS:
            self._blocked(envelope)
            raise ValueError("cognitive_work_provider_action_invalid")
        assessment = CognitiveWorkSemanticAssessment(
            **{**semantic, "evidence_refs": tuple(refs)}
        )
        invocation = envelope.invocation_receipt.as_dict()
        if invocation.get("input_hash") != task.contract_hash() or invocation.get("output_hash") != hash_payload(semantic):
            self._blocked(envelope)
            raise ValueError("cognitive_work_provider_invocation_binding_invalid")
        audit = self._cognition.audit_operation(
            "cognitive_work_round_assessment",
            {
                "operation_id": "cognitive_work_round_assessment",
                "provider_support_receipt": semantic,
                "provider_support_receipt_hash": hash_payload(semantic),
            },
        )
        if audit.get("status") not in _PASS_AUDITS:
            self._blocked(envelope, audit)
            raise ValueError(f"cognitive_work_provider_audit_failed:{audit.get('status')}")
        return assessment, invocation, audit

    def _blocked(self, envelope: Any, audit: dict[str, Any] | None = None) -> None:
        payload = {"provider_envelope": envelope.as_dict()}
        if audit is not None:
            payload["provider_audit"] = audit
        self.event_sink("COGNITIVE_WORK_PROVIDER_BLOCKED", payload)

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
                **{name: {"type": "number"} for name in _FIELDS if name not in {
                    "recommended_action", "rationale", "evidence_refs"
                }},
                "recommended_action": {"type": "string"},
                "rationale": {"type": "string"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
