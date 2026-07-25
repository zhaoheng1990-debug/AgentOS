"""Deterministic compiler for grounded v0.69 witnesses."""

from __future__ import annotations

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .relation_witness_contracts import (
    validate_witness_basis,
    validate_witness_frame,
)


COMPATIBLE = {
    "EXACT",
    "ALLOWED_BY_UNCONSTRAINED",
    "IMPLICITLY_COMPATIBLE",
}


def compile_witness_basis(*, item, admission, catalog, frame, basis):
    refs = evidence_refs(item)
    failures = validate_witness_frame(
        receipt=frame,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
    )
    failures.extend(validate_witness_basis(
        receipt=basis,
        item=item,
        admission=admission,
        catalog=catalog,
        frame=frame,
        refs=refs,
    ))
    if failures:
        raise ValueError("witness_compile_invalid:" + ",".join(failures))
    records = basis["basis_records"]
    usable = [
        record for record in records
        if record["evidence_relevance"] == "EXACT_OBJECT"
        and record["timepoint_binding"] in COMPATIBLE
        and record["measurement_binding"] in COMPATIBLE
        and record["evidence_role"] in {"DECISIVE", "SUPPORTING"}
    ]
    decisive = [
        record for record in usable if record["evidence_role"] == "DECISIVE"
    ]
    authoritative = decisive or usable
    normalized = [
        (record["span_id"], _normalize(record))
        for record in authoritative
    ]
    labels = {value for _, value in normalized if value is not None}
    ambiguity = (
        frame["ambiguity_axes"][0]
        if frame["frame_status"] != "RESOLVED"
        else "INSUFFICIENT_BASIS"
        if not authoritative or any(value is None for _, value in normalized)
        else "MIXED_EFFECTS"
        if len(labels) != 1
        else "NONE"
    )
    label = (
        next(iter(labels))
        if ambiguity == "NONE"
        else "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    partition = _partition(records)
    commitment = {
        "case_id": item["case_id"],
        "mechanism": "A5_RELATION_WITNESS_COMPILER",
        "compiler_version": "relation_witness_compiler_v0_69",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_arm_catalog_hash": catalog["catalog_hash"],
        "source_frame_hash": hash_payload(frame),
        "source_basis_hash": hash_payload(basis),
        "decision_state": (
            "DECISIVE" if ambiguity == "NONE"
            else "UNRESOLVED_MATERIAL_AMBIGUITY"
        ),
        "predicted_label": label,
        "material_ambiguity": ambiguity,
        **partition,
        "normalized_basis": [
            {"span_id": span_id, "normalized_label": value}
            for span_id, value in normalized
        ],
        "rationale": f"Grounded witness compilation: {normalized}.",
        "evidence_refs": list(refs),
        "provider_override_allowed": False,
    }
    return {**commitment, "compiler_hash": hash_payload(commitment)}


def _normalize(record):
    relation = record["observed_relation"]
    if relation == "NO_COMPARATIVE_EFFECT_REPORTED":
        return "NO_DIFFERENCE"
    if record["significance_state"] in {
        "NOT_SIGNIFICANT",
        "TREND_OR_BORDERLINE",
    }:
        return "NO_DIFFERENCE"
    if relation == "NO_MATERIAL_DIFFERENCE":
        return "NO_DIFFERENCE"
    if record["significance_state"] != "SIGNIFICANT":
        return None
    subject, reference = (
        record["subject_group_id"],
        record["reference_group_id"],
    )
    if subject == "FOCAL_INTERVENTION" and reference in {
        "FOCAL_COMPARATOR",
        "WITHIN_GROUP_BASELINE",
    }:
        return {
            "SUBJECT_HIGHER": "INCREASED",
            "SUBJECT_LOWER": "DECREASED",
        }.get(relation)
    if (
        subject == "FOCAL_COMPARATOR"
        and reference == "FOCAL_INTERVENTION"
    ):
        return {
            "SUBJECT_HIGHER": "DECREASED",
            "SUBJECT_LOWER": "INCREASED",
        }.get(relation)
    return None


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
