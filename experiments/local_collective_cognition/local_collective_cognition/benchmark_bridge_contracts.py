"""Receipt contracts for the v0.65 benchmark bridge."""

from __future__ import annotations

from typing import Any

from .provider_telemetry import hash_payload


LABELS = ("INCREASED", "DECREASED", "NO_DIFFERENCE")
ONE_PASS_FIELDS = (
    "primary_span_ids",
    "corroborating_span_ids",
    "counter_span_ids",
    "irrelevant_span_ids",
)
STAGED_FIELDS = (
    "primary_span_ids",
    "corroborating_span_ids",
    "counter_span_ids",
)


def one_pass_schema(
    item: dict[str, Any], refs: tuple[str, ...]
) -> dict[str, Any]:
    span_ids = _span_ids(item)
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A0_ONE_PASS"]},
        "source_item_hash": {
            "type": "string", "enum": [hash_payload(item)]
        },
        "predicted_label": {"type": "string", "enum": list(LABELS)},
        **{
            field: _id_array(span_ids, minimum=1 if field == ONE_PASS_FIELDS[0] else 0)
            for field in ONE_PASS_FIELDS
        },
        "rationale": {"type": "string"},
        "evidence_refs": _ref_array(refs),
    }
    return _object_schema(properties)


def admission_schema(
    item: dict[str, Any], refs: tuple[str, ...]
) -> dict[str, Any]:
    span_ids = _span_ids(item)
    decision = {
        "type": "object",
        "additionalProperties": False,
        "required": ["span_id", "decision", "relation", "rationale"],
        "properties": {
            "span_id": {"type": "string", "enum": span_ids},
            "decision": {"type": "string", "enum": ["ADMIT", "REJECT"]},
            "relation": {
                "type": "string",
                "enum": ["DIRECT", "CONTEXTUAL", "IRRELEVANT"],
            },
            "rationale": {"type": "string"},
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A1_SPAN_ADMISSION"]},
        "source_item_hash": {
            "type": "string", "enum": [hash_payload(item)]
        },
        "all_candidates_assessed": {"type": "boolean", "enum": [True]},
        "decisions": {
            "type": "array",
            "minItems": len(span_ids),
            "maxItems": len(span_ids),
            "items": decision,
        },
        "evidence_refs": _ref_array(refs),
    }
    return _object_schema(properties)


def staged_binding_schema(
    *,
    item: dict[str, Any],
    admitted_ids: list[str],
    rejected_ids: list[str],
    admission_hash: str,
    refs: tuple[str, ...],
) -> dict[str, Any]:
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A1_STAGED_BINDING"]},
        "source_item_hash": {
            "type": "string", "enum": [hash_payload(item)]
        },
        "source_admission_hash": {
            "type": "string", "enum": [admission_hash]
        },
        "predicted_label": {"type": "string", "enum": list(LABELS)},
        **{
            field: _id_array(
                admitted_ids,
                minimum=1 if field == STAGED_FIELDS[0] else 0,
            )
            for field in STAGED_FIELDS
        },
        "rejected_span_ids": {
            "type": "array",
            "minItems": len(rejected_ids),
            "maxItems": len(rejected_ids),
            "uniqueItems": True,
            "items": {"type": "string", "enum": rejected_ids},
        },
        "rationale": {"type": "string"},
        "evidence_refs": _ref_array(refs),
    }
    return _object_schema(properties)


def validate_one_pass(
    receipt: dict[str, Any], item: dict[str, Any], refs: tuple[str, ...]
) -> list[str]:
    failures = _base_failures(
        receipt, item, refs, mechanism="A0_ONE_PASS"
    )
    failures.extend(
        _partition_failures(
            receipt, fields=ONE_PASS_FIELDS, expected=set(_span_ids(item))
        )
    )
    if not receipt.get("primary_span_ids"):
        failures.append("PRIMARY_SPAN_REQUIRED")
    if receipt.get("predicted_label") not in LABELS:
        failures.append("LABEL_INVALID")
    return sorted(set(failures))


