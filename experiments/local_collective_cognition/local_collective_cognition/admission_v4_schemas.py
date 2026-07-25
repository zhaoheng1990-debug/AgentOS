"""Provider schema for minimal semantic witness v0.79."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES
from .admission_v4_facts import FACT_FIELDS, OUTCOME_SCOPES
from .provider_telemetry import hash_payload


def minimal_witness_schema(*, item, refs):
    span_ids = [
        span["span_id"] for span in item["candidate_spans"]
    ]
    fact_properties = {
        "span_id": {"type": "string", "enum": span_ids},
        "outcome_scope": {
            "type": "string",
            "enum": list(OUTCOME_SCOPES),
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
        "non_effect_context_relevance": {"type": "boolean"},
        "rationale": {"type": "string"},
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string",
            "enum": ["A13_MINIMAL_SEMANTIC_WITNESS"],
        },
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "all_candidates_assessed": {
            "type": "boolean",
            "enum": [True],
        },
        "records": {
            "type": "array",
            "minItems": len(span_ids),
            "maxItems": len(span_ids),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": list(FACT_FIELDS),
                "properties": fact_properties,
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
