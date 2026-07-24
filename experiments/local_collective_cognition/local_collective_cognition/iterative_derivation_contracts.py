"""One-action Provider contract for bounded iterative derivation sessions."""

from __future__ import annotations

from typing import Any

from .candidate_revision_contracts import CHOICE_LABELS
from .typed_derivation_contracts import BINARY_OPERATORS, OPERATORS


ACTIONS = ("APPLY", "FINALIZE", "ABSTAIN")
PROPOSALS = (*CHOICE_LABELS, "PENDING", "ABSTAIN")


def validate_iterative_action(
    result, *, item_id: str, candidate_id: str, evidence_refs: list[str],
    available_symbols: tuple[str, ...],
) -> None:
    if (
        set(result) != {"item_id", "candidate_id", "action", "operator", "inputs",
                        "proposed_candidate", "evidence_refs"}
        or result.get("item_id") != item_id or result.get("candidate_id") != candidate_id
        or result.get("action") not in ACTIONS or result.get("operator") not in (*OPERATORS, "NONE")
        or result.get("proposed_candidate") not in PROPOSALS
        or not isinstance(result.get("inputs"), list)
        or result.get("evidence_refs") != evidence_refs
    ):
        raise ValueError("iterative_derivation_action_invalid")
    action, operator, inputs = result["action"], result["operator"], result["inputs"]
    if action == "APPLY":
        arity = 2 if operator in BINARY_OPERATORS else 1
        if operator == "NONE" or result["proposed_candidate"] != "PENDING" or len(inputs) != arity:
            raise ValueError("iterative_derivation_apply_invalid")
    elif action == "FINALIZE":
        if (operator != "NONE" or result["proposed_candidate"] not in CHOICE_LABELS
                or len(inputs) != 1 or not inputs[0].startswith("STEP_")):
            raise ValueError("iterative_derivation_finalize_invalid")
    elif operator != "NONE" or result["proposed_candidate"] != "ABSTAIN" or inputs:
        raise ValueError("iterative_derivation_abstain_invalid")
    if any(value not in available_symbols for value in inputs):
        raise ValueError("iterative_derivation_input_unavailable")


def iterative_action_schema(
    item_id: str, candidate_id: str, available_symbols: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["item_id", "candidate_id", "action", "operator", "inputs",
                     "proposed_candidate", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "candidate_id": {"type": "string", "enum": [candidate_id]},
            "action": {"type": "string", "enum": list(ACTIONS)},
            "operator": {"type": "string", "enum": [*OPERATORS, "NONE"]},
            "inputs": {"type": "array", "maxItems": 2,
                       "items": {"type": "string", "enum": list(available_symbols)}},
            "proposed_candidate": {"type": "string", "enum": list(PROPOSALS)},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }
