"""Context-only Provider facts for staged admission v0.82."""

from __future__ import annotations

from .admission_v6_facts import CONTEXT_UTILITY_CODES


FACT_FIELDS = (
    "span_id",
    "context_utility_code",
    "context_changes_downstream_decision",
    "utility_anchor_quote",
    "rationale",
)


def structural_fact_violations(fact):
    failures = []
    if set(fact) != set(FACT_FIELDS):
        failures.append("ADMISSION_V7_FACT_SHAPE_INVALID")
    if fact.get("context_utility_code") not in CONTEXT_UTILITY_CODES:
        failures.append("ADMISSION_V7_CONTEXT_UTILITY_CODE_INVALID")
    if not isinstance(
        fact.get("context_changes_downstream_decision"),
        bool,
    ):
        failures.append("ADMISSION_V7_DECISION_CHANGE_INVALID")
    for field in ("utility_anchor_quote", "rationale"):
        if not isinstance(fact.get(field), str):
            failures.append(f"ADMISSION_V7_{field.upper()}_INVALID")
    if isinstance(fact.get("rationale"), str) and not fact["rationale"].strip():
        failures.append("ADMISSION_V7_RATIONALE_MISSING")
    return sorted(set(failures))


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
