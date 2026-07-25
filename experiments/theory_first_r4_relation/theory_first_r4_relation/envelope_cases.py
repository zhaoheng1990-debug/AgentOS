"""Frozen adversarial envelope fixtures for R4 v0.3C."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .semantic_schemas import REQUIRED_KEYS


@dataclass(frozen=True)
class EnvelopeCase:
    case_id: str
    root: Any
    should_accept: bool
    expected_root_type: str | None = None
    expected_source_key: str | None = None
    expected_metadata_fields: tuple[str, ...] = ()


ITEM = {
    "case_id": "SHAPE-01",
    "relation_state": "UNRESOLVED",
    "evidence_refs": ["shape://a", "shape://b"],
    "unresolved_assumptions": [],
}


ACCEPTED_CASES = (
    EnvelopeCase("A1_ROOT_ARRAY", [ITEM], True, "root_array"),
    EnvelopeCase("A2_DIRECT_ITEM", ITEM, True, "direct_item"),
    EnvelopeCase(
        "A3_RECEIPTS_WRAPPER",
        {"receipts": [ITEM]},
        True,
        "object_collection",
        "receipts",
    ),
    EnvelopeCase(
        "A4_CASES_WRAPPER",
        {"cases": [ITEM]},
        True,
        "object_collection",
        "cases",
    ),
    EnvelopeCase(
        "A5_UNSEEN_KEY_WITH_SCALAR_METADATA",
        {"payload": [ITEM], "request_id": "req-1", "attempt": 1},
        True,
        "object_collection",
        "payload",
        ("attempt", "request_id"),
    ),
)


REJECTED_CASES = (
    EnvelopeCase("R1_SCALAR_ROOT", "receipt", False),
    EnvelopeCase("R2_EMPTY_ROOT_ARRAY", [], False),
    EnvelopeCase("R3_EMPTY_WRAPPED_ARRAY", {"items": []}, False),
    EnvelopeCase("R4_NO_COLLECTION", {"status": "ok"}, False),
    EnvelopeCase("R5_NONOBJECT_ITEMS", {"items": ["bad"]}, False),
    EnvelopeCase(
        "R6_HETEROGENEOUS_ITEMS",
        {"items": [ITEM, {"case_id": "incomplete"}]},
        False,
    ),
    EnvelopeCase(
        "R7_TWO_LIST_FIELDS",
        {"first": [ITEM], "second": [ITEM]},
        False,
    ),
    EnvelopeCase(
        "R8_LIST_METADATA",
        {"items": [ITEM], "warnings": []},
        False,
    ),
    EnvelopeCase(
        "R9_NESTED_OBJECT_METADATA",
        {"items": [ITEM], "metadata": {"attempt": 1}},
        False,
    ),
)


def required_keys() -> frozenset[str]:
    return frozenset(REQUIRED_KEYS)

