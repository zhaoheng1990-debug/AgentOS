"""Provider semantic support for contextual organization policy selection."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import (
    CONTEXTUAL_POLICY_IDS,
    ContextualProblemStructure,
    ContextualProviderPolicyAssessment,
    ContextualRolePolicy,
    MatchedPolicyEvidence,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
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

from .contextual_policy_contracts import ContextualProviderAdvice


_PASS_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}
_ASSESSMENT_FIELDS = {
    "policy_id",
    "structure_fit",
    "expected_cbit_gain",
    "estimated_normalized_cost",
    "residual_risk",
    "anti_additive_signal",
    "uncertainty",
    "rationale",
    "evidence_refs",
}


class ContextualOrganizationProviderAdvisor:
    """Assess registered policies without receiving selection authority."""

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
        selection_id: str,
        problem: ContextualProblemStructure,
        policies: tuple[ContextualRolePolicy, ...],
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        public_agent_profiles: tuple[dict[str, Any], ...],
    ) -> ContextualProviderAdvice:
        allowed_evidence = tuple(
            dict.fromkeys(
                (*problem.evidence_refs, *(ref for item in matched_evidence for ref in item.evidence_refs))
            )
        )
        task = self._build_task(
            selection_id,
            problem,
            policies,
            matched_evidence,
            budget,
            risk,
            public_agent_profiles,
            allowed_evidence,
        )
        envelope = self.provider_router.route(task)
        semantic = self._require_semantic_result(envelope, allowed_evidence)
        try:
            assessments = self._parse_assessments(semantic["policy_assessments"], allowed_evidence)
        except ValueError:
            self._blocked(envelope)
            raise
        if abs(float(semantic["global_uncertainty"]) - max(item.uncertainty for item in assessments)) > 1e-6:
            self._blocked(envelope)
            raise ValueError("contextual_policy_provider_global_uncertainty_mismatch")
        provider_audit = self._audit(semantic, envelope)
        invocation = envelope.invocation_receipt.as_dict()
        if (
            invocation.get("input_hash") != task.contract_hash()
            or invocation.get("output_hash") != hash_payload(semantic)
        ):
            self._blocked(envelope)
            raise ValueError("contextual_policy_provider_invocation_binding_invalid")
        return ContextualProviderAdvice.create(
            recommended_policy_id=semantic["recommended_policy_id"],
            policy_assessments=assessments,
            global_uncertainty=float(semantic["global_uncertainty"]),
            evidence_refs=tuple(semantic["evidence_refs"]),
            provider_invocation_receipt=invocation,
            provider_audit=provider_audit,
        )

    def _build_task(
        self,
        selection_id: str,
        problem: ContextualProblemStructure,
        policies: tuple[ContextualRolePolicy, ...],
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        public_agent_profiles: tuple[dict[str, Any], ...],
        allowed_evidence: tuple[str, ...],
    ) -> ProviderCognitiveTask:
        return ProviderCognitiveTask(
            task_id=f"{self.runtime_id}-{selection_id}-provider-assessment",
            task_kind="contextual_organization_policy_assessment",
            objective=(
                "Assess every registered organization policy for this exact problem structure and matched-evidence "
                "surface. Return semantic fit, expected Cbit, bounded cost, residual risk, uncertainty, and "
                "anti-additive pressure. The recommendation is advisory: do not alter policy roles, matched metrics, "
                "budget, risk envelope, registry bindings, or claim execution/global policy authority."
            ),
            inputs={
                "problem_structure": problem.as_dict(),
                "registered_policies": [item.as_dict() for item in policies],
                "matched_evidence": [item.as_dict() for item in matched_evidence],
                "budget_envelope": budget.as_dict(),
                "risk_envelope": risk.as_dict(),
                "registered_agent_profiles": list(public_agent_profiles),
            },
            allowed_evidence=list(allowed_evidence),
            expected_schema=self.provider_schema(),
            failure_semantics="abstain_without_complete_contextual_policy_assessment",
            budget={"max_provider_calls": 1},
        )

    def _require_semantic_result(self, envelope: Any, allowed_evidence: tuple[str, ...]) -> dict[str, Any]:
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self._blocked(envelope)
            raise RuntimeError(f"contextual_policy_provider_blocked:{envelope.status}")
        semantic = dict(envelope.normalized_result or {})
        if set(semantic) != set(self.provider_schema()["required"]):
            self._blocked(envelope)
            raise ValueError("contextual_policy_provider_field_set_invalid")
        if semantic.get("recommended_policy_id") not in CONTEXTUAL_POLICY_IDS:
            self._blocked(envelope)
            raise ValueError("contextual_policy_provider_recommendation_invalid")
        try:
            require_unit("contextual_policy_global_uncertainty", semantic.get("global_uncertainty"))
        except ValueError:
            self._blocked(envelope)
            raise
        refs = semantic.get("evidence_refs")
        if not self._refs_valid(refs, allowed_evidence):
            self._blocked(envelope)
            raise ValueError("contextual_policy_provider_evidence_invalid")
        if not envelope.provenance_refs or not set(envelope.provenance_refs).issubset(allowed_evidence):
            self._blocked(envelope)
            raise ValueError("contextual_policy_provider_provenance_invalid")
        return semantic

    def _parse_assessments(
        self,
        payload: Any,
        allowed_evidence: tuple[str, ...],
    ) -> tuple[ContextualProviderPolicyAssessment, ...]:
        if not isinstance(payload, list) or len(payload) != len(CONTEXTUAL_POLICY_IDS):
            raise ValueError("contextual_policy_provider_assessment_count_invalid")
        if any(not isinstance(item, dict) or set(item) != _ASSESSMENT_FIELDS for item in payload):
            raise ValueError("contextual_policy_provider_assessment_schema_invalid")
        if {item["policy_id"] for item in payload} != set(CONTEXTUAL_POLICY_IDS):
            raise ValueError("contextual_policy_provider_assessment_coverage_invalid")
        assessments = []
        for item in payload:
            if not self._refs_valid(item.get("evidence_refs"), allowed_evidence):
                raise ValueError("contextual_policy_provider_assessment_evidence_invalid")
            assessments.append(
                ContextualProviderPolicyAssessment(
                    policy_id=item["policy_id"],
                    structure_fit=item["structure_fit"],
                    expected_cbit_gain=item["expected_cbit_gain"],
                    estimated_normalized_cost=item["estimated_normalized_cost"],
                    residual_risk=item["residual_risk"],
                    anti_additive_signal=item["anti_additive_signal"],
                    uncertainty=item["uncertainty"],
                    rationale=item["rationale"],
                    evidence_refs=tuple(item["evidence_refs"]),
                )
            )
        return tuple(assessments)

    def _audit(self, semantic: dict[str, Any], envelope: Any) -> dict[str, Any]:
        provider_audit = self._cognition.audit_operation(
            "contextual_organization_policy_assessment",
            {
                "operation_id": "contextual_organization_policy_assessment",
                "provider_support_receipt": semantic,
                "provider_support_receipt_hash": hash_payload(semantic),
            },
        )
        if provider_audit.get("status") not in _PASS_AUDITS:
            self._blocked(envelope, provider_audit=provider_audit)
            raise ValueError(f"contextual_policy_provider_audit_failed:{provider_audit.get('status')}")
        return provider_audit

    def _blocked(self, envelope: Any, *, provider_audit: dict[str, Any] | None = None) -> None:
        payload = {"provider_envelope": envelope.as_dict()}
        if provider_audit is not None:
            payload["provider_audit"] = provider_audit
        self.event_sink("CONTEXTUAL_POLICY_PROVIDER_BLOCKED", payload)

    @staticmethod
    def _refs_valid(refs: Any, allowed_evidence: tuple[str, ...]) -> bool:
        return bool(
            isinstance(refs, list)
            and refs
            and len(refs) == len(set(refs))
            and set(refs).issubset(allowed_evidence)
        )

    @staticmethod
    def provider_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": [
                "recommended_policy_id",
                "policy_assessments",
                "global_uncertainty",
                "evidence_refs",
            ],
            "properties": {
                "recommended_policy_id": {"type": "string"},
                "policy_assessments": {"type": "array", "items": {"type": "object"}},
                "global_uncertainty": {"type": "number"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
