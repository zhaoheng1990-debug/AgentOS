import pytest

from theory_first_r3.distribution import informative_distribution, null_distribution
from theory_first_r3.information import (
    exact_shapley_information,
    expected_log_loss,
    weighted_error_phi,
)


@pytest.mark.parametrize("dependence", [0.0, 0.5, 1.0])
def test_shapley_information_sums_to_joint_information(dependence: float) -> None:
    states = informative_distribution(dependence)
    joint_information = expected_log_loss(states, ("x",)) - expected_log_loss(
        states, ("x", "z1", "z2", "z3")
    )
    shapley = exact_shapley_information(states)
    assert sum(shapley.values()) == pytest.approx(joint_information, abs=1e-12)
    assert shapley["z1"] == pytest.approx(0.0, abs=1e-12)


def test_null_information_is_zero() -> None:
    states = null_distribution()
    joint_information = expected_log_loss(states, ("x",)) - expected_log_loss(
        states, ("x", "z1", "z2", "z3")
    )
    assert joint_information == pytest.approx(0.0, abs=1e-12)


def test_dependence_raises_error_phi_and_reduces_information() -> None:
    rows = []
    for dependence in (0.0, 0.5, 1.0):
        states = informative_distribution(dependence)
        rows.append(
            (
                weighted_error_phi(states, "z2", "z3"),
                expected_log_loss(states, ("x",))
                - expected_log_loss(states, ("x", "z1", "z2", "z3")),
            )
        )
    assert rows[0][0] <= rows[1][0] <= rows[2][0]
    assert rows[0][1] >= rows[1][1] >= rows[2][1] > 0.0
