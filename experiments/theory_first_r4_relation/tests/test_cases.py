from theory_first_r4_relation.cases import CASES
from theory_first_r4_relation.contracts import RELATION_STATES


def test_frozen_case_count_and_states() -> None:
    assert len(CASES) == 12
    assert len({case.case_id for case in CASES}) == 12
    assert {
        relation.relation_state
        for case in CASES
        for relation in case.relations
    }.issubset(set(RELATION_STATES))
