"""Provider contracts for replayable current-case argument evidence."""

from __future__ import annotations

from typing import Any


def validate_argument_evidence(result, item_id: str, candidate_id: str, evidence_refs: list[str]) -> None:
    facts = result.get("derived_facts")
    valid_facts = isinstance(facts, list) and 1 <= len(facts) <= 4
    if valid_facts:
        ids = []
        for fact in facts:
            if not isinstance(fact, dict) or set(fact) != {"fact_id", "expression", "claimed_result"}:
                valid_facts = False
                break
            ids.append(fact["fact_id"])
            if not all(isinstance(fact[key], str) and fact[key].strip() for key in fact):
                valid_facts = False
                break
        valid_facts = valid_facts and len(ids) == len(set(ids))
    if (
        result.get("item_id") != item_id or result.get("candidate_id") != candidate_id
        or not str(result.get("argument", "")).strip() or not valid_facts
        or not str(result.get("conclusion_value", "")).strip()
        or not str(result.get("uncertainty", "")).strip()
        or result.get("evidence_refs") != evidence_refs
    ):
        raise ValueError("argument_evidence_invalid")


def argument_evidence_schema(item_id: str, candidate_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "item_id", "candidate_id", "argument", "derived_facts",
            "conclusion_value", "uncertainty", "evidence_refs",
        ],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "candidate_id": {"type": "string", "enum": [candidate_id]},
            "argument": {"type": "string", "minLength": 1},
            "derived_facts": {
                "type": "array", "minItems": 1,
                "items": {"type": "object"},
            },
            "conclusion_value": {"type": "string", "minLength": 1},
            "uncertainty": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }
