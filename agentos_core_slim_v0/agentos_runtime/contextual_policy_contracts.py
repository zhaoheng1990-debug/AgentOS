"""Immutable Runtime receipts for contextual organization selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agentos_kernel import (
    CONTEXTUAL_POLICY_IDS,
    ContextualOrganizationPolicyDecision,
    ContextualProviderPolicyAssessment,
    EnsembleAssignment,
    MatchedPolicyEvidence,
)
from agentos_kernel.contextual_policy_models import hash_payload, require_refs, require_text, require_unit


CONTEXTUAL_ORGANIZATION_POLICY_RUNTIME_VERSION = "contextual_organization_policy_selector_v0_1"


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


@dataclass(frozen=True)
class ContextualProviderAdvice:
    recommended_policy_id: str
    policy_assessments: tuple[ContextualProviderPolicyAssessment, ...]
    global_uncertainty: float
    evidence_refs: tuple[str, ...]
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    advice_hash: str

    def __post_init__(self) -> None:
        require_text("contextual_provider_recommended_policy", self.recommended_policy_id)
        require_unit("contextual_provider_global_uncertainty", self.global_uncertainty)
        require_refs("contextual_provider_advice_evidence_refs", self.evidence_refs)
        policy_ids = tuple(item.policy_id for item in self.policy_assessments)
        if len(policy_ids) != len(set(policy_ids)) or set(policy_ids) != set(CONTEXTUAL_POLICY_IDS):
            raise ValueError("contextual_provider_advice_policy_coverage_invalid")
        if self.advice_hash != hash_payload(self._committed_dict()):
            raise ValueError("contextual_provider_advice_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        recommended_policy_id: str,
        policy_assessments: tuple[ContextualProviderPolicyAssessment, ...],
        global_uncertainty: float,
        evidence_refs: tuple[str, ...],
        provider_invocation_receipt: dict[str, Any],
        provider_audit: dict[str, Any],
    ) -> "ContextualProviderAdvice":
        committed = {
            "recommended_policy_id": recommended_policy_id,
            "policy_assessments": [item.as_dict() for item in policy_assessments],
            "global_uncertainty": global_uncertainty,
            "evidence_refs": list(evidence_refs),
            "provider_invocation_receipt": provider_invocation_receipt,
            "provider_audit": provider_audit,
        }
        return cls(
            recommended_policy_id=recommended_policy_id,
            policy_assessments=policy_assessments,
            global_uncertainty=float(global_uncertainty),
            evidence_refs=evidence_refs,
            provider_invocation_receipt=provider_invocation_receipt,
            provider_audit=provider_audit,
            advice_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "recommended_policy_id": self.recommended_policy_id,
            "policy_assessments": [item.as_dict() for item in self.policy_assessments],
            "global_uncertainty": self.global_uncertainty,
            "evidence_refs": list(self.evidence_refs),
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "advice_hash": self.advice_hash}


@dataclass(frozen=True)
class ContextualOrganizationSelectionReceipt:
    selection_id: str
    runtime_id: str
    project_scope: str
    context_key: str
    evidence_tier: str
    provider_advice: ContextualProviderAdvice
    matched_evidence: tuple[MatchedPolicyEvidence, ...]
    kernel_decision: ContextualOrganizationPolicyDecision
    assignment: EnsembleAssignment | None
    created_at: str
    receipt_hash: str
    candidate_state: str = "CONTEXTUAL_POLICY_SELECTED_PROJECT_SCOPED"

    def __post_init__(self) -> None:
        for name in ("selection_id", "runtime_id", "project_scope", "context_key", "evidence_tier", "created_at"):
            require_text(name, getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("contextual_selection_scope_must_be_project_uri")
        if self.candidate_state != "CONTEXTUAL_POLICY_SELECTED_PROJECT_SCOPED":
            raise ValueError("contextual_selection_candidate_state_invalid")
        if tuple(item.policy_id for item in self.matched_evidence) != CONTEXTUAL_POLICY_IDS:
            raise ValueError("contextual_selection_matched_evidence_coverage_invalid")
        if any(
            item.context_key != self.context_key or item.evidence_tier != self.evidence_tier
            for item in self.matched_evidence
        ):
            raise ValueError("contextual_selection_matched_evidence_binding_invalid")
        if self.kernel_decision.provider_advice_hash != self.provider_advice.advice_hash:
            raise ValueError("contextual_selection_provider_advice_binding_invalid")
        if any(
            item.project_scope != self.project_scope
            or item.context_key != self.context_key
            or item.evidence_tier != self.evidence_tier
            for item in self.kernel_decision.calibration_controls
        ):
            raise ValueError("contextual_selection_calibration_scope_mismatch")
        if any(
            item.calibration_receipt_ref
            and item.calibration_receipt_ref not in self.kernel_decision.evidence_refs
            for item in self.kernel_decision.calibration_controls
        ):
            raise ValueError("contextual_selection_calibration_evidence_binding_invalid")
        if self.assignment is None and self.kernel_decision.selected_policy_id:
            raise ValueError("contextual_selection_assignment_required")
        if self.assignment is not None:
            if self.assignment.execution_authorized != self.kernel_decision.execution_authorized:
                raise ValueError("contextual_selection_assignment_authority_mismatch")
            if tuple(agent.role for agent in self.assignment.agents) != self.kernel_decision.selected_roles:
                raise ValueError("contextual_selection_assignment_role_mismatch")
        if self.receipt_hash != hash_payload(self._committed_dict()):
            raise ValueError("contextual_selection_receipt_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        selection_id: str,
        runtime_id: str,
        project_scope: str,
        context_key: str,
        evidence_tier: str,
        provider_advice: ContextualProviderAdvice,
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
        kernel_decision: ContextualOrganizationPolicyDecision,
        assignment: EnsembleAssignment | None,
    ) -> "ContextualOrganizationSelectionReceipt":
        created_at = utc_now()
        committed = {
            "selection_id": selection_id,
            "runtime_id": runtime_id,
            "project_scope": project_scope,
            "context_key": context_key,
            "evidence_tier": evidence_tier,
            "provider_advice": provider_advice.as_dict(),
            "matched_evidence": [item.as_dict() for item in matched_evidence],
            "kernel_decision": kernel_decision.as_dict(),
            "assignment": assignment.as_dict() if assignment else None,
            "created_at": created_at,
            "candidate_state": "CONTEXTUAL_POLICY_SELECTED_PROJECT_SCOPED",
        }
        return cls(
            selection_id=selection_id,
            runtime_id=runtime_id,
            project_scope=project_scope,
            context_key=context_key,
            evidence_tier=evidence_tier,
            provider_advice=provider_advice,
            matched_evidence=matched_evidence,
            kernel_decision=kernel_decision,
            assignment=assignment,
            created_at=created_at,
            receipt_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "context_key": self.context_key,
            "evidence_tier": self.evidence_tier,
            "provider_advice": self.provider_advice.as_dict(),
            "matched_evidence": [item.as_dict() for item in self.matched_evidence],
            "kernel_decision": self.kernel_decision.as_dict(),
            "assignment": self.assignment.as_dict() if self.assignment else None,
            "created_at": self.created_at,
            "candidate_state": self.candidate_state,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "receipt_hash": self.receipt_hash,
            "execution_authorized": self.kernel_decision.execution_authorized,
            "trial_authorized": self.kernel_decision.trial_authorized,
            "global_policy_authority": False,
            "production_activation": False,
        }


@dataclass(frozen=True)
class ContextualOrganizationPolicySnapshot:
    runtime_id: str
    project_scope: str
    selections: tuple[ContextualOrganizationSelectionReceipt, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "selections": [item.as_dict() for item in self.selections],
        }