def validate_admission(
    receipt: dict[str, Any], item: dict[str, Any], refs: tuple[str, ...]
) -> list[str]:
    failures = _base_failures(
        receipt, item, refs, mechanism="A1_SPAN_ADMISSION"
    )
    if receipt.get("all_candidates_assessed") is not True:
        failures.append("ADMISSION_COVERAGE_NOT_CONFIRMED")
    decisions = receipt.get("decisions")
    if not isinstance(decisions, list):
        return sorted(set([*failures, "ADMISSION_DECISIONS_NOT_ARRAY"]))
    ids = [
        value.get("span_id")
        for value in decisions
        if isinstance(value, dict)
    ]
    if len(ids) != len(set(ids)) or set(ids) != set(_span_ids(item)):
        failures.append("ADMISSION_CANDIDATE_PARTITION_INVALID")
    for value in decisions:
        if not isinstance(value, dict):
            failures.append("ADMISSION_DECISION_NOT_OBJECT")
            continue
        if value.get("decision") not in {"ADMIT", "REJECT"}:
            failures.append("ADMISSION_DECISION_INVALID")
        if value.get("relation") not in {
            "DIRECT", "CONTEXTUAL", "IRRELEVANT"
        }:
            failures.append("ADMISSION_RELATION_INVALID")
        if (
            value.get("decision") == "REJECT"
            and value.get("relation") != "IRRELEVANT"
        ):
            failures.append("ADMISSION_REJECT_RELATION_CONFLICT")
        if (
            value.get("decision") == "ADMIT"
            and value.get("relation") == "IRRELEVANT"
        ):
            failures.append("ADMISSION_ADMIT_RELATION_CONFLICT")
    admitted, _ = admission_partition(receipt)
    if not admitted:
        failures.append("ADMISSION_EMPTY")
    return sorted(set(failures))


def validate_staged_binding(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    refs: tuple[str, ...],
) -> list[str]:
    failures = _base_failures(
        receipt, item, refs, mechanism="A1_STAGED_BINDING"
    )
    admission_hash = hash_payload(admission)
    if receipt.get("source_admission_hash") != admission_hash:
        failures.append("ADMISSION_HASH_MISMATCH")
    admitted, rejected = admission_partition(admission)
    failures.extend(
        _partition_failures(
            receipt, fields=STAGED_FIELDS, expected=set(admitted)
        )
    )
    if receipt.get("rejected_span_ids") != sorted(rejected):
        failures.append("REJECTED_SPAN_REPLAY_MISMATCH")
    if not receipt.get("primary_span_ids"):
        failures.append("PRIMARY_SPAN_REQUIRED")
    if receipt.get("predicted_label") not in LABELS:
        failures.append("LABEL_INVALID")
    return sorted(set(failures))


def admission_partition(
    receipt: dict[str, Any],
) -> tuple[list[str], list[str]]:
    admitted = sorted(
        value["span_id"]
        for value in receipt.get("decisions", [])
        if value.get("decision") == "ADMIT"
    )
    rejected = sorted(
        value["span_id"]
        for value in receipt.get("decisions", [])
        if value.get("decision") == "REJECT"
    )
    return admitted, rejected


def _base_failures(
    receipt: dict[str, Any],
    item: dict[str, Any],
    refs: tuple[str, ...],
    *,
    mechanism: str,
) -> list[str]:
    failures: list[str] = []
    if receipt.get("case_id") != item["case_id"]:
        failures.append("CASE_ID_MISMATCH")
    if receipt.get("mechanism") != mechanism:
        failures.append("MECHANISM_MISMATCH")
    if receipt.get("source_item_hash") != hash_payload(item):
        failures.append("SOURCE_ITEM_HASH_MISMATCH")
    if receipt.get("evidence_refs") != list(refs):
        failures.append("EVIDENCE_SCOPE_MISMATCH")
    return failures


def _partition_failures(
    receipt: dict[str, Any],
    *,
    fields: tuple[str, ...],
    expected: set[str],
) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    for field in fields:
        values = receipt.get(field)
        if not isinstance(values, list) or len(values) != len(set(values)):
            failures.append(f"{field.upper()}_INVALID")
            continue
        overlap = seen & set(values)
        if overlap:
            failures.append("CROSS_TYPE_SPAN_OVERLAP")
        seen.update(values)
    if seen != expected:
        failures.append("SPAN_PARTITION_INCOMPLETE")
    return failures


def _span_ids(item: dict[str, Any]) -> list[str]:
    return [value["span_id"] for value in item["candidate_spans"]]


def _id_array(ids: list[str], *, minimum: int) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": minimum,
        "uniqueItems": True,
        "items": {"type": "string", "enum": ids},
    }


def _ref_array(refs: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": len(refs),
        "maxItems": len(refs),
        "items": {"type": "string", "enum": list(refs)},
    }


def _object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
