"""Provider schema for selective evidence-boundary review v0.83."""

from __future__ import annotations

from .admission_v8_facts import BOUNDARY_ISSUE_CODES, FACT_FIELDS
from .provider_telemetry import hash_payload


def boundary_review_schema(
    *,
    item,
    reviewed_span_ids,
    staged_partition,
    refs,
):
    fact_properties = {
        "span_id": {
            "type": "string",
            "enum": list(reviewed_span_ids),
        },
        **{
            field: {"type": "boolean"}
            for field in FACT_FIELDS[1:8]
        },
        "boundary_issue_codes": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": list(BOUNDARY_ISSUE_CODES),
            },
        },
        "support_anchor_quote": {"type": "string"},
        "boundary_anchor_quote": {"type": "string"},
        "rationale": {"type": "string"},
    }
    properties = {
        "case_id": {"type": "string", "enum": [item["case_id"]]},
        "mechanism": {
            "type": "string",
            "enum": ["A17_SELECTIVE_EVIDENCE_BOUNDARY_REVIEW"],
        },
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "source_staged_partition_hash": {
            "type": "string",
            "enum": [staged_partition["partition_hash"]],
        },
        "all_candidates_assessed": {
            "type": "boolean",
            "enum": [True],
        },
        "records": {
            "type": "array",
            "minItems": len(reviewed_span_ids),
            "maxItems": len(reviewed_span_ids),
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
