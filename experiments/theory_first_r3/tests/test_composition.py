import pytest

from theory_first_r3.composition import (
    evaluate_composition,
    round_dynamics,
    suppression_metrics,
)
from theory_first_r3.distribution import informative_distribution, null_distribution


def test_null_has_no_positive_gain() -> None:
    states = null_distribution()
    for k in (0.0, 0.5, 1.0):
        result = evaluate_composition(states, k)
        assert result["observed_gain"] <= 1e-12
        assert result["identity_error"] <= 1e-12


@pytest.mark.parametrize("dependence", [0.0, 0.5, 1.0])
def test_gain_changes_sign_at_preregistered_boundary(dependence: float) -> None:
    states = informative_distribution(dependence)
    base = evaluate_composition(states, 0.0)
    j = float(base["packet_information_j"])
    h = float(base["corruption_harm_h"])
    k_star = h / (j + h)
    below = evaluate_composition(states, k_star - 0.10)
    at = evaluate_composition(states, k_star)
    above = evaluate_composition(states, k_star + 0.10)
    assert below["observed_gain"] < 0.0
    assert at["observed_gain"] == pytest.approx(0.0, abs=1e-12)
    assert above["observed_gain"] > 0.0


def test_suppression_removes_action_not_error() -> None:
    result = suppression_metrics(informative_distribution(0.0))
    assert result["harmful_strong_mass"] == pytest.approx(0.0, abs=1e-12)
    assert result["correct_retention"] == pytest.approx(0.0, abs=1e-12)
    assert result["task_gain"] < 0.0


def test_round_totals_equal_marginal_sum() -> None:
    result = round_dynamics(0.3, 0.2, 0.75)
    for count in (1, 2, 4, 8):
        expected = sum(row["gain"] for row in result["rounds"][:count])
        assert result["totals"][str(count)] == pytest.approx(expected, abs=1e-12)
