"""Deterministic compiler for v0.71 candidate-ID receipts."""

from .provider_telemetry import hash_payload


def compile_surface_binding(
    *, item, admission, arm_catalog, frame, catalog, basis, refs
):
    records = basis["basis_records"]
    usable = [
        record for record in records
        if record["evidence_relevance"] == "EXACT_OBJECT"
        and record["evidence_role"] in {"DECISIVE", "SUPPORTING"}
        and record["timepoint_binding"] not in {"DIFFERENT", "UNRESOLVED"}
        and record["measurement_binding"] not in {"DIFFERENT", "UNRESOLVED"}
    ]
    decisive = [
        record for record in usable if record["evidence_role"] == "DECISIVE"
    ]
    authoritative = decisive or usable
    labels = [_normalize(record) for record in authoritative]
    unique = {value for value in labels if value is not None}
    label = (
        next(iter(unique))
        if labels and None not in labels and len(unique) == 1
        else "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    partition = _partition(records)
    value = {
        "case_id": item["case_id"],
        "mechanism": "A7_SURFACE_ID_COMPILER",
        "compiler_version": "surface_binding_compiler_v0_71",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_arm_catalog_hash": arm_catalog["catalog_hash"],
        "source_frame_hash": hash_payload(frame),
        "source_surface_catalog_hash": catalog["catalog_hash"],
        "source_basis_hash": hash_payload(basis),
        "decision_state": (
            "DECISIVE" if label != "UNRESOLVED_MATERIAL_AMBIGUITY"
            else "UNRESOLVED_MATERIAL_AMBIGUITY"
        ),
        "predicted_label": label,
        "material_ambiguity": (
            "NONE" if label != "UNRESOLVED_MATERIAL_AMBIGUITY"
            else "INSUFFICIENT_BASIS"
        ),
        **partition,
        "normalized_basis": labels,
        "rationale": f"Candidate-ID compilation: {labels}.",
        "evidence_refs": list(refs),
        "provider_override_allowed": False,
    }
    return {**value, "compiler_hash": hash_payload(value)}


def _normalize(record):
    relation = record["observed_relation"]
    if relation == "NO_COMPARATIVE_EFFECT_REPORTED":
        return "NO_DIFFERENCE"
    if record["significance_state"] in {
        "NOT_SIGNIFICANT",
        "TREND_OR_BORDERLINE",
    } or relation == "NO_MATERIAL_DIFFERENCE":
        return "NO_DIFFERENCE"
    if record["significance_state"] != "SIGNIFICANT":
        return None
    direct = record["subject_group_id"] == "FOCAL_INTERVENTION"
    if direct:
        return {
            "SUBJECT_HIGHER": "INCREASED",
            "SUBJECT_LOWER": "DECREASED",
        }.get(relation)
    return {
        "SUBJECT_HIGHER": "DECREASED",
        "SUBJECT_LOWER": "INCREASED",
    }.get(relation)


def _partition(records):
    mapping = {
        "DECISIVE": "primary_span_ids",
        "SUPPORTING": "corroborating_span_ids",
        "COUNTER": "counter_span_ids",
        "EXCLUDE_UNRELATED": "rejected_after_basis_span_ids",
    }
    result = {field: [] for field in mapping.values()}
    for record in records:
        result[mapping[record["evidence_role"]]].append(record["span_id"])
    return result
