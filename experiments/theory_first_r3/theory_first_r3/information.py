"""Exact decoders and conditional-information readbacks."""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable

from .distribution import State


ROLE_NAMES = ("z1", "z2", "z3")


def feature_key(state: State, features: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(int(getattr(state, name)) for name in features)


def posterior_table(
    states: list[State], features: tuple[str, ...]
) -> dict[tuple[int, ...], float]:
    masses: dict[tuple[int, ...], list[float]] = {}
    for state in states:
        key = feature_key(state, features)
        bucket = masses.setdefault(key, [0.0, 0.0])
        bucket[state.y] += state.probability
    return {
        key: bucket[1] / (bucket[0] + bucket[1])
        for key, bucket in masses.items()
    }


def expected_log_loss(states: list[State], features: tuple[str, ...]) -> float:
    posteriors = posterior_table(states, features)
    loss = 0.0
    for state in states:
        probability_y1 = posteriors[feature_key(state, features)]
        probability_true = probability_y1 if state.y == 1 else 1.0 - probability_y1
        loss -= state.probability * math.log2(probability_true)
    return loss


def exact_shapley_information(states: list[State]) -> dict[str, float]:
    role_count = len(ROLE_NAMES)
    contributions = {role: 0.0 for role in ROLE_NAMES}
    loss_cache: dict[frozenset[str], float] = {}

    def coalition_loss(coalition: frozenset[str]) -> float:
        if coalition not in loss_cache:
            features = ("x",) + tuple(
                role for role in ROLE_NAMES if role in coalition
            )
            loss_cache[coalition] = expected_log_loss(states, features)
        return loss_cache[coalition]

    for role in ROLE_NAMES:
        others = [candidate for candidate in ROLE_NAMES if candidate != role]
        for subset_size in range(len(others) + 1):
            for subset_tuple in itertools.combinations(others, subset_size):
                subset = frozenset(subset_tuple)
                weight = (
                    math.factorial(subset_size)
                    * math.factorial(role_count - subset_size - 1)
                    / math.factorial(role_count)
                )
                marginal = coalition_loss(subset) - coalition_loss(
                    subset | {role}
                )
                contributions[role] += weight * marginal
    return contributions


def weighted_error_phi(states: Iterable[State], left: str, right: str) -> float:
    rows = list(states)
    left_mean = sum(
        row.probability * int(getattr(row, left) != row.y) for row in rows
    )
    right_mean = sum(
        row.probability * int(getattr(row, right) != row.y) for row in rows
    )
    covariance = sum(
        row.probability
        * (int(getattr(row, left) != row.y) - left_mean)
        * (int(getattr(row, right) != row.y) - right_mean)
        for row in rows
    )
    left_variance = left_mean * (1.0 - left_mean)
    right_variance = right_mean * (1.0 - right_mean)
    if left_variance == 0.0 or right_variance == 0.0:
        raise ValueError("error phi is undefined for a constant error variable")
    return covariance / math.sqrt(left_variance * right_variance)
