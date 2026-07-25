import json
from pathlib import Path

from theory_first_r4_relation.transform_cli import run
from theory_first_r4_relation.transform_evaluation import evaluate_transform_grid


def test_transform_grid_passes_all_frozen_gates() -> None:
    result = evaluate_transform_grid()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == 14
    assert result["gate_count"] == 14
    assert result["provider_calls"] == 0


def test_transform_grid_artifacts_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(first)
    run(second)
    for name in ("result.json", "hash_inventory.json", "closure.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        json.loads((first / name).read_text(encoding="utf-8"))
