"""Provider contract for unstated ambiguity discovery."""

from __future__ import annotations

import re

from .unstated_ambiguity_holdout import EVIDENCE_REFS, NULL, POSITIVE


TASK_KIND = "pilot_unstated_ambiguity_discovery"
STATES = (POSITIVE, NULL, "UNCERTAIN")
STRUCTURE_FIELDS = ("rival_a", "rival_b", "decisive_contrast", "discriminating_question")


def discovery_schema(item_id, *, evidence_refs=EVIDENCE_REFS):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["item_id", "discovery_state", *STRUCTURE_FIELDS, "confidence", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "discovery_state": {"type": "string", "enum": list(state_order(item_id))},
            **{field: {"type": "string", "maxLength": 500} for field in STRUCTURE_FIELDS},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {
                "type": "array", "minItems": len(evidence_refs), "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def state_order(item_id):
    suffix = re.search(r"(\d+)$", item_id)
    if suffix is None:
        raise ValueError("ambiguity_discovery_item_id_numeric_suffix_required")
    offset = (int(suffix.group(1)) - 1) % len(STATES)
    return STATES[offset:] + STATES[:offset]


def validate_discovery_payload(payload, *, item_id, evidence_refs=EVIDENCE_REFS):
    _, warnings = normalize_discovery_payload(
        payload, item_id=item_id, evidence_refs=evidence_refs,
    )
    if warnings:
        raise ValueError("ambiguity_discovery_null_packet_not_empty")


def normalize_discovery_payload(payload, *, item_id, evidence_refs=EVIDENCE_REFS):
    required = {"item_id", "discovery_state", *STRUCTURE_FIELDS, "confidence", "evidence_refs"}
    if not isinstance(payload, dict) or set(payload) != required or payload.get("item_id") != item_id:
        raise ValueError("ambiguity_discovery_payload_shape_invalid")
    if payload["discovery_state"] not in STATES or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("ambiguity_discovery_payload_state_or_evidence_invalid")
    confidence = payload["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        raise ValueError("ambiguity_discovery_payload_confidence_invalid")
    values = [payload[field].strip() if isinstance(payload[field], str) else "" for field in STRUCTURE_FIELDS]
    if payload["discovery_state"] == POSITIVE and (not all(values) or "?" not in values[-1]):
        raise ValueError("ambiguity_discovery_positive_packet_incomplete")
    normalized, warnings = dict(payload), []
    if payload["discovery_state"] in {NULL, "UNCERTAIN"} and any(values):
        normalized.update({field: "" for field in STRUCTURE_FIELDS})
        warnings.append("NONPOSITIVE_STRUCTURE_FIELDS_MECHANICALLY_CLEARED")
    return normalized, tuple(warnings)
