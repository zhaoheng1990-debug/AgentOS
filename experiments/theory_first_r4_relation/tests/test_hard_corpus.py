from theory_first_r4_relation.hard_corpus_audit import audit_hard_corpus


def test_fresh_hard_corpus_passes_all_pre_call_gates() -> None:
    result = audit_hard_corpus()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == 9
    assert result["gate_count"] == 9
    assert result["case_count"] == 18
    assert result["domain_count"] >= 12

