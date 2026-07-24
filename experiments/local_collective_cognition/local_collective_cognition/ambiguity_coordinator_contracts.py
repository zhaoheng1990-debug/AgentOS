"""Provider contract for identity-blind coordination of discovery receipts."""

from __future__ import annotations

from .unstated_ambiguity_holdout import NULL, POSITIVE


TASK_KIND = "pilot_ambiguity_receipt_coordination"
STATES = (POSITIVE, NULL, "UNCERTAIN")
POSITIONS = ("POSITION_A", "POSITION_B", "BOTH", "NEITHER", "UNRESOLVED")


def coordinator_schema(batch_id, item_ids, evidence_refs):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["batch_id", "decisions", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "decisions": {
                "type": "array", "minItems": len(item_ids), "maxItems": len(item_ids),
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["coordination_item_id", "final_state", "supported_position", "confidence", "decision_note"],
                    "properties": {
                        "coordination_item_id": {"type": "string", "enum": list(item_ids)},
                        "final_state": {"type": "string", "enum": list(STATES)},
                        "supported_position": {"type": "string", "enum": list(POSITIONS)},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "decision_note": {"type": "string", "maxLength": 500},
                    },
                },
            },
            "evidence_refs": {
                "type": "array", "minItems": len(evidence_refs), "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def validate_coordinator_payload(payload, *, batch_id, item_ids, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "decisions", "evidence_refs"}:
        raise ValueError("ambiguity_coordinator_payload_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("ambiguity_coordinator_payload_binding_invalid")
    decisions = payload["decisions"]
    if not isinstance(decisions, list) or len(decisions) != len(item_ids):
        raise ValueError("ambiguity_coordinator_decision_count_invalid")
    required = {"coordination_item_id", "final_state", "supported_position", "confidence", "decision_note"}
    observed = []
    for item in decisions:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("ambiguity_coordinator_decision_shape_invalid")
        observed.append(item["coordination_item_id"])
        confidence = item["confidence"]
        if (item["final_state"] not in STATES or item["supported_position"] not in POSITIONS
                or not isinstance(confidence, (int, float)) or isinstance(confidence, bool)
                or not 0 <= confidence <= 1 or not isinstance(item["decision_note"], str)
                or not item["decision_note"].strip()):
            raise ValueError("ambiguity_coordinator_decision_value_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(item_ids):
        raise ValueError("ambiguity_coordinator_item_binding_invalid")
