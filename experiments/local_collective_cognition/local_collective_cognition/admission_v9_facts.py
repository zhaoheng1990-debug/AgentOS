"""Ternary boundary facts and semantic consistency for v0.84."""

from __future__ import annotations


COMPONENT_STATES = (
    "MATCHED",
    "EXPLICITLY_CONTRADICTED",
    "NOT_STATED",
)
ISOLATION_STATES = (
    "ISOLATED",
    "EXPLICITLY_POOLED",
    "NOT_APPLICABLE_OR_NOT_STATED",
)
COMPONENT_FIELDS = (
    "intervention_state",
    "comparator_state",
    "outcome_state",
    "timepoint_state",
)
ISOLATION_FIELDS = (
    "comparator_isolation_state",
    "outcome_isolation_state",
)
FACT_FIELDS = (
    "span_id",
    *COMPONENT_FIELDS,
    *ISOLATION_FIELDS,
    "independent_effect_statement_present",
    "target_coreference_supported",
    "effect_anchor_quote",
    "contradiction_anchor_quote",
    "rationale",
)


def structural_fact_violations(fact):
    failures = []
    if set(fact) != set(FACT_FIELDS):
        failures.append("ADMISSION_V9_FACT_SHAPE_INVALID")
    for field in COMPONENT_FIELDS:
        if fact.get(field) not in COMPONENT_STATES:
            failures.append(f"ADMISSION_V9_{field.upper()}_INVALID")
    for field in ISOLATION_FIELDS:
        if fact.get(field) not in ISOLATION_STATES:
            failures.append(f"ADMISSION_V9_{field.upper()}_INVALID")
    for field in (
        "independent_effect_statement_present",
        "target_coreference_supported",
    ):
        if not isinstance(fact.get(field), bool):
            failures.append(f"ADMISSION_V9_{field.upper()}_INVALID")
    for field in (
        "effect_anchor_quote",
        "contradiction_anchor_quote",
        "rationale",
    ):
        if not isinstance(fact.get(field), str):
            failures.append(f"ADMISSION_V9_{field.upper()}_INVALID")
    if isinstance(fact.get("rationale"), str) and not fact["rationale"].strip():
        failures.append("ADMISSION_V9_RATIONALE_MISSING")
    return sorted(set(failures))


def has_explicit_negative(fact):
    return (
        any(
            fact.get(field) == "EXPLICITLY_CONTRADICTED"
            for field in COMPONENT_FIELDS
        )
        or any(
            fact.get(field) == "EXPLICITLY_POOLED"
            for field in ISOLATION_FIELDS
        )
    )


def semantic_fact_conflicts(fact, *, span_text):
    conflicts = []
    negative = has_explicit_negative(fact)
    effect_quote = " ".join(fact["effect_anchor_quote"].split())
    contradiction_quote = " ".join(
        fact["contradiction_anchor_quote"].split()
    )
    normalized_span = " ".join(span_text.split()).casefold()
    if negative:
        if not contradiction_quote:
            conflicts.append("EXPLICIT_NEGATIVE_WITHOUT_ANCHOR")
        elif contradiction_quote.casefold() not in normalized_span:
            conflicts.append("CONTRADICTION_ANCHOR_NOT_GROUNDED")
    elif contradiction_quote:
        conflicts.append("CONTRADICTION_ANCHOR_WITHOUT_EXPLICIT_NEGATIVE")
    if fact["independent_effect_statement_present"]:
        if not effect_quote:
            conflicts.append("EFFECT_STATEMENT_WITHOUT_ANCHOR")
        elif effect_quote.casefold() not in normalized_span:
            conflicts.append("EFFECT_ANCHOR_NOT_GROUNDED")
    elif effect_quote:
        conflicts.append("EFFECT_ANCHOR_WITHOUT_EFFECT_STATEMENT")
    if (
        fact["target_coreference_supported"]
        and not fact["independent_effect_statement_present"]
    ):
        conflicts.append("COREFERENCE_WITHOUT_EFFECT_STATEMENT")
    return sorted(set(conflicts))


def positive_boundary_witness(fact, *, span_text):
    return (
        not has_explicit_negative(fact)
        and fact["independent_effect_statement_present"]
        and fact["target_coreference_supported"]
        and not semantic_fact_conflicts(fact, span_text=span_text)
    )


def negative_boundary_witness(fact, *, span_text):
    return (
        has_explicit_negative(fact)
        and not semantic_fact_conflicts(fact, span_text=span_text)
    )
