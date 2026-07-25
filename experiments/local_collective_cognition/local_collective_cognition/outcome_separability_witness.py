"""Outcome separability witness for typed evidence admission."""

from __future__ import annotations


OUTCOME_BINDINGS = (
    "EXACT_SEPARABLE_TARGET",
    "TARGET_IN_NONSEPARABLE_COMPOSITE",
    "RELATED_OUTCOME",
    "TARGET_ABSENT",
)

_EXPECTED_RELATION = {
    "EXACT_SEPARABLE_TARGET": "EXACT_OBJECT",
    "TARGET_IN_NONSEPARABLE_COMPOSITE": "CONTEXTUAL_OBJECT",
    "RELATED_OUTCOME": "CONTEXTUAL_OBJECT",
    "TARGET_ABSENT": "IRRELEVANT_OBJECT",
}


def separability_violations(record):
    """Return mechanical conflicts in a Provider semantic witness."""

    failures = []
    binding = record.get("outcome_binding")
    separable = record.get("target_effect_separable")
    if binding not in OUTCOME_BINDINGS:
        return ["ADMISSION_V3_OUTCOME_BINDING_INVALID"]
    if not isinstance(separable, bool):
        failures.append("ADMISSION_V3_SEPARABILITY_FLAG_INVALID")
    expected_separable = binding == "EXACT_SEPARABLE_TARGET"
    if isinstance(separable, bool) and separable != expected_separable:
        failures.append("ADMISSION_V3_SEPARABILITY_BINDING_CONFLICT")
    if record.get("object_relation") != _EXPECTED_RELATION[binding]:
        failures.append("ADMISSION_V3_OUTCOME_RELATION_CONFLICT")
    return failures
