"""Base constants and candidate contracts for Anti-Additive Methodology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contextual_policy_models import hash_payload, require_refs, require_text


ANTI_ADDITIVE_METHODOLOGY_VERSION = "anti_additive_methodology_v0_1"
ANTI_ADDITIVE_CHANGE_KINDS = (
    "VARIABLE", "MODULE", "METRIC", "WINDOW", "EXCEPTION", "OBJECT", "MEMORY", "POLICY",
)
ANTI_ADDITIVE_OBJECT_LEVELS = ("METRIC", "OBSERVABLE", "PROXY", "ONTOLOGY_OBJECT")
ANTI_ADDITIVE_OBJECT_ADEQUACY = ("ADEQUATE", "UNDERPOWERED", "WRONG_OBJECT", "UNCERTAIN")
ANTI_ADDITIVE_RECOMMENDED_ACTIONS = (
    "KEEP_OBJECT", "UPGRADE_OBJECT", "REPLACE_OBJECT", "ABSTAIN",
)
ANTI_ADDITIVE_TRIGGER_IDS = (
    "TERMS_WITHOUT_ERROR_PATH_REDUCTION",
    "EXPLANATION_GROWTH_WITHOUT_CONSTRAINT_CLARITY",
    "TRAJECTORY_MULTIPLICATION_WITHOUT_STABILIZATION",
    "PATCH_PRESERVES_OBJECT_WITHOUT_CBIT_GAIN",
    "TABLE_FILLING_WITHOUT_POSSIBILITY_COMPRESSION",
    "EDGE_CONTROL_WITH_CENTRAL_FAILURE",
    "WRITEBACK_GROWTH_WITHOUT_DECISIVENESS",
)
ANTI_ADDITIVE_DECISION_STATES = (
    "ALLOW_BOUNDED_CHANGE",
    "REQUIRE_FIRST_PRINCIPLES_REFRAMING",
    "REQUIRE_OBJECT_UPGRADE",
    "BLOCK_PATCH_ACCUMULATION",
    "BLOCK_ABSTRACTION_FOG",
    "REQUIRE_CALIBRATED_VALIDATION",
    "BLOCK_CALIBRATION_DRIFT",
)


def methodology_candidate_commitment(payload: dict[str, Any]) -> str:
    excluded = {
        "anti_additive_methodology_receipt",
        "anti_additive_methodology_decision",
        "methodology_receipt",
    }
    return hash_payload({key: value for key, value in payload.items() if key not in excluded})


def require_anti_additive_id(name: str, value: str) -> None:
    require_text(name, value)
    if any(char.isspace() for char in value):
        raise ValueError(f"{name}_invalid")


def _require_nonnegative_int(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class AntiAdditiveChangeCandidate:
    audit_id: str
    candidate_id: str
    project_scope: str
    change_kind: str
    target_type: str
    current_object_ref: str
    proposed_object_ref: str
    current_object_level: str
    proposed_object_level: str
    prior_failure_count: int
    prior_patch_count: int
    candidate_payload_hash: str
    evidence_refs: tuple[str, ...]
    candidate_hash: str

    def __post_init__(self) -> None:
        require_anti_additive_id("anti_additive_audit_id", self.audit_id)
        require_anti_additive_id("anti_additive_candidate_id", self.candidate_id)
        if not self.project_scope.startswith("project://"):
            raise ValueError("anti_additive_project_scope_invalid")
        if self.change_kind not in ANTI_ADDITIVE_CHANGE_KINDS:
            raise ValueError("anti_additive_change_kind_invalid")
        require_text("anti_additive_target_type", self.target_type)
        require_text("anti_additive_current_object_ref", self.current_object_ref)
        require_text("anti_additive_proposed_object_ref", self.proposed_object_ref)
        if self.current_object_level not in ANTI_ADDITIVE_OBJECT_LEVELS:
            raise ValueError("anti_additive_current_object_level_invalid")
        if self.proposed_object_level not in ANTI_ADDITIVE_OBJECT_LEVELS:
            raise ValueError("anti_additive_proposed_object_level_invalid")
        _require_nonnegative_int("anti_additive_prior_failure_count", self.prior_failure_count)
        _require_nonnegative_int("anti_additive_prior_patch_count", self.prior_patch_count)
        if len(self.candidate_payload_hash) != 64:
            raise ValueError("anti_additive_candidate_payload_hash_invalid")
        require_refs("anti_additive_candidate_evidence_refs", self.evidence_refs)
        if self.candidate_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_candidate_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveChangeCandidate":
        committed = {**values, "evidence_refs": list(values["evidence_refs"])}
        return cls(**values, candidate_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            key: (list(value) if key == "evidence_refs" else value)
            for key, value in self.__dict__.items()
            if key != "candidate_hash"
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "candidate_hash": self.candidate_hash}


@dataclass(frozen=True)
class AntiAdditiveTriggerAssessment:
    trigger_id: str
    triggered: bool
    rationale: str
    evidence_refs: tuple[str, ...]
    assessment_hash: str

    def __post_init__(self) -> None:
        if self.trigger_id not in ANTI_ADDITIVE_TRIGGER_IDS:
            raise ValueError("anti_additive_trigger_id_invalid")
        if not isinstance(self.triggered, bool):
            raise ValueError("anti_additive_trigger_value_invalid")
        require_text("anti_additive_trigger_rationale", self.rationale)
        require_refs("anti_additive_trigger_evidence_refs", self.evidence_refs)
        if self.assessment_hash != hash_payload(self._committed_dict()):
            raise ValueError("anti_additive_trigger_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "AntiAdditiveTriggerAssessment":
        committed = {**values, "evidence_refs": list(values["evidence_refs"])}
        return cls(**values, assessment_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "triggered": self.triggered,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "assessment_hash": self.assessment_hash}
