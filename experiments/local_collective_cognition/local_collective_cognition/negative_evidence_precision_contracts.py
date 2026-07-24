"""Contracts for independent confirmation of a live-ambiguity veto."""

from __future__ import annotations


CONFIRMATION_VERSION = "negative_evidence_veto_confirmation_v0_3"
CONFIRMATION_TASK_KIND = "negative_evidence_live_veto_confirmation"
CONFIRMATION_STATES = ("CONFIRM_VETO", "REJECT_VETO", "UNCERTAIN")
OBJECT_STATES = (
    "EXPLICITLY_FIXED",
    "GENUINELY_OPEN",
    "RIVAL_INVALID_OR_EQUIVALENT",
    "UNCERTAIN",
)
QUESTION_STATES = ("WOULD_DISCRIMINATE", "WOULD_NOT_DISCRIMINATE", "UNCERTAIN")


def confirmation_schema(batch_id, candidate_ids):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["batch_id", "assessments", "evidence_refs"],
        "properties": {
            "batch_id": {"type": "string", "enum": [batch_id]},
            "assessments": {
                "type": "array",
                "minItems": len(candidate_ids),
                "maxItems": len(candidate_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "blind_candidate_id", "state", "requested_object_status",
                        "question_function", "explicit_disambiguator_quote",
                        "evidence_basis", "confidence",
                    ],
                    "properties": {
                        "blind_candidate_id": {
                            "type": "string", "enum": list(candidate_ids),
                        },
                        "state": {"type": "string", "enum": list(CONFIRMATION_STATES)},
                        "requested_object_status": {
                            "type": "string", "enum": list(OBJECT_STATES),
                        },
                        "question_function": {
                            "type": "string", "enum": list(QUESTION_STATES),
                        },
                        "explicit_disambiguator_quote": {"type": "string"},
                        "evidence_basis": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_confirmation(payload, *, batch_id, candidate_ids, evidence_refs):
    required = {"batch_id", "assessments", "evidence_refs"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("negative_evidence_confirmation_shape_invalid")
    if (
        payload["batch_id"] != batch_id
        or payload["evidence_refs"] != list(evidence_refs)
    ):
        raise ValueError("negative_evidence_confirmation_binding_invalid")
    assessments = payload["assessments"]
    if not isinstance(assessments, list) or len(assessments) != len(candidate_ids):
        raise ValueError("negative_evidence_confirmation_count_invalid")
    item_keys = {
        "blind_candidate_id", "state", "requested_object_status",
        "question_function", "explicit_disambiguator_quote", "evidence_basis",
        "confidence",
    }
    observed = []
    for item in assessments:
        if not isinstance(item, dict) or set(item) != item_keys:
            raise ValueError("negative_evidence_confirmation_item_shape_invalid")
        observed.append(item["blind_candidate_id"])
        state = item["state"]
        object_state = item["requested_object_status"]
        question_state = item["question_function"]
        if (
            state not in CONFIRMATION_STATES
            or object_state not in OBJECT_STATES
            or question_state not in QUESTION_STATES
            or not item["evidence_basis"].strip()
        ):
            raise ValueError("negative_evidence_confirmation_value_invalid")
        confidence = item["confidence"]
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("negative_evidence_confirmation_confidence_invalid")
        if state == "REJECT_VETO" and not (
            object_state == "GENUINELY_OPEN"
            and question_state == "WOULD_DISCRIMINATE"
            and not item["explicit_disambiguator_quote"].strip()
        ):
            raise ValueError("negative_evidence_confirmation_rejection_inconsistent")
        if state == "CONFIRM_VETO" and not (
            object_state in {"EXPLICITLY_FIXED", "RIVAL_INVALID_OR_EQUIVALENT"}
            or question_state == "WOULD_NOT_DISCRIMINATE"
        ):
            raise ValueError("negative_evidence_confirmation_veto_inconsistent")
        if (
            object_state == "EXPLICITLY_FIXED"
            and not item["explicit_disambiguator_quote"].strip()
        ):
            raise ValueError("negative_evidence_confirmation_quote_required")
    if len(observed) != len(set(observed)) or set(observed) != set(candidate_ids):
        raise ValueError("negative_evidence_confirmation_candidate_binding_invalid")
