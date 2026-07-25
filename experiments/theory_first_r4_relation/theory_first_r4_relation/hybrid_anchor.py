"""Immutable historical Batch A binding for R4 v0.3D."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .semantic_cases import CASES
from .semantic_schemas import ParsedSemanticReceipts, parse_semantic_receipts


EXPECTED_HASHES = (
    "7f7e5c2beb2270577dfdcbfa6fc0ee04b5a0fa0ac9520dfcd6cff94d7f25cb94",
    "706fef18308dc37bfba3312824983566e748e271ae6ab23a42f8c333f4223236",
)


@dataclass(frozen=True)
class HistoricalBatchAnchor:
    primary: ParsedSemanticReceipts
    witness: ParsedSemanticReceipts
    source_hashes: tuple[str, str]
    relation_agreement: float
    source_files_unchanged: bool


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _states(parsed: ParsedSemanticReceipts) -> dict[str, str]:
    return {receipt.case_id: receipt.relation_state for receipt in parsed.receipts}


def load_historical_anchor(raw_dir: Path) -> HistoricalBatchAnchor:
    paths = tuple(
        raw_dir / f"batch_A_attempt_{attempt}.json.txt" for attempt in (1, 2)
    )
    before = tuple(_sha(path) for path in paths)
    if before != EXPECTED_HASHES:
        raise ValueError("historical Batch A source hash mismatch")
    parsed = tuple(
        parse_semantic_receipts(path.read_text(encoding="utf-8"), CASES)
        for path in paths
    )
    primary_states = _states(parsed[0])
    witness_states = _states(parsed[1])
    agreement = sum(
        primary_states[case.case_id] == witness_states[case.case_id]
        for case in CASES
    ) / len(CASES)
    if agreement != 1.0:
        raise ValueError("historical Batch A attempts do not agree 12/12")
    after = tuple(_sha(path) for path in paths)
    return HistoricalBatchAnchor(
        primary=parsed[0],
        witness=parsed[1],
        source_hashes=before,
        relation_agreement=agreement,
        source_files_unchanged=before == after,
    )

