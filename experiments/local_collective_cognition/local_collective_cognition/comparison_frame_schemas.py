"""Strict Provider schemas for v0.67 frame and basis receipts."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .comparison_frame_types import (
    ADMISSIBILITY_STATES,
    CONTRAST_BINDINGS,
    CONTRAST_TYPES,
    DIRECTIONS,
    FRAME_AMBIGUITY_AXES,
    FRAME_BINDINGS,
    FRAME_STATES,
    NORMALIZATION_RULES,
    ORIENTATIONS,
    OUTCOME_BINDINGS,
    REQUIREMENT_MODES,
    SIGNIFICANCE_STATES,
)


def comparison_frame_schema(
    *, item: dict[str, Any], admission: dict[str, Any], refs: tuple[str, ...]
) -> dict[str, Any]:
    requirement = _object({
        "mode": {"type": "string", "enum": list(REQUIREMENT_MODES)},
        "value": {"type": "string"},
    })
    string_set = {
        "type": "array",
        "minItems": 1,
        "uniqueItems": True,
        "items": {"type": "string"},
    }
    return _object({
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A3_COMPARISON_FRAME"]},
        "source_item_hash": {"type": "string", "enum": [hash_payload(item)]},
        "source_admission_hash": {
            "type": "string", "enum": [hash_payload(admission)]
        },
        "study_arms": {**string_set, "minItems": 2},
        "focal_intervention_members": string_set,
        "comparator_members": string_set,
        "contrast_type": {"type": "string", "enum": list(CONTRAST_TYPES)},
        "normalization_rule": {
            "type": "string", "enum": list(NORMALIZATION_RULES)
        },
        "timepoint_requirement": requirement,
        "measurement_requirement": requirement,
        "frame_status": {"type": "string", "enum": list(FRAME_STATES)},
        "ambiguity_axes": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string", "enum": list(FRAME_AMBIGUITY_AXES)
            },
        },
        "rationale": {"type": "string"},
        "evidence_refs": _refs(refs),
    })


def frame_basis_schema(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    frame: dict[str, Any],
    refs: tuple[str, ...],
) -> dict[str, Any]:
    admitted, _ = admission_partition(admission)
    record = _object({
        "span_id": {"type": "string", "enum": admitted},
        "outcome_binding": {
            "type": "string", "enum": list(OUTCOME_BINDINGS)
        },
        "focal_contrast_binding": {
            "type": "string", "enum": list(CONTRAST_BINDINGS)
        },
        "timepoint_binding": {
            "type": "string", "enum": list(FRAME_BINDINGS)
        },
        "measurement_binding": {
            "type": "string", "enum": list(FRAME_BINDINGS)
        },
        "comparison_orientation": {
            "type": "string", "enum": list(ORIENTATIONS)
        },
        "observed_direction": {
            "type": "string", "enum": list(DIRECTIONS)
        },
        "significance_state": {
            "type": "string", "enum": list(SIGNIFICANCE_STATES)
        },
        "admissibility": {
            "type": "string", "enum": list(ADMISSIBILITY_STATES)
        },
        "rationale": {"type": "string"},
    })
    return _object({
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A3_FRAME_BOUND_BASIS"]},
        "source_item_hash": {"type": "string", "enum": [hash_payload(item)]},
        "source_admission_hash": {
            "type": "string", "enum": [hash_payload(admission)]
        },
        "source_frame_hash": {
            "type": "string", "enum": [hash_payload(frame)]
        },
        "frame_consumed": {"type": "boolean", "enum": [True]},
        "all_admitted_spans_assessed": {
            "type": "boolean", "enum": [True]
        },
        "basis_records": {
            "type": "array",
            "minItems": len(admitted),
            "maxItems": len(admitted),
            "items": record,
        },
        "evidence_refs": _refs(refs),
    })


def _refs(refs: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": len(refs),
        "maxItems": len(refs),
        "items": {"type": "string", "enum": list(refs)},
    }


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
