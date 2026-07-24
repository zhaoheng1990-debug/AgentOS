"""Replayable local compiler for v0.68 explicit relations."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .relational_contrast_contracts import (
    validate_relational_basis,
    validate_relational_frame,
)


COMPILER_VERSION = "relational_basis_compiler_v0_68"
COMPATIBLE = {
    "EXACT",
    "ALLOWED_BY_UNCONSTRAINED",
    "IMPLICITLY_COMPATIBLE",
}


def compile_relational_basis(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
    frame: dict[str, Any],
    basis: dict[str, Any],
) -> dict[str, Any]:
    refs = evidence_refs(item)
    failures = validate_relational_frame(
        receipt=frame,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
    )
    failures.extend(validate_relational_basis(
        receipt=basis,
        item=item,
        admission=admission,
        catalog=catalog,
        frame=frame,
        refs=refs,
    ))
    if failures:
        raise ValueError(
            "relational_compile_input_invalid:" + ",".join(failures)
        )
    partition = _partition(basis["basis_records"])
    authoritative = _authoritative(basis["basis_records"])
    normalized = [
        (record["span_id"], _normalize(record))
        for record in authoritative
    ]
    labels = {value for _, value in normalized if value is not None}
    ambiguity = _ambiguity(frame, authoritative, normalized, labels)
    label = (
        next(iter(labels))
        if ambiguity == "NONE"
        else "UNRESOLVED_MATERIAL_AMBIGUITY"
    )
    commitment = {
        "case_id": item["case_id"],
        "mechanism": "A4_RELATIONAL_BASIS_COMPILER",
        "compiler_version": COMPILER_VERSION,
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
        "rationale": _rationale(label, ambiguity, normalized),
        "evidence_refs": list(refs),
        "provider_override_allowed": False,
    }
    return {**commitment, "compiler_hash": hash_payload(commitment)}


def _authoritative(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compatible = [
        record for record in records
        if record["evidence_relevance"] == "EXACT_OBJECT"
        and record["subject_group_id"] != "UNRESOLVED"
        and record["reference_group_id"] != "UNRESOLVED"
        and record["timepoint_binding"] in COMPATIBLE
        and record["measurement_binding"] in COMPATIBLE
        and record["evidence_role"] in {"DECISIVE", "SUPPORTING"}
    ]
    decisive = [
        record for record in compatible
        if record["evidence_role"] == "DECISIVE"
    ]
    return decisive or compatible


def _normalize(record: dict[str, Any]) -> str | None:
    significance = record["significance_state"]
    relation = record["observed_relation"]
    if significance in {"NOT_SIGNIFICANT", "TREND_OR_BORDERLINE"}:
        return "NO_DIFFERENCE"
    if relation == "NO_MATERIAL_DIFFERENCE":
        return "NO_DIFFERENCE"
    if significance != "SIGNIFICANT":
        return None
    subject = record["subject_group_id"]
    reference = record["reference_group_id"]
    direct = (
        subject == "FOCAL_INTERVENTION"
        and reference in {"FOCAL_COMPARATOR", "WITHIN_GROUP_BASELINE"}
    )
    reverse = (
        subject == "FOCAL_COMPARATOR"
        and reference == "FOCAL_INTERVENTION"
    )
    if direct:
        return {
            "SUBJECT_HIGHER": "INCREASED",
            "SUBJECT_LOWER": "DECREASED",
        }.get(relation)
    if reverse:
        return {
            "SUBJECT_HIGHER": "DECREASED",
            "SUBJECT_LOWER": "INCREASED",
        }.get(relation)
    return None


def _ambiguity(frame, authoritative, normalized, labels) -> str:
    if frame["frame_status"] != "RESOLVED":
        return frame["ambiguity_axes"][0]
    if not authoritative or any(value is None for _, value in normalized):
        return "INSUFFICIENT_BASIS"
    if len(labels) != 1:
        return "MIXED_EFFECTS"
    return "NONE"


def _partition(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping = {
        "DECISIVE": "primary_span_ids",
        "SUPPORTING": "corroborating_span_ids",
        "COUNTER": "counter_span_ids",
        "EXCLUDE_UNRELATED": "rejected_after_basis_span_ids",
    }
    result = {field: [] for field in mapping.values()}
    for record in records:
        result[mapping[record["evidence_role"]]].append(record["span_id"])
    for values in result.values():
        values.sort()
    return result


def _rationale(label, ambiguity, normalized) -> str:
    trace = ", ".join(
        f"{span_id}={value or 'UNRESOLVED'}"
        for span_id, value in normalized
    ) or "no authoritative relational basis"
    if ambiguity == "NONE":
        return f"Explicit subject/reference relations compiled {label}: {trace}."
    return f"Relational compiler abstained on {ambiguity}: {trace}."
