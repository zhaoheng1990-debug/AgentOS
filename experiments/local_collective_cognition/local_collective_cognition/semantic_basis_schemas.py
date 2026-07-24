"""JSON schemas for v0.66 semantic-basis Provider tasks."""

from __future__ import annotations

from typing import Any

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload
from .semantic_basis_types import (
    ADMISSIBILITY_STATES,
    AMBIGUITY_AXES,
    DIRECTIONS,
    FINAL_LABELS,
    MEASUREMENT_BINDINGS,
    ORIENTATIONS,
    OUTCOME_BINDINGS,
    SIGNIFICANCE_STATES,
    SYNTHESIS_FIELDS,
    TIMEPOINT_BINDINGS,
)


def semantic_basis_schema(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    refs: tuple[str, ...],
) -> dict[str, Any]:
    admitted, _ = admission_partition(admission)
    record = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "span_id",
            "outcome_binding",
            "timepoint_binding",
            "measurement_binding",
            "comparison_orientation",
            "observed_direction",
            "significance_state",
            "admissibility",
            "rationale",
        ],
        "properties": {
            "span_id": {"type": "string", "enum": admitted},
            "outcome_binding": {
                "type": "string", "enum": list(OUTCOME_BINDINGS)
            },
            "timepoint_binding": {
                "type": "string", "enum": list(TIMEPOINT_BINDINGS)
            },
            "measurement_binding": {
                "type": "string", "enum": list(MEASUREMENT_BINDINGS)
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
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {"type": "string", "enum": ["A2_SEMANTIC_BASIS"]},
        "source_item_hash": {
            "type": "string", "enum": [hash_payload(item)]
        },
        "source_admission_hash": {
            "type": "string", "enum": [hash_payload(admission)]
        },
        "all_admitted_spans_assessed": {
            "type": "boolean", "enum": [True]
        },
        "basis_records": {
            "type": "array",
            "minItems": len(admitted),
            "maxItems": len(admitted),
            "items": record,
        },
        "ambiguity_axes": {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "enum": list(AMBIGUITY_AXES)},
        },
        "evidence_refs": _ref_array(refs),
    }
    return _object_schema(properties)


def synthesis_schema(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    basis: dict[str, Any],
    refs: tuple[str, ...],
) -> dict[str, Any]:
    admitted, _ = admission_partition(admission)
    span_array = {
        "type": "array",
        "uniqueItems": True,
        "items": {"type": "string", "enum": admitted},
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string", "enum": ["A2_SEMANTIC_SYNTHESIS"]
        },
        "source_item_hash": {
            "type": "string", "enum": [hash_payload(item)]
        },
        "source_admission_hash": {
            "type": "string", "enum": [hash_payload(admission)]
        },
        "source_basis_hash": {
            "type": "string", "enum": [hash_payload(basis)]
        },
        "basis_records_consumed": {
            "type": "boolean", "enum": [True]
        },
        "decision_state": {
            "type": "string",
            "enum": ["DECISIVE", "UNRESOLVED_MATERIAL_AMBIGUITY"],
        },
        "predicted_label": {
            "type": "string", "enum": list(FINAL_LABELS)
        },
        "material_ambiguity": {
            "type": "string",
            "enum": ["NONE", *AMBIGUITY_AXES],
        },
        "orientation_rule_applied": {
            "type": "boolean", "enum": [True]
        },
        "significance_rule_applied": {
            "type": "boolean", "enum": [True]
        },
        **{field: span_array for field in SYNTHESIS_FIELDS},
        "rationale": {"type": "string"},
        "evidence_refs": _ref_array(refs),
    }
    return _object_schema(properties)


def _ref_array(refs: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": len(refs),
        "maxItems": len(refs),
        "items": {"type": "string", "enum": list(refs)},
    }


def _object_schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
