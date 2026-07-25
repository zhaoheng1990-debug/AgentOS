"""Structural contract for staged context-only receipts."""

from __future__ import annotations

from .admission_v7_facts import structural_fact_violations
from .provider_telemetry import hash_payload


def validate_context_addon(
    *,
    receipt,
    item,
    atomic_receipt,
    atomic_partition,
    refs,
):
    failures = []
    evidence = set(atomic_partition["evidence_span_ids"])
    expected_ids = {
        span["span_id"] for span in item["candidate_spans"]
        if span["span_id"] not in evidence
    }
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A16_STAGED_CONTEXT_UTILITY_ADDON",
        "source_item_hash": hash_payload(item),
        "source_atomic_receipt_hash": hash_payload(atomic_receipt),
        "source_atomic_partition_hash": atomic_partition["partition_hash"],
        "evidence_refs": list(refs),
    }
    if set(receipt) != {
        "case_id",
        "mechanism",
        "source_item_hash",
        "source_atomic_receipt_hash",
        "source_atomic_partition_hash",
        "all_candidates_assessed",
        "records",
        "evidence_refs",
    }:
        failures.append("ADMISSION_V7_RECEIPT_SHAPE_INVALID")
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"ADMISSION_V7_{field.upper()}_MISMATCH")
    if receipt.get("all_candidates_assessed") is not True:
        failures.append("ADMISSION_V7_COVERAGE_NOT_CONFIRMED")
    records = receipt.get("records")
    if not isinstance(records, list):
        return sorted(set([
            *failures,
            "ADMISSION_V7_RECORDS_NOT_ARRAY",
        ]))
    observed_ids = [
        fact.get("span_id")
        for fact in records
        if isinstance(fact, dict)
    ]
    if (
        len(observed_ids) != len(set(observed_ids))
        or set(observed_ids) != expected_ids
    ):
        failures.append("ADMISSION_V7_SPAN_COVERAGE_INVALID")
    for fact in records:
        if not isinstance(fact, dict):
            failures.append("ADMISSION_V7_RECORD_NOT_OBJECT")
            continue
        failures.extend(structural_fact_violations(fact))
    return sorted(set(failures))
