"""Atomic effect and context-utility facts for admission v0.81."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES


CONTEXT_UTILITY_CODES = (
    "TARGET_IDENTITY_OR_MAPPING",
    "EFFECT_INTERPRETATION",
    "SCOPE_OR_APPLICABILITY",
    "EVIDENCE_VALIDITY",
    "NO_TARGET_UTILITY",
)
FACT_FIELDS = (
    "span_id",
    "exact_target_object_mentioned",
    "target_effect_separately_extractable",
    "independent_effect_support",
    "effect_basis_codes",
    "context_utility_code",
    "context_changes_downstream_decision",
    "utility_anchor_quote",
    "rationale",
)


def structural_fact_violations(fact):
    failures = []
    if set(fact) != set(FACT_FIELDS):
        failures.append("ADMISSION_V6_FACT_SHAPE_INVALID")
    for field in (
        "exact_target_object_mentioned",
        "target_effect_separately_extractable",
        "independent_effect_support",
        "context_changes_downstream_decision",
    ):
        if not isinstance(fact.get(field), bool):
            failures.append(f"ADMISSION_V6_{field.upper()}_INVALID")
    bases = fact.get("effect_basis_codes")
    if (
        not isinstance(bases, list)
        or not bases
        or len(bases) != len(set(bases))
        or not set(bases).issubset(EFFECT_BASIS_CODES)
    ):
        failures.append("ADMISSION_V6_EFFECT_BASIS_INVALID")
    if fact.get("context_utility_code") not in CONTEXT_UTILITY_CODES:
        failures.append("ADMISSION_V6_CONTEXT_UTILITY_CODE_INVALID")
    for field in ("utility_anchor_quote", "rationale"):
        if not isinstance(fact.get(field), str):
            failures.append(f"ADMISSION_V6_{field.upper()}_INVALID")
    if isinstance(fact.get("rationale"), str) and not fact["rationale"].strip():
        failures.append("ADMISSION_V6_RATIONALE_MISSING")
    return sorted(set(failures))


def effect_fact_conflicts(fact):
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


def context_fact_conflicts(fact, *, span_text):
    conflicts = []
    code = fact["context_utility_code"]
    changes = fact["context_changes_downstream_decision"]
    quote = " ".join(fact["utility_anchor_quote"].split())
    normalized_span = " ".join(span_text.split())
    if code == "NO_TARGET_UTILITY":
        if changes:
            conflicts.append("NO_UTILITY_WITH_DECISION_CHANGE")
        if quote:
            conflicts.append("NO_UTILITY_WITH_ANCHOR")
    else:
        if not changes:
            conflicts.append("UTILITY_WITHOUT_DECISION_CHANGE")
        if not quote:
            conflicts.append("UTILITY_WITHOUT_ANCHOR")
        elif quote.casefold() not in normalized_span.casefold():
            conflicts.append("UTILITY_ANCHOR_NOT_GROUNDED")
    return sorted(set(conflicts))


def semantic_fact_conflicts(fact, *, span_text):
    return sorted(set([
        *effect_fact_conflicts(fact),
        *context_fact_conflicts(fact, span_text=span_text),
    ]))
