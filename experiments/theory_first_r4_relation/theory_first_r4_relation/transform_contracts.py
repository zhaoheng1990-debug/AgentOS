"""Typed transformation-equivalence candidates for R4 v0.3F."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import PLAN_ACTIONS, RELATION_STATES


SOURCE_IDENTITIES = (
    "SAME_SOURCE",
    "PARTIAL_SOURCE",
    "DISTINCT_SOURCE",
    "UNKNOWN_SOURCE",
)
LINEAGE_COUPLINGS = (
    "SAME_PIPELINE",
    "SEPARATE_PIPELINES",
    "UNKNOWN_PIPELINE",
    "NOT_APPLICABLE",
)
INFORMATION_RELATIONS = (
    "VERIFIED_GLOBAL_EQUIVALENCE",
    "VERIFIED_CLAIM_EQUIVALENCE",
    "INFORMATION_REDUCING",
    "INFORMATION_AUGMENTING",
    "UNVERIFIED_TRANSFORM",
    "NOT_APPLICABLE",
)
ADDED_UNCERTAINTIES = (
    "IMMATERIAL_FOR_CLAIM",
    "MATERIAL_FOR_CLAIM",
    "UNKNOWN_UNCERTAINTY",
    "NOT_APPLICABLE",
)
TARGET_CLAIM_RELATIONS = (
    "SAME_TARGET_CLAIM",
    "DIFFERENT_TARGET_CLAIM",
    "UNKNOWN_TARGET_CLAIM",
)


@dataclass(frozen=True)
class TransformationRelationCandidate:
    case_id: str
    case_family: str
    source_identity: str
    lineage_coupling: str
    information_relation: str
    added_uncertainty: str
    target_claim_relation: str
    source_witness_ref: str | None
    lineage_witness_ref: str | None
    transformation_witness_ref: str | None
    target_claim_witness_ref: str | None
    uncertainty_witness_ref: str | None
    claim_tolerance_witness_ref: str | None
    expected_relation_state: str
    expected_action: str

    def __post_init__(self) -> None:
        checks = (
            (self.source_identity, SOURCE_IDENTITIES, "source identity"),
            (self.lineage_coupling, LINEAGE_COUPLINGS, "lineage coupling"),
            (
                self.information_relation,
                INFORMATION_RELATIONS,
                "information relation",
            ),
            (
                self.added_uncertainty,
                ADDED_UNCERTAINTIES,
                "added uncertainty",
            ),
            (
                self.target_claim_relation,
                TARGET_CLAIM_RELATIONS,
                "target claim relation",
            ),
            (
                self.expected_relation_state,
                RELATION_STATES,
                "expected relation state",
            ),
            (self.expected_action, PLAN_ACTIONS, "expected action"),
        )
        for value, allowed, name in checks:
            if value not in allowed:
                raise ValueError(f"unknown {name}: {value}")
        if not self.case_id or not self.case_family:
            raise ValueError("case identity and family are required")


@dataclass(frozen=True)
class TransformationCompilationReceipt:
    case_id: str
    relation_state: str
    action: str
    errors: tuple[str, ...]
    candidate_hash: str
    receipt_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
