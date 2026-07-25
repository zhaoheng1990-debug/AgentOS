"""Bounded live orchestration for R4 v0.3D."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .hybrid_anchor import load_historical_anchor
from .hybrid_scoring import score_hybrid_panel
from .semantic_cases import CASES
from .semantic_prompts import SYSTEM_PROMPT, batch_prompt, single_prompt
from .semantic_schemas import ParsedSemanticReceipts, parse_semantic_receipts


def run_hybrid_live(adapter: Any, historical_raw_dir: Path) -> dict[str, Any]:
    anchor = load_historical_anchor(historical_raw_dir)
    _, batch_b = adapter.call_json(
        "batch_B",
        SYSTEM_PROMPT,
        batch_prompt("B"),
        lambda value: parse_semantic_receipts(value, CASES),
    )
    singles: dict[str, ParsedSemanticReceipts] = {}
    for index, case in enumerate(CASES):
        logical_id = f"single_{case.case_id}"
        _, parsed = adapter.call_json(
            logical_id,
            SYSTEM_PROMPT,
            single_prompt(case, index),
            lambda value, item=case: parse_semantic_receipts(value, (item,)),
        )
        singles[case.case_id] = parsed
    return score_hybrid_panel(anchor, batch_b, singles, adapter.ledger())

