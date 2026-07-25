"""Pure factorized transformation compiler for R4 v0.3H."""

from __future__ import annotations

from .contracts import hash_payload
from .factor_contracts import (
    VALID_STATUS_EFFECT_PAIRS,
    FactorizedCompilationReceipt,
    FactorizedTransformationCandidate,
)
from .transform_compiler import RELATION_TO_ACTION


def _errors(candidate: FactorizedTransformationCandidate) -> tuple[str, ...]:
    errors = []
    if (
        candidate.transform_status,
        candidate.information_effect,
    ) not in VALID_STATUS_EFFECT_PAIRS:
        errors.append("STATUS_EFFECT_INCONSISTENT")
    required = (
        ("SOURCE_WITNESS_MISSING", candidate.source_witness_ref),
        ("TRANSFORM_STATUS_WITNESS_MISSING", candidate.transform_status_witness_ref),
        (
            "INFORMATION_EFFECT_WITNESS_MISSING",
            candidate.information_effect_witness_ref,
        ),
        ("TARGET_CLAIM_WITNESS_MISSING", candidate.target_claim_witness_ref),
    )
    errors.extend(name for name, value in required if not value)
    if (
        candidate.lineage_coupling != "NOT_APPLICABLE"
        and not candidate.lineage_witness_ref
    ):
        errors.append("LINEAGE_WITNESS_MISSING")
    if (
        candidate.added_uncertainty != "NOT_APPLICABLE"
        and not candidate.uncertainty_witness_ref
    ):
        errors.append("UNCERTAINTY_WITNESS_MISSING")
    if (
        candidate.information_effect == "GLOBAL_EQUIVALENT"
        and not candidate.full_domain_witness_ref
    ):
        errors.append("FULL_DOMAIN_WITNESS_MISSING")
    if (
        candidate.information_effect == "CLAIM_EQUIVALENT"
        or candidate.added_uncertainty == "IMMATERIAL_FOR_CLAIM"
    ) and not candidate.claim_tolerance_witness_ref:
        errors.append("CLAIM_TOLERANCE_WITNESS_MISSING")
    return tuple(sorted(set(errors)))


def _relation(
    candidate: FactorizedTransformationCandidate, errors: tuple[str, ...]
) -> str:
    if errors:
        return "UNRESOLVED"
    if candidate.source_identity == "UNKNOWN_SOURCE":
        return "UNRESOLVED"
    if candidate.target_claim_relation == "UNKNOWN_TARGET_CLAIM":
        return "UNRESOLVED"
    if candidate.lineage_coupling == "UNKNOWN_PIPELINE":
        return "UNRESOLVED"
    if candidate.transform_status in {
        "ASSERTED_UNVERIFIED_TRANSFORM",
        "UNKNOWN_TRANSFORM_APPLICABILITY",
    }:
        return "UNRESOLVED"
    if candidate.information_effect == "UNKNOWN_EFFECT":
        return "UNRESOLVED"
    if candidate.added_uncertainty == "UNKNOWN_UNCERTAINTY":
        return "UNRESOLVED"
    if candidate.target_claim_relation == "DIFFERENT_TARGET_CLAIM":
        return "SCOPE_INCOMPATIBLE"
    if candidate.source_identity == "PARTIAL_SOURCE":
        return "PARTIAL_OVERLAP"
    if candidate.source_identity == "DISTINCT_SOURCE":
        if candidate.lineage_coupling == "SEPARATE_PIPELINES":
            return "INDEPENDENT_DISTINCT"
        if candidate.lineage_coupling == "SAME_PIPELINE":
            return "DEPENDENT_DISTINCT"
        return "UNRESOLVED"
    if candidate.source_identity != "SAME_SOURCE":
        return "UNRESOLVED"
    if candidate.transform_status != "VERIFIED_TRANSFORM":
        return "UNRESOLVED"
    if (
        candidate.information_effect
        in {"GLOBAL_EQUIVALENT", "CLAIM_EQUIVALENT"}
        and candidate.added_uncertainty
        in {"IMMATERIAL_FOR_CLAIM", "NOT_APPLICABLE"}
    ):
        return "EXACT_DUPLICATE"
    if (
        candidate.information_effect
        in {"INFORMATION_REDUCING", "INFORMATION_AUGMENTING"}
        or candidate.added_uncertainty == "MATERIAL_FOR_CLAIM"
    ):
        return "DEPENDENT_DISTINCT"
    return "UNRESOLVED"


def compile_factorized_transformation(
    candidate: FactorizedTransformationCandidate,
) -> FactorizedCompilationReceipt:
    values = {
        key: value
        for key, value in candidate.__dict__.items()
        if not key.startswith("expected_")
    }
    candidate_hash = hash_payload(values)
    errors = _errors(candidate)
    relation_state = _relation(candidate, errors)
    action = RELATION_TO_ACTION[relation_state]
    receipt_values = {
        "case_id": candidate.case_id,
        "relation_state": relation_state,
        "action": action,
        "errors": errors,
        "candidate_hash": candidate_hash,
    }
    return FactorizedCompilationReceipt(
        **receipt_values,
        receipt_hash=hash_payload(receipt_values),
    )
