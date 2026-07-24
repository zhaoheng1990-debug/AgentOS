"""Observable structural fingerprint receipts for clarification action credit."""

from __future__ import annotations


FINGERPRINT_VERSION = "clarification_action_fingerprint_v0_7"
FINGERPRINT_TASK_KIND = "clarification_action_fingerprint"
FINGERPRINTS = ("OPEN_RIVALS", "PROMPT_FIXED", "EQUIVALENT_RIVALS", "UNSUPPORTED_RIVAL", "UNCERTAIN")
DIRECT_ANSWERS = ("ANSWER_A", "ANSWER_B", "UNCERTAIN")


def fingerprint_schema(batch_id, case_ids):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["batch_id", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "assessments": {"type": "array", "minItems": len(case_ids), "maxItems": len(case_ids), "items": {
                "type": "object", "additionalProperties": False,
                "required": ["blind_case_id", "fingerprint", "preferred_direct_answer", "evidence_basis", "counterfactual"],
                "properties": {
                    "blind_case_id": {"type": "string", "enum": list(case_ids)},
                    "fingerprint": {"type": "string", "enum": list(FINGERPRINTS)},
                    "preferred_direct_answer": {"type": "string", "enum": list(DIRECT_ANSWERS)},
                    "evidence_basis": {"type": "string"},
                    "counterfactual": {"type": "string"},
                },
            }},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_fingerprint(payload, *, batch_id, case_ids, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("clarification_fingerprint_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("clarification_fingerprint_binding_invalid")
    items = payload["assessments"]
    if not isinstance(items, list) or len(items) != len(case_ids):
        raise ValueError("clarification_fingerprint_count_invalid")
    keys = {"blind_case_id", "fingerprint", "preferred_direct_answer", "evidence_basis", "counterfactual"}
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("clarification_fingerprint_item_shape_invalid")
        observed.append(item["blind_case_id"])
        if item["fingerprint"] not in FINGERPRINTS or item["preferred_direct_answer"] not in DIRECT_ANSWERS or not item["evidence_basis"].strip() or not item["counterfactual"].strip():
            raise ValueError("clarification_fingerprint_value_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(case_ids):
        raise ValueError("clarification_fingerprint_case_binding_invalid")
