"""Provider semantic support for Anti-Additive Methodology audits."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import (
    ANTI_ADDITIVE_OBJECT_ADEQUACY,
    ANTI_ADDITIVE_RECOMMENDED_ACTIONS,
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    AntiAdditiveProviderJudgment,
    AntiAdditiveTriggerAssessment,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCognitiveTask,
    ProviderTaskRouter,
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
    "current_object_adequacy",
    "trigger_assessments",
    "expected_effective_cbit_gain",
    "complexity_cost",
    "object_upgrade_gain",
    "abstraction_cost",
    "uncertainty",
    "recommended_action",
    "rationale",
    "evidence_refs",
}
_TRIGGER_FIELDS = {"trigger_id", "triggered", "rationale", "evidence_refs"}


class AntiAdditiveProviderAdvisor:
    """Assess object adequacy and patch pressure without owning the decision."""

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

    def assess(self, candidate: AntiAdditiveChangeCandidate) -> AntiAdditiveProviderJudgment:
        task = ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-{candidate.audit_id}-anti-additive-audit",
            task_kind="anti_additive_methodology_assessment",
            objective=(
                "Audit whether the proposed change reduces the possibility space or accumulates patches on an "
                "underpowered object. Evaluate all seven frozen Anti-Additive triggers, current object adequacy, "
                "effective Cbit gain versus complexity cost, and object-upgrade gain versus abstraction cost. "
                "Return bounded semantic support only; do not authorize writes, choose candidate state, alter "
                "identity or scope, or claim baseline, global, or production authority."
            ),
            inputs={"change_candidate": candidate.as_dict()},
            allowed_evidence=list(candidate.evidence_refs),
            expected_schema=self.provider_schema(),
            failure_semantics="block_methodology_admission_without_provider_supported_object_audit",
            budget={"max_provider_calls": 1},
        )
        envelope = self.provider_router.route(task)
        semantic = self._semantic(envelope, candidate)
        trigger_assessments = self._triggers(semantic["trigger_assessments"], candidate.evidence_refs)
        audit = self._cognition.audit_operation(
            "anti_additive_methodology_assessment",
            {
                "operation_id": "anti_additive_methodology_assessment",
                "provider_support_receipt": semantic,
                "provider_support_receipt_hash": hash_payload(semantic),
            },
        )
        if audit.get("status") not in _PASS_AUDITS:
            self._blocked(envelope, audit)
            raise ValueError(f"anti_additive_provider_audit_failed:{audit.get('status')}")
        invocation = envelope.invocation_receipt.as_dict()
        if (
            invocation.get("input_hash") != task.contract_hash()
            or invocation.get("output_hash") != hash_payload(semantic)
        ):
            self._blocked(envelope, audit)
            raise ValueError("anti_additive_provider_invocation_binding_invalid")
        return AntiAdditiveProviderJudgment.create(
            candidate_hash=candidate.candidate_hash,
            current_object_adequacy=semantic["current_object_adequacy"],
            trigger_assessments=trigger_assessments,
            expected_effective_cbit_gain=float(semantic["expected_effective_cbit_gain"]),
            complexity_cost=float(semantic["complexity_cost"]),
            object_upgrade_gain=float(semantic["object_upgrade_gain"]),
            abstraction_cost=float(semantic["abstraction_cost"]),
            uncertainty=float(semantic["uncertainty"]),
            recommended_action=semantic["recommended_action"],
            rationale=semantic["rationale"],
            evidence_refs=tuple(semantic["evidence_refs"]),
            provider_invocation_receipt=invocation,
            provider_audit=audit,
        )

    def _semantic(
        self,
        envelope: Any,
        candidate: AntiAdditiveChangeCandidate,
    ) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._blocked(envelope)
            raise RuntimeError(f"anti_additive_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        if set(semantic) != _FIELDS:
            self._blocked(envelope)
            raise ValueError("anti_additive_provider_field_set_invalid")
        if semantic.get("current_object_adequacy") not in ANTI_ADDITIVE_OBJECT_ADEQUACY:
            self._blocked(envelope)
            raise ValueError("anti_additive_provider_object_adequacy_invalid")
        if semantic.get("recommended_action") not in ANTI_ADDITIVE_RECOMMENDED_ACTIONS:
            self._blocked(envelope)
            raise ValueError("anti_additive_provider_recommended_action_invalid")
        for name in (
            "expected_effective_cbit_gain",
            "complexity_cost",
            "object_upgrade_gain",
            "abstraction_cost",
            "uncertainty",
        ):
            try:
                require_unit(f"anti_additive_provider_{name}", semantic.get(name))
            except ValueError:
                self._blocked(envelope)
                raise
        if not isinstance(semantic.get("rationale"), str) or not semantic["rationale"].strip():
            self._blocked(envelope)
            raise ValueError("anti_additive_provider_rationale_required")
        if not self._refs_valid(semantic.get("evidence_refs"), candidate.evidence_refs):
            self._blocked(envelope)
            raise ValueError("anti_additive_provider_evidence_invalid")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(
            candidate.evidence_refs
        ):
            self._blocked(envelope)
            raise ValueError("anti_additive_provider_provenance_invalid")
        return semantic

    @staticmethod
    def _triggers(
        payload: Any,
        allowed_evidence: tuple[str, ...],
    ) -> tuple[AntiAdditiveTriggerAssessment, ...]:
        if not isinstance(payload, list) or len(payload) != len(ANTI_ADDITIVE_TRIGGER_IDS):
            raise ValueError("anti_additive_provider_trigger_count_invalid")
        if any(not isinstance(item, dict) or set(item) != _TRIGGER_FIELDS for item in payload):
            raise ValueError("anti_additive_provider_trigger_schema_invalid")
        by_id = {item["trigger_id"]: item for item in payload}
        if set(by_id) != set(ANTI_ADDITIVE_TRIGGER_IDS) or len(by_id) != len(payload):
            raise ValueError("anti_additive_provider_trigger_coverage_invalid")
        assessments = []
        for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS:
            item = by_id[trigger_id]
            if not isinstance(item["triggered"], bool):
                raise ValueError("anti_additive_provider_trigger_value_invalid")
            if not AntiAdditiveProviderAdvisor._refs_valid(
                item.get("evidence_refs"), allowed_evidence
            ):
                raise ValueError("anti_additive_provider_trigger_evidence_invalid")
            assessments.append(
                AntiAdditiveTriggerAssessment.create(
                    trigger_id=trigger_id,
                    triggered=item["triggered"],
                    rationale=item["rationale"],
                    evidence_refs=tuple(item["evidence_refs"]),
                )
            )
        return tuple(assessments)

    def _blocked(self, envelope: Any, audit: dict[str, Any] | None = None) -> None:
        payload = {"provider_envelope": envelope.as_dict()}
        if audit is not None:
            payload["provider_audit"] = audit
        self.event_sink("ANTI_ADDITIVE_PROVIDER_BLOCKED", payload)

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
                "current_object_adequacy": {"type": "string"},
                "trigger_assessments": {"type": "array", "items": {"type": "object"}},
                "expected_effective_cbit_gain": {"type": "number"},
                "complexity_cost": {"type": "number"},
                "object_upgrade_gain": {"type": "number"},
                "abstraction_cost": {"type": "number"},
                "uncertainty": {"type": "number"},
                "recommended_action": {"type": "string"},
                "rationale": {"type": "string"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
