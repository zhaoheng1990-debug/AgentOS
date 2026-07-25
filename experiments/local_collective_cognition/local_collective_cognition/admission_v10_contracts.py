"""Contract validation for study-relation graph receipts."""

from __future__ import annotations

from .admission_v10_facts import (
    structural_binding_violations,
    structural_span_fact_violations,
)
from .provider_telemetry import hash_payload


def validate_study_relation_review(
    *,
    receipt,
    item,
    staged_partition,
    refs,
):
    failures = []
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A19_STUDY_RELATION_REVIEW",
        "source_item_hash": hash_payload(item),
        "source_staged_partition_hash": staged_partition["partition_hash"],
        "evidence_refs": list(refs),
    }
    if set(receipt) != {
        "case_id",
        "mechanism",
        "source_item_hash",
        "source_staged_partition_hash",
        "all_spans_assessed",
        "bindings",
        "span_records",
        "evidence_refs",
    }:
        failures.append("ADMISSION_V10_RECEIPT_SHAPE_INVALID")
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"ADMISSION_V10_{field.upper()}_MISMATCH")
    if receipt.get("all_spans_assessed") is not True:
        failures.append("ADMISSION_V10_COVERAGE_NOT_CONFIRMED")
    bindings = receipt.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        failures.append("ADMISSION_V10_BINDINGS_INVALID")
        bindings = []
    for binding in bindings:
        if not isinstance(binding, dict):
            failures.append("ADMISSION_V10_BINDING_NOT_OBJECT")
            continue
        failures.extend(structural_binding_violations(binding))
    binding_ids = [
        value.get("binding_id")
        for value in bindings
        if isinstance(value, dict)
    ]
    if len(binding_ids) != len(set(binding_ids)):
        failures.append("ADMISSION_V10_BINDING_IDS_NOT_UNIQUE")
    records = receipt.get("span_records")
    if not isinstance(records, list):
        return sorted(set([
            *failures,
            "ADMISSION_V10_SPAN_RECORDS_NOT_ARRAY",
        ]))
    expected_ids = {
        span["span_id"] for span in item["candidate_spans"]
    }
    observed_ids = [
        fact.get("span_id")
        for fact in records
        if isinstance(fact, dict)
    ]
    if (
        len(observed_ids) != len(set(observed_ids))
        or set(observed_ids) != expected_ids
    ):
        failures.append("ADMISSION_V10_SPAN_COVERAGE_INVALID")
    for fact in records:
        if not isinstance(fact, dict):
            failures.append("ADMISSION_V10_SPAN_RECORD_NOT_OBJECT")
            continue
        failures.extend(structural_span_fact_violations(fact))
    return sorted(set(failures))
