"""Finite preregistered signal distributions."""

from __future__ import annotations

from dataclasses import dataclass


ERROR_RATE = 0.30
DEPENDENCE_LEVELS = (0.0, 0.5, 1.0)


@dataclass(frozen=True)
class State:
    probability: float
    y: int
    x: int
    z1: int
    z2: int
    z3: int


def bernoulli_probability(value: int, probability_one: float = ERROR_RATE) -> float:
    return probability_one if value else 1.0 - probability_one


def _collapse(rows: list[State]) -> list[State]:
    masses: dict[tuple[int, int, int, int, int], float] = {}
    for row in rows:
        key = (row.y, row.x, row.z1, row.z2, row.z3)
        masses[key] = masses.get(key, 0.0) + row.probability
    return [
        State(probability=probability, y=y, x=x, z1=z1, z2=z2, z3=z3)
        for (y, x, z1, z2, z3), probability in sorted(masses.items())
        if probability > 0.0
    ]


def null_distribution() -> list[State]:
    rows: list[State] = []
    for y in (0, 1):
        for e0 in (0, 1):
            x = y ^ e0
            rows.append(
                State(
                    probability=0.5 * bernoulli_probability(e0),
                    y=y,
                    x=x,
                    z1=x,
                    z2=x,
                    z3=x,
                )
            )
    return _collapse(rows)


def informative_distribution(dependence: float) -> list[State]:
    if dependence not in DEPENDENCE_LEVELS:
        raise ValueError(f"unsupported dependence level: {dependence}")

    rows: list[State] = []
    for y in (0, 1):
        for e0 in (0, 1):
            x = y ^ e0
            base_mass = 0.5 * bernoulli_probability(e0)

            if dependence > 0.0:
                for shared_error in (0, 1):
                    signal = y ^ shared_error
                    rows.append(
                        State(
                            probability=base_mass
                            * dependence
                            * bernoulli_probability(shared_error),
                            y=y,
                            x=x,
                            z1=x,
                            z2=signal,
                            z3=signal,
                        )
                    )

            if dependence < 1.0:
                for e2 in (0, 1):
                    for e3 in (0, 1):
                        rows.append(
                            State(
                                probability=base_mass
                                * (1.0 - dependence)
                                * bernoulli_probability(e2)
                                * bernoulli_probability(e3),
                                y=y,
                                x=x,
                                z1=x,
                                z2=y ^ e2,
                                z3=y ^ e3,
                            )
                        )
    return _collapse(rows)


def total_probability(states: list[State]) -> float:
    return sum(state.probability for state in states)
