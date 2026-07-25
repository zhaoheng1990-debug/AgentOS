"""Mechanical contracts for typed evidence admission v0.76."""

from __future__ import annotations

from .admission_v2_types import (
    ADMISSION_STATES,
    DISPOSITIONS,
    EVIDENCE_UTILITIES,
    OBJECT_RELATIONS,
)
from .provider_telemetry import hash_payload


def validate_typed_admission(*, receipt, item, refs):
    failures = []
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A11_TYPED_EVIDENCE_ADMISSION",
        "source_item_hash": hash_payload(item),
        "evidence_refs": list(refs),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"ADMISSION_V2_{field.upper()}_MISMATCH")
    if receipt.get("all_candidates_assessed") is not True:
        failures.append("ADMISSION_V2_COVERAGE_NOT_CONFIRMED")
    if receipt.get("admission_state") not in ADMISSION_STATES:
        failures.append("ADMISSION_V2_STATE_INVALID")
    if "predicted_label" in receipt:
        failures.append("ADMISSION_V2_PREMATURE_LABEL_AUTHORITY")
    records = receipt.get("records")
    if not isinstance(records, list):
        return sorted(set([
            *failures,
            "ADMISSION_V2_RECORDS_NOT_ARRAY",
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
        failures.append("ADMISSION_V2_SPAN_PARTITION_INVALID")
    for record in records:
        failures.extend(_record_failures(record))
    evidence_count = sum(
        isinstance(record, dict)
        and record.get("disposition") == "ADMIT_EVIDENCE"
        for record in records
    )
    state = receipt.get("admission_state")
    if evidence_count and state != "EVIDENCE_AVAILABLE":
        failures.append("ADMISSION_V2_AVAILABLE_STATE_MISMATCH")
    if not evidence_count and state != "NO_APPLICABLE_EVIDENCE":
        failures.append("ADMISSION_V2_NULL_STATE_MISMATCH")
    return sorted(set(failures))


def _record_failures(record):
    if not isinstance(record, dict):
        return ["ADMISSION_V2_RECORD_NOT_OBJECT"]
    failures = []
    relation = record.get("object_relation")
    utility = record.get("evidence_utility")
    disposition = record.get("disposition")
    if relation not in OBJECT_RELATIONS:
        failures.append("ADMISSION_V2_OBJECT_RELATION_INVALID")
    if utility not in EVIDENCE_UTILITIES:
        failures.append("ADMISSION_V2_EVIDENCE_UTILITY_INVALID")
    if disposition not in DISPOSITIONS:
        failures.append("ADMISSION_V2_DISPOSITION_INVALID")
    expected_disposition = {
        "EFFECT_BEARING": "ADMIT_EVIDENCE",
        "CONTEXT_ONLY": "RETAIN_CONTEXT",
        "NONE": "REJECT",
    }.get(utility)
    if expected_disposition and disposition != expected_disposition:
        failures.append("ADMISSION_V2_UTILITY_DISPOSITION_CONFLICT")
    if relation == "IRRELEVANT_OBJECT" and disposition != "REJECT":
        failures.append("ADMISSION_V2_IRRELEVANT_OBJECT_RETAINED")
    if (
        disposition == "ADMIT_EVIDENCE"
        and relation != "EXACT_OBJECT"
    ):
        failures.append("ADMISSION_V2_EFFECT_OBJECT_MISMATCH")
    rationale = record.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("ADMISSION_V2_RATIONALE_MISSING")
    return failures
