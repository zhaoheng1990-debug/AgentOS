"""Provider semantic support for problem-structure dimension assessment."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import (
    PROBLEM_STRUCTURE_DIMENSIONS,
    PROBLEM_STRUCTURE_SOURCE_SIGNALS,
    ProblemStructureCandidate,
    ProblemStructureDimensionAssessment,
    ProblemStructureProviderJudgment,
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
_ASSESSMENT_FIELDS = {
    "dimension",
    "score",
    "uncertainty",
    "support_status",
    "rationale",
    "evidence_refs",
    "source_signal_names",
}


class ProblemStructureProviderAdvisor:
    """Assess a frozen candidate without receiving admission authority."""

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

    def assess(self, candidate: ProblemStructureCandidate) -> ProblemStructureProviderJudgment:
        task = self._task(candidate)
        envelope = self.provider_router.route(task)
        semantic = self._semantic(envelope, candidate)
        try:
            assessments = self._assessments(semantic["dimension_assessments"], candidate)
            global_uncertainty = float(semantic["global_uncertainty"])
            require_unit("problem_structure_provider_global_uncertainty", global_uncertainty)
            if abs(global_uncertainty - max(item.uncertainty for item in assessments)) > 1e-9:
                raise ValueError("problem_structure_provider_global_uncertainty_mismatch")
        except (TypeError, ValueError):
            self._blocked(envelope)
            raise
        audit = self._audit(semantic, envelope)
        invocation = envelope.invocation_receipt.as_dict()
        if (
            invocation.get("input_hash") != task.contract_hash()
            or invocation.get("output_hash") != hash_payload(semantic)
        ):
            self._blocked(envelope, provider_audit=audit)
            raise ValueError("problem_structure_provider_invocation_binding_invalid")
        return ProblemStructureProviderJudgment.create(
            candidate_hash=candidate.candidate_hash,
            dimension_assessments=assessments,
            global_uncertainty=global_uncertainty,
            evidence_refs=tuple(semantic["evidence_refs"]),
            provider_invocation_receipt=invocation,
            provider_audit=audit,
        )

    def _task(self, candidate: ProblemStructureCandidate) -> ProviderCognitiveTask:
        return ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-{candidate.candidate_id}-structure-assessment",
            task_kind="problem_structure_dimension_assessment",
            objective=(
                "Assess the frozen problem candidate across exactly six constraint dimensions. "
                "Use only cited evidence and committed source signals. Mark contradictions or insufficient "
                "support explicitly. Do not alter objective, scope, evidence, identities, candidate state, "
                "authorization, or claim global policy authority."
            ),
            inputs={"problem_structure_candidate": candidate.as_dict()},
            allowed_evidence=list(candidate.evidence_refs),
            expected_schema=self.provider_schema(),
            failure_semantics="keep_problem_structure_pending_without_complete_provider_judgment",
            budget={"max_provider_calls": 1},
        )

    def _semantic(self, envelope: Any, candidate: ProblemStructureCandidate) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._blocked(envelope)
            raise RuntimeError(f"problem_structure_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        required = set(self.provider_schema()["required"])
        if set(semantic) != required:
            self._blocked(envelope)
            raise ValueError("problem_structure_provider_field_set_invalid")
        if semantic.get("candidate_hash") != candidate.candidate_hash:
            self._blocked(envelope)
            raise ValueError("problem_structure_provider_candidate_hash_mismatch")
        if not self._refs_valid(semantic.get("evidence_refs"), candidate.evidence_refs):
            self._blocked(envelope)
            raise ValueError("problem_structure_provider_evidence_invalid")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(
            candidate.evidence_refs
        ):
            self._blocked(envelope)
            raise ValueError("problem_structure_provider_provenance_invalid")
        return semantic

    @staticmethod
    def _assessments(payload: Any, candidate: ProblemStructureCandidate):
        if not isinstance(payload, list) or len(payload) != len(PROBLEM_STRUCTURE_DIMENSIONS):
            raise ValueError("problem_structure_provider_assessment_count_invalid")
        if any(not isinstance(item, dict) or set(item) != _ASSESSMENT_FIELDS for item in payload):
            raise ValueError("problem_structure_provider_assessment_schema_invalid")
        by_dimension = {item["dimension"]: item for item in payload}
        if set(by_dimension) != set(PROBLEM_STRUCTURE_DIMENSIONS):
            raise ValueError("problem_structure_provider_dimension_coverage_invalid")
        assessments = []
        for dimension in PROBLEM_STRUCTURE_DIMENSIONS:
            item = by_dimension[dimension]
            if item.get("support_status") not in {"CONSISTENT", "CONFLICT", "INSUFFICIENT"}:
                raise ValueError("problem_structure_provider_support_status_invalid")
            if not ProblemStructureProviderAdvisor._refs_valid(
                item.get("evidence_refs"), candidate.evidence_refs
            ):
                raise ValueError("problem_structure_provider_dimension_evidence_invalid")
            signals = item.get("source_signal_names")
            if (
                not isinstance(signals, list)
                or not signals
                or len(signals) != len(set(signals))
                or not set(signals).issubset(PROBLEM_STRUCTURE_SOURCE_SIGNALS)
            ):
                raise ValueError("problem_structure_provider_source_signals_invalid")
            assessments.append(
                ProblemStructureDimensionAssessment.create(
                    dimension=dimension,
                    score=float(item["score"]),
                    uncertainty=float(item["uncertainty"]),
                    support_status=item["support_status"],
                    rationale=item["rationale"],
                    evidence_refs=tuple(item["evidence_refs"]),
                    source_signal_names=tuple(signals),
                )
            )
        return tuple(assessments)

    def _audit(self, semantic: dict[str, Any], envelope: Any) -> dict[str, Any]:
        audit = self._cognition.audit_operation(
            "problem_structure_dimension_assessment",
            {
                "operation_id": "problem_structure_dimension_assessment",
                "provider_support_receipt": semantic,
                "provider_support_receipt_hash": hash_payload(semantic),
            },
        )
        if audit.get("status") not in _PASS_AUDITS:
            self._blocked(envelope, provider_audit=audit)
            raise ValueError(f"problem_structure_provider_audit_failed:{audit.get('status')}")
        return audit

    def _blocked(self, envelope: Any, *, provider_audit: dict[str, Any] | None = None) -> None:
        payload = {"provider_envelope": envelope.as_dict()}
        if provider_audit is not None:
            payload["provider_audit"] = provider_audit
        self.event_sink("PROBLEM_STRUCTURE_PROVIDER_BLOCKED", payload)

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
            "required": [
                "candidate_hash",
                "dimension_assessments",
                "global_uncertainty",
                "evidence_refs",
            ],
            "properties": {
                "candidate_hash": {"type": "string"},
                "dimension_assessments": {"type": "array", "items": {"type": "object"}},
                "global_uncertainty": {"type": "number"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
