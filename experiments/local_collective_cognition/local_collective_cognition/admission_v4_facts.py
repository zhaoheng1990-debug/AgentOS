"""Minimal Provider semantic facts for admission v0.79."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES


OUTCOME_SCOPES = (
    "TARGET_SEPARATELY_REPORTED",
    "TARGET_COMPONENT_OF_COMPOSITE",
    "RELATED_OUTCOME_ONLY",
    "TARGET_ABSENT",
)
FACT_FIELDS = (
    "span_id",
    "outcome_scope",
    "independent_effect_support",
    "effect_basis_codes",
    "non_effect_context_relevance",
    "rationale",
)


def semantic_fact_violations(record):
    failures = []
    scope = record.get("outcome_scope")
    support = record.get("independent_effect_support")
    bases = record.get("effect_basis_codes")
    context = record.get("non_effect_context_relevance")
    if set(record) != set(FACT_FIELDS):
        failures.append("ADMISSION_V4_FACT_SHAPE_INVALID")
    if scope not in OUTCOME_SCOPES:
        failures.append("ADMISSION_V4_OUTCOME_SCOPE_INVALID")
    if not isinstance(support, bool):
        failures.append("ADMISSION_V4_EFFECT_SUPPORT_FLAG_INVALID")
    if not isinstance(context, bool):
        failures.append("ADMISSION_V4_CONTEXT_RELEVANCE_FLAG_INVALID")
    if (
        not isinstance(bases, list)
        or not bases
        or len(bases) != len(set(bases))
        or not set(bases).issubset(EFFECT_BASIS_CODES)
    ):
        failures.append("ADMISSION_V4_EFFECT_BASIS_INVALID")
    elif support is True:
        if scope != "TARGET_SEPARATELY_REPORTED":
            failures.append("ADMISSION_V4_SUPPORT_SCOPE_CONFLICT")
        if "NOT_EFFECT_BEARING" in bases:
            failures.append("ADMISSION_V4_EFFECT_BASIS_SUPPORT_CONFLICT")
    elif support is False and bases != ["NOT_EFFECT_BEARING"]:
        failures.append("ADMISSION_V4_NON_EFFECT_BASIS_CONFLICT")
    rationale = record.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("ADMISSION_V4_RATIONALE_MISSING")
    return sorted(set(failures))
