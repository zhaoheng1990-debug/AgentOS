"""Coordinator phase, hard-decision, and round accounting."""

from __future__ import annotations

import math
from typing import Callable

from .distribution import State
from .information import feature_key, posterior_table


TOLERANCE = 1e-9
STRONG_THRESHOLD = 0.60


def control_probability_y1(state: State) -> float:
    return 0.70 if state.x == 1 else 0.30


def corrupt_probability_y1(state: State) -> float:
    return 0.30 if state.x == 1 else 0.70


def expected_loss_for_predictor(
    states: list[State], predictor: Callable[[State], float]
) -> float:
    loss = 0.0
    for state in states:
        probability_y1 = predictor(state)
        probability_true = probability_y1 if state.y == 1 else 1.0 - probability_y1
        loss -= state.probability * math.log2(probability_true)
    return loss


def faithful_predictor(states: list[State]) -> Callable[[State], float]:
    features = ("x", "z1", "z2", "z3")
    table = posterior_table(states, features)
    return lambda state: table[feature_key(state, features)]


def decision(probability_y1: float) -> int | None:
    confidence = max(probability_y1, 1.0 - probability_y1)
    if confidence < STRONG_THRESHOLD:
        return None
    return int(probability_y1 >= 0.5)


def hard_metrics(
    states: list[State],
    predictors: tuple[tuple[float, Callable[[State], float]], ...],
) -> dict[str, float]:
    control_correct_mass = 0.0
    retained_correct_mass = 0.0
    corrected_mass = 0.0
    introduced_error_mass = 0.0
    harmful_strong_mass = 0.0
    abstention_mass = 0.0

    for state in states:
        control_decision = decision(control_probability_y1(state))
        control_correct = control_decision == state.y
        if control_correct:
            control_correct_mass += state.probability

        for branch_weight, predictor in predictors:
            mass = state.probability * branch_weight
            candidate_decision = decision(predictor(state))
            candidate_correct = candidate_decision == state.y
            if candidate_decision is None:
                abstention_mass += mass
            elif not candidate_correct:
                harmful_strong_mass += mass
            if control_correct and candidate_correct:
                retained_correct_mass += mass
            elif control_correct and not candidate_correct:
                introduced_error_mass += mass
            elif not control_correct and candidate_correct:
                corrected_mass += mass

    return {
        "corrected_mass": corrected_mass,
        "introduced_error_mass": introduced_error_mass,
        "correct_retention": (
            retained_correct_mass / control_correct_mass
            if control_correct_mass
            else 0.0
        ),
        "harmful_strong_mass": harmful_strong_mass,
        "abstention_mass": abstention_mass,
    }


def evaluate_composition(states: list[State], k: float) -> dict[str, float | None]:
    if not 0.0 <= k <= 1.0:
        raise ValueError("k must be in [0, 1]")

    faithful = faithful_predictor(states)
    control_loss = expected_loss_for_predictor(states, control_probability_y1)
    faithful_loss = expected_loss_for_predictor(states, faithful)
    corrupt_loss = expected_loss_for_predictor(states, corrupt_probability_y1)
    packet_information = control_loss - faithful_loss
    corruption_harm = corrupt_loss - control_loss
    observed_loss = k * faithful_loss + (1.0 - k) * corrupt_loss
    observed_gain = control_loss - observed_loss
    analytic_gain = k * packet_information - (1.0 - k) * corruption_harm
    metrics = hard_metrics(
        states,
        (
            (k, faithful),
            (1.0 - k, corrupt_probability_y1),
        ),
    )
    return {
        "k": k,
        "control_loss": control_loss,
        "faithful_loss": faithful_loss,
        "corrupt_loss": corrupt_loss,
        "packet_information_j": packet_information,
        "corruption_harm_h": corruption_harm,
        "observed_loss": observed_loss,
        "observed_gain": observed_gain,
        "analytic_gain": analytic_gain,
        "identity_error": abs(observed_gain - analytic_gain),
        "k_info": (
            observed_gain / packet_information
            if packet_information > TOLERANCE
            else None
        ),
        **metrics,
    }


def suppression_metrics(states: list[State]) -> dict[str, float]:
    suppress = lambda _state: 0.5
    control_loss = expected_loss_for_predictor(states, control_probability_y1)
    suppression_loss = expected_loss_for_predictor(states, suppress)
    metrics = hard_metrics(states, ((1.0, suppress),))
    return {
        "control_loss": control_loss,
        "suppression_loss": suppression_loss,
        "task_gain": control_loss - suppression_loss,
        **metrics,
    }


def round_dynamics(
    first_round_j: float,
    corruption_harm: float,
    k: float,
    max_rounds: int = 8,
) -> dict[str, object]:
    rounds = []
    cumulative = 0.0
    first_nonpositive = None
    totals: dict[str, float] = {}
    requested_totals = {1, 2, 4, 8}

    for index in range(1, max_rounds + 1):
        round_j = first_round_j * (0.5 ** (index - 1))
        gain = k * round_j - (1.0 - k) * corruption_harm
        cumulative += gain
        rounds.append(
            {
                "round": index,
                "j": round_j,
                "h": corruption_harm,
                "k": k,
                "gain": gain,
                "cumulative_gain": cumulative,
            }
        )
        if gain <= 0.0 and first_nonpositive is None:
            first_nonpositive = index
        if index in requested_totals:
            totals[str(index)] = cumulative

    return {
        "rounds": rounds,
        "totals": totals,
        "first_nonpositive_round": first_nonpositive,
    }
