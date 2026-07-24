"""Strict schemas for v0.68 relational Provider receipts."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .relational_contrast_types import (
    COORDINATE_BINDINGS,
    EVIDENCE_RELEVANCE,
    EVIDENCE_ROLES,
    FRAME_AMBIGUITY_AXES,
    FRAME_STATES,
    OBSERVED_RELATIONS,
    REFERENCE_IDS,
    RELATION_MODES,
    REQUIREMENT_MODES,
    SIGNIFICANCE_STATES,
    SUBJECT_IDS,
)


def relational_frame_schema(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
    refs: tuple[str, ...],
) -> dict[str, Any]:
    aliases = {
        "type": "array",
        "minItems": 1,
        "uniqueItems": True,
        "items": {"type": "string"},
    }
    requirement = _object({
        "mode": {"type": "string", "enum": list(REQUIREMENT_MODES)},
        "value": {"type": "string"},
    })
    return _object({
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A4_RELATIONAL_FRAME"]},
        "source_item_hash": {"type": "string", "enum": [hash_payload(item)]},
        "source_admission_hash": {
            "type": "string", "enum": [hash_payload(admission)]
        },
        "source_arm_catalog_hash": {
            "type": "string", "enum": [catalog["catalog_hash"]]
        },
        "intervention_aliases": aliases,
        "comparator_aliases": aliases,
        "relation_mode": {
            "type": "string", "enum": list(RELATION_MODES)
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


def relational_basis_schema(
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
        "mechanism": {"type": "string", "enum": ["A4_RELATIONAL_BASIS"]},
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
