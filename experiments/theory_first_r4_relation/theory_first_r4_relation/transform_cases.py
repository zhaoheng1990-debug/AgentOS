"""Frozen transformation-equivalence grid for R4 v0.3F."""

from __future__ import annotations

from .transform_contracts import TransformationRelationCandidate


def _case(
    case_id: str,
    family: str,
    source: str,
    pipeline: str,
    information: str,
    uncertainty: str,
    claim: str,
    relation: str,
    action: str,
    *,
    transform_witness: bool = True,
    uncertainty_witness: bool = True,
    tolerance_witness: bool = True,
) -> TransformationRelationCandidate:
    return TransformationRelationCandidate(
        case_id=case_id,
        case_family=family,
        source_identity=source,
        lineage_coupling=pipeline,
        information_relation=information,
        added_uncertainty=uncertainty,
        target_claim_relation=claim,
        source_witness_ref=f"source://{case_id}",
        lineage_witness_ref=(
            f"lineage://{case_id}" if pipeline != "NOT_APPLICABLE" else None
        ),
        transformation_witness_ref=(
            f"transform://{case_id}"
            if information != "NOT_APPLICABLE" and transform_witness
            else None
        ),
        target_claim_witness_ref=f"claim://{case_id}",
        uncertainty_witness_ref=(
            f"uncertainty://{case_id}"
            if uncertainty != "NOT_APPLICABLE" and uncertainty_witness
            else None
        ),
        claim_tolerance_witness_ref=(
            f"tolerance://{case_id}"
            if (
                information == "VERIFIED_CLAIM_EQUIVALENCE"
                or uncertainty == "IMMATERIAL_FOR_CLAIM"
            )
            and tolerance_witness
            else None
        ),
        expected_relation_state=relation,
        expected_action=action,
    )


TRANSFORMATION_CASES = (
    _case(
        "R43F-01",
        "renamed identical source",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_GLOBAL_EQUIVALENCE",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43F-02",
        "lossless compression",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_GLOBAL_EQUIVALENCE",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43F-03",
        "exact unit conversion",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_CLAIM_EQUIVALENCE",
        "IMMATERIAL_FOR_CLAIM",
        "SAME_TARGET_CLAIM",
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43F-04",
        "claim-preserving redaction",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_CLAIM_EQUIVALENCE",
        "IMMATERIAL_FOR_CLAIM",
        "SAME_TARGET_CLAIM",
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43F-05",
        "calibrated conversion below claim tolerance",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_CLAIM_EQUIVALENCE",
        "IMMATERIAL_FOR_CLAIM",
        "SAME_TARGET_CLAIM",
        "EXACT_DUPLICATE",
        "DEDUPE_AND_COMBINE",
    ),
    _case(
        "R43F-06",
        "calibrated conversion with material error",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_CLAIM_EQUIVALENCE",
        "MATERIAL_FOR_CLAIM",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-07",
        "aggregate mean from full source",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "INFORMATION_REDUCING",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-08",
        "lossy summary",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "INFORMATION_REDUCING",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-09",
        "model-derived score",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "INFORMATION_AUGMENTING",
        "MATERIAL_FOR_CLAIM",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-10",
        "stochastic transformed output",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "INFORMATION_AUGMENTING",
        "MATERIAL_FOR_CLAIM",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-11",
        "distinct statistics from one full source",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "INFORMATION_REDUCING",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-12",
        "subset versus full source",
        "PARTIAL_SOURCE",
        "SAME_PIPELINE",
        "NOT_APPLICABLE",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "PARTIAL_OVERLAP",
        "BLOCK",
    ),
    _case(
        "R43F-13",
        "one source used for different target claims",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "NOT_APPLICABLE",
        "NOT_APPLICABLE",
        "DIFFERENT_TARGET_CLAIM",
        "SCOPE_INCOMPATIBLE",
        "BLOCK",
    ),
    _case(
        "R43F-14",
        "distinct sources and separate pipelines",
        "DISTINCT_SOURCE",
        "SEPARATE_PIPELINES",
        "NOT_APPLICABLE",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "INDEPENDENT_DISTINCT",
        "COMBINE",
    ),
    _case(
        "R43F-15",
        "same source with unverified transform",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "UNVERIFIED_TRANSFORM",
        "UNKNOWN_UNCERTAINTY",
        "SAME_TARGET_CLAIM",
        "UNRESOLVED",
        "BLOCK",
    ),
    _case(
        "R43F-16",
        "unknown source identity",
        "UNKNOWN_SOURCE",
        "UNKNOWN_PIPELINE",
        "NOT_APPLICABLE",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "UNRESOLVED",
        "BLOCK",
    ),
    _case(
        "R43F-17",
        "distinct sources with shared pipeline",
        "DISTINCT_SOURCE",
        "SAME_PIPELINE",
        "NOT_APPLICABLE",
        "NOT_APPLICABLE",
        "SAME_TARGET_CLAIM",
        "DEPENDENT_DISTINCT",
        "BLOCK",
    ),
    _case(
        "R43F-18",
        "unknown target claim relation",
        "SAME_SOURCE",
        "SAME_PIPELINE",
        "VERIFIED_GLOBAL_EQUIVALENCE",
        "NOT_APPLICABLE",
        "UNKNOWN_TARGET_CLAIM",
        "UNRESOLVED",
        "BLOCK",
    ),
)
