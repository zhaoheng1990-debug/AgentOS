"""Provider schema for study-relation graph review v0.85."""

from __future__ import annotations

from .admission_v10_facts import (
    BINDING_FIELDS,
    BINDING_RELATIONS,
    COMPARISON_RELATIONS,
    COREFERENCE_RELATIONS,
    EFFECT_RELATIONS,
    OUTCOME_RELATIONS,
    POOLING_RELATIONS,
    SPAN_FACT_FIELDS,
)
from .provider_telemetry import hash_payload


def study_relation_schema(*, item, staged_partition, refs):
    span_ids = [span["span_id"] for span in item["candidate_spans"]]
    binding = {
        "type": "object",
        "additionalProperties": False,
        "required": list(BINDING_FIELDS),
        "properties": {
            "binding_id": {"type": "string"},
            "surface_form": {"type": "string"},
            "relation": {
                "type": "string",
                "enum": list(BINDING_RELATIONS),
            },
            "anchor_quote": {"type": "string"},
            "rationale": {"type": "string"},
        },
    }
    fact = {
        "type": "object",
        "additionalProperties": False,
        "required": list(SPAN_FACT_FIELDS),
        "properties": {
            "span_id": {"type": "string", "enum": span_ids},
            "binding_refs": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string"},
            },
            "comparison_relation": {
                "type": "string",
                "enum": list(COMPARISON_RELATIONS),
            },
            "outcome_relation": {
                "type": "string",
                "enum": list(OUTCOME_RELATIONS),
            },
            "effect_relation": {
                "type": "string",
                "enum": list(EFFECT_RELATIONS),
            },
            "pooling_relation": {
                "type": "string",
                "enum": list(POOLING_RELATIONS),
            },
            "coreference_relation": {
                "type": "string",
                "enum": list(COREFERENCE_RELATIONS),
            },
            "effect_anchor_quote": {"type": "string"},
            "relation_anchor_quote": {"type": "string"},
            "rationale": {"type": "string"},
        },
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string",
            "enum": ["A19_STUDY_RELATION_REVIEW"],
        },
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "source_staged_partition_hash": {
            "type": "string",
            "enum": [staged_partition["partition_hash"]],
        },
        "all_spans_assessed": {"type": "boolean", "enum": [True]},
        "bindings": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": binding,
        },
        "span_records": {
            "type": "array",
            "minItems": len(span_ids),
            "maxItems": len(span_ids),
            "items": fact,
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
