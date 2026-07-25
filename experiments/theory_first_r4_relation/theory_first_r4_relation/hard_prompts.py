"""Frozen single-batch prompt for R4 v0.3E."""

from __future__ import annotations

import json

from .contracts import RELATION_STATES
from .hard_cases import HARD_CASES
from .semantic_prompts import STATE_DEFINITIONS, SYSTEM_PROMPT


CASE_ORDER = (
    "R43E-01",
    "R43E-04",
    "R43E-07",
    "R43E-10",
    "R43E-13",
    "R43E-16",
    "R43E-02",
    "R43E-05",
    "R43E-08",
    "R43E-11",
    "R43E-14",
    "R43E-17",
    "R43E-03",
    "R43E-06",
    "R43E-09",
    "R43E-12",
    "R43E-15",
    "R43E-18",
)


def hard_batch_prompt() -> str:
    by_id = {case.case_id: case for case in HARD_CASES}
    payload = {
        "relation_definitions": [
            {
                "relation_state": state,
                "definition": STATE_DEFINITIONS[state],
            }
            for state in RELATION_STATES
        ],
        "required_receipt_schema": {
            "case_id": "R43E-01",
            "relation_state": "ONE_ALLOWED_RELATION_STATE",
            "evidence_refs": [
                "descriptor://case/left",
                "descriptor://case/right",
            ],
            "unresolved_assumptions": [],
        },
        "cases": [by_id[case_id].public_dict() for case_id in CASE_ORDER],
    }
    return (
        "Classify every case using exactly one defined relation state. Infer the "
        "relation from source lineage, observation identity, set intersection, "
        "and target scope rather than matching isolated words. Cite exactly the "
        "two descriptor evidence_refs from that case. Put materially missing "
        "facts only in unresolved_assumptions. Return a JSON object containing "
        "one receipt collection.\n"
        + json.dumps(payload, ensure_ascii=True, sort_keys=True)
    )


__all__ = ["SYSTEM_PROMPT", "hard_batch_prompt"]

