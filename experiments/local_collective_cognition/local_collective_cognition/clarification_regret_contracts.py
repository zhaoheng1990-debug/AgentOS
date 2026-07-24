"""Provider contracts for formal clarification-regret decisions."""

from __future__ import annotations


DIRECT_VERSION = "clarification_direct_policy_v0_6"
REGRET_VERSION = "clarification_regret_receipt_v0_6"
DIRECT_TASK_KIND = "clarification_direct_policy"
REGRET_TASK_KIND = "clarification_regret_estimation"
ACTIONS = ("ASK", "ANSWER_A", "ANSWER_B", "UNCERTAIN")
DIRECT_ANSWERS = ("ANSWER_A", "ANSWER_B", "UNCERTAIN")


def direct_schema(batch_id, case_ids):
    return _schema(batch_id, case_ids, {
        "required": ["blind_case_id", "action", "evidence_basis", "confidence"],
        "properties": {
            "blind_case_id": {"type": "string", "enum": list(case_ids)},
            "action": {"type": "string", "enum": list(ACTIONS)},
            "evidence_basis": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    })


def regret_schema(batch_id, case_ids):
    return _schema(batch_id, case_ids, {
        "required": [
            "blind_case_id", "preferred_direct_answer",
            "probability_preferred_wrong", "evidence_basis",
            "counterfactual", "confidence",
        ],
        "properties": {
            "blind_case_id": {"type": "string", "enum": list(case_ids)},
            "preferred_direct_answer": {"type": "string", "enum": list(DIRECT_ANSWERS)},
            "probability_preferred_wrong": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_basis": {"type": "string"},
            "counterfactual": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    })


def validate_direct(payload, *, batch_id, case_ids, evidence_refs):
    _validate(payload, batch_id=batch_id, case_ids=case_ids, evidence_refs=evidence_refs,
              keys={"blind_case_id", "action", "evidence_basis", "confidence"})
    for item in payload["assessments"]:
        if item["action"] not in ACTIONS or not item["evidence_basis"].strip():
            raise ValueError("clarification_direct_value_invalid")
        _validate_probability(item["confidence"], "clarification_direct_confidence_invalid")


def validate_regret(payload, *, batch_id, case_ids, evidence_refs):
    _validate(payload, batch_id=batch_id, case_ids=case_ids, evidence_refs=evidence_refs,
              keys={"blind_case_id", "preferred_direct_answer", "probability_preferred_wrong", "evidence_basis", "counterfactual", "confidence"})
    for item in payload["assessments"]:
        if (
            item["preferred_direct_answer"] not in DIRECT_ANSWERS
            or not item["evidence_basis"].strip()
            or not item["counterfactual"].strip()
        ):
            raise ValueError("clarification_regret_value_invalid")
        _validate_probability(item["probability_preferred_wrong"], "clarification_regret_probability_invalid")
        _validate_probability(item["confidence"], "clarification_regret_confidence_invalid")


def _schema(batch_id, case_ids, item_contract):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "assessments": {
                "type": "array",
                "minItems": len(case_ids),
                "maxItems": len(case_ids),
                "items": {"type": "object", "additionalProperties": False, **item_contract},
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def _validate(payload, *, batch_id, case_ids, evidence_refs, keys):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("clarification_receipt_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("clarification_receipt_binding_invalid")
    items = payload["assessments"]
    if not isinstance(items, list) or len(items) != len(case_ids):
        raise ValueError("clarification_receipt_count_invalid")
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("clarification_receipt_item_shape_invalid")
        observed.append(item["blind_case_id"])
    if len(observed) != len(set(observed)) or set(observed) != set(case_ids):
        raise ValueError("clarification_receipt_case_binding_invalid")


def _validate_probability(value, error):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ValueError(error)
