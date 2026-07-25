"""Deterministic analysis of an early-stopped R4 v0.2 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

from .cases import CASES, ROLE_IDS, exact_reference
from .schemas import expected_direction, parse_role_receipts


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "maximum": max(values),
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_inventory(output_dir: Path, paths: list[Path]) -> dict[str, Any]:
    return {
        "inventory_version": "agentos_r4_v0_2_early_stop_hash_inventory_v0_1",
        "files": [
            {
                "path": str(path.relative_to(output_dir)),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted(paths)
        ],
    }


def _compose(prior: float, probabilities: list[float]) -> float:
    prior_log_odds = math.log(prior / (1.0 - prior))
    combined = sum(
        math.log(probability / (1.0 - probability))
        for probability in probabilities
    ) - (len(probabilities) - 1) * prior_log_odds
    return 1.0 / (1.0 + math.exp(-combined))


def analyze(output_dir: Path) -> dict[str, Any]:
    raw_dir = output_dir / "raw_attempts"
    reference = exact_reference()
    role_probabilities: dict[str, dict[str, dict[str, float]]] = {}
    role_errors: list[float] = []
    role_rows = []
    stability_values: list[float] = []
    stability_directions: list[bool] = []
    role_exact_directions: list[bool] = []
    per_role_errors: dict[str, list[float]] = {role: [] for role in ROLE_IDS}

    for role in ROLE_IDS:
        role_probabilities[role] = {}
        for replicate in ("A", "B"):
            path = raw_dir / f"role_{role}_{replicate}_attempt_1.json.txt"
            receipts = parse_role_receipts(
                path.read_text(encoding="utf-8"),
                role,
                require_provider_direction=False,
            )
            probabilities = {
                receipt.case_id: receipt.probability_y1 for receipt in receipts
            }
            role_probabilities[role][replicate] = probabilities
            for case in CASES:
                exact = reference[case.case_id][role]
                observed = probabilities[case.case_id]
                error = abs(observed - exact)
                role_errors.append(error)
                per_role_errors[role].append(error)
                role_exact_directions.append(
                    expected_direction(observed) == expected_direction(exact)
                )
                role_rows.append(
                    {
                        "role": role,
                        "replicate": replicate,
                        "case_id": case.case_id,
                        "exact": exact,
                        "observed": observed,
                        "absolute_error": error,
                    }
                )
        for case in CASES:
            first = role_probabilities[role]["A"][case.case_id]
            second = role_probabilities[role]["B"][case.case_id]
            stability_values.append(abs(first - second))
            stability_directions.append(
                expected_direction(first) == expected_direction(second)
            )

    coordinator_paths = sorted(
        raw_dir.glob("coordinator_ROLE_A_ROLE_B_A_attempt_*.json.txt")
    )
    coordinator_rows = []
    coordinator_attempt_errors: dict[str, list[float]] = {}
    coordinator_attempt_directions: dict[str, list[bool]] = {}
    coordinator_attempt_neutral_counts: dict[str, int] = {}
    coordinator_attempt_prior_copy_counts: dict[str, int] = {}
    coordinator_values: list[dict[str, float]] = []
    for attempt_index, path in enumerate(coordinator_paths, start=1):
        root = _load_json(path)
        values = {
            str(item["case_id"]): float(item["probability_y1"]) for item in root
        }
        coordinator_values.append(values)
        errors = []
        direction_matches = []
        neutral_count = 0
        prior_copy_count = 0
        for case in CASES:
            exact = reference[case.case_id]["ROLE_A+ROLE_B"]
            observed = values[case.case_id]
            error = abs(observed - exact)
            errors.append(error)
            direction_matches.append(
                expected_direction(observed) == expected_direction(exact)
            )
            neutral_count += abs(observed - 0.5) <= 1e-6
            prior_copy_count += abs(observed - case.prior_y1) <= 1e-6
            coordinator_rows.append(
                {
                    "attempt": attempt_index,
                    "case_id": case.case_id,
                    "exact_ab": exact,
                    "observed": observed,
                    "absolute_error": error,
                    "direction_match": direction_matches[-1],
                }
            )
        coordinator_attempt_errors[str(attempt_index)] = errors
        coordinator_attempt_directions[str(attempt_index)] = direction_matches
        coordinator_attempt_neutral_counts[str(attempt_index)] = neutral_count
        coordinator_attempt_prior_copy_counts[str(attempt_index)] = prior_copy_count

    ledger = _load_json(output_dir / "attempt_ledger_checkpoint.json")
    usage_fields = (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cache_hit_tokens",
    )
    token_usage = {
        field: sum(int(row["usage"][field]) for row in ledger)
        for field in usage_fields
    }
    between_attempt_mae = statistics.fmean(
        abs(coordinator_values[0][case.case_id] - coordinator_values[1][case.case_id])
        for case in CASES
    )
    role_rows.sort(key=lambda row: row["absolute_error"], reverse=True)
    coordinator_rows.sort(key=lambda row: row["absolute_error"], reverse=True)

    local_composition: dict[str, dict[str, float]] = {}
    for roles in (
        ("ROLE_A", "ROLE_B"),
        ("ROLE_A", "ROLE_C"),
        ("ROLE_B", "ROLE_C"),
        ROLE_IDS,
    ):
        key = "+".join(roles)
        errors = []
        for case in CASES:
            observed = _compose(
                case.prior_y1,
                [
                    role_probabilities[role]["A"][case.case_id]
                    for role in roles
                ],
            )
            errors.append(abs(observed - reference[case.case_id][key]))
        local_composition[key] = _summary(errors)

    return {
        "analysis_version": "agentos_r4_v0_2_early_stop_analysis_v0_1",
        "status": "FAIL_COORDINATOR_MECHANICAL_VALIDITY",
        "logical_calls_valid": 6,
        "physical_attempts": len(ledger),
        "token_usage": token_usage,
        "role_layer": {
            "mechanical_coverage": 1.0,
            "probability_error": _summary(role_errors),
            "probability_error_by_role": {
                role: _summary(errors) for role, errors in per_role_errors.items()
            },
            "exact_direction_agreement": (
                sum(role_exact_directions) / len(role_exact_directions)
            ),
            "replicate_probability_difference": _summary(stability_values),
            "replicate_direction_agreement": (
                sum(stability_directions) / len(stability_directions)
            ),
            "largest_errors": role_rows[:12],
        },
        "unaccepted_pair_coordinator_diagnostic": {
            "contract_valid": False,
            "root_types": [
                type(_load_json(path)).__name__ for path in coordinator_paths
            ],
            "attempt_probability_error": {
                attempt: _summary(errors)
                for attempt, errors in coordinator_attempt_errors.items()
            },
            "attempt_direction_agreement": {
                attempt: sum(matches) / len(matches)
                for attempt, matches in coordinator_attempt_directions.items()
            },
            "attempt_neutral_output_count": coordinator_attempt_neutral_counts,
            "attempt_prior_copy_count": coordinator_attempt_prior_copy_counts,
            "between_attempt_probability_mae": between_attempt_mae,
            "between_attempt_exact_match_count": sum(
                abs(
                    coordinator_values[0][case.case_id]
                    - coordinator_values[1][case.case_id]
                )
                <= 1e-9
                for case in CASES
            ),
            "largest_errors": coordinator_rows[:12],
            "scoring_authority": False,
        },
        "posthoc_deterministic_composition": {
            "provider_calls": 0,
            "promotion_authority": False,
            "probability_error_by_subset": local_composition,
            "interpretation": (
                "Accepted role packets contain sufficient numeric information "
                "for deterministic Runtime composition."
            ),
        },
        "preregistered_gate_readback": {
            "call_and_attempt_budget": False,
            "token_limit": token_usage["total_tokens"] <= 200000,
            "role_mechanical_validity": True,
            "coordinator_mechanical_validity": False,
            "role_mean_probability_error": _summary(role_errors)["mean"] <= 0.02,
            "role_max_probability_error": _summary(role_errors)["maximum"] <= 0.08,
            "replicate_direction_agreement": all(stability_directions),
            "replicate_probability_mae": _summary(stability_values)["mean"] <= 0.03,
            "remaining_semantic_gates": "NOT_SCORABLE",
            "no_forbidden_project_write": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    result = analyze(args.output_dir.resolve())
    destination = args.output_dir.resolve() / "partial_analysis.json"
    destination.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    inventory = _hash_inventory(
        args.output_dir.resolve(),
        [
            args.output_dir.resolve() / "attempt_ledger_checkpoint.json",
            destination,
            *sorted((args.output_dir.resolve() / "raw_attempts").glob("*.txt")),
        ],
    )
    (args.output_dir.resolve() / "hash_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
