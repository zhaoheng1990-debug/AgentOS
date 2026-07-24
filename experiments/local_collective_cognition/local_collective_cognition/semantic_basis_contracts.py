"""Typed semantic-basis receipt contracts for v0.66."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .semantic_basis_types import (
    ADMISSIBILITY_STATES,
    AMBIGUITY_AXES,
    DIRECTIONS,
    FINAL_LABELS,
    MEASUREMENT_BINDINGS,
    ORIENTATIONS,
    OUTCOME_BINDINGS,
    SIGNIFICANCE_STATES,
    SYNTHESIS_FIELDS,
    TIMEPOINT_BINDINGS,
)


def validate_semantic_basis(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base_failures(
        receipt=receipt,
        item=item,
        admission=admission,
        refs=refs,
        mechanism="A2_SEMANTIC_BASIS",
    )
    if receipt.get("all_admitted_spans_assessed") is not True:
        failures.append("BASIS_COVERAGE_NOT_CONFIRMED")
    records = receipt.get("basis_records")
    if not isinstance(records, list):
        return sorted(set([*failures, "BASIS_RECORDS_NOT_ARRAY"]))
    admitted, _ = admission_partition(admission)
    ids = [
        value.get("span_id")
        for value in records
        if isinstance(value, dict)
    ]
    if len(ids) != len(set(ids)) or set(ids) != set(admitted):
        failures.append("BASIS_SPAN_COVERAGE_INVALID")
    if "predicted_label" in receipt:
        failures.append("BASIS_PREMATURE_LABEL_AUTHORITY")
    for record in records:
        if not isinstance(record, dict):
            failures.append("BASIS_RECORD_NOT_OBJECT")
            continue
        failures.extend(_record_failures(record))
    axes = receipt.get("ambiguity_axes")
    if (
        not isinstance(axes, list)
        or len(axes) != len(set(axes))
        or not set(axes).issubset(AMBIGUITY_AXES)
    ):
        failures.append("BASIS_AMBIGUITY_AXES_INVALID")
    return sorted(set(failures))


def validate_synthesis(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    basis: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base_failures(
        receipt=receipt,
        item=item,
        admission=admission,
        refs=refs,
        mechanism="A2_SEMANTIC_SYNTHESIS",
    )
    if receipt.get("source_basis_hash") != hash_payload(basis):
        failures.append("SYNTHESIS_BASIS_HASH_MISMATCH")
    if receipt.get("basis_records_consumed") is not True:
        failures.append("SYNTHESIS_BASIS_NOT_CONSUMED")
    admitted, _ = admission_partition(admission)
    failures.extend(
        _partition_failures(receipt, expected=set(admitted))
    )
    state = receipt.get("decision_state")
    label = receipt.get("predicted_label")
    ambiguity = receipt.get("material_ambiguity")
    if state == "DECISIVE":
        if label not in FINAL_LABELS[:3] or ambiguity != "NONE":
            failures.append("SYNTHESIS_DECISIVE_STATE_INVALID")
    elif state == "UNRESOLVED_MATERIAL_AMBIGUITY":
        if (
            label != "UNRESOLVED_MATERIAL_AMBIGUITY"
            or ambiguity not in AMBIGUITY_AXES
        ):
            failures.append("SYNTHESIS_UNRESOLVED_STATE_INVALID")
    else:
        failures.append("SYNTHESIS_DECISION_STATE_INVALID")
    if receipt.get("orientation_rule_applied") is not True:
        failures.append("SYNTHESIS_ORIENTATION_RULE_MISSING")
    if receipt.get("significance_rule_applied") is not True:
        failures.append("SYNTHESIS_SIGNIFICANCE_RULE_MISSING")
    return sorted(set(failures))


def _record_failures(record: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    checks = (
        ("outcome_binding", OUTCOME_BINDINGS),
        ("timepoint_binding", TIMEPOINT_BINDINGS),
        ("measurement_binding", MEASUREMENT_BINDINGS),
        ("comparison_orientation", ORIENTATIONS),
        ("observed_direction", DIRECTIONS),
        ("significance_state", SIGNIFICANCE_STATES),
        ("admissibility", ADMISSIBILITY_STATES),
    )
    for field, allowed in checks:
        if record.get(field) not in allowed:
            failures.append(f"BASIS_{field.upper()}_INVALID")
    if (
        record.get("outcome_binding") == "DIFFERENT"
        and record.get("admissibility") != "REJECT_AFTER_BASIS"
    ):
        failures.append("BASIS_DIFFERENT_OUTCOME_NOT_REJECTED")
    return failures


def _partition_failures(
    receipt: dict[str, Any], *, expected: set[str]
) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for field in SYNTHESIS_FIELDS:
        values = receipt.get(field)
        if not isinstance(values, list) or len(values) != len(set(values)):
            failures.append(f"SYNTHESIS_{field.upper()}_INVALID")
            continue
        if seen & set(values):
            failures.append("SYNTHESIS_CROSS_TYPE_OVERLAP")
        seen.update(values)
    if seen != expected:
        failures.append("SYNTHESIS_SPAN_PARTITION_INCOMPLETE")
    return failures


def _base_failures(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    refs: tuple[str, ...],
    mechanism: str,
) -> list[str]:
    failures: list[str] = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("SEMANTIC_BASIS_CASE_MISMATCH")
    if receipt.get("mechanism") != mechanism:
        failures.append("SEMANTIC_BASIS_MECHANISM_MISMATCH")
    if receipt.get("source_item_hash") != hash_payload(item):
        failures.append("SEMANTIC_BASIS_ITEM_HASH_MISMATCH")
    if receipt.get("source_admission_hash") != hash_payload(admission):
        failures.append("SEMANTIC_BASIS_ADMISSION_HASH_MISMATCH")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("SEMANTIC_BASIS_EVIDENCE_SCOPE_MISMATCH")
    return failures
