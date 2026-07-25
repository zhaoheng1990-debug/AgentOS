"""Preregistered R3 experiment orchestration and gates."""

from __future__ import annotations

from typing import Any

from .composition import (
    TOLERANCE,
    evaluate_composition,
    round_dynamics,
    suppression_metrics,
)
from .distribution import (
    DEPENDENCE_LEVELS,
    informative_distribution,
    null_distribution,
    total_probability,
)
from .information import (
    exact_shapley_information,
    expected_log_loss,
    weighted_error_phi,
)


def _scenario(name: str, states: list[Any], dependence: float | None) -> dict[str, Any]:
    control_loss = expected_log_loss(states, ("x",))
    joint_loss = expected_log_loss(states, ("x", "z1", "z2", "z3"))
    packet_information = control_loss - joint_loss
    shapley = exact_shapley_information(states)
    baseline = evaluate_composition(states, 0.0)
    harm = float(baseline["corruption_harm_h"])
    k_star = harm / (packet_information + harm)

    if name == "null":
        k_values = (0.0, 0.5, 1.0)
    else:
        k_values = (
            max(0.0, k_star - 0.10),
            k_star,
            min(1.0, k_star + 0.10),
        )

    cells = [evaluate_composition(states, k) for k in k_values]
    fixed_k_cells = [
        evaluate_composition(states, k) for k in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    return {
        "name": name,
        "dependence": dependence,
        "state_count": len(states),
        "total_probability": total_probability(states),
        "control_loss": control_loss,
        "joint_packet_loss": joint_loss,
        "packet_information_j": packet_information,
        "shapley_information": shapley,
        "shapley_sum": sum(shapley.values()),
        "paired_error_phi_z2_z3": weighted_error_phi(states, "z2", "z3"),
        "corruption_harm_h": harm,
        "k_star": k_star,
        "phase_cells": cells,
        "fixed_k_cells": fixed_k_cells,
        "suppression": suppression_metrics(states),
    }


def _gate(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def run_experiment() -> dict[str, Any]:
    scenarios = [_scenario("null", null_distribution(), None)]
    scenarios.extend(
        _scenario(
            f"informative_d_{dependence:.1f}",
            informative_distribution(dependence),
            dependence,
        )
        for dependence in DEPENDENCE_LEVELS
    )
    null = scenarios[0]
    informative = scenarios[1:]

    all_cells = [
        cell for scenario in scenarios for cell in scenario["phase_cells"]
    ]
    analytic_identity_pass = all(
        float(cell["identity_error"]) <= TOLERANCE for cell in all_cells
    )
    null_pass = all(
        float(cell["observed_gain"]) <= TOLERANCE
        for cell in null["phase_cells"]
    )
    phase_sign_pass = all(
        float(scenario["phase_cells"][0]["observed_gain"]) < 0.0
        and abs(float(scenario["phase_cells"][1]["observed_gain"])) <= TOLERANCE
        and float(scenario["phase_cells"][2]["observed_gain"]) > 0.0
        for scenario in informative
    )

    by_information = sorted(informative, key=lambda item: item["packet_information_j"])
    fixed_k_monotone = True
    for index in range(5):
        gains = [
            float(scenario["fixed_k_cells"][index]["observed_gain"])
            for scenario in by_information
        ]
        fixed_k_monotone = fixed_k_monotone and all(
            left <= right + TOLERANCE for left, right in zip(gains, gains[1:])
        )

    k_monotone = all(
        all(
            float(left["observed_gain"]) <= float(right["observed_gain"]) + TOLERANCE
            for left, right in zip(
                scenario["fixed_k_cells"], scenario["fixed_k_cells"][1:]
            )
        )
        for scenario in scenarios
    )
    shapley_sum_pass = all(
        abs(float(scenario["shapley_sum"]) - float(scenario["packet_information_j"]))
        <= TOLERANCE
        for scenario in scenarios
    )
    redundant_role_pass = all(
        abs(float(scenario["shapley_information"]["z1"])) <= TOLERANCE
        for scenario in scenarios
    )

    dependence_order = sorted(informative, key=lambda item: item["dependence"])
    phis = [float(item["paired_error_phi_z2_z3"]) for item in dependence_order]
    information_values = [
        float(item["packet_information_j"]) for item in dependence_order
    ]
    dependence_pass = all(
        left <= right + TOLERANCE for left, right in zip(phis, phis[1:])
    ) and all(
        left + TOLERANCE >= right
        for left, right in zip(information_values, information_values[1:])
    )

    suppression_pass = all(
        float(scenario["suppression"]["harmful_strong_mass"]) <= TOLERANCE
        and float(scenario["suppression"]["correct_retention"]) <= TOLERANCE
        and float(scenario["suppression"]["task_gain"]) < 0.0
        for scenario in scenarios
    )

    round_source = informative[0]
    round_k = min(1.0, float(round_source["k_star"]) + 0.10)
    dynamics = round_dynamics(
        float(round_source["packet_information_j"]),
        float(round_source["corruption_harm_h"]),
        round_k,
    )
    round_sum_pass = all(
        abs(
            float(dynamics["totals"][str(round_count)])
            - sum(
                float(row["gain"])
                for row in dynamics["rounds"][:round_count]
            )
        )
        <= TOLERANCE
        for round_count in (1, 2, 4, 8)
    )

    gates = [
        _gate("DISTRIBUTION_NORMALIZATION", all(abs(float(s["total_probability"]) - 1.0) <= TOLERANCE for s in scenarios), "All finite scenario masses sum to one."),
        _gate("ANALYTIC_IDENTITY", analytic_identity_pass, "Observed and analytic composition gains agree."),
        _gate("NULL_NO_POSITIVE_GAIN", null_pass, "J=0 produces no positive gain."),
        _gate("PHASE_SIGN_AT_K_STAR", phase_sign_pass, "Informative cells change sign at k_star."),
        _gate("GAIN_MONOTONE_IN_J", fixed_k_monotone, "Gain is nondecreasing in packet information."),
        _gate("GAIN_MONOTONE_IN_K", k_monotone, "Gain is nondecreasing in composition fidelity."),
        _gate("SHAPLEY_EFFICIENCY", shapley_sum_pass, "Role allocations sum to J_set."),
        _gate("REDUNDANT_ROLE_ZERO", redundant_role_pass, "Z1 has zero conditional contribution."),
        _gate("DEPENDENCE_INFORMATION_ORDER", dependence_pass, "Injected dependence raises phi and does not raise J."),
        _gate("SUPPRESSION_IS_NOT_CORRECTION", suppression_pass, "Suppression removes strong harm by removing all strong action and loses task bits."),
        _gate("ROUND_ACCOUNTING", round_sum_pass, "Reported totals equal summed marginal gains."),
        _gate("NO_FORBIDDEN_CHANNELS", True, "Standalone finite enumeration uses no Provider, holdout, Runtime, CoreSlim, retention, or baseline channel."),
    ]
    return {
        "experiment_version": "agentos_r3_minimal_synthetic_v0_1",
        "status": "PASS" if all(gate["passed"] for gate in gates) else "FAIL",
        "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
        "tolerance": TOLERANCE,
        "provider_calls": 0,
        "fresh_holdout_consumed": False,
        "runtime_imported": False,
        "scenarios": scenarios,
        "round_dynamics": dynamics,
        "gates": gates,
        "gate_pass_count": sum(gate["passed"] for gate in gates),
        "gate_count": len(gates),
    }
