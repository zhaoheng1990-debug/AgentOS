from collections import Counter

from theory_first_r4_relation.semantic_cases import CASES


def test_fresh_semantic_corpus_is_balanced_and_public_surface_is_blind() -> None:
    assert len(CASES) == 12
    assert Counter(case.private_relation_state for case in CASES) == {
        "INDEPENDENT_DISTINCT": 2,
        "EXACT_DUPLICATE": 2,
        "DEPENDENT_DISTINCT": 2,
        "PARTIAL_OVERLAP": 2,
        "SCOPE_INCOMPATIBLE": 2,
        "UNRESOLVED": 2,
    }
    for case in CASES:
        public = case.public_dict()
        assert "private_relation_state" not in public
        assert "private_action" not in public
        assert len(case.evidence_refs) == 2
