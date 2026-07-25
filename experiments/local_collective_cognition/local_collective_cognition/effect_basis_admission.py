"""Effect-basis witness for typed evidence admission."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES


def effect_basis_violations(record):
    """Return mechanical conflicts in effect-bearing support claims."""

    failures = []
    support = record.get("independent_effect_support")
    bases = record.get("effect_basis_codes")
    if not isinstance(support, bool):
        failures.append("ADMISSION_V3_EFFECT_SUPPORT_FLAG_INVALID")
    if (
        not isinstance(bases, list)
        or not bases
        or len(bases) != len(set(bases))
        or not set(bases).issubset(EFFECT_BASIS_CODES)
    ):
        return sorted(set([
            *failures,
            "ADMISSION_V3_EFFECT_BASIS_INVALID",
        ]))
    if support is True:
        if (
            record.get("outcome_binding") != "EXACT_SEPARABLE_TARGET"
            or record.get("target_effect_separable") is not True
            or record.get("object_relation") != "EXACT_OBJECT"
            or record.get("evidence_utility") != "EFFECT_BEARING"
            or record.get("disposition") != "ADMIT_EVIDENCE"
        ):
            failures.append("ADMISSION_V3_EFFECT_SUPPORT_CONFLICT")
        if "NOT_EFFECT_BEARING" in bases:
            failures.append("ADMISSION_V3_EFFECT_BASIS_SUPPORT_CONFLICT")
    elif support is False:
        if (
            record.get("evidence_utility") == "EFFECT_BEARING"
            or record.get("disposition") == "ADMIT_EVIDENCE"
        ):
            failures.append("ADMISSION_V3_UNSUPPORTED_ADMISSION")
        if bases != ["NOT_EFFECT_BEARING"]:
            failures.append("ADMISSION_V3_NON_EFFECT_BASIS_CONFLICT")
    return failures
