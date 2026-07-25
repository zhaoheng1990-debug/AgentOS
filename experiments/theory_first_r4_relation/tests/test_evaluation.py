from theory_first_r4_relation.evaluation import evaluate


def test_all_frozen_gates_pass() -> None:
    result = evaluate()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == result["gate_count"] == 14
    assert result["provider_calls"] == 0
    assert result["anti_additive_controls"]["duplicate_overconfidence_error"] > 0
