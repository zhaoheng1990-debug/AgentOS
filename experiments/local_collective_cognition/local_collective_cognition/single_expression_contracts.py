"""Anti-Additive Provider contract for one candidate-bound expression."""

from __future__ import annotations

from typing import Any


def validate_single_expression(result, item_id: str, candidate_id: str, evidence_refs: list[str]) -> None:
    if (
        set(result) != {"item_id", "candidate_id", "expression", "evidence_refs"}
        or result.get("item_id") != item_id or result.get("candidate_id") != candidate_id
        or not isinstance(result.get("expression"), str) or not result["expression"].strip()
        or result.get("evidence_refs") != evidence_refs
    ):
        raise ValueError("single_expression_evidence_invalid")


def single_expression_schema(item_id: str, candidate_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["item_id", "candidate_id", "expression", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "candidate_id": {"type": "string", "enum": [candidate_id]},
            "expression": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }
