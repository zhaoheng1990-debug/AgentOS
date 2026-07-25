"""Mechanical contracts for witness-backed admission v0.78."""

from __future__ import annotations

from .admission_v2_annotation_rubric import label_violations
from .admission_v2_types import ADMISSION_STATES
from .effect_basis_admission import effect_basis_violations
from .outcome_separability_witness import separability_violations
from .provider_telemetry import hash_payload


def validate_witness_admission(*, receipt, item, refs):
    failures = []
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A12_WITNESS_BACKED_ADMISSION",
        "source_item_hash": hash_payload(item),
        "evidence_refs": list(refs),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            failures.append(f"ADMISSION_V3_{field.upper()}_MISMATCH")
    if receipt.get("all_candidates_assessed") is not True:
        failures.append("ADMISSION_V3_COVERAGE_NOT_CONFIRMED")
    if receipt.get("admission_state") not in ADMISSION_STATES:
        failures.append("ADMISSION_V3_STATE_INVALID")
    if "predicted_label" in receipt:
        failures.append("ADMISSION_V3_PREMATURE_LABEL_AUTHORITY")
    records = receipt.get("records")
    if not isinstance(records, list):
        return sorted(set([
            *failures,
            "ADMISSION_V3_RECORDS_NOT_ARRAY",
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
        failures.append("ADMISSION_V3_SPAN_PARTITION_INVALID")
    for record in records:
        failures.extend(_record_failures(record))
    admitted = sum(
        isinstance(record, dict)
        and record.get("disposition") == "ADMIT_EVIDENCE"
        for record in records
    )
    expected_state = (
        "EVIDENCE_AVAILABLE"
        if admitted
        else "NO_APPLICABLE_EVIDENCE"
    )
    if receipt.get("admission_state") != expected_state:
        failures.append("ADMISSION_V3_STATE_PARTITION_CONFLICT")
    return sorted(set(failures))


def _record_failures(record):
    if not isinstance(record, dict):
        return ["ADMISSION_V3_RECORD_NOT_OBJECT"]
    failures = [
        f"ADMISSION_V3_{failure}"
        for failure in label_violations(record)
    ]
    failures.extend(separability_violations(record))
    failures.extend(effect_basis_violations(record))
    rationale = record.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        failures.append("ADMISSION_V3_RATIONALE_MISSING")
    return failures
