"""Provider schema for staged context-only receipts v0.82."""

from __future__ import annotations

from .admission_v6_facts import CONTEXT_UTILITY_CODES
from .admission_v7_facts import FACT_FIELDS
from .provider_telemetry import hash_payload


def context_addon_schema(
    *,
    item,
    candidate_span_ids,
    atomic_receipt,
    atomic_partition,
    refs,
):
    fact_properties = {
        "span_id": {
            "type": "string",
            "enum": list(candidate_span_ids),
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
            "enum": ["A16_STAGED_CONTEXT_UTILITY_ADDON"],
        },
        "source_item_hash": {
            "type": "string",
            "enum": [hash_payload(item)],
        },
        "source_atomic_receipt_hash": {
            "type": "string",
            "enum": [hash_payload(atomic_receipt)],
        },
        "source_atomic_partition_hash": {
            "type": "string",
            "enum": [atomic_partition["partition_hash"]],
        },
        "all_candidates_assessed": {
            "type": "boolean",
            "enum": [True],
        },
        "records": {
            "type": "array",
            "minItems": len(candidate_span_ids),
            "maxItems": len(candidate_span_ids),
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
