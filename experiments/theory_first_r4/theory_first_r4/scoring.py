"""Private-reference scoring for Provider packets."""

from __future__ import annotations

import itertools
import math
import statistics
from typing import Any

from .cases import CASES, ROLE_IDS, exact_reference


SUBSETS = (
    (),
    ("ROLE_A",),
    ("ROLE_B",),
    ("ROLE_C",),
    ("ROLE_A", "ROLE_B"),
    ("ROLE_A", "ROLE_C"),
    ("ROLE_B", "ROLE_C"),
    ROLE_IDS,
)


def subset_key(roles: tuple[str, ...]) -> str:
    return "+".join(roles) if roles else "PRIOR"


def cross_entropy(target_y1: float, prediction_y1: float) -> float:
    prediction = min(max(prediction_y1, 1e-12), 1.0 - 1e-12)
    return -target_y1 * math.log2(prediction) - (1.0 - target_y1) * math.log2(
        1.0 - prediction
    )


def mean_loss(
    predictions: dict[str, float], targets: dict[str, float]
) -> float:
    return statistics.fmean(
        cross_entropy(targets[case_id], predictions[case_id])
        for case_id in sorted(targets)
    )


def shapley_from_losses(losses: dict[str, float]) -> dict[str, float]:
    role_count = len(ROLE_IDS)
    contributions = {role: 0.0 for role in ROLE_IDS}
    for role in ROLE_IDS:
        others = [candidate for candidate in ROLE_IDS if candidate != role]
        for subset_size in range(len(others) + 1):
            for subset_tuple in itertools.combinations(others, subset_size):
                subset = tuple(role_id for role_id in ROLE_IDS if role_id in subset_tuple)
                with_role = tuple(
                    role_id
                    for role_id in ROLE_IDS
                    if role_id in set(subset_tuple) | {role}
                )
                weight = (
                    math.factorial(subset_size)
                    * math.factorial(role_count - subset_size - 1)
                    / math.factorial(role_count)
                )
                contributions[role] += weight * (
                    losses[subset_key(subset)] - losses[subset_key(with_role)]
                )
    return contributions


def probability_summary(errors: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(errors),
        "median": statistics.median(errors),
        "maximum": max(errors),
    }


def evaluate_predictions(
    predictions: dict[str, dict[str, float]],
    role_replicates: dict[str, tuple[dict[str, float], dict[str, float]]],
    full_replicates: tuple[dict[str, float], dict[str, float]],
) -> dict[str, Any]:
    reference = exact_reference()
    full_targets = {
        case.case_id: reference[case.case_id][subset_key(ROLE_IDS)] for case in CASES
    }
    subset_targets = {
        subset_key(roles): {
            case.case_id: reference[case.case_id][subset_key(roles)] for case in CASES
        }
        for roles in SUBSETS
    }

    role_errors = []
    role_direction_matches = []
    stability_differences = []
    stability_direction_matches = []
    for role in ROLE_IDS:
        target = subset_targets[role]
        first, second = role_replicates[role]
        for case_id in sorted(target):
            role_errors.extend(
                (
                    abs(first[case_id] - target[case_id]),
                    abs(second[case_id] - target[case_id]),
                )
            )
            role_direction_matches.extend(
                (
                    (first[case_id] >= 0.5) == (target[case_id] >= 0.5),
                    (second[case_id] >= 0.5) == (target[case_id] >= 0.5),
                )
            )
            stability_differences.append(abs(first[case_id] - second[case_id]))
            stability_direction_matches.append(
                (first[case_id] >= 0.5) == (second[case_id] >= 0.5)
            )

    full_errors = []
    full_direction_matches = []
    full_stability = []
    full_strong_wrong = 0
    for case_id in sorted(full_targets):
        target = full_targets[case_id]
        first = full_replicates[0][case_id]
        second = full_replicates[1][case_id]
        full_errors.extend((abs(first - target), abs(second - target)))
        full_direction_matches.extend(
            (
                (first >= 0.5) == (target >= 0.5),
                (second >= 0.5) == (target >= 0.5),
            )
        )
        full_stability.append(abs(first - second))
        if max(first, 1.0 - first) >= 0.70 and (first >= 0.5) != (target >= 0.5):
            full_strong_wrong += 1

    provider_losses = {
        subset_key(roles): mean_loss(predictions[subset_key(roles)], full_targets)
        for roles in SUBSETS
    }
    exact_losses = {
        subset_key(roles): mean_loss(subset_targets[subset_key(roles)], full_targets)
        for roles in SUBSETS
    }
    provider_gain = provider_losses["PRIOR"] - provider_losses[subset_key(ROLE_IDS)]
    exact_gain = exact_losses["PRIOR"] - exact_losses[subset_key(ROLE_IDS)]
    provider_shapley = shapley_from_losses(provider_losses)
    exact_shapley = shapley_from_losses(exact_losses)
    provider_order = sorted(ROLE_IDS, key=lambda role: (-provider_shapley[role], role))
    exact_order = sorted(ROLE_IDS, key=lambda role: (-exact_shapley[role], role))

    best_singleton_retained = 0
    best_singleton_correct_strong = 0
    abstention_count = 0
    full_first = full_replicates[0]
    for case_id, target in full_targets.items():
        singleton_values = {
            role: predictions[role][case_id] for role in ROLE_IDS
        }
        best_role = min(
            ROLE_IDS,
            key=lambda role: cross_entropy(target, singleton_values[role]),
        )
        best_value = singleton_values[best_role]
        best_correct = (best_value >= 0.5) == (target >= 0.5)
        best_strong = max(best_value, 1.0 - best_value) >= 0.70
        full_value = full_first[case_id]
        if 0.45 <= full_value <= 0.55:
            abstention_count += 1
        if best_correct and best_strong:
            best_singleton_correct_strong += 1
            if (full_value >= 0.5) == (target >= 0.5):
                best_singleton_retained += 1

    return {
        "role_probability_error": probability_summary(role_errors),
        "role_direction_agreement": sum(role_direction_matches)
        / len(role_direction_matches),
        "role_stability_probability": probability_summary(stability_differences),
        "role_stability_direction_agreement": sum(stability_direction_matches)
        / len(stability_direction_matches),
        "full_probability_error": probability_summary(full_errors),
        "full_direction_agreement": sum(full_direction_matches)
        / len(full_direction_matches),
        "full_stability_probability": probability_summary(full_stability),
        "full_strong_wrong_count": full_strong_wrong,
        "full_abstention_count": abstention_count,
        "correct_strong_retention": (
            best_singleton_retained / best_singleton_correct_strong
            if best_singleton_correct_strong
            else None
        ),
        "provider_losses": provider_losses,
        "exact_losses": exact_losses,
        "provider_j": provider_gain,
        "exact_j": exact_gain,
        "k_info": provider_gain / exact_gain if exact_gain > 0.0 else None,
        "provider_shapley": provider_shapley,
        "exact_shapley": exact_shapley,
        "provider_role_order": provider_order,
        "exact_role_order": exact_order,
        "role_order_matches": provider_order == exact_order,
    }

