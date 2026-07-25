from theory_first_r3.distribution import (
    DEPENDENCE_LEVELS,
    informative_distribution,
    null_distribution,
    total_probability,
)


def test_all_distributions_are_normalized() -> None:
    distributions = [null_distribution()]
    distributions.extend(informative_distribution(value) for value in DEPENDENCE_LEVELS)
    assert all(abs(total_probability(states) - 1.0) <= 1e-12 for states in distributions)


def test_null_roles_copy_the_control() -> None:
    assert all(
        state.z1 == state.x and state.z2 == state.x and state.z3 == state.x
        for state in null_distribution()
    )
