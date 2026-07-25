"""Frozen external annotation rubric for Admission V2."""

from __future__ import annotations

from .admission_v2_types import (
    DISPOSITIONS,
    EVIDENCE_UTILITIES,
    OBJECT_RELATIONS,
)


PANEL_VERSION = "admission_v2_typed_external_panel_v0_77"
ADJUDICATION_VERSION = "admission_v2_typed_adjudication_v0_77"
REFERENCE_VERSION = "admission_v2_typed_reference_v0_77"
LANE_SPECS = (
    ("ANNOTATION_LANE_A", "OpenAI", "GPT-5.6"),
    ("ANNOTATION_LANE_B", "Google", "Gemini-3.1"),
)
K3_SPEC = ("Moonshot", "Kimi-K3")
EFFECT_BASIS_CODES = (
    "DIRECTION_OR_MAGNITUDE",
    "SIGNIFICANCE_OR_UNCERTAINTY",
    "NULL_OR_NO_DIFFERENCE",
    "QUANTITATIVE_CORROBORATION",
    "NOT_EFFECT_BEARING",
)
RUBRIC = {
    "OBJECT_RELATION": {
        "EXACT_OBJECT": (
            "The span addresses the target intervention, comparator, and "
            "outcome, including an explicit null comparison."
        ),
        "CONTEXTUAL_OBJECT": (
            "The span concerns the same study, arms, measurement, timepoint, "
            "or outcome context but cannot independently answer the target "
            "effect question."
        ),
        "IRRELEVANT_OBJECT": (
            "The span concerns a different intervention, comparator, outcome, "
            "or otherwise does not help interpret the target object."
        ),
    },
    "EVIDENCE_UTILITY": {
        "EFFECT_BEARING": (
            "The span independently supports an increased, decreased, null, "
            "no-difference, uncertain, magnitude, significance, or valid "
            "quantitative corroboration claim for the exact target. A more "
            "concise sibling span does not demote it."
        ),
        "CONTEXT_ONLY": (
            "The span is useful for interpreting arms, methods, timepoints, "
            "measurements, or scope but cannot independently support the "
            "target effect claim."
        ),
        "NONE": (
            "The span provides neither target effect evidence nor useful "
            "target context."
        ),
    },
    "DISPOSITION": {
        "ADMIT_EVIDENCE": "Required when evidence utility is EFFECT_BEARING.",
        "RETAIN_CONTEXT": "Required when evidence utility is CONTEXT_ONLY.",
        "REJECT": "Required when evidence utility is NONE.",
    },
    "EFFECT_BASIS_CODES": {
        "DIRECTION_OR_MAGNITUDE": (
            "Reports comparative direction, rate, size, or magnitude."
        ),
        "SIGNIFICANCE_OR_UNCERTAINTY": (
            "Reports statistical significance, uncertainty, interval, or "
            "borderline evidence relevant to the effect."
        ),
        "NULL_OR_NO_DIFFERENCE": (
            "Reports no significant difference, equivalence, absence, or "
            "another bounded null result."
        ),
        "QUANTITATIVE_CORROBORATION": (
            "Provides valid numbers or repeated effect evidence even if "
            "another span is more concise."
        ),
        "NOT_EFFECT_BEARING": (
            "Required as the sole code when utility is not EFFECT_BEARING."
        ),
    },
}


def label_violations(label):
    violations = []
    relation = label.get("object_relation")
    utility = label.get("evidence_utility")
    disposition = label.get("disposition")
    bases = label.get("effect_basis_codes")
    if relation not in OBJECT_RELATIONS:
        violations.append("OBJECT_RELATION_INVALID")
    if utility not in EVIDENCE_UTILITIES:
        violations.append("EVIDENCE_UTILITY_INVALID")
    if disposition not in DISPOSITIONS:
        violations.append("DISPOSITION_INVALID")
    expected_disposition = {
        "EFFECT_BEARING": "ADMIT_EVIDENCE",
        "CONTEXT_ONLY": "RETAIN_CONTEXT",
        "NONE": "REJECT",
    }.get(utility)
    if expected_disposition and disposition != expected_disposition:
        violations.append("UTILITY_DISPOSITION_CONFLICT")
    if relation == "IRRELEVANT_OBJECT" and utility != "NONE":
        violations.append("IRRELEVANT_OBJECT_UTILITY_CONFLICT")
    if utility == "EFFECT_BEARING" and relation != "EXACT_OBJECT":
        violations.append("EFFECT_OBJECT_CONFLICT")
    if (
        not isinstance(bases, list)
        or not bases
        or len(bases) != len(set(bases))
        or not set(bases).issubset(EFFECT_BASIS_CODES)
    ):
        violations.append("EFFECT_BASIS_INVALID")
    elif utility == "EFFECT_BEARING":
        if bases == ["NOT_EFFECT_BEARING"] or (
            "NOT_EFFECT_BEARING" in bases
        ):
            violations.append("EFFECT_BASIS_UTILITY_CONFLICT")
    elif bases != ["NOT_EFFECT_BEARING"]:
        violations.append("NON_EFFECT_BASIS_CONFLICT")
    return sorted(set(violations))
