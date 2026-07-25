"""Frozen twenty-case factorization grid for R4 v0.3H."""

from __future__ import annotations

from dataclasses import replace

from .factor_contracts import FactorizedTransformationCandidate


def _case(
    case_id: str,
    family: str,
    source: str,
    lineage: str,
    status: str,
    effect: str,
    uncertainty: str,
    target: str,
    relation: str,
    action: str,
) -> FactorizedTransformationCandidate:
    return FactorizedTransformationCandidate(
        case_id=case_id,
        case_family=family,
        source_identity=source,
        lineage_coupling=lineage,
        transform_status=status,
        information_effect=effect,
        added_uncertainty=uncertainty,
        target_claim_relation=target,
        source_witness_ref=f"witness://{case_id}/source",
        lineage_witness_ref=f"witness://{case_id}/lineage",
        transform_status_witness_ref=f"witness://{case_id}/transform-status",
        information_effect_witness_ref=f"witness://{case_id}/information-effect",
        target_claim_witness_ref=f"witness://{case_id}/target",
        uncertainty_witness_ref=(
            None
            if uncertainty == "NOT_APPLICABLE"
            else f"witness://{case_id}/uncertainty"
        ),
        claim_tolerance_witness_ref=(
            f"witness://{case_id}/tolerance"
            if effect == "CLAIM_EQUIVALENT"
            or uncertainty == "IMMATERIAL_FOR_CLAIM"
            else None
        ),
        full_domain_witness_ref=(
            f"witness://{case_id}/full-domain"
            if effect == "GLOBAL_EQUIVALENT"
            else None
        ),
        expected_relation_state=relation,
        expected_action=action,
    )


FACTORIZED_CASES = (
    _case("R43H-01", "reversible exact conversion", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "GLOBAL_EQUIVALENT", "IMMATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "EXACT_DUPLICATE", "DEDUPE_AND_COMBINE"),
    _case("R43H-02", "claim bounded redaction", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "CLAIM_EQUIVALENT", "IMMATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "EXACT_DUPLICATE", "DEDUPE_AND_COMBINE"),
    _case("R43H-03", "material calibration", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "CLAIM_EQUIVALENT", "MATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "DEPENDENT_DISTINCT", "BLOCK"),
    _case("R43H-04", "aggregate reduction", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "INFORMATION_REDUCING", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "DEPENDENT_DISTINCT", "BLOCK"),
    _case("R43H-05", "derived model score", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "INFORMATION_AUGMENTING", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "DEPENDENT_DISTINCT", "BLOCK"),
    _case("R43H-06", "strict subset reduction", "PARTIAL_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "INFORMATION_REDUCING", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "PARTIAL_OVERLAP", "BLOCK"),
    _case("R43H-07", "distinct independent records", "DISTINCT_SOURCE", "SEPARATE_PIPELINES", "NO_TRANSFORM", "NOT_APPLICABLE", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "INDEPENDENT_DISTINCT", "COMBINE"),
    _case("R43H-08", "distinct shared pipeline", "DISTINCT_SOURCE", "SAME_PIPELINE", "NO_TRANSFORM", "NOT_APPLICABLE", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "DEPENDENT_DISTINCT", "BLOCK"),
    _case("R43H-09", "unknown source and transform", "UNKNOWN_SOURCE", "UNKNOWN_PIPELINE", "UNKNOWN_TRANSFORM_APPLICABILITY", "UNKNOWN_EFFECT", "UNKNOWN_UNCERTAINTY", "SAME_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-10", "asserted unverified transform", "SAME_SOURCE", "SAME_PIPELINE", "ASSERTED_UNVERIFIED_TRANSFORM", "UNKNOWN_EFFECT", "UNKNOWN_UNCERTAINTY", "SAME_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-11", "unknown transform applicability", "SAME_SOURCE", "SAME_PIPELINE", "UNKNOWN_TRANSFORM_APPLICABILITY", "UNKNOWN_EFFECT", "UNKNOWN_UNCERTAINTY", "SAME_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-12", "same source without transform relation", "SAME_SOURCE", "NOT_APPLICABLE", "NO_TRANSFORM", "NOT_APPLICABLE", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-13", "different target claim", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "GLOBAL_EQUIVALENT", "IMMATERIAL_FOR_CLAIM", "DIFFERENT_TARGET_CLAIM", "SCOPE_INCOMPATIBLE", "BLOCK"),
    _case("R43H-14", "unknown target claim", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "GLOBAL_EQUIVALENT", "IMMATERIAL_FOR_CLAIM", "UNKNOWN_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-15", "unknown independent lineage", "DISTINCT_SOURCE", "UNKNOWN_PIPELINE", "NO_TRANSFORM", "NOT_APPLICABLE", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-16", "lossless full domain transform", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "GLOBAL_EQUIVALENT", "NOT_APPLICABLE", "SAME_TARGET_CLAIM", "EXACT_DUPLICATE", "DEDUPE_AND_COMBINE"),
    _case("R43H-17", "bounded claim equivalent transform", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "CLAIM_EQUIVALENT", "IMMATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "EXACT_DUPLICATE", "DEDUPE_AND_COMBINE"),
    _case("R43H-18", "reducing transform with material error", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "INFORMATION_REDUCING", "MATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "DEPENDENT_DISTINCT", "BLOCK"),
    _case("R43H-19", "registered but unverified calibration", "SAME_SOURCE", "SAME_PIPELINE", "ASSERTED_UNVERIFIED_TRANSFORM", "UNKNOWN_EFFECT", "MATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "UNRESOLVED", "BLOCK"),
    _case("R43H-20", "verified augmenting transform with material uncertainty", "SAME_SOURCE", "SAME_PIPELINE", "VERIFIED_TRANSFORM", "INFORMATION_AUGMENTING", "MATERIAL_FOR_CLAIM", "SAME_TARGET_CLAIM", "DEPENDENT_DISTINCT", "BLOCK"),
)


REMOVAL_CASES = (
    ("REMOVE_TRANSFORM_STATUS_WITNESS", replace(FACTORIZED_CASES[0], transform_status_witness_ref=None), "UNRESOLVED", "BLOCK"),
    ("REMOVE_INFORMATION_EFFECT_WITNESS", replace(FACTORIZED_CASES[0], information_effect_witness_ref=None), "UNRESOLVED", "BLOCK"),
    ("REMOVE_FULL_DOMAIN_WITNESS", replace(FACTORIZED_CASES[0], full_domain_witness_ref=None), "UNRESOLVED", "BLOCK"),
    ("REMOVE_CLAIM_TOLERANCE_WITNESS", replace(FACTORIZED_CASES[1], claim_tolerance_witness_ref=None), "UNRESOLVED", "BLOCK"),
    ("MAKE_STATUS_EFFECT_INCONSISTENT", replace(FACTORIZED_CASES[1], transform_status="ASSERTED_UNVERIFIED_TRANSFORM"), "UNRESOLVED", "BLOCK"),
    ("MAKE_SUBSET_SOURCE_UNKNOWN", replace(FACTORIZED_CASES[5], source_identity="UNKNOWN_SOURCE"), "UNRESOLVED", "BLOCK"),
)
