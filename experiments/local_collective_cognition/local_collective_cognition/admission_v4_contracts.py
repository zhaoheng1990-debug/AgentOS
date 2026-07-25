"""Mechanical contract for minimal semantic facts v0.79."""

from __future__ import annotations

from .admission_v4_facts import semantic_fact_violations
from .provider_telemetry import hash_payload


def validate_minimal_witness(*, receipt, item, refs):
    failures = []
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A13_MINIMAL_SEMANTIC_WITNESS",
        "source_item_hash": hash_payload(item),
        "evidence_refs": list(refs),
    }
    if set(receipt) != {
        "case_id",
        "mechanism",
        "source_item_hash",
        "all_candidates_assessed",
        "records",
        "evidence_refs",
    }:
        failures.append("ADMISSION_V4_RECEIPT_SHAPE_INVALID")
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"ADMISSION_V4_{field.upper()}_MISMATCH")
    if receipt.get("all_candidates_assessed") is not True:
        failures.append("ADMISSION_V4_COVERAGE_NOT_CONFIRMED")
    records = receipt.get("records")
    if not isinstance(records, list):
        return sorted(set([
            *failures,
            "ADMISSION_V4_RECORDS_NOT_ARRAY",
        ]))
    expected_ids = {
        span["span_id"] for span in item["candidate_spans"]
    }
    observed_ids = [
        record.get("span_id")
        for record in records
        if isinstance(record, dict)
    ]
    if (
        len(observed_ids) != len(set(observed_ids))
        or set(observed_ids) != expected_ids
    ):
        failures.append("ADMISSION_V4_SPAN_COVERAGE_INVALID")
    for record in records:
        if not isinstance(record, dict):
            failures.append("ADMISSION_V4_RECORD_NOT_OBJECT")
            continue
        failures.extend(semantic_fact_violations(record))
    return sorted(set(failures))
