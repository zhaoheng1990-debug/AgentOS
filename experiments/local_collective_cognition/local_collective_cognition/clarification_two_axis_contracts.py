"""Orthogonal object-selection and assessment-status receipt contract."""

from __future__ import annotations


TWO_AXIS_VERSION = "clarification_two_axis_receipt_v0_9"
TWO_AXIS_TASK_KIND = "clarification_two_axis_selection"
OBJECT_SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE")
ASSESSMENT_STATUSES = ("RESOLVED", "UNRESOLVED")


def two_axis_schema(batch_id, case_ids):
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
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "blind_case_id",
                        "request_object_quote",
                        "object_selection",
                        "assessment_status",
                        "decisive_quote",
                        "selection_basis",
                        "status_basis",
                    ],
                    "properties": {
                        "blind_case_id": {"type": "string", "enum": list(case_ids)},
                        "request_object_quote": {"type": "string"},
                        "object_selection": {"type": "string", "enum": list(OBJECT_SELECTIONS)},
                        "assessment_status": {"type": "string", "enum": list(ASSESSMENT_STATUSES)},
                        "decisive_quote": {"type": "string"},
                        "selection_basis": {"type": "string"},
                        "status_basis": {"type": "string"},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_two_axis(payload, *, batch_id, public_cases, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("clarification_two_axis_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("clarification_two_axis_binding_invalid")
    cases = {case["blind_case_id"]: case for case in public_cases}
    items = payload["assessments"]
    if not isinstance(items, list) or len(items) != len(cases):
        raise ValueError("clarification_two_axis_count_invalid")
    keys = {"blind_case_id", "request_object_quote", "object_selection", "assessment_status", "decisive_quote", "selection_basis", "status_basis"}
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("clarification_two_axis_item_shape_invalid")
        blind_id = item["blind_case_id"]
        observed.append(blind_id)
        if blind_id not in cases or item["object_selection"] not in OBJECT_SELECTIONS or item["assessment_status"] not in ASSESSMENT_STATUSES:
            raise ValueError("clarification_two_axis_value_invalid")
        if not all(item[key].strip() for key in ("request_object_quote", "selection_basis", "status_basis")):
            raise ValueError("clarification_two_axis_text_invalid")
        prompt = cases[blind_id]["public_prompt"].casefold()
        if item["request_object_quote"].strip().casefold() not in prompt:
            raise ValueError("clarification_two_axis_request_quote_unbound")
        decisive = item["decisive_quote"].strip()
        if item["object_selection"] == "NONE":
            if decisive != "NONE":
                raise ValueError("clarification_two_axis_none_quote_invalid")
        elif not decisive or decisive.casefold() not in prompt:
            raise ValueError("clarification_two_axis_decisive_quote_unbound")
    if len(observed) != len(set(observed)) or set(observed) != set(cases):
        raise ValueError("clarification_two_axis_case_binding_invalid")


def derive_category(object_selection, assessment_status):
    if assessment_status == "UNRESOLVED":
        return "UNCERTAIN"
    if object_selection == "NONE":
        return "OPEN_RIVALS"
    return "PROMPT_FIXED"
