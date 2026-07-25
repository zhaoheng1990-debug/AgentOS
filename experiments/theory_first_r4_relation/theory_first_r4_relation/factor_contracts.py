"""Factorized transformation-semantics contracts for R4 v0.3H."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .contracts import PLAN_ACTIONS, RELATION_STATES
from .transform_contracts import (
    ADDED_UNCERTAINTIES,
    LINEAGE_COUPLINGS,
    SOURCE_IDENTITIES,
    TARGET_CLAIM_RELATIONS,
)


TRANSFORM_STATUSES = (
    "NO_TRANSFORM",
    "VERIFIED_TRANSFORM",
    "ASSERTED_UNVERIFIED_TRANSFORM",
    "UNKNOWN_TRANSFORM_APPLICABILITY",
)
INFORMATION_EFFECTS = (
    "GLOBAL_EQUIVALENT",
    "CLAIM_EQUIVALENT",
    "INFORMATION_REDUCING",
    "INFORMATION_AUGMENTING",
    "UNKNOWN_EFFECT",
    "NOT_APPLICABLE",
)
VALID_STATUS_EFFECT_PAIRS = frozenset(
    {
        ("NO_TRANSFORM", "NOT_APPLICABLE"),
        ("VERIFIED_TRANSFORM", "GLOBAL_EQUIVALENT"),
        ("VERIFIED_TRANSFORM", "CLAIM_EQUIVALENT"),
        ("VERIFIED_TRANSFORM", "INFORMATION_REDUCING"),
        ("VERIFIED_TRANSFORM", "INFORMATION_AUGMENTING"),
        ("ASSERTED_UNVERIFIED_TRANSFORM", "UNKNOWN_EFFECT"),
        ("UNKNOWN_TRANSFORM_APPLICABILITY", "UNKNOWN_EFFECT"),
    }
)


@dataclass(frozen=True)
class FactorizedTransformationCandidate:
    case_id: str
    case_family: str
    source_identity: str
    lineage_coupling: str
    transform_status: str
    information_effect: str
    added_uncertainty: str
    target_claim_relation: str
    source_witness_ref: str | None
    lineage_witness_ref: str | None
    transform_status_witness_ref: str | None
    information_effect_witness_ref: str | None
    target_claim_witness_ref: str | None
    uncertainty_witness_ref: str | None
    claim_tolerance_witness_ref: str | None
    full_domain_witness_ref: str | None
    expected_relation_state: str
    expected_action: str

    def __post_init__(self) -> None:
        checks = (
            (self.source_identity, SOURCE_IDENTITIES, "source identity"),
            (self.lineage_coupling, LINEAGE_COUPLINGS, "lineage coupling"),
            (self.transform_status, TRANSFORM_STATUSES, "transform status"),
            (self.information_effect, INFORMATION_EFFECTS, "information effect"),
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
class FactorizedCompilationReceipt:
    case_id: str
    relation_state: str
    action: str
    errors: tuple[str, ...]
    candidate_hash: str
    receipt_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
