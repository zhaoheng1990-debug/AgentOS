"""Kernel decision and receipt contracts for Anti-Additive Methodology."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .anti_additive_base import (
    ANTI_ADDITIVE_DECISION_STATES,
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    require_anti_additive_id,
)
from .anti_additive_judgment import AntiAdditiveProviderJudgment
from .anti_additive_control import AntiAdditiveCalibrationControl
from .contextual_policy_models import hash_payload, require_text


@dataclass(frozen=True)
class AntiAdditiveMethodologyDecision:
    audit_id: str
    project_scope: str
    candidate_id: str
    candidate_hash: str
    candidate_payload_hash: str
    provider_judgment_hash: str
    policy_hash: str
    state: str
    allowed: bool
    candidate_only_allowed: bool
    reason: str
    active_trigger_ids: tuple[str, ...]
    effective_cbit_margin: float
    object_upgrade_margin: float
    kernel_authorization_ref: str
    calibration_control: AntiAdditiveCalibrationControl
    decision_hash: str

    def __post_init__(self) -> None:
        if self.state not in ANTI_ADDITIVE_DECISION_STATES:
            raise ValueError("anti_additive_decision_state_invalid")
        if self.allowed != (self.state == "ALLOW_BOUNDED_CHANGE"):
            raise ValueError("anti_additive_decision_authority_invalid")
        if self.candidate_only_allowed != (
            self.state in {"ALLOW_BOUNDED_CHANGE", "REQUIRE_CALIBRATED_VALIDATION"}
        ):
            raise ValueError("anti_additive_decision_candidate_authority_invalid")
        if not self.project_scope.startswith("project://"):
            raise ValueError("anti_additive_decision_scope_invalid")
        require_anti_additive_id("anti_additive_decision_audit_id", self.audit_id)
        require_anti_additive_id("anti_additive_decision_candidate_id", self.candidate_id)
        for name in ("candidate_hash", "candidate_payload_hash", "provider_judgment_hash", "policy_hash"):
            if len(getattr(self, name)) != 64:
                raise ValueError(f"anti_additive_decision_{name}_invalid")
        if not set(self.active_trigger_ids).issubset(ANTI_ADDITIVE_TRIGGER_IDS):
            raise ValueError("anti_additive_decision_trigger_invalid")
        if len(self.active_trigger_ids) != len(set(self.active_trigger_ids)):
            raise ValueError("anti_additive_decision_duplicate_trigger")
        for name in ("effective_cbit_margin", "object_upgrade_margin"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not -1 <= value <= 1:
                raise ValueError(f"anti_additive_decision_{name}_invalid")
        require_text("anti_additive_decision_reason", self.reason)
        if not self.kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("anti_additive_kernel_authorization_required")
        if self.calibration_control.project_scope != self.project_scope:
            raise ValueError("anti_additive_decision_calibration_scope_invalid")
        if self.decision_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_decision_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveMethodologyDecision":
        committed = {
            **values,
            "active_trigger_ids": list(values["active_trigger_ids"]),
            "calibration_control": values["calibration_control"].as_dict(),
        }
        return cls(**values, decision_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        payload = {key: value for key, value in self.__dict__.items() if key != "decision_hash"}
        payload["active_trigger_ids"] = list(self.active_trigger_ids)
        payload["calibration_control"] = self.calibration_control.as_dict()
        return payload

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "decision_hash": self.decision_hash}


@dataclass(frozen=True)
class AntiAdditiveMethodologyReceipt:
    candidate: AntiAdditiveChangeCandidate
    provider_judgment: AntiAdditiveProviderJudgment
    decision: AntiAdditiveMethodologyDecision
    created_at: str
    receipt_hash: str

    def __post_init__(self) -> None:
        if self.provider_judgment.candidate_hash != self.candidate.candidate_hash:
            raise ValueError("anti_additive_receipt_provider_binding_invalid")
        if (
            self.decision.candidate_hash != self.candidate.candidate_hash
            or self.decision.candidate_payload_hash != self.candidate.candidate_payload_hash
            or self.decision.provider_judgment_hash != self.provider_judgment.judgment_hash
            or self.decision.project_scope != self.candidate.project_scope
            or self.decision.candidate_id != self.candidate.candidate_id
        ):
            raise ValueError("anti_additive_receipt_decision_binding_invalid")
        if self.receipt_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_receipt_hash_mismatch")

    @classmethod
    def create(cls, *, candidate, provider_judgment, decision) -> "AntiAdditiveMethodologyReceipt":
        created_at = datetime.now(timezone.utc).astimezone().isoformat()
        committed = {
            "candidate": candidate.as_dict(),
            "provider_judgment": provider_judgment.as_dict(),
            "decision": decision.as_dict(),
            "created_at": created_at,
        }
        return cls(
            candidate=candidate,
            provider_judgment=provider_judgment,
            decision=decision,
            created_at=created_at,
            receipt_hash=hash_payload(committed),
        )

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.as_dict(),
            "provider_judgment": self.provider_judgment.as_dict(),
            "decision": self.decision.as_dict(),
            "created_at": self.created_at,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._committed_dict(),
            "receipt_hash": self.receipt_hash,
            "baseline_write_authority": False,
            "global_authority": False,
            "production_activation": False,
        }
