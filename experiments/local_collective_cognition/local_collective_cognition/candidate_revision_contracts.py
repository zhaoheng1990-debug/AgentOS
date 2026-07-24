"""Anti-Additive contract allowing a Provider to revise its original candidate."""

from __future__ import annotations

from typing import Any


CHOICE_LABELS = ("A", "B", "C", "D")
REVISION_LABELS = (*CHOICE_LABELS, "ABSTAIN")


def validate_candidate_revision(
    result, item_id: str, candidate_id: str, evidence_refs: list[str],
) -> None:
    if (
        set(result) != {"item_id", "candidate_id", "expression", "proposed_candidate", "evidence_refs"}
        or result.get("item_id") != item_id or result.get("candidate_id") != candidate_id
        or result.get("proposed_candidate") not in REVISION_LABELS
        or not isinstance(result.get("expression"), str)
        or (result["proposed_candidate"] != "ABSTAIN" and not result["expression"].strip())
        or result.get("evidence_refs") != evidence_refs
    ):
        raise ValueError("candidate_revision_evidence_invalid")


def candidate_revision_schema(item_id: str, candidate_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["item_id", "candidate_id", "expression", "proposed_candidate", "evidence_refs"],
        "properties": {
            "item_id": {"type": "string", "enum": [item_id]},
            "candidate_id": {"type": "string", "enum": [candidate_id]},
            "expression": {"type": "string"},
            "proposed_candidate": {"type": "string", "enum": list(REVISION_LABELS)},
            "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        },
    }
