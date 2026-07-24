"""Post-selection consequence and retention-evidence contracts."""

from __future__ import annotations

from dataclasses import dataclass

from .selection_models import hash_selection_payload
from .sro_retention_models import parse_timestamp, require_sha256


VALIDITY_ASSESSMENT_STATES = ("CURRENT", "UNKNOWN", "DRIFTED", "STALE")
CONSEQUENCE_KINDS = ("IMMEDIATE", "DELAYED")


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def _refs(name: str, refs: tuple[str, ...]) -> None:
    if (
        not refs
        or len(refs) != len(set(refs))
        or any(not isinstance(ref, str) or not ref for ref in refs)
    ):
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class ConsequenceBinding:
    binding_id: str
    project_scope: str
    selection_event_hash: str
    consequence_ref: str
    consequence_kind: str
    evidence_refs: tuple[str, ...]
    observed_at: str
    assignment_state: str = "UNASSIGNED"
    binding_hash: str = ""

    @classmethod
    def create(cls, **values):
        commitment = cls._commitment(values)
        return cls(**values, binding_hash=hash_selection_payload(commitment))

    def __post_init__(self) -> None:
        _required("binding_id", self.binding_id)
        _required("consequence_ref", self.consequence_ref)
        if not self.project_scope.startswith("project://"):
            raise ValueError("consequence_project_scope_invalid")
        require_sha256("selection_event_hash", self.selection_event_hash)
        if self.consequence_kind not in CONSEQUENCE_KINDS:
            raise ValueError("consequence_kind_invalid")
        _refs("consequence_evidence_refs", self.evidence_refs)
        parse_timestamp("observed_at", self.observed_at)
        if self.assignment_state != "UNASSIGNED":
            raise ValueError("consequence_must_begin_unassigned")
        require_sha256("binding_hash", self.binding_hash)
        if self.binding_hash != hash_selection_payload(
            self._commitment(self.__dict__)
        ):
            raise ValueError("consequence_binding_hash_invalid")

    @staticmethod
    def _commitment(values):
        return {
            "binding_id": values["binding_id"],
            "project_scope": values["project_scope"],
            "selection_event_hash": values["selection_event_hash"],
            "consequence_ref": values["consequence_ref"],
            "consequence_kind": values["consequence_kind"],
            "evidence_refs": list(values["evidence_refs"]),
            "observed_at": values["observed_at"],
            "assignment_state": values.get("assignment_state", "UNASSIGNED"),
            "retention_attribution_authority": False,
        }

    def as_dict(self):
        return {
            **self._commitment(self.__dict__),
            "binding_hash": self.binding_hash,
        }


@dataclass(frozen=True)
class ApplicabilityDelta:
    selection_event_hash: str
    consequence_binding_hash: str
    applicability_delta: float
    provider_receipt_hash: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "selection_event_hash",
            "consequence_binding_hash",
            "provider_receipt_hash",
        ):
            require_sha256(name, getattr(self, name))
        if isinstance(self.applicability_delta, bool) or not (
            -1 <= self.applicability_delta <= 1
        ):
            raise ValueError("applicability_delta_invalid")
        _refs("applicability_delta_evidence_refs", self.evidence_refs)


@dataclass(frozen=True)
class ValueDelta:
    selection_event_hash: str
    consequence_binding_hash: str
    observed_cbit_gain: float
    observed_cost: float
    harness_receipt_hash: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "selection_event_hash",
            "consequence_binding_hash",
            "harness_receipt_hash",
        ):
            require_sha256(name, getattr(self, name))
        if isinstance(self.observed_cbit_gain, bool) or isinstance(
            self.observed_cost, bool
        ) or self.observed_cost < 0:
            raise ValueError("value_delta_invalid")
        _refs("value_delta_evidence_refs", self.evidence_refs)


@dataclass(frozen=True)
class ValidityAssessment:
    selection_event_hash: str
    validity_state: str
    boundary_ref: str
    provider_receipt_hash: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        require_sha256("selection_event_hash", self.selection_event_hash)
        require_sha256(
            "validity_provider_receipt_hash", self.provider_receipt_hash
        )
        if self.validity_state not in VALIDITY_ASSESSMENT_STATES:
            raise ValueError("validity_state_invalid")
        _required("validity_boundary_ref", self.boundary_ref)
        _refs("validity_evidence_refs", self.evidence_refs)
