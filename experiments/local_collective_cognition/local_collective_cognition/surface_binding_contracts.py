"""Mechanical contracts for v0.71 candidate-ID binding."""

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload


def validate_surface_binding(
    *, receipt, item, admission, arm_catalog, frame, catalog, refs
):
    expected = {
        "case_id": item["case_id"],
        "mechanism": "A7_SURFACE_ID_BINDING",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_arm_catalog_hash": arm_catalog["catalog_hash"],
        "source_frame_hash": hash_payload(frame),
        "source_surface_catalog_hash": catalog["catalog_hash"],
        "evidence_refs": list(refs),
    }
    failures = [
        f"SURFACE_BINDING_{field.upper()}_MISMATCH"
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    records = receipt.get("basis_records")
    if not isinstance(records, list):
        return sorted(set([*failures, "SURFACE_BINDING_RECORDS_INVALID"]))
    admitted, _ = admission_partition(admission)
    ids = [record.get("span_id") for record in records]
    if len(ids) != len(set(ids)) or set(ids) != set(admitted):
        failures.append("SURFACE_BINDING_COVERAGE_INVALID")
    candidates = {
        value["candidate_id"]: value for value in catalog["candidates"]
    }
    for record in records:
        relation_id = record.get("relation_surface_candidate_id")
        subject_id = record.get("subject_surface_candidate_id")
        if relation_id not in candidates:
            failures.append("SURFACE_BINDING_RELATION_ID_INVALID")
        if subject_id != "IMPLICIT_SUBJECT" and subject_id not in candidates:
            failures.append("SURFACE_BINDING_SUBJECT_ID_INVALID")
        if subject_id == "IMPLICIT_SUBJECT" and record.get(
            "observed_relation"
        ) != "NO_COMPARATIVE_EFFECT_REPORTED":
            failures.append("SURFACE_BINDING_IMPLICIT_SUBJECT_INVALID")
        exact = (
            record.get("evidence_relevance") == "EXACT_OBJECT"
            and record.get("timepoint_binding") not in {"DIFFERENT", "UNRESOLVED"}
            and record.get("measurement_binding") not in {"DIFFERENT", "UNRESOLVED"}
        )
        if exact and record.get("evidence_role") == "EXCLUDE_UNRELATED":
            failures.append("SURFACE_BINDING_EXACT_EVIDENCE_EXCLUDED")
    if receipt.get("all_admitted_spans_assessed") is not True:
        failures.append("SURFACE_BINDING_COVERAGE_NOT_CONFIRMED")
    if "predicted_label" in receipt:
        failures.append("SURFACE_BINDING_PREMATURE_LABEL_AUTHORITY")
    return sorted(set(failures))
