"""Immutable Runtime receipts for selection-to-execution feedback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agentos_kernel import (
    CONTEXTUAL_POLICY_IDS,
    MatchedPolicyEvidence,
    OrganizationTrialRecord,
    PolicyExecutionBundle,
    SelectionExecutionRequest,
)
from agentos_kernel.contextual_policy_models import hash_payload


SELECTION_EXECUTION_FEEDBACK_RUNTIME_VERSION = "selection_execution_feedback_bridge_v0_1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


@dataclass(frozen=True)
class SelectionExecutionFeedbackReceipt:
    request: SelectionExecutionRequest
    execution_bundle: PolicyExecutionBundle
    admitted_records: tuple[OrganizationTrialRecord, ...]
    matched_evidence: tuple[MatchedPolicyEvidence, ...]
    created_at: str
    receipt_hash: str
    candidate_state: str = "EXECUTION_FEEDBACK_ADMITTED_PROJECT_SCOPED"

    def __post_init__(self) -> None:
        if self.candidate_state != "EXECUTION_FEEDBACK_ADMITTED_PROJECT_SCOPED":
            raise ValueError("selection_feedback_candidate_state_invalid")
        if self.execution_bundle.bridge_run_id != self.request.bridge_run_id:
            raise ValueError("selection_feedback_bundle_request_mismatch")
        if {item.protocol_id for item in self.admitted_records} != {
            item.protocol_id for item in self.execution_bundle.outcomes
        }:
            raise ValueError("selection_feedback_record_protocol_mismatch")
        if any(
            item.trial_group_id != self.request.trial_group_id
            or item.context_key != self.request.context_key
            or item.evidence_tier != self.request.evidence_tier
            for item in self.admitted_records
        ):
            raise ValueError("selection_feedback_record_scope_mismatch")
        if tuple(item.policy_id for item in self.matched_evidence) != CONTEXTUAL_POLICY_IDS:
            raise ValueError("selection_feedback_matched_evidence_coverage_invalid")
        if any(
            item.context_key != self.request.context_key
            or item.evidence_tier != self.request.evidence_tier
            for item in self.matched_evidence
        ):
            raise ValueError("selection_feedback_matched_evidence_scope_invalid")
        if self.receipt_hash != hash_payload(self._committed_dict()):
            raise ValueError("selection_feedback_receipt_hash_mismatch")

    @classmethod
    def create(
        cls,
        *,
        request: SelectionExecutionRequest,
        execution_bundle: PolicyExecutionBundle,
        admitted_records: tuple[OrganizationTrialRecord, ...],
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
    ) -> "SelectionExecutionFeedbackReceipt":
        created_at = _utc_now()
        committed = {
            "request": request.as_dict(),
            "execution_bundle": execution_bundle.as_dict(),
            "admitted_records": [item.as_dict() for item in admitted_records],
            "matched_evidence": [item.as_dict() for item in matched_evidence],
            "created_at": created_at,
            "candidate_state": "EXECUTION_FEEDBACK_ADMITTED_PROJECT_SCOPED",
        }
        return cls(
            request=request,
            execution_bundle=execution_bundle,
            admitted_records=admitted_records,
            matched_evidence=matched_evidence,
            created_at=created_at,
            receipt_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.as_dict(),
            "execution_bundle": self.execution_bundle.as_dict(),
            "admitted_records": [item.as_dict() for item in self.admitted_records],
            "matched_evidence": [item.as_dict() for item in self.matched_evidence],
            "created_at": self.created_at,
            "candidate_state": self.candidate_state,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "receipt_hash": self.receipt_hash,
            "global_policy_authority": False,
            "production_activation": False,
        }


@dataclass(frozen=True)
class SelectionExecutionFeedbackSnapshot:
    runtime_id: str
    project_scope: str
    receipts: tuple[SelectionExecutionFeedbackReceipt, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "receipts": [item.as_dict() for item in self.receipts],
        }
