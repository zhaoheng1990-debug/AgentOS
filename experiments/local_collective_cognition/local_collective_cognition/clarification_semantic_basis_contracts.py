"""Four-class semantic-basis receipt contract for clarification v0.11."""

from __future__ import annotations


SEMANTIC_BASIS_VERSION = "clarification_semantic_basis_v0_11"
SEMANTIC_BASIS_TASK_KIND = "clarification_semantic_basis"
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE")
SELECTION_BASES = (
    "LEXICAL_EXACT",
    "COMPOSITIONAL_ENTAILMENT",
    "PRAGMATIC_DEFAULT",
    "NO_PREFERENCE",
)
HARD_SELECTION_BASES = frozenset(("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT"))
SOFT_SELECTION_BASES = frozenset(("PRAGMATIC_DEFAULT", "NO_PREFERENCE"))


def semantic_basis_schema(batch_id, case_ids):
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
                        "selected_object",
                        "selection_basis",
                        "pragmatic_preference",
                        "axis_assessment_complete",
                        "entailment_evidence_quote",
                        "entailment_explanation",
                        "preference_basis",
                        "completeness_basis",
                    ],
                    "properties": {
                        "blind_case_id": {"type": "string", "enum": list(case_ids)},
                        "request_object_quote": {"type": "string"},
                        "selected_object": {"type": "string", "enum": list(SELECTIONS)},
                        "selection_basis": {"type": "string", "enum": list(SELECTION_BASES)},
                        "pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
                        "axis_assessment_complete": {"type": "boolean"},
                        "entailment_evidence_quote": {"type": "string"},
                        "entailment_explanation": {"type": "string"},
                        "preference_basis": {"type": "string"},
                        "completeness_basis": {"type": "string"},
                    },
                },
            },
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def validate_semantic_basis(payload, *, batch_id, public_cases, evidence_refs):
    if not isinstance(payload, dict) or set(payload) != {"batch_id", "assessments", "evidence_refs"}:
        raise ValueError("clarification_semantic_basis_shape_invalid")
    if payload["batch_id"] != batch_id or payload["evidence_refs"] != list(evidence_refs):
        raise ValueError("clarification_semantic_basis_binding_invalid")
    cases = {case["blind_case_id"]: case for case in public_cases}
    items = payload["assessments"]
    if not isinstance(items, list) or len(items) != len(cases):
        raise ValueError("clarification_semantic_basis_count_invalid")
    keys = {
        "blind_case_id", "request_object_quote", "selected_object", "selection_basis",
        "pragmatic_preference", "axis_assessment_complete", "entailment_evidence_quote",
        "entailment_explanation", "preference_basis", "completeness_basis",
    }
    observed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError("clarification_semantic_basis_item_shape_invalid")
        blind_id = item["blind_case_id"]
        observed.append(blind_id)
        if blind_id not in cases or item["selected_object"] not in SELECTIONS or item["pragmatic_preference"] not in SELECTIONS or item["selection_basis"] not in SELECTION_BASES or not isinstance(item["axis_assessment_complete"], bool):
            raise ValueError("clarification_semantic_basis_value_invalid")
        if not all(isinstance(item[key], str) and item[key].strip() for key in ("request_object_quote", "entailment_explanation", "preference_basis", "completeness_basis")):
            raise ValueError("clarification_semantic_basis_text_invalid")
        prompt = cases[blind_id]["public_prompt"].casefold()
        if item["request_object_quote"].strip().casefold() not in prompt:
            raise ValueError("clarification_semantic_basis_request_quote_unbound")
        evidence_quote = item["entailment_evidence_quote"].strip()
        if item["selection_basis"] in HARD_SELECTION_BASES:
            if item["selected_object"] == "NONE" or not evidence_quote or evidence_quote.casefold() not in prompt:
                raise ValueError("clarification_semantic_basis_hard_evidence_invalid")
        elif evidence_quote != "NONE":
            raise ValueError("clarification_semantic_basis_soft_evidence_invalid")
        if item["selection_basis"] == "NO_PREFERENCE" and item["pragmatic_preference"] != "NONE":
            raise ValueError("clarification_semantic_basis_no_preference_invalid")
    if len(observed) != len(set(observed)) or set(observed) != set(cases):
        raise ValueError("clarification_semantic_basis_case_binding_invalid")


def derive_semantic_basis_decision(selected_object, selection_basis, axis_assessment_complete):
    if not axis_assessment_complete:
        return "UNCERTAIN", "NONE", False
    if selection_basis in HARD_SELECTION_BASES:
        if selected_object in ("CANDIDATE_A", "CANDIDATE_B"):
            return "PROMPT_FIXED", selected_object, False
        return "UNCERTAIN", "NONE", False
    return "OPEN_RIVALS", "NONE", selected_object in ("CANDIDATE_A", "CANDIDATE_B")
