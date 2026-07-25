import json

from theory_first_r4_relation.factor_cli import run
from theory_first_r4_relation.factor_evaluation import evaluate_factorization


def test_factorization_grid_passes_all_frozen_gates() -> None:
    result = evaluate_factorization()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == 16
    assert result["case_count"] == 20
    assert result["admissible_pair_count"] == 7
    assert result["invalid_pair_count"] == 17
    assert result["provider_calls"] == 0


def test_factorization_artifacts_are_byte_identical(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(first)
    run(second)
    for name in ("result.json", "hash_inventory.json", "closure.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        json.loads((first / name).read_text(encoding="utf-8"))
