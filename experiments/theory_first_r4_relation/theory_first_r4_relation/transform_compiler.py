"""Pure attribute-to-relation compiler for R4 v0.3F."""

from __future__ import annotations

from .contracts import hash_payload
from .transform_contracts import (
    TransformationCompilationReceipt,
    TransformationRelationCandidate,
)


RELATION_TO_ACTION = {
    "INDEPENDENT_DISTINCT": "COMBINE",
    "EXACT_DUPLICATE": "DEDUPE_AND_COMBINE",
    "DEPENDENT_DISTINCT": "BLOCK",
    "PARTIAL_OVERLAP": "BLOCK",
    "SCOPE_INCOMPATIBLE": "BLOCK",
    "UNRESOLVED": "BLOCK",
}


def _missing_witnesses(
    candidate: TransformationRelationCandidate,
) -> tuple[str, ...]:
    missing = []
    if not candidate.source_witness_ref:
        missing.append("SOURCE_WITNESS_MISSING")
    if (
        candidate.lineage_coupling != "NOT_APPLICABLE"
        and not candidate.lineage_witness_ref
    ):
        missing.append("LINEAGE_WITNESS_MISSING")
    if not candidate.target_claim_witness_ref:
        missing.append("TARGET_CLAIM_WITNESS_MISSING")
    if (
        candidate.information_relation != "NOT_APPLICABLE"
        and not candidate.transformation_witness_ref
    ):
        missing.append("TRANSFORMATION_WITNESS_MISSING")
    if (
        candidate.added_uncertainty != "NOT_APPLICABLE"
        and not candidate.uncertainty_witness_ref
    ):
        missing.append("UNCERTAINTY_WITNESS_MISSING")
    if (
        candidate.information_relation == "VERIFIED_CLAIM_EQUIVALENCE"
        or candidate.added_uncertainty == "IMMATERIAL_FOR_CLAIM"
    ) and not candidate.claim_tolerance_witness_ref:
        missing.append("CLAIM_TOLERANCE_WITNESS_MISSING")
    return tuple(sorted(missing))


def _compile_relation(
    candidate: TransformationRelationCandidate, errors: tuple[str, ...]
) -> str:
    if errors:
        return "UNRESOLVED"
    if candidate.source_identity == "UNKNOWN_SOURCE":
        return "UNRESOLVED"
    if candidate.target_claim_relation == "UNKNOWN_TARGET_CLAIM":
        return "UNRESOLVED"
    if candidate.target_claim_relation == "DIFFERENT_TARGET_CLAIM":
        return "SCOPE_INCOMPATIBLE"
    if candidate.source_identity == "PARTIAL_SOURCE":
        return "PARTIAL_OVERLAP"
    if candidate.source_identity == "DISTINCT_SOURCE":
        if candidate.lineage_coupling == "UNKNOWN_PIPELINE":
            return "UNRESOLVED"
        if candidate.lineage_coupling == "SEPARATE_PIPELINES":
            return "INDEPENDENT_DISTINCT"
        if candidate.lineage_coupling == "SAME_PIPELINE":
            return "DEPENDENT_DISTINCT"
        return "UNRESOLVED"
    if candidate.source_identity != "SAME_SOURCE":
        return "UNRESOLVED"
    if candidate.information_relation == "UNVERIFIED_TRANSFORM":
        return "UNRESOLVED"
    if candidate.added_uncertainty == "UNKNOWN_UNCERTAINTY":
        return "UNRESOLVED"
    if (
        candidate.information_relation == "VERIFIED_GLOBAL_EQUIVALENCE"
        and candidate.added_uncertainty
        in {"IMMATERIAL_FOR_CLAIM", "NOT_APPLICABLE"}
    ):
        return "EXACT_DUPLICATE"
    if (
        candidate.information_relation == "VERIFIED_CLAIM_EQUIVALENCE"
        and candidate.added_uncertainty == "IMMATERIAL_FOR_CLAIM"
    ):
        return "EXACT_DUPLICATE"
    if (
        candidate.information_relation
        in {"INFORMATION_REDUCING", "INFORMATION_AUGMENTING"}
        or candidate.added_uncertainty == "MATERIAL_FOR_CLAIM"
    ):
        return "DEPENDENT_DISTINCT"
    return "UNRESOLVED"


def compile_transformation_relation(
    candidate: TransformationRelationCandidate,
) -> TransformationCompilationReceipt:
    candidate_values = {
        key: value
        for key, value in candidate.__dict__.items()
        if not key.startswith("expected_")
    }
    candidate_hash = hash_payload(candidate_values)
    errors = _missing_witnesses(candidate)
    relation_state = _compile_relation(candidate, errors)
    action = RELATION_TO_ACTION[relation_state]
    receipt_values = {
        "case_id": candidate.case_id,
        "relation_state": relation_state,
        "action": action,
        "errors": errors,
        "candidate_hash": candidate_hash,
    }
    return TransformationCompilationReceipt(
        **receipt_values,
        receipt_hash=hash_payload(receipt_values),
    )
