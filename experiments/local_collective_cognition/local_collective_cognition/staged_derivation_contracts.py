"""Two-stage Provider contracts for action choice and narrow arguments."""

from __future__ import annotations

from typing import Any

from .candidate_revision_contracts import CHOICE_LABELS
from .iterative_derivation_contracts import ACTIONS
from .typed_derivation_contracts import BINARY_OPERATORS, OPERATORS


def selection_schema(item_id: str, candidate_id: str) -> dict[str, Any]:
    return _schema(item_id, candidate_id, {
        "action": {"type": "string", "enum": list(ACTIONS)},
    })


def validate_selection(result, *, item_id, candidate_id, evidence_refs) -> None:
    _validate_identity(result, item_id, candidate_id, evidence_refs, {"action"})
    if result["action"] not in ACTIONS:
        raise ValueError("staged_derivation_selection_invalid")


def arguments_schema(action: str, item_id: str, candidate_id: str,
                     available_symbols: tuple[str, ...]) -> dict[str, Any]:
    if action == "APPLY":
        fields = {
            "operator": {"type": "string", "enum": list(OPERATORS)},
            "inputs": {"type": "array", "minItems": 1, "maxItems": 2,
                       "items": {"type": "string", "enum": list(available_symbols)}},
        }
    elif action == "FINALIZE":
        fields = {
            "selected_step": {"type": "string", "enum": [
                item for item in available_symbols if item.startswith("STEP_")
            ]},
            "proposed_candidate": {"type": "string", "enum": list(CHOICE_LABELS)},
        }
    else:
        raise ValueError("staged_derivation_arguments_not_required")
    return _schema(item_id, candidate_id, fields)


def validate_arguments(result, *, action, item_id, candidate_id,
                       evidence_refs, available_symbols) -> None:
    fields = {"operator", "inputs"} if action == "APPLY" else {
        "selected_step", "proposed_candidate",
    }
    _validate_identity(result, item_id, candidate_id, evidence_refs, fields)
    if action == "APPLY":
        operator, inputs = result["operator"], result["inputs"]
        arity = 2 if operator in BINARY_OPERATORS else 1
        if operator not in OPERATORS or not isinstance(inputs, list) or len(inputs) != arity:
            raise ValueError("staged_derivation_apply_arguments_invalid")
        if any(item not in available_symbols for item in inputs):
            raise ValueError("staged_derivation_input_unavailable")
    elif (result["proposed_candidate"] not in CHOICE_LABELS
          or result["selected_step"] not in available_symbols
          or not result["selected_step"].startswith("STEP_")):
        raise ValueError("staged_derivation_finalize_arguments_invalid")


def normalized_action(*, selection, arguments, evidence_refs):
    action = selection["action"]
    identity = {"item_id": selection["item_id"], "candidate_id": selection["candidate_id"]}
    if action == "APPLY":
        return {**identity, "action": action, "operator": arguments["operator"],
                "inputs": arguments["inputs"], "proposed_candidate": "PENDING",
                "evidence_refs": evidence_refs}
    if action == "FINALIZE":
        return {**identity, "action": action, "operator": "NONE",
                "inputs": [arguments["selected_step"]],
                "proposed_candidate": arguments["proposed_candidate"],
                "evidence_refs": evidence_refs}
    return {**identity, "action": action, "operator": "NONE", "inputs": [],
            "proposed_candidate": "ABSTAIN", "evidence_refs": evidence_refs}


def _schema(item_id, candidate_id, fields):
    properties = {"item_id": {"type": "string", "enum": [item_id]},
                  "candidate_id": {"type": "string", "enum": [candidate_id]},
                  **fields,
                  "evidence_refs": {"type": "array", "minItems": 1,
                                    "items": {"type": "string"}}}
    return {"type": "object", "required": list(properties), "properties": properties}


def _validate_identity(result, item_id, candidate_id, evidence_refs, fields):
    expected = {"item_id", "candidate_id", "evidence_refs", *fields}
    if (set(result) != expected or result.get("item_id") != item_id
            or result.get("candidate_id") != candidate_id
            or result.get("evidence_refs") != evidence_refs):
        raise ValueError("staged_derivation_contract_invalid")
