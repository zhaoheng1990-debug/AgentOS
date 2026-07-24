"""Structured semantic subjudgments for live-ambiguity auditing."""

from __future__ import annotations


STRUCTURED_LIVE_VERSION = "structured_live_ambiguity_receipt_v0_4"
STRUCTURED_LIVE_TASK_KIND = "structured_live_ambiguity_audit"
OBJECT_STATES = ("GENUINELY_OPEN", "EXPLICITLY_FIXED", "UNCERTAIN")
RIVAL_RELATIONS = (
    "BOTH_VALID_DISTINCT", "RIVAL_A_INVALID", "RIVAL_B_INVALID",
    "EQUIVALENT", "UNCERTAIN",
)
QUESTION_STATES = ("WOULD_DISCRIMINATE", "WOULD_NOT_DISCRIMINATE", "UNCERTAIN")


def structured_live_schema(batch_id, candidate_ids):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "assessments": {
                "type": "array", "minItems": len(candidate_ids),
                "maxItems": len(candidate_ids),
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "blind_candidate_id", "requested_object_status",
                        "rival_relation", "question_function",
                        "explicit_disambiguator_quote", "evidence_basis", "confidence",
                    ],
                    "properties": {
                        "blind_candidate_id": {"type": "string", "enum": list(candidate_ids)},
                        "requested_object_status": {"type": "string", "enum": list(OBJECT_STATES)},
                        "rival_relation": {"type": "string", "enum": list(RIVAL_RELATIONS)},
                        "question_function": {"type": "string", "enum": list(QUESTION_STATES)},
                        "explicit_disambiguator_quote": {"type": "string"},
                        "evidence_basis": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_structured_live(payload, *, batch_id, candidate_ids, evidence_refs):
    required = {"batch_id", "assessments", "evidence_refs"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("structured_live_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("structured_live_binding_invalid")
    assessments = payload["assessments"]
    if not isinstance(assessments, list) or len(assessments) != len(candidate_ids):
        raise ValueError("structured_live_count_invalid")
    keys = {
        "blind_candidate_id", "requested_object_status", "rival_relation",
        "question_function", "explicit_disambiguator_quote", "evidence_basis",
        "confidence",
    }
    observed = []
    for item in assessments:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("structured_live_item_shape_invalid")
        observed.append(item["blind_candidate_id"])
        if (
            item["requested_object_status"] not in OBJECT_STATES
            or item["rival_relation"] not in RIVAL_RELATIONS
            or item["question_function"] not in QUESTION_STATES
            or not item["evidence_basis"].strip()
        ):
            raise ValueError("structured_live_value_invalid")
        confidence = item["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("structured_live_confidence_invalid")
        if item["requested_object_status"] == "EXPLICITLY_FIXED" and not item["explicit_disambiguator_quote"].strip():
            raise ValueError("structured_live_quote_required")
        if item["requested_object_status"] == "GENUINELY_OPEN" and item["explicit_disambiguator_quote"].strip():
            raise ValueError("structured_live_open_quote_forbidden")
    if len(observed) != len(set(observed)) or set(observed) != set(candidate_ids):
        raise ValueError("structured_live_candidate_binding_invalid")


def derive_structured_state(assessment):
    object_state = assessment["requested_object_status"]
    relation = assessment["rival_relation"]
    question = assessment["question_function"]
    if (
        object_state == "GENUINELY_OPEN"
        and relation == "BOTH_VALID_DISTINCT"
        and question == "WOULD_DISCRIMINATE"
    ):
        return "PASS"
    if (
        object_state == "EXPLICITLY_FIXED"
        or relation in {"RIVAL_A_INVALID", "RIVAL_B_INVALID", "EQUIVALENT"}
        or question == "WOULD_NOT_DISCRIMINATE"
    ):
        return "VETO"
    return "UNCERTAIN"
