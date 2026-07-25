"""Bounded one-batch live orchestration for R4 v0.3E."""

from __future__ import annotations

from typing import Any

from .hard_cases import HARD_CASES
from .hard_corpus_audit import audit_hard_corpus
from .hard_prompts import SYSTEM_PROMPT, hard_batch_prompt
from .hard_scoring import score_hard_batch
from .semantic_schemas import parse_semantic_receipts


def run_hard_live(adapter: Any) -> dict[str, Any]:
    if audit_hard_corpus()["status"] != "PASS":
        raise ValueError("fresh hard corpus preflight failed")
    _, parsed = adapter.call_json(
        "fresh_hard_batch",
        SYSTEM_PROMPT,
        hard_batch_prompt(),
        lambda value: parse_semantic_receipts(value, HARD_CASES),
    )
    return score_hard_batch(parsed, adapter.ledger())

