import json
from pathlib import Path

from theory_first_r4_relation.envelope_cli import run
from theory_first_r4_relation.envelope_evaluation import evaluate


REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "outputs/r4_provider_semantic_relation_v0_3b/raw_attempts"


def test_v03c_all_frozen_gates_pass() -> None:
    result = evaluate(RAW_DIR)
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == 15
    assert result["gate_count"] == 15
    assert result["provider_calls"] == 0


def test_v03c_two_runs_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(first, RAW_DIR)
    run(second, RAW_DIR)
    for name in ("result.json", "hash_inventory.json", "closure.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        json.loads((first / name).read_text(encoding="utf-8"))

