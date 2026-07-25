"""Boundary-review facts and semantic consistency for v0.83."""

from __future__ import annotations


BOUNDARY_ISSUE_CODES = (
    "NONE",
    "INTERVENTION_MISMATCH",
    "COMPARATOR_MISMATCH",
    "COMPARATOR_POOLED_NOT_ISOLATED",
    "OUTCOME_MISMATCH",
    "OUTCOME_POOLED_NOT_ISOLATED",
    "TIMEPOINT_MISMATCH",
    "NO_INDEPENDENT_EFFECT_STATEMENT",
)
FACT_FIELDS = (
    "span_id",
    "exact_intervention_matched",
    "exact_comparator_matched",
    "comparator_separately_isolated",
    "exact_outcome_matched",
    "target_timepoint_matched",
    "outcome_separately_isolated",
    "independent_effect_statement_present",
    "boundary_issue_codes",
    "support_anchor_quote",
    "boundary_anchor_quote",
    "rationale",
)


def structural_fact_violations(fact):
    failures = []
    if set(fact) != set(FACT_FIELDS):
        failures.append("ADMISSION_V8_FACT_SHAPE_INVALID")
    for field in FACT_FIELDS[1:8]:
        if not isinstance(fact.get(field), bool):
            failures.append(f"ADMISSION_V8_{field.upper()}_INVALID")
    issues = fact.get("boundary_issue_codes")
    if (
        not isinstance(issues, list)
        or not issues
        or len(issues) != len(set(issues))
        or not set(issues).issubset(BOUNDARY_ISSUE_CODES)
    ):
        failures.append("ADMISSION_V8_BOUNDARY_ISSUES_INVALID")
    for field in (
        "support_anchor_quote",
        "boundary_anchor_quote",
        "rationale",
    ):
        if not isinstance(fact.get(field), str):
            failures.append(f"ADMISSION_V8_{field.upper()}_INVALID")
    if isinstance(fact.get("rationale"), str) and not fact["rationale"].strip():
        failures.append("ADMISSION_V8_RATIONALE_MISSING")
    return sorted(set(failures))


def semantic_fact_conflicts(fact, *, span_text):
    conflicts = []
    issues = set(fact["boundary_issue_codes"])
    all_positive = all(
        fact[field] for field in FACT_FIELDS[1:8]
    )
    if "NONE" in issues and len(issues) > 1:
        conflicts.append("NONE_MIXED_WITH_BOUNDARY_ISSUE")
    if all_positive and issues != {"NONE"}:
        conflicts.append("POSITIVE_FACTS_WITH_BOUNDARY_ISSUE")
    if not all_positive and issues == {"NONE"}:
        conflicts.append("NEGATIVE_FACT_WITHOUT_BOUNDARY_ISSUE")
    expected_negative = {
        "INTERVENTION_MISMATCH": not fact[
            "exact_intervention_matched"
        ],
        "COMPARATOR_MISMATCH": not fact["exact_comparator_matched"],
        "COMPARATOR_POOLED_NOT_ISOLATED": not fact[
            "comparator_separately_isolated"
        ],
        "OUTCOME_MISMATCH": not fact["exact_outcome_matched"],
        "OUTCOME_POOLED_NOT_ISOLATED": not fact[
            "outcome_separately_isolated"
        ],
        "TIMEPOINT_MISMATCH": not fact["target_timepoint_matched"],
        "NO_INDEPENDENT_EFFECT_STATEMENT": not fact[
            "independent_effect_statement_present"
        ],
    }
    for issue, expected in expected_negative.items():
        if issue in issues and not expected:
            conflicts.append(f"{issue}_WITHOUT_MATCHING_NEGATIVE_FACT")
    support_quote = " ".join(fact["support_anchor_quote"].split())
    boundary_quote = " ".join(fact["boundary_anchor_quote"].split())
    normalized_span = " ".join(span_text.split()).casefold()
    if all_positive:
        if not support_quote:
            conflicts.append("POSITIVE_WITNESS_WITHOUT_SUPPORT_ANCHOR")
        elif support_quote.casefold() not in normalized_span:
            conflicts.append("SUPPORT_ANCHOR_NOT_GROUNDED")
        if boundary_quote:
            conflicts.append("POSITIVE_WITNESS_WITH_BOUNDARY_ANCHOR")
    else:
        if not boundary_quote:
            conflicts.append("NEGATIVE_WITNESS_WITHOUT_BOUNDARY_ANCHOR")
        elif boundary_quote.casefold() not in normalized_span:
            conflicts.append("BOUNDARY_ANCHOR_NOT_GROUNDED")
    return sorted(set(conflicts))


def positive_boundary_witness(fact, *, span_text):
    return (
        all(fact[field] for field in FACT_FIELDS[1:8])
        and fact["boundary_issue_codes"] == ["NONE"]
        and not semantic_fact_conflicts(fact, span_text=span_text)
    )


def negative_boundary_witness(fact, *, span_text):
    return (
        fact["boundary_issue_codes"] != ["NONE"]
        and not semantic_fact_conflicts(fact, span_text=span_text)
    )
