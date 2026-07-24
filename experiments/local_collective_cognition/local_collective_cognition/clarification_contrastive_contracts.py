"""Provider contract for evidence-bound request-object selection."""

from __future__ import annotations


SELECTION_VERSION = "clarification_request_selection_v0_8"
SELECTION_TASK_KIND = "clarification_request_selection"
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NEITHER", "UNCERTAIN")


def selection_schema(batch_id, case_ids):
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
                        "explicit_selection",
                        "decisive_quote",
                        "contrastive_explanation",
                    ],
                    "properties": {
                        "blind_case_id": {"type": "string", "enum": list(case_ids)},
                        "request_object_quote": {"type": "string"},
                        "explicit_selection": {"type": "string", "enum": list(SELECTIONS)},
                        "decisive_quote": {"type": "string"},
                        "contrastive_explanation": {"type": "string"},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_selection(payload, *, batch_id, public_cases, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("clarification_selection_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("clarification_selection_binding_invalid")
    cases = {case["blind_case_id"]: case for case in public_cases}
    items = payload["assessments"]
    if not isinstance(items, list) or len(items) != len(cases):
        raise ValueError("clarification_selection_count_invalid")
    keys = {"blind_case_id", "request_object_quote", "explicit_selection", "decisive_quote", "contrastive_explanation"}
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("clarification_selection_item_shape_invalid")
        blind_id = item["blind_case_id"]
        observed.append(blind_id)
        if blind_id not in cases or item["explicit_selection"] not in SELECTIONS:
            raise ValueError("clarification_selection_value_invalid")
        if not item["request_object_quote"].strip() or not item["contrastive_explanation"].strip():
            raise ValueError("clarification_selection_text_invalid")
        prompt = cases[blind_id]["public_prompt"].casefold()
        if item["request_object_quote"].strip().casefold() not in prompt:
            raise ValueError("clarification_request_quote_unbound")
        decisive = item["decisive_quote"].strip()
        if item["explicit_selection"] in ("CANDIDATE_A", "CANDIDATE_B"):
            if not decisive or decisive.casefold() not in prompt:
                raise ValueError("clarification_decisive_quote_unbound")
        elif decisive != "NONE":
            raise ValueError("clarification_absence_quote_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(cases):
        raise ValueError("clarification_selection_case_binding_invalid")


def selection_to_category(selection):
    if selection in ("CANDIDATE_A", "CANDIDATE_B"):
        return "PROMPT_FIXED"
    if selection == "NEITHER":
        return "OPEN_RIVALS"
    return "UNCERTAIN"
