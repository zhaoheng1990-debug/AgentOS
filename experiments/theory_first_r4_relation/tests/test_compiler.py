import pytest

from theory_first_r4_relation.cases import CASES
from theory_first_r4_relation.compiler import compile_plan
from theory_first_r4_relation.composer import compose


def _case(case_id: str):
    return next(case for case in CASES if case.case_id == case_id)


def test_independent_packets_compose_exactly() -> None:
    case = _case("R43A-01")
    receipt = compose(case.packets, compile_plan(case))
    assert receipt.action == "COMBINE"
    assert receipt.probability_y1 == pytest.approx(case.expected_probability_y1)


def test_duplicates_are_selected_once() -> None:
    case = _case("R43A-04")
    plan = compile_plan(case)
    assert plan.action == "DEDUPE_AND_COMBINE"
    assert plan.selected_packet_ids == ("P1", "P3")
    assert plan.excluded_duplicate_ids == ("P2",)


@pytest.mark.parametrize(
    "case_id",
    ("R43A-05", "R43A-06", "R43A-07", "R43A-08", "R43A-09", "R43A-10", "R43A-11", "R43A-12"),
)
def test_unsafe_or_incomplete_graphs_block(case_id: str) -> None:
    case = _case(case_id)
    receipt = compose(case.packets, compile_plan(case))
    assert receipt.action == "BLOCK"
    assert receipt.probability_y1 is None
