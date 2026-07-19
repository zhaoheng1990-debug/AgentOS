"""Provider judgment and frozen policy contracts for Anti-Additive Methodology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .anti_additive_base import (
    ANTI_ADDITIVE_OBJECT_ADEQUACY,
    ANTI_ADDITIVE_RECOMMENDED_ACTIONS,
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveTriggerAssessment,
)
from .contextual_policy_models import hash_payload, require_refs, require_text, require_unit


@dataclass(frozen=True)
class AntiAdditiveProviderJudgment:
    candidate_hash: str
    current_object_adequacy: str
    trigger_assessments: tuple[AntiAdditiveTriggerAssessment, ...]
    expected_effective_cbit_gain: float
    complexity_cost: float
    object_upgrade_gain: float
    abstraction_cost: float
    uncertainty: float
    recommended_action: str
    rationale: str
    evidence_refs: tuple[str, ...]
    provider_invocation_receipt: dict[str, Any]
    provider_audit: dict[str, Any]
    judgment_hash: str

    def __post_init__(self) -> None:
        if len(self.candidate_hash) != 64:
            raise ValueError("anti_additive_provider_candidate_hash_invalid")
        if self.current_object_adequacy not in ANTI_ADDITIVE_OBJECT_ADEQUACY:
            raise ValueError("anti_additive_object_adequacy_invalid")
        if tuple(item.trigger_id for item in self.trigger_assessments) != ANTI_ADDITIVE_TRIGGER_IDS:
            raise ValueError("anti_additive_trigger_coverage_invalid")
        for name in (
            "expected_effective_cbit_gain", "complexity_cost", "object_upgrade_gain",
            "abstraction_cost", "uncertainty",
        ):
            require_unit(f"anti_additive_{name}", getattr(self, name))
        if self.recommended_action not in ANTI_ADDITIVE_RECOMMENDED_ACTIONS:
            raise ValueError("anti_additive_recommended_action_invalid")
        require_text("anti_additive_provider_rationale", self.rationale)
        require_refs("anti_additive_provider_evidence_refs", self.evidence_refs)
        if any(not set(item.evidence_refs).issubset(self.evidence_refs) for item in self.trigger_assessments):
            raise ValueError("anti_additive_trigger_evidence_outside_judgment")
        if self.judgment_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_provider_judgment_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveProviderJudgment":
        committed = {
            **values,
            "trigger_assessments": [item.as_dict() for item in values["trigger_assessments"]],
            "evidence_refs": list(values["evidence_refs"]),
        }
        return cls(**values, judgment_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "candidate_hash": self.candidate_hash,
            "current_object_adequacy": self.current_object_adequacy,
            "trigger_assessments": [item.as_dict() for item in self.trigger_assessments],
            "expected_effective_cbit_gain": self.expected_effective_cbit_gain,
            "complexity_cost": self.complexity_cost,
            "object_upgrade_gain": self.object_upgrade_gain,
            "abstraction_cost": self.abstraction_cost,
            "uncertainty": self.uncertainty,
            "recommended_action": self.recommended_action,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "provider_invocation_receipt": self.provider_invocation_receipt,
            "provider_audit": self.provider_audit,
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "judgment_hash": self.judgment_hash}


@dataclass(frozen=True)
class AntiAdditiveMethodologyPolicy:
    policy_ref: str = "methodology://anti-additive/v1.1"
    max_provider_uncertainty: float = 0.45

    def __post_init__(self) -> None:
        require_text("anti_additive_policy_ref", self.policy_ref)
        require_unit("anti_additive_max_provider_uncertainty", self.max_provider_uncertainty)

    def as_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["policy_hash"] = hash_payload(payload)
        return payload
