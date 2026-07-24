"""Prospective selection and semantic-route contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .sro_retention_models import parse_timestamp, require_sha256


SELECTION_RETENTION_OBJECT_VERSION = "selection-retention-object-v0.1"


def hash_selection_payload(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value


def _refs(name: str, refs: tuple[str, ...], *, required=True) -> None:
    if (
        (required and not refs)
        or len(refs) != len(set(refs))
        or any(not isinstance(ref, str) or not ref for ref in refs)
    ):
        raise ValueError(f"{name}_invalid")


@dataclass(frozen=True)
class ProspectiveSelectionEvent:
    selection_event_id: str
    project_scope: str
    selection_context_ref: str
    alternatives: tuple[str, ...]
    selected_ref: str
    rejected_refs: tuple[str, ...]
    deferred_refs: tuple[str, ...]
    path_change_hypothesis_ref: str
    sro_address_ref: str
    validity_boundary_ref: str
    reconstruction_ref: str
    authority_ref: str
    evidence_refs: tuple[str, ...]
    sealed_at: str
    preconsequence_hash: str
    candidate_state: str = "PRECOMMITTED_SELECTION"
    schema_version: str = SELECTION_RETENTION_OBJECT_VERSION

    @classmethod
    def create(cls, **values: Any) -> "ProspectiveSelectionEvent":
        commitment = cls._commitment(values)
        return cls(
            **values,
            preconsequence_hash=hash_selection_payload(commitment),
        )

    def __post_init__(self) -> None:
        for name in (
            "selection_event_id",
            "selection_context_ref",
            "selected_ref",
            "path_change_hypothesis_ref",
            "sro_address_ref",
            "validity_boundary_ref",
            "reconstruction_ref",
            "authority_ref",
        ):
            _required(name, getattr(self, name))
        if not self.project_scope.startswith("project://"):
            raise ValueError("selection_project_scope_invalid")
        if not self.authority_ref.startswith("kernel://"):
            raise ValueError("selection_kernel_authority_required")
        _refs("selection_alternatives", self.alternatives)
        _refs("selection_rejected_refs", self.rejected_refs, required=False)
        _refs("selection_deferred_refs", self.deferred_refs, required=False)
        _refs("selection_evidence_refs", self.evidence_refs)
        if len(self.alternatives) < 2 or self.selected_ref not in self.alternatives:
            raise ValueError("selection_requires_real_alternatives")
        if set(self.rejected_refs).intersection(self.deferred_refs):
            raise ValueError("selection_rejected_deferred_overlap")
        remaining = set(self.alternatives) - {self.selected_ref}
        if set(self.rejected_refs) | set(self.deferred_refs) != remaining:
            raise ValueError("selection_alternative_partition_incomplete")
        parse_timestamp("sealed_at", self.sealed_at)
        require_sha256("preconsequence_hash", self.preconsequence_hash)
        if self.candidate_state != "PRECOMMITTED_SELECTION":
            raise ValueError("selection_state_must_be_precommitted")
        expected = hash_selection_payload(
            self._commitment(self.__dict__)
        )
        if self.preconsequence_hash != expected:
            raise ValueError("selection_preconsequence_hash_invalid")

    @staticmethod
    def _commitment(values: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": values.get(
                "schema_version", SELECTION_RETENTION_OBJECT_VERSION
            ),
            "selection_event_id": values["selection_event_id"],
            "project_scope": values["project_scope"],
            "selection_context_ref": values["selection_context_ref"],
            "alternatives": list(values["alternatives"]),
            "selected_ref": values["selected_ref"],
            "rejected_refs": list(values["rejected_refs"]),
            "deferred_refs": list(values["deferred_refs"]),
            "path_change_hypothesis_ref": values[
                "path_change_hypothesis_ref"
            ],
            "sro_address_ref": values["sro_address_ref"],
            "validity_boundary_ref": values["validity_boundary_ref"],
            "reconstruction_ref": values["reconstruction_ref"],
            "authority_ref": values["authority_ref"],
            "evidence_refs": list(values["evidence_refs"]),
            "sealed_at": values["sealed_at"],
            "candidate_state": values.get(
                "candidate_state", "PRECOMMITTED_SELECTION"
            ),
            "consequence_known": False,
            "retention_authority": False,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._commitment(self.__dict__),
            "preconsequence_hash": self.preconsequence_hash,
        }


@dataclass(frozen=True)
class SemanticOperatorRoute:
    route_id: str
    project_scope: str
    selection_event_hash: str
    ranked_alternative_refs: tuple[str, ...]
    selected_ref: str
    expected_cbit_gain: float
    residual_risk: float
    uncertainty: float
    provider_receipt_hash: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _required("semantic_route_id", self.route_id)
        if not self.project_scope.startswith("project://"):
            raise ValueError("semantic_route_project_scope_invalid")
        require_sha256("selection_event_hash", self.selection_event_hash)
        require_sha256(
            "semantic_route_provider_receipt_hash",
            self.provider_receipt_hash,
        )
        _refs(
            "semantic_route_ranked_alternative_refs",
            self.ranked_alternative_refs,
        )
        if self.selected_ref not in self.ranked_alternative_refs:
            raise ValueError("semantic_route_selected_ref_not_ranked")
        for name, value in (
            ("residual_risk", self.residual_risk),
            ("uncertainty", self.uncertainty),
        ):
            if isinstance(value, bool) or not 0 <= value <= 1:
                raise ValueError(f"semantic_route_{name}_invalid")
        if isinstance(self.expected_cbit_gain, bool):
            raise ValueError("semantic_route_cbit_invalid")
        _refs("semantic_route_evidence_refs", self.evidence_refs)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "route_id": self.route_id,
            "project_scope": self.project_scope,
            "selection_event_hash": self.selection_event_hash,
            "ranked_alternative_refs": list(
                self.ranked_alternative_refs
            ),
            "selected_ref": self.selected_ref,
            "expected_cbit_gain": self.expected_cbit_gain,
            "residual_risk": self.residual_risk,
            "uncertainty": self.uncertainty,
            "provider_receipt_hash": self.provider_receipt_hash,
            "evidence_refs": list(self.evidence_refs),
            "kernel_selection_authority": True,
            "provider_selection_authority": False,
        }
        return {**payload, "route_hash": hash_selection_payload(payload)}
