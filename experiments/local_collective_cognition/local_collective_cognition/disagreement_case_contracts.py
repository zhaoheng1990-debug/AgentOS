"""Structured schemas and mechanical validation for disagreement cases."""

from __future__ import annotations

from typing import Any


def validate_argument(result, item_id: str, candidate_id: str, evidence_refs: list[str]) -> None:
    if (
        result.get("item_id") != item_id or result.get("candidate_id") != candidate_id
        or not str(result.get("argument", "")).strip()
        or result.get("evidence_refs") != evidence_refs
    ):
        raise ValueError("disagreement_case_argument_invalid")


def validate_judgment(result, item_id: str, evidence_refs: list[str]) -> None:
    confidence = result.get("confidence")
    if (
        result.get("item_id") != item_id
        or result.get("selected_candidate") not in {"CANDIDATE_1", "CANDIDATE_2", "ABSTAIN"}
        or result.get("adjudicability") not in {"ADJUDICABLE", "AMBIGUOUS"}
        or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
        or not 0.0 <= float(confidence) <= 1.0
        or not str(result.get("decisive_reason", "")).strip()
        or result.get("evidence_refs") != evidence_refs
    ):
        raise ValueError("disagreement_case_judgment_invalid")


def argument_schema(item_id: str, candidate_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["item_id", "candidate_id", "argument", "uncertainty", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "candidate_id": {"type": "string", "enum": [candidate_id]},
            "argument": {"type": "string", "minLength": 1},
            "uncertainty": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }


def judgment_schema(item_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["item_id", "selected_candidate", "adjudicability", "confidence", "decisive_reason", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "selected_candidate": {"type": "string", "enum": ["CANDIDATE_1", "CANDIDATE_2", "ABSTAIN"]},
            "adjudicability": {"type": "string", "enum": ["ADJUDICABLE", "AMBIGUOUS"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "decisive_reason": {"type": "string", "minLength": 1},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }
