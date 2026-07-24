"""Low-entropy Provider contract for a typed candidate derivation plan."""

from __future__ import annotations

from typing import Any

from .candidate_revision_contracts import REVISION_LABELS


BINARY_OPERATORS = ("ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "MODULO")
UNARY_OPERATORS = ("SWAP_HALVES", "REVERSE_PAIRS")
OPERATORS = (*BINARY_OPERATORS, *UNARY_OPERATORS)


def validate_typed_derivation(
    result, *, item_id: str, candidate_id: str, evidence_refs: list[str],
    scaffold: dict[str, str],
) -> None:
    if (
        set(result) != {"item_id", "candidate_id", "proposed_candidate", "steps",
                        "result_step", "evidence_refs"}
        or result.get("item_id") != item_id or result.get("candidate_id") != candidate_id
        or result.get("proposed_candidate") not in REVISION_LABELS
        or result.get("evidence_refs") != evidence_refs or not isinstance(result.get("steps"), list)
    ):
        raise ValueError("typed_derivation_invalid")
    if result["proposed_candidate"] == "ABSTAIN":
        if result["steps"] or result.get("result_step") != "NONE":
            raise ValueError("typed_derivation_retraction_invalid")
        return
    if not 1 <= len(result["steps"]) <= 8:
        raise ValueError("typed_derivation_step_count_invalid")
    available = set(scaffold)
    for index, step in enumerate(result["steps"], 1):
        step_id = f"STEP_{index}"
        if (
            not isinstance(step, dict) or set(step) != {"step_id", "operator", "inputs"}
            or step.get("step_id") != step_id or step.get("operator") not in OPERATORS
            or not isinstance(step.get("inputs"), list)
            or len(step["inputs"]) != (2 if step["operator"] in BINARY_OPERATORS else 1)
            or any(value not in available for value in step["inputs"])
        ):
            raise ValueError("typed_derivation_step_invalid")
        available.add(step_id)
    if result.get("result_step") != f"STEP_{len(result['steps'])}":
        raise ValueError("typed_derivation_result_step_invalid")


def typed_derivation_schema(item_id: str, candidate_id: str, scaffold: dict[str, str]) -> dict[str, Any]:
    symbols = [*scaffold, *(f"STEP_{index}" for index in range(1, 9))]
    return {
        "type": "object",
        "required": ["item_id", "candidate_id", "proposed_candidate", "steps",
                     "result_step", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "candidate_id": {"type": "string", "enum": [candidate_id]},
            "proposed_candidate": {"type": "string", "enum": list(REVISION_LABELS)},
            "steps": {"type": "array", "maxItems": 8, "items": {"type": "object",
                "required": ["step_id", "operator", "inputs"], "properties": {
                    "step_id": {"type": "string"},
                    "operator": {"type": "string", "enum": list(OPERATORS)},
                    "inputs": {"type": "array", "minItems": 1, "maxItems": 2,
                               "items": {"type": "string", "enum": symbols}},
                }}},
            "result_step": {"type": "string"},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }
