from pathlib import Path

import pytest

from theory_first_r4_relation.hybrid_anchor import (
    EXPECTED_HASHES,
    load_historical_anchor,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "outputs/r4_provider_semantic_relation_v0_3b/raw_attempts"


def test_historical_anchor_is_hash_bound_and_exact() -> None:
    anchor = load_historical_anchor(RAW_DIR)
    assert anchor.source_hashes == EXPECTED_HASHES
    assert anchor.relation_agreement == 1.0
    assert anchor.source_files_unchanged


def test_historical_anchor_blocks_hash_mismatch(tmp_path: Path) -> None:
    for attempt in (1, 2):
        source = RAW_DIR / f"batch_A_attempt_{attempt}.json.txt"
        (tmp_path / source.name).write_bytes(source.read_bytes())
    (tmp_path / "batch_A_attempt_1.json.txt").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="source hash mismatch"):
        load_historical_anchor(tmp_path)

