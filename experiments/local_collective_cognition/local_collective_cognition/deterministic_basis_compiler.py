"""Zero-Provider compiler from frame-bound basis to outcome receipt."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .comparison_frame_contracts import (
    validate_comparison_frame,
    validate_frame_basis,
)


COMPILER_VERSION = "deterministic_basis_compiler_v0_67"
COMPATIBLE = {
    "EXACT",
    "ALLOWED_BY_UNCONSTRAINED",
    "IMPLICITLY_COMPATIBLE",
}


def compile_basis(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    frame: dict[str, Any],
    basis: dict[str, Any],
) -> dict[str, Any]:
    refs = evidence_refs(item)
    failures = validate_comparison_frame(
        receipt=frame,
        item=item,
        admission=admission,
        refs=refs,
    )
    failures.extend(validate_frame_basis(
        receipt=basis,
        item=item,
        admission=admission,
        frame=frame,
        refs=refs,
    ))
    if failures:
        raise ValueError(
            "comparison_frame_compile_input_invalid:" + ",".join(failures)
        )
    partition = _partition(basis["basis_records"])
    authoritative = _authoritative_records(basis["basis_records"])
    normalized = [
        (record["span_id"], _normalize(record))
        for record in authoritative
    ]
    labels = {
        label for _, label in normalized if label is not None
    }
    ambiguity = _ambiguity(frame, authoritative, normalized, labels)
    if ambiguity == "NONE":
        label = next(iter(labels))
        state = "DECISIVE"
    else:
        label = "UNRESOLVED_MATERIAL_AMBIGUITY"
        state = "UNRESOLVED_MATERIAL_AMBIGUITY"
    commitment = {
        "case_id": item["case_id"],
        "mechanism": "A3_DETERMINISTIC_BASIS_COMPILER",
        "compiler_version": COMPILER_VERSION,
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_frame_hash": hash_payload(frame),
        "source_basis_hash": hash_payload(basis),
        "decision_state": state,
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


def validate_compiled_receipt(
    *,
    receipt: dict[str, Any],
    item: dict[str, Any],
    admission: dict[str, Any],
    frame: dict[str, Any],
    basis: dict[str, Any],
) -> list[str]:
    expected = compile_basis(
        item=item, admission=admission, frame=frame, basis=basis
    )
    return [] if receipt == expected else ["COMPILER_RECEIPT_NOT_REPLAYABLE"]


def _authoritative_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compatible = [
        record for record in records
        if record["outcome_binding"] == "EXACT"
        and record["focal_contrast_binding"] == "EXACT"
        and record["timepoint_binding"] in COMPATIBLE
        and record["measurement_binding"] in COMPATIBLE
        and record["admissibility"] in {"DECISIVE", "SUPPORTING"}
    ]
    decisive = [
        record for record in compatible
        if record["admissibility"] == "DECISIVE"
    ]
    return decisive or compatible


def _normalize(record: dict[str, Any]) -> str | None:
    significance = record["significance_state"]
    direction = record["observed_direction"]
    orientation = record["comparison_orientation"]
    if significance in {"NOT_SIGNIFICANT", "TREND_OR_BORDERLINE"}:
        return "NO_DIFFERENCE"
    if direction == "NO_MATERIAL_DIFFERENCE":
        return "NO_DIFFERENCE"
    if significance != "SIGNIFICANT":
        return None
    mapping = {
        ("INTERVENTION_VS_COMPARATOR", "HIGHER"): "INCREASED",
        ("INTERVENTION_VS_COMPARATOR", "LOWER"): "DECREASED",
        ("COMPARATOR_VS_INTERVENTION", "HIGHER"): "DECREASED",
        ("COMPARATOR_VS_INTERVENTION", "LOWER"): "INCREASED",
    }
    return mapping.get((orientation, direction))


def _ambiguity(
    frame: dict[str, Any],
    authoritative: list[dict[str, Any]],
    normalized: list[tuple[str, str | None]],
    labels: set[str],
) -> str:
    if frame["frame_status"] != "RESOLVED":
        return frame["ambiguity_axes"][0]
    if not authoritative or any(label is None for _, label in normalized):
        return "INSUFFICIENT_BASIS"
    if len(labels) != 1:
        return "MIXED_EFFECTS"
    return "NONE"


def _partition(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping = {
        "DECISIVE": "primary_span_ids",
        "SUPPORTING": "corroborating_span_ids",
        "COUNTER": "counter_span_ids",
        "REJECT_AFTER_BASIS": "rejected_after_basis_span_ids",
    }
    result = {field: [] for field in mapping.values()}
    for record in records:
        result[mapping[record["admissibility"]]].append(record["span_id"])
    for values in result.values():
        values.sort()
    return result


def _rationale(
    label: str,
    ambiguity: str,
    normalized: list[tuple[str, str | None]],
) -> str:
    trace = ", ".join(
        f"{span_id}={value or 'UNRESOLVED'}"
        for span_id, value in normalized
    ) or "no authoritative frame-compatible basis"
    if ambiguity == "NONE":
        return f"Deterministic normalization compiled {label}: {trace}."
    return (
        "Deterministic normalization abstained on "
        f"{ambiguity}: {trace}."
    )
