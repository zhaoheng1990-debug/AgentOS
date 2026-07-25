"""Atomic Provider semantic facts and conflict detection v0.80."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES


FACT_FIELDS = (
    "span_id",
    "exact_target_object_mentioned",
    "target_effect_separately_extractable",
    "independent_effect_support",
    "effect_basis_codes",
    "non_effect_context_relevance",
    "rationale",
)


def structural_fact_violations(fact):
    failures = []
    if set(fact) != set(FACT_FIELDS):
        failures.append("ADMISSION_V5_FACT_SHAPE_INVALID")
    for field in (
        "exact_target_object_mentioned",
        "target_effect_separately_extractable",
        "independent_effect_support",
        "non_effect_context_relevance",
    ):
        if not isinstance(fact.get(field), bool):
            failures.append(
                f"ADMISSION_V5_{field.upper()}_INVALID"
            )
    bases = fact.get("effect_basis_codes")
    if (
        not isinstance(bases, list)
        or not bases
        or len(bases) != len(set(bases))
        or not set(bases).issubset(EFFECT_BASIS_CODES)
    ):
        failures.append("ADMISSION_V5_EFFECT_BASIS_INVALID")
    rationale = fact.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("ADMISSION_V5_RATIONALE_MISSING")
    return sorted(set(failures))


def semantic_fact_conflicts(fact):
    conflicts = []
    exact = fact["exact_target_object_mentioned"]
    extractable = fact["target_effect_separately_extractable"]
    support = fact["independent_effect_support"]
    bases = fact["effect_basis_codes"]
    if extractable and not exact:
        conflicts.append("EXTRACTABLE_WITHOUT_EXACT_TARGET")
    if support and not exact:
        conflicts.append("SUPPORT_WITHOUT_EXACT_TARGET")
    if support and not extractable:
        conflicts.append("SUPPORT_WITHOUT_EXTRACTABILITY")
    if support and "NOT_EFFECT_BEARING" in bases:
        conflicts.append("SUPPORT_WITH_NON_EFFECT_BASIS")
    if not support and bases != ["NOT_EFFECT_BEARING"]:
        conflicts.append("NON_SUPPORT_WITH_EFFECT_BASIS")
    return sorted(set(conflicts))
