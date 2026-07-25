"""Live Provider orchestration for R4 v0.3B."""

from __future__ import annotations

from typing import Any

from .semantic_cases import CASES
from .semantic_prompts import SYSTEM_PROMPT, batch_prompt, single_prompt
from .semantic_schemas import ParsedSemanticReceipts, parse_semantic_receipts
from .semantic_scoring import score_panel


def run_live(adapter: Any) -> dict[str, Any]:
    parsed_runs: dict[str, ParsedSemanticReceipts] = {}
    raw_contents = {}
    for replicate in ("A", "B"):
        logical_id = f"batch_{replicate}"
        content, parsed = adapter.call_json(
            logical_id,
            SYSTEM_PROMPT,
            batch_prompt(replicate),
            lambda value: parse_semantic_receipts(value, CASES),
        )
        raw_contents[logical_id] = content
        parsed_runs[logical_id] = parsed
    for index, case in enumerate(CASES):
        logical_id = f"single_{case.case_id}"
        content, parsed = adapter.call_json(
            logical_id,
            SYSTEM_PROMPT,
            single_prompt(case, index),
            lambda value, item=case: parse_semantic_receipts(value, (item,)),
        )
        raw_contents[logical_id] = content
        parsed_runs[logical_id] = parsed
    return score_panel(parsed_runs, adapter.ledger(), raw_contents)
