"""Structural contracts for v0.67 comparison-frame cognition."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .comparison_frame_types import (
    ADMISSIBILITY_STATES,
    CONTRAST_BINDINGS,
    CONTRAST_TYPES,
    DIRECTIONS,
    FRAME_AMBIGUITY_AXES,
    FRAME_BINDINGS,
    FRAME_STATES,
    NORMALIZATION_RULES,
    ORIENTATIONS,
    OUTCOME_BINDINGS,
    REQUIREMENT_MODES,
    SIGNIFICANCE_STATES,
)


def validate_comparison_frame(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base(
        receipt, item, admission, refs, "A3_COMPARISON_FRAME"
    )
    if "predicted_label" in receipt:
        failures.append("FRAME_PREMATURE_LABEL_AUTHORITY")
    arms = _string_set(receipt.get("study_arms"), minimum=2)
    focal = _string_set(receipt.get("focal_intervention_members"))
    comparator = _string_set(receipt.get("comparator_members"))
    if arms is None:
        failures.append("FRAME_STUDY_ARMS_INVALID")
        arms = set()
    if focal is None or comparator is None:
        failures.append("FRAME_FOCAL_CONTRAST_INVALID")
    else:
        if focal & comparator or not (focal | comparator).issubset(arms):
            failures.append("FRAME_FOCAL_CONTRAST_INVALID")
    if receipt.get("contrast_type") not in CONTRAST_TYPES:
        failures.append("FRAME_CONTRAST_TYPE_INVALID")
    if receipt.get("normalization_rule") not in NORMALIZATION_RULES:
        failures.append("FRAME_NORMALIZATION_RULE_INVALID")
    for field in ("timepoint_requirement", "measurement_requirement"):
        requirement = receipt.get(field)
        if (
            not isinstance(requirement, dict)
            or requirement.get("mode") not in REQUIREMENT_MODES
            or not isinstance(requirement.get("value"), str)
        ):
            failures.append(f"FRAME_{field.upper()}_INVALID")
    axes = receipt.get("ambiguity_axes")
    if (
        not isinstance(axes, list)
        or len(axes) != len(set(axes))
        or not set(axes).issubset(FRAME_AMBIGUITY_AXES)
    ):
        failures.append("FRAME_AMBIGUITY_AXES_INVALID")
        axes = []
    state = receipt.get("frame_status")
    if state not in FRAME_STATES:
        failures.append("FRAME_STATUS_INVALID")
    elif state == "RESOLVED":
        if axes or receipt.get("normalization_rule") == "UNRESOLVED":
            failures.append("FRAME_RESOLVED_STATE_INCONSISTENT")
    elif not axes:
        failures.append("FRAME_UNRESOLVED_AXIS_MISSING")
    return sorted(set(failures))


def validate_frame_basis(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    frame: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base(
        receipt, item, admission, refs, "A3_FRAME_BOUND_BASIS"
    )
    if receipt.get("source_frame_hash") != hash_payload(frame):
        failures.append("BASIS_FRAME_HASH_MISMATCH")
    if receipt.get("frame_consumed") is not True:
        failures.append("BASIS_FRAME_NOT_CONSUMED")
    if receipt.get("all_admitted_spans_assessed") is not True:
        failures.append("BASIS_COVERAGE_NOT_CONFIRMED")
    if "predicted_label" in receipt:
        failures.append("BASIS_PREMATURE_LABEL_AUTHORITY")
    records = receipt.get("basis_records")
    if not isinstance(records, list):
        return sorted(set([*failures, "BASIS_RECORDS_NOT_ARRAY"]))
    admitted, _ = admission_partition(admission)
    ids = [
        value.get("span_id") for value in records
        if isinstance(value, dict)
    ]
    if len(ids) != len(set(ids)) or set(ids) != set(admitted):
        failures.append("BASIS_SPAN_COVERAGE_INVALID")
    for record in records:
        failures.extend(_record_failures(record))
    return sorted(set(failures))


def _record_failures(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["BASIS_RECORD_NOT_OBJECT"]
    failures: list[str] = []
    checks = (
        ("outcome_binding", OUTCOME_BINDINGS),
        ("focal_contrast_binding", CONTRAST_BINDINGS),
        ("timepoint_binding", FRAME_BINDINGS),
        ("measurement_binding", FRAME_BINDINGS),
        ("comparison_orientation", ORIENTATIONS),
        ("observed_direction", DIRECTIONS),
        ("significance_state", SIGNIFICANCE_STATES),
        ("admissibility", ADMISSIBILITY_STATES),
    )
    for field, allowed in checks:
        if record.get(field) not in allowed:
            failures.append(f"BASIS_{field.upper()}_INVALID")
    incompatible = (
        record.get("outcome_binding") in {"DIFFERENT", "UNRESOLVED"}
        or record.get("focal_contrast_binding") in {"DIFFERENT", "UNRESOLVED"}
        or record.get("timepoint_binding") in {"DIFFERENT", "UNRESOLVED"}
        or record.get("measurement_binding") in {"DIFFERENT", "UNRESOLVED"}
    )
    if incompatible and record.get("admissibility") != "REJECT_AFTER_BASIS":
        failures.append("BASIS_INCOMPATIBLE_SPAN_NOT_REJECTED")
    return failures


def _base(
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    refs: tuple[str, ...],
    mechanism: str,
) -> list[str]:
    failures: list[str] = []
    expected = (
        ("case_id", item["case_id"], "CASE_MISMATCH"),
        ("mechanism", mechanism, "MECHANISM_MISMATCH"),
        ("source_item_hash", hash_payload(item), "ITEM_HASH_MISMATCH"),
        (
            "source_admission_hash",
            hash_payload(admission),
            "ADMISSION_HASH_MISMATCH",
        ),
        ("evidence_refs", list(refs), "EVIDENCE_SCOPE_MISMATCH"),
    )
    for field, value, code in expected:
        if receipt.get(field) != value:
            failures.append(f"COMPARISON_FRAME_{code}")
    return failures


def _string_set(value: Any, minimum: int = 1) -> set[str] | None:
    if (
        not isinstance(value, list)
        or len(value) < minimum
        or len(value) != len(set(value))
        or any(not isinstance(item, str) or not item for item in value)
    ):
        return None
    return set(value)
