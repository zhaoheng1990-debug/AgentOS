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
    invalid = [
        item
        for item in result["cartesian_pair_results"]
        if not item["expected_valid"]
    ]
    assert len(invalid) == 17
    assert all(item["observed_relation_state"] == "UNRESOLVED" for item in invalid)
    assert all(item["observed_action"] == "BLOCK" for item in invalid)
    assert all("STATUS_EFFECT_INCONSISTENT" in item["errors"] for item in invalid)
    assert result["gates"]["compiler_has_no_case_surface"]
    assert result["gates"]["forbidden_calls_and_writes_zero"]
    assert result["provider_calls"] == 0


def test_factorization_artifacts_are_byte_identical(tmp_path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(first)
    run(second)
    for name in ("result.json", "hash_inventory.json", "closure.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
        json.loads((first / name).read_text(encoding="utf-8"))
