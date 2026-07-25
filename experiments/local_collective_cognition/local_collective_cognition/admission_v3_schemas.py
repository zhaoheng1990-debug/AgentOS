"""Provider schema for witness-backed admission v0.78."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES
from .admission_v2_types import (
    ADMISSION_STATES,
    DISPOSITIONS,
    EVIDENCE_UTILITIES,
    OBJECT_RELATIONS,
)
from .outcome_separability_witness import OUTCOME_BINDINGS
from .provider_telemetry import hash_payload


def witness_admission_schema(*, item, refs):
    span_ids = [
        span["span_id"] for span in item["candidate_spans"]
    ]
    record_properties = {
        "span_id": {"type": "string", "enum": span_ids},
        "outcome_binding": {
            "type": "string",
            "enum": list(OUTCOME_BINDINGS),
        },
        "target_effect_separable": {"type": "boolean"},
        "object_relation": {
            "type": "string",
            "enum": list(OBJECT_RELATIONS),
        },
        "independent_effect_support": {"type": "boolean"},
        "effect_basis_codes": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": list(EFFECT_BASIS_CODES),
            },
        },
        "evidence_utility": {
            "type": "string",
            "enum": list(EVIDENCE_UTILITIES),
        },
        "disposition": {
            "type": "string",
            "enum": list(DISPOSITIONS),
        },
        "rationale": {"type": "string"},
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string",
            "enum": ["A12_WITNESS_BACKED_ADMISSION"],
        },
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "all_candidates_assessed": {
            "type": "boolean",
            "enum": [True],
        },
        "admission_state": {
            "type": "string",
            "enum": list(ADMISSION_STATES),
        },
        "records": {
            "type": "array",
            "minItems": len(span_ids),
            "maxItems": len(span_ids),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": list(record_properties),
                "properties": record_properties,
            },
        },
        "evidence_refs": {
            "type": "array",
            "minItems": len(refs),
            "maxItems": len(refs),
            "uniqueItems": True,
            "items": {"type": "string", "enum": list(refs)},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
