"""Provider schema for context-utility witnesses v0.81."""

from __future__ import annotations

from .admission_v2_annotation_rubric import EFFECT_BASIS_CODES
from .admission_v6_facts import CONTEXT_UTILITY_CODES, FACT_FIELDS
from .provider_telemetry import hash_payload


def context_utility_witness_schema(*, item, refs):
    span_ids = [span["span_id"] for span in item["candidate_spans"]]
    fact_properties = {
        "span_id": {"type": "string", "enum": span_ids},
        "exact_target_object_mentioned": {"type": "boolean"},
        "target_effect_separately_extractable": {"type": "boolean"},
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
        "context_utility_code": {
            "type": "string",
            "enum": list(CONTEXT_UTILITY_CODES),
        },
        "context_changes_downstream_decision": {"type": "boolean"},
        "utility_anchor_quote": {"type": "string"},
        "rationale": {"type": "string"},
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string",
            "enum": ["A15_CONTEXT_UTILITY_WITNESS"],
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
