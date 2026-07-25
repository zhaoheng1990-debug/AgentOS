"""Mechanical normalization for candidate Provider relation receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .contracts import RELATION_STATES
from .semantic_cases import SemanticCase


REQUIRED_KEYS = {
    "case_id",
    "relation_state",
    "evidence_refs",
    "unresolved_assumptions",
}
FORBIDDEN_KEYS = {
    "accepted",
    "action",
    "baseline_state",
    "composed_probability",
    "composition_action",
    "excluded_packet_ids",
    "final_state",
    "probability",
    "published",
    "retained",
    "selected_packet_ids",
}


@dataclass(frozen=True)
class SemanticRelationReceipt:
    case_id: str
    relation_state: str
    evidence_refs: tuple[str, ...]
    unresolved_assumptions: tuple[str, ...]
    dropped_provider_fields: tuple[str, ...]


@dataclass(frozen=True)
class ParsedSemanticReceipts:
    receipts: tuple[SemanticRelationReceipt, ...]
    root_type: str


def _items(content: str) -> tuple[list[Any], str]:
    root = json.loads(content)
    if isinstance(root, list):
        return root, "array"
    if isinstance(root, dict) and isinstance(root.get("receipts"), list):
        return root["receipts"], "object_receipts"
    if isinstance(root, dict) and "case_id" in root:
        return [root], "object_single"
    raise ValueError("root must be a receipt object, receipts object, or array")


def parse_semantic_receipts(
    content: str, expected_cases: tuple[SemanticCase, ...]
) -> ParsedSemanticReceipts:
    items, root_type = _items(content)
    expected = {case.case_id: case for case in expected_cases}
    receipts = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("semantic receipt must be an object")
        missing = REQUIRED_KEYS - set(item)
        if missing:
            raise ValueError(f"semantic receipt fields missing: {sorted(missing)}")
        forbidden = FORBIDDEN_KEYS.intersection(item)
        if forbidden:
            raise ValueError(f"forbidden semantic authority fields: {sorted(forbidden)}")
        case_id = str(item["case_id"])
        if case_id not in expected:
            raise ValueError(f"unexpected semantic case: {case_id}")
        state = str(item["relation_state"])
        if state not in RELATION_STATES:
            raise ValueError(f"unknown semantic relation state: {state}")
        evidence_refs = item["evidence_refs"]
        if (
            not isinstance(evidence_refs, list)
            or len(evidence_refs) != 2
            or set(evidence_refs) != set(expected[case_id].evidence_refs)
        ):
            raise ValueError(f"semantic evidence scope mismatch: {case_id}")
        assumptions = item["unresolved_assumptions"]
        if not isinstance(assumptions, list) or not all(
            isinstance(value, str) for value in assumptions
        ):
            raise ValueError(f"unresolved assumptions invalid: {case_id}")
        receipts.append(
            SemanticRelationReceipt(
                case_id=case_id,
                relation_state=state,
                evidence_refs=tuple(sorted(evidence_refs)),
                unresolved_assumptions=tuple(assumptions),
                dropped_provider_fields=tuple(sorted(set(item) - REQUIRED_KEYS)),
            )
        )
    if len(receipts) != len(expected) or {item.case_id for item in receipts} != set(
        expected
    ):
        raise ValueError("semantic case coverage must be exact")
    return ParsedSemanticReceipts(
        receipts=tuple(sorted(receipts, key=lambda item: item.case_id)),
        root_type=root_type,
    )
