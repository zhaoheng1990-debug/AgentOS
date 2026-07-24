"""Typed relation-evidence binding contracts validated by v0.63."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


TYPED_EVIDENCE_BINDING_VERSION = "typed-evidence-binding-v0.1"
EVIDENCE_DESIGNS = (
    "INTERVENTION_OR_ROLLBACK",
    "MATCHED_NULL_COMPARISON",
    "UNTESTED_DIFFERENCE",
    "OTHER",
)
OBJECT_BINDING_STATES = ("EXACT_EXPLICIT", "COREFERENCE", "UNBOUND")


def _hash_payload(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _valid_refs(name: str, refs: tuple[str, ...], *, required=False) -> None:
    if (
        (required and not refs)
        or len(refs) != len(set(refs))
        or any(not isinstance(ref, str) or not ref for ref in refs)
    ):
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class TypedRelationEvidenceBinding:
    relation_id: str
    source_object_ref: str
    target_object_ref: str
    source_object_binding: str
    target_outcome_binding: str
    evidence_design: str
    primary_evidence_refs: tuple[str, ...]
    corroborating_evidence_refs: tuple[str, ...] = ()
    counterevidence_refs: tuple[str, ...] = ()
    gap_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(
            (self.relation_id, self.source_object_ref, self.target_object_ref)
        ):
            raise ValueError("typed_evidence_relation_identity_required")
        if (
            self.source_object_binding not in OBJECT_BINDING_STATES
            or self.target_outcome_binding not in OBJECT_BINDING_STATES
        ):
            raise ValueError("typed_evidence_object_binding_invalid")
        if self.evidence_design not in EVIDENCE_DESIGNS:
            raise ValueError("typed_evidence_design_invalid")
        fields = (
            ("primary_evidence_refs", self.primary_evidence_refs, True),
            (
                "corroborating_evidence_refs",
                self.corroborating_evidence_refs,
                False,
            ),
            ("counterevidence_refs", self.counterevidence_refs, False),
            ("gap_evidence_refs", self.gap_evidence_refs, False),
        )
        seen: set[str] = set()
        for name, refs, required in fields:
            _valid_refs(name, refs, required=required)
            if seen.intersection(refs):
                raise ValueError("typed_evidence_cross_type_overlap")
            seen.update(refs)

    @property
    def binding_state(self) -> str:
        return (
            "BOUND"
            if self.source_object_binding != "UNBOUND"
            and self.target_outcome_binding != "UNBOUND"
            else "UNBOUND"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "source_object_ref": self.source_object_ref,
            "target_object_ref": self.target_object_ref,
            "source_object_binding": self.source_object_binding,
            "target_outcome_binding": self.target_outcome_binding,
            "evidence_design": self.evidence_design,
            "binding_state": self.binding_state,
            "primary_evidence_refs": list(self.primary_evidence_refs),
            "corroborating_evidence_refs": list(
                self.corroborating_evidence_refs
            ),
            "counterevidence_refs": list(self.counterevidence_refs),
            "gap_evidence_refs": list(self.gap_evidence_refs),
            "truth_state_authority": False,
        }


@dataclass(frozen=True)
class TypedEvidenceConsensus:
    relation_binding: TypedRelationEvidenceBinding | None
    conflicts: tuple[str, ...]
    auxiliary_divergences: tuple[str, ...]
    source_receipt_hashes: tuple[str, str]

    @property
    def ready(self) -> bool:
        return self.relation_binding is not None and not self.conflicts

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "version": TYPED_EVIDENCE_BINDING_VERSION,
            "relation_binding": (
                self.relation_binding.as_dict()
                if self.relation_binding
                else None
            ),
            "conflicts": list(self.conflicts),
            "auxiliary_divergences": list(
                self.auxiliary_divergences
            ),
            "source_receipt_hashes": list(self.source_receipt_hashes),
            "ready": self.ready,
            "primary_consensus": "STRICT_SET_EQUALITY",
            "auxiliary_policy": "NONCONFLICTING_TYPED_UNION",
            "truth_state_authority": False,
        }
        return {**payload, "consensus_hash": _hash_payload(payload)}


class TypedEvidenceConsensusGate:
    """Merge only the typed auxiliary evidence that does not conflict."""

    def evaluate(
        self,
        left: TypedRelationEvidenceBinding,
        right: TypedRelationEvidenceBinding,
        *,
        left_receipt_hash: str,
        right_receipt_hash: str,
    ) -> TypedEvidenceConsensus:
        conflicts: list[str] = []
        if (
            left.relation_id != right.relation_id
            or left.source_object_ref != right.source_object_ref
            or left.target_object_ref != right.target_object_ref
        ):
            conflicts.append("RELATION_IDENTITY_DISAGREEMENT")
        if (left.source_object_binding != "UNBOUND") != (
            right.source_object_binding != "UNBOUND"
        ):
            conflicts.append("SOURCE_BINDING_DISAGREEMENT")
        if (left.target_outcome_binding != "UNBOUND") != (
            right.target_outcome_binding != "UNBOUND"
        ):
            conflicts.append("TARGET_BINDING_DISAGREEMENT")
        if left.evidence_design != right.evidence_design:
            conflicts.append("EVIDENCE_DESIGN_DISAGREEMENT")
        if set(left.primary_evidence_refs) != set(
            right.primary_evidence_refs
        ):
            conflicts.append("PRIMARY_EVIDENCE_DISAGREEMENT")
        left_types = self._typed_refs(left)
        right_types = self._typed_refs(right)
        if any(
            ref in right_types and right_types[ref] != evidence_type
            for ref, evidence_type in left_types.items()
        ):
            conflicts.append("EVIDENCE_TYPE_CONFLICT")
        hashes = (left_receipt_hash, right_receipt_hash)
        if conflicts:
            return TypedEvidenceConsensus(
                None, tuple(conflicts), (), hashes
            )
        divergence: list[str] = []
        merged: dict[str, tuple[str, ...]] = {}
        for field in (
            "corroborating_evidence_refs",
            "counterevidence_refs",
            "gap_evidence_refs",
        ):
            first = set(getattr(left, field))
            second = set(getattr(right, field))
            merged[field] = tuple(sorted(first | second))
            if first != second:
                divergence.append(field)
        relation = TypedRelationEvidenceBinding(
            relation_id=left.relation_id,
            source_object_ref=left.source_object_ref,
            target_object_ref=left.target_object_ref,
            source_object_binding=self._coarse(
                left.source_object_binding,
                right.source_object_binding,
            ),
            target_outcome_binding=self._coarse(
                left.target_outcome_binding,
                right.target_outcome_binding,
            ),
            evidence_design=left.evidence_design,
            primary_evidence_refs=tuple(
                sorted(set(left.primary_evidence_refs))
            ),
            **merged,
        )
        return TypedEvidenceConsensus(
            relation, (), tuple(divergence), hashes
        )

    @staticmethod
    def _typed_refs(
        value: TypedRelationEvidenceBinding,
    ) -> dict[str, str]:
        return {
            ref: field
            for field in (
                "primary_evidence_refs",
                "corroborating_evidence_refs",
                "counterevidence_refs",
                "gap_evidence_refs",
            )
            for ref in getattr(value, field)
        }

    @staticmethod
    def _coarse(left: str, right: str) -> str:
        if "UNBOUND" in (left, right):
            return "UNBOUND"
        if "COREFERENCE" in (left, right):
            return "COREFERENCE"
        return "EXACT_EXPLICIT"
