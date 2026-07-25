"""Schemas for v0.69 span-anchored relation witnesses."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .relational_contrast_schemas import relational_frame_schema
from .relational_contrast_types import (
    COORDINATE_BINDINGS,
    EVIDENCE_RELEVANCE,
    EVIDENCE_ROLES,
    REFERENCE_IDS,
    SIGNIFICANCE_STATES,
    SUBJECT_IDS,
)


OBSERVED_RELATIONS = (
    "SUBJECT_HIGHER",
    "SUBJECT_LOWER",
    "NO_MATERIAL_DIFFERENCE",
    "NO_COMPARATIVE_EFFECT_REPORTED",
    "DIRECTION_NOT_REPORTED",
    "CONFLICTING",
)


def witness_frame_schema(**values: Any) -> dict[str, Any]:
    return relational_frame_schema(**values)


def witness_basis_schema(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
    frame: dict[str, Any],
    refs: tuple[str, ...],
) -> dict[str, Any]:
    admitted, _ = admission_partition(admission)
    record = _object({
        "span_id": {"type": "string", "enum": admitted},
        "evidence_relevance": {
            "type": "string", "enum": list(EVIDENCE_RELEVANCE)
        },
        "subject_group_id": {
            "type": "string", "enum": list(SUBJECT_IDS)
        },
        "reference_group_id": {
            "type": "string", "enum": list(REFERENCE_IDS)
        },
        "subject_surface_mode": {
            "type": "string", "enum": ["EXPLICIT_ALIAS", "FRAME_IMPLICIT"]
        },
        "subject_surface": {"type": "string"},
        "relation_surface": {"type": "string"},
        "timepoint_binding": {
            "type": "string", "enum": list(COORDINATE_BINDINGS)
        },
        "measurement_binding": {
            "type": "string", "enum": list(COORDINATE_BINDINGS)
        },
        "observed_relation": {
            "type": "string", "enum": list(OBSERVED_RELATIONS)
        },
        "significance_state": {
            "type": "string", "enum": list(SIGNIFICANCE_STATES)
        },
        "evidence_role": {
            "type": "string", "enum": list(EVIDENCE_ROLES)
        },
        "rationale": {"type": "string"},
    })
    return _object({
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A5_RELATION_WITNESS_BASIS"]},
        "source_item_hash": {"type": "string", "enum": [hash_payload(item)]},
        "source_admission_hash": {
            "type": "string", "enum": [hash_payload(admission)]
        },
        "source_arm_catalog_hash": {
            "type": "string", "enum": [catalog["catalog_hash"]]
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
        "evidence_refs": {
            "type": "array",
            "minItems": len(refs),
            "maxItems": len(refs),
            "items": {"type": "string", "enum": list(refs)},
        },
    })


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
