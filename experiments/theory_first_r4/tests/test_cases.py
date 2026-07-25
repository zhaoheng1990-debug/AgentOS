import pytest

from theory_first_r4.cases import CASES, ROLE_IDS, exact_reference, posterior


def test_frozen_case_count_and_bounds() -> None:
    assert len(CASES) == 12
    assert len({case.case_id for case in CASES}) == 12
    assert all(0.0 < posterior(case, ROLE_IDS) < 1.0 for case in CASES)


def test_reference_contains_all_eight_subsets() -> None:
    reference = exact_reference()
    assert all(len(values) == 8 for values in reference.values())


def test_neutral_full_case_is_preserved() -> None:
    case = next(item for item in CASES if item.case_id == "R4-10")
    assert posterior(case, ROLE_IDS) == pytest.approx(0.5, abs=1e-12)

