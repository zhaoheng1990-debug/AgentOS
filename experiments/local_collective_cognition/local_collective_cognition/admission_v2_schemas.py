"""Provider JSON schema for typed evidence admission v0.76."""

from __future__ import annotations

from .admission_v2_types import (
    ADMISSION_STATES,
    DISPOSITIONS,
    EVIDENCE_UTILITIES,
    OBJECT_RELATIONS,
)
from .provider_telemetry import hash_payload


def typed_admission_schema(*, item, refs):
    span_ids = [
        span["span_id"] for span in item["candidate_spans"]
    ]
    record = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "span_id",
            "object_relation",
            "evidence_utility",
            "disposition",
            "rationale",
        ],
        "properties": {
            "span_id": {"type": "string", "enum": span_ids},
            "object_relation": {
                "type": "string",
                "enum": list(OBJECT_RELATIONS),
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
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string",
            "enum": ["A11_TYPED_EVIDENCE_ADMISSION"],
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
            "items": record,
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
