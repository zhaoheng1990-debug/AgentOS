"""Three-axis explicit-selection warrant receipt contract."""

from __future__ import annotations


WARRANT_VERSION = "clarification_selection_warrant_v0_10"
WARRANT_TASK_KIND = "clarification_selection_warrant"
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE")
STATUSES = ("RESOLVED", "UNRESOLVED")
WARRANT_TYPES = (
    "EXACT_OBJECT_MENTION",
    "EXPLICIT_DEFINITION",
    "EXPLICIT_OPERATION",
    "DEFAULT_COMPATIBILITY",
    "NO_EXPLICIT_WARRANT",
)
HARD_WARRANT_TYPES = frozenset(("EXACT_OBJECT_MENTION", "EXPLICIT_DEFINITION", "EXPLICIT_OPERATION"))


def warrant_schema(batch_id, case_ids):
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
                        "pragmatic_preference",
                        "assessment_status",
                        "warrant_type",
                        "warrant_quote",
                        "preference_basis",
                        "status_basis",
                    ],
                    "properties": {
                        "blind_case_id": {"type": "string", "enum": list(case_ids)},
                        "request_object_quote": {"type": "string"},
                        "explicit_selection": {"type": "string", "enum": list(SELECTIONS)},
                        "pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
                        "assessment_status": {"type": "string", "enum": list(STATUSES)},
                        "warrant_type": {"type": "string", "enum": list(WARRANT_TYPES)},
                        "warrant_quote": {"type": "string"},
                        "preference_basis": {"type": "string"},
                        "status_basis": {"type": "string"},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_warrant(payload, *, batch_id, public_cases, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("clarification_warrant_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("clarification_warrant_binding_invalid")
    cases = {case["blind_case_id"]: case for case in public_cases}
    items = payload["assessments"]
    if not isinstance(items, list) or len(items) != len(cases):
        raise ValueError("clarification_warrant_count_invalid")
    keys = {"blind_case_id", "request_object_quote", "explicit_selection", "pragmatic_preference", "assessment_status", "warrant_type", "warrant_quote", "preference_basis", "status_basis"}
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("clarification_warrant_item_shape_invalid")
        blind_id = item["blind_case_id"]
        observed.append(blind_id)
        if blind_id not in cases or item["explicit_selection"] not in SELECTIONS or item["pragmatic_preference"] not in SELECTIONS or item["assessment_status"] not in STATUSES or item["warrant_type"] not in WARRANT_TYPES:
            raise ValueError("clarification_warrant_value_invalid")
        if not all(item[key].strip() for key in ("request_object_quote", "preference_basis", "status_basis")):
            raise ValueError("clarification_warrant_text_invalid")
        prompt = cases[blind_id]["public_prompt"].casefold()
        if item["request_object_quote"].strip().casefold() not in prompt:
            raise ValueError("clarification_warrant_request_quote_unbound")
        warrant_quote = item["warrant_quote"].strip()
        if item["warrant_type"] in HARD_WARRANT_TYPES:
            if not warrant_quote or warrant_quote.casefold() not in prompt:
                raise ValueError("clarification_warrant_quote_unbound")
        elif warrant_quote != "NONE":
            raise ValueError("clarification_soft_warrant_quote_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(cases):
        raise ValueError("clarification_warrant_case_binding_invalid")


def derive_warrant_decision(explicit_selection, assessment_status, warrant_type):
    if assessment_status == "UNRESOLVED":
        return "UNCERTAIN", "NONE", False
    if warrant_type in HARD_WARRANT_TYPES:
        if explicit_selection in ("CANDIDATE_A", "CANDIDATE_B"):
            return "PROMPT_FIXED", explicit_selection, False
        return "UNCERTAIN", "NONE", False
    return "OPEN_RIVALS", "NONE", explicit_selection in ("CANDIDATE_A", "CANDIDATE_B")
