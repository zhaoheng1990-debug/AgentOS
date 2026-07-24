"""Contracts separating identity, relevance, and significance in v0.68."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .relational_contrast_types import (
    COORDINATE_BINDINGS,
    EVIDENCE_RELEVANCE,
    EVIDENCE_ROLES,
    FRAME_AMBIGUITY_AXES,
    FRAME_STATES,
    OBSERVED_RELATIONS,
    REFERENCE_IDS,
    RELATION_MODES,
    REQUIREMENT_MODES,
    SIGNIFICANCE_STATES,
    SUBJECT_IDS,
)


def validate_relational_frame(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base(
        receipt, item, admission, refs, "A4_RELATIONAL_FRAME"
    )
    if receipt.get("source_arm_catalog_hash") != catalog["catalog_hash"]:
        failures.append("RELATIONAL_FRAME_CATALOG_HASH_MISMATCH")
    for field in ("intervention_aliases", "comparator_aliases"):
        if not _string_set(receipt.get(field)):
            failures.append(f"RELATIONAL_FRAME_{field.upper()}_INVALID")
    if receipt.get("relation_mode") not in RELATION_MODES:
        failures.append("RELATIONAL_FRAME_MODE_INVALID")
    for field in ("timepoint_requirement", "measurement_requirement"):
        requirement = receipt.get(field)
        if (
            not isinstance(requirement, dict)
            or requirement.get("mode") not in REQUIREMENT_MODES
            or not isinstance(requirement.get("value"), str)
        ):
            failures.append(f"RELATIONAL_FRAME_{field.upper()}_INVALID")
    axes = receipt.get("ambiguity_axes")
    if (
        not isinstance(axes, list)
        or len(axes) != len(set(axes))
        or not set(axes).issubset(FRAME_AMBIGUITY_AXES)
    ):
        failures.append("RELATIONAL_FRAME_AMBIGUITY_INVALID")
        axes = []
    state = receipt.get("frame_status")
    if state not in FRAME_STATES:
        failures.append("RELATIONAL_FRAME_STATUS_INVALID")
    elif state == "RESOLVED" and (
        axes or receipt.get("relation_mode") == "UNRESOLVED"
    ):
        failures.append("RELATIONAL_FRAME_RESOLVED_STATE_INCONSISTENT")
    elif state == "UNRESOLVED" and not axes:
        failures.append("RELATIONAL_FRAME_UNRESOLVED_AXIS_MISSING")
    if "predicted_label" in receipt:
        failures.append("RELATIONAL_FRAME_PREMATURE_LABEL_AUTHORITY")
    return sorted(set(failures))


def validate_relational_basis(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
    frame: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base(
        receipt, item, admission, refs, "A4_RELATIONAL_BASIS"
    )
    if receipt.get("source_arm_catalog_hash") != catalog["catalog_hash"]:
        failures.append("RELATIONAL_BASIS_CATALOG_HASH_MISMATCH")
    if receipt.get("source_frame_hash") != hash_payload(frame):
        failures.append("RELATIONAL_BASIS_FRAME_HASH_MISMATCH")
    if receipt.get("frame_consumed") is not True:
        failures.append("RELATIONAL_BASIS_FRAME_NOT_CONSUMED")
    if receipt.get("all_admitted_spans_assessed") is not True:
        failures.append("RELATIONAL_BASIS_COVERAGE_NOT_CONFIRMED")
    if "predicted_label" in receipt:
        failures.append("RELATIONAL_BASIS_PREMATURE_LABEL_AUTHORITY")
    records = receipt.get("basis_records")
    if not isinstance(records, list):
        return sorted(set([*failures, "RELATIONAL_BASIS_NOT_ARRAY"]))
    admitted, _ = admission_partition(admission)
    ids = [
        value.get("span_id") for value in records
        if isinstance(value, dict)
    ]
    if len(ids) != len(set(ids)) or set(ids) != set(admitted):
        failures.append("RELATIONAL_BASIS_SPAN_COVERAGE_INVALID")
    for record in records:
        failures.extend(_record_failures(record))
    return sorted(set(failures))


def _record_failures(record: Any) -> list[str]:
    if not isinstance(record, dict):
        return ["RELATIONAL_BASIS_RECORD_NOT_OBJECT"]
    failures: list[str] = []
    checks = (
        ("evidence_relevance", EVIDENCE_RELEVANCE),
        ("subject_group_id", SUBJECT_IDS),
        ("reference_group_id", REFERENCE_IDS),
        ("timepoint_binding", COORDINATE_BINDINGS),
        ("measurement_binding", COORDINATE_BINDINGS),
        ("observed_relation", OBSERVED_RELATIONS),
        ("significance_state", SIGNIFICANCE_STATES),
        ("evidence_role", EVIDENCE_ROLES),
    )
    for field, allowed in checks:
        if record.get(field) not in allowed:
            failures.append(f"RELATIONAL_BASIS_{field.upper()}_INVALID")
    if record.get("subject_group_id") == record.get("reference_group_id"):
        failures.append("RELATIONAL_BASIS_SELF_RELATION")
    incompatible = (
        record.get("evidence_relevance")
        in {"DIFFERENT_OBJECT", "UNRESOLVED"}
        or record.get("subject_group_id") == "UNRESOLVED"
        or record.get("reference_group_id") == "UNRESOLVED"
        or record.get("timepoint_binding") in {"DIFFERENT", "UNRESOLVED"}
        or record.get("measurement_binding") in {"DIFFERENT", "UNRESOLVED"}
    )
    if incompatible and record.get("evidence_role") != "EXCLUDE_UNRELATED":
        failures.append("RELATIONAL_BASIS_INCOMPATIBLE_NOT_EXCLUDED")
    exact = (
        record.get("evidence_relevance") == "EXACT_OBJECT"
        and record.get("subject_group_id") != "UNRESOLVED"
        and record.get("reference_group_id") != "UNRESOLVED"
        and record.get("timepoint_binding") not in {"DIFFERENT", "UNRESOLVED"}
        and record.get("measurement_binding")
        not in {"DIFFERENT", "UNRESOLVED"}
    )
    if exact and record.get("evidence_role") == "EXCLUDE_UNRELATED":
        failures.append("RELATIONAL_BASIS_EXACT_EVIDENCE_EXCLUDED")
    return failures


def _base(receipt, item, admission, refs, mechanism) -> list[str]:
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
    return [
        f"RELATIONAL_{code}" for field, value, code in expected
        if receipt.get(field) != value
    ]


def _string_set(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )
