"""Structural contract for context-utility witness receipts."""

from __future__ import annotations

from .admission_v6_facts import structural_fact_violations
from .provider_telemetry import hash_payload


def validate_context_utility_witness(*, receipt, item, refs):
    failures = []
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A15_CONTEXT_UTILITY_WITNESS",
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
        failures.append("ADMISSION_V6_RECEIPT_SHAPE_INVALID")
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"ADMISSION_V6_{field.upper()}_MISMATCH")
    if receipt.get("all_candidates_assessed") is not True:
        failures.append("ADMISSION_V6_COVERAGE_NOT_CONFIRMED")
    records = receipt.get("records")
    if not isinstance(records, list):
        return sorted(set([
            *failures,
            "ADMISSION_V6_RECORDS_NOT_ARRAY",
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
        failures.append("ADMISSION_V6_SPAN_COVERAGE_INVALID")
    for fact in records:
        if not isinstance(fact, dict):
            failures.append("ADMISSION_V6_RECORD_NOT_OBJECT")
            continue
        failures.extend(structural_fact_violations(fact))
    return sorted(set(failures))
