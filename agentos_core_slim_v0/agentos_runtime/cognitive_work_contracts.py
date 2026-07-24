"""Runtime-facing immutable contracts for cognitive-work accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agentos_kernel.cognitive_work_models import (
    COGNITIVE_WORK_ACCOUNTING_VERSION,
    CognitiveWorkBudget,
    CognitiveWorkControlDecision,
    CognitiveWorkRoundObservation,
    CognitiveWorkSemanticAssessment,
    hash_payload,
)


COGNITIVE_WORK_RUNTIME_VERSION = "provider_backed_cognitive_work_runtime_v0_1"
_PASS_PROVIDER_AUDITS = {
    "PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT",
    "PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


@dataclass(frozen=True)
class CognitiveWorkRoundReceipt:
    receipt_id: str
    runtime_id: str
    observation: CognitiveWorkRoundObservation
    semantic_assessment: CognitiveWorkSemanticAssessment
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    mechanical_audit: dict[str, Any]
    kernel_control: CognitiveWorkControlDecision
    budget: CognitiveWorkBudget
    created_at: str
    receipt_hash: str
    candidate_state: str = "COGNITIVE_WORK_OBSERVED_PROJECT_SCOPED"

    def __post_init__(self) -> None:
        if not self.receipt_id or not self.runtime_id or not self.created_at:
            raise ValueError("cognitive_work_receipt_identity_incomplete")
        if self.candidate_state != "COGNITIVE_WORK_OBSERVED_PROJECT_SCOPED":
            raise ValueError("cognitive_work_receipt_state_invalid")
        observation = self.observation
        control = self.kernel_control
        if (observation.trajectory_id, observation.project_scope, observation.context_key) != (
            control.trajectory_id, control.project_scope, control.context_key
        ):
            raise ValueError("cognitive_work_receipt_control_binding_invalid")
        if control.observation_hashes[-1] != observation.observation_hash:
            raise ValueError("cognitive_work_receipt_observation_lineage_invalid")
        if control.budget_hash != self.budget.as_dict()["budget_hash"]:
            raise ValueError("cognitive_work_receipt_budget_binding_invalid")
        invocation = dict(self.provider_invocation_receipt)
        invocation_hash = invocation.pop("receipt_hash", "")
        if invocation_hash != hash_payload(invocation):
            raise ValueError("cognitive_work_provider_invocation_hash_invalid")
        if control.provider_receipt_hashes[-1] != invocation_hash:
            raise ValueError("cognitive_work_receipt_provider_lineage_invalid")
        semantic_hash = hash_payload(self.semantic_assessment.as_dict())
        if invocation.get("output_hash") != semantic_hash:
            raise ValueError("cognitive_work_provider_output_binding_invalid")
        if self.provider_audit.get("operation_id") != "cognitive_work_round_assessment":
            raise ValueError("cognitive_work_provider_audit_operation_invalid")
        if self.provider_audit.get("status") not in _PASS_PROVIDER_AUDITS:
            raise ValueError("cognitive_work_provider_audit_status_invalid")
        if self.provider_audit.get("provider_support_receipt_hash") != semantic_hash:
            raise ValueError("cognitive_work_provider_audit_binding_invalid")
        mechanical_record = {"kernel_control": control.as_dict(), "budget": self.budget.as_dict()}
        if self.mechanical_audit.get("operation_id") != "cognitive_work_trajectory_accounting":
            raise ValueError("cognitive_work_mechanical_audit_operation_invalid")
        if self.mechanical_audit.get("status") != "PASS_MECHANICAL_RUNTIME_OPERATION":
            raise ValueError("cognitive_work_mechanical_audit_invalid")
        if self.mechanical_audit.get("runtime_record_hash") != hash_payload(mechanical_record):
            raise ValueError("cognitive_work_mechanical_audit_binding_invalid")
        if self.receipt_hash != hash_payload(self._committed(self.__dict__)):
            raise ValueError("cognitive_work_receipt_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "CognitiveWorkRoundReceipt":
        committed = cls._committed(values)
        return cls(**values, receipt_hash=hash_payload(committed))

    @staticmethod
    def _committed(values: dict[str, Any]) -> dict[str, Any]:
        return {
            "receipt_id": values["receipt_id"],
            "runtime_id": values["runtime_id"],
            "observation": values["observation"].as_dict(),
            "semantic_assessment": values["semantic_assessment"].as_dict(),
            "provider_invocation_receipt": values["provider_invocation_receipt"],
            "provider_audit": values["provider_audit"],
            "mechanical_audit": values["mechanical_audit"],
            "kernel_control": values["kernel_control"].as_dict(),
            "budget": values["budget"].as_dict(),
            "created_at": values["created_at"],
            "candidate_state": values.get(
                "candidate_state", "COGNITIVE_WORK_OBSERVED_PROJECT_SCOPED"
            ),
        }

    def as_dict(self) -> dict[str, Any]:
        payload = self._committed(self.__dict__)
        return {
            **payload,
            "receipt_hash": self.receipt_hash,
            "baseline_write_authority": False,
            "global_memory_write_authority": False,
            "production_activation": False,
        }


@dataclass(frozen=True)
class CognitiveWorkSnapshot:
    runtime_id: str
    project_scope: str
    receipts: tuple[CognitiveWorkRoundReceipt, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_id": COGNITIVE_WORK_ACCOUNTING_VERSION,
            "runtime_version": COGNITIVE_WORK_RUNTIME_VERSION,
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "receipts": [item.as_dict() for item in self.receipts],
        }
