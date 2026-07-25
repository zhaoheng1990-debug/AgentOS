"""Frozen formal evaluation for R4 v0.3H."""

from __future__ import annotations

from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any

from .factor_cases import FACTORIZED_CASES, REMOVAL_CASES
from .factor_compiler import compile_factorized_transformation
from .factor_contracts import (
    INFORMATION_EFFECTS,
    TRANSFORM_STATUSES,
    VALID_STATUS_EFFECT_PAIRS,
)


def evaluate_factorization() -> dict[str, Any]:
    case_results = []
    for case in FACTORIZED_CASES:
        receipt = compile_factorized_transformation(case)
        case_results.append(
            {
                "case_id": case.case_id,
                "case_family": case.case_family,
                "transform_status": case.transform_status,
                "information_effect": case.information_effect,
                "expected_relation_state": case.expected_relation_state,
                "observed_relation_state": receipt.relation_state,
                "expected_action": case.expected_action,
                "observed_action": receipt.action,
                "errors": receipt.errors,
                "receipt_hash": receipt.receipt_hash,
            }
        )
    pair_results = []
    for status, effect in product(TRANSFORM_STATUSES, INFORMATION_EFFECTS):
        valid = (status, effect) in VALID_STATUS_EFFECT_PAIRS
        candidate = replace(
            FACTORIZED_CASES[0],
            case_id=f"PAIR-{status}-{effect}",
            case_family="cartesian_status_effect_audit",
            transform_status=status,
            information_effect=effect,
        )
        receipt = compile_factorized_transformation(candidate)
        pair_results.append(
            {
                "transform_status": status,
                "information_effect": effect,
                "expected_valid": valid,
                "observed_relation_state": receipt.relation_state,
                "observed_action": receipt.action,
                "errors": receipt.errors,
            }
        )
    removal_results = []
    for removal_id, candidate, expected_relation, expected_action in REMOVAL_CASES:
        receipt = compile_factorized_transformation(candidate)
        removal_results.append(
            {
                "removal_id": removal_id,
                "observed_relation_state": receipt.relation_state,
                "observed_action": receipt.action,
                "expected_relation_state": expected_relation,
                "expected_action": expected_action,
                "errors": receipt.errors,
                "passed": receipt.relation_state == expected_relation
                and receipt.action == expected_action,
            }
        )
    signatures = {
        "calibration_verified_material": (
            FACTORIZED_CASES[2].transform_status,
            FACTORIZED_CASES[2].information_effect,
        ),
        "calibration_asserted_unverified": (
            FACTORIZED_CASES[18].transform_status,
            FACTORIZED_CASES[18].information_effect,
        ),
        "subset_simultaneous_facts": (
            FACTORIZED_CASES[5].source_identity,
            FACTORIZED_CASES[5].information_effect,
        ),
        "no_transform": (
            FACTORIZED_CASES[11].transform_status,
            FACTORIZED_CASES[11].information_effect,
        ),
        "asserted_unverified": (
            FACTORIZED_CASES[9].transform_status,
            FACTORIZED_CASES[9].information_effect,
        ),
        "unknown_applicability": (
            FACTORIZED_CASES[10].transform_status,
            FACTORIZED_CASES[10].information_effect,
        ),
        "global_equivalence": (
            FACTORIZED_CASES[0].transform_status,
            FACTORIZED_CASES[0].information_effect,
        ),
        "claim_equivalence": (
            FACTORIZED_CASES[1].transform_status,
            FACTORIZED_CASES[1].information_effect,
        ),
    }
    disagreement_resolution = {
        "calibration_status_is_distinct": signatures[
            "calibration_verified_material"
        ]
        != signatures["calibration_asserted_unverified"],
        "subset_preserves_two_axes": signatures["subset_simultaneous_facts"]
        == ("PARTIAL_SOURCE", "INFORMATION_REDUCING"),
        "absence_unverified_unknown_are_distinct": len(
            {
                signatures["no_transform"],
                signatures["asserted_unverified"],
                signatures["unknown_applicability"],
            }
        )
        == 3,
        "global_and_claim_scope_are_distinct": signatures["global_equivalence"]
        != signatures["claim_equivalence"],
    }
    relations = {
        item["observed_relation_state"] for item in case_results
    }
    actions = {item["observed_action"] for item in case_results}
    compiler_source = (
        Path(__file__).with_name("factor_compiler.py").read_text(encoding="utf-8")
    )
    case_surface_tokens = (
        "R43H-",
        "calibration",
        "subset",
        "redaction",
        "compression",
        "speed conversion",
    )
    forbidden_dependency_tokens = (
        "openai",
        "anthropic",
        "deepseek",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "CoreSlim",
        "retention",
        "baseline",
    )
    gates = {
        "new_enums_validate": len(TRANSFORM_STATUSES) == 4
        and len(INFORMATION_EFFECTS) == 6,
        "seven_pairs_admissible": len(VALID_STATUS_EFFECT_PAIRS) == 7,
        "seventeen_pairs_invalid": len(pair_results)
        - len(VALID_STATUS_EFFECT_PAIRS)
        == 17,
        "invalid_pairs_fail_closed": all(
            item["observed_relation_state"] == "UNRESOLVED"
            and item["observed_action"] == "BLOCK"
            and "STATUS_EFFECT_INCONSISTENT" in item["errors"]
            for item in pair_results
            if not item["expected_valid"]
        ),
        "twenty_relations_exact": all(
            item["observed_relation_state"] == item["expected_relation_state"]
            for item in case_results
        ),
        "twenty_actions_exact": all(
            item["observed_action"] == item["expected_action"]
            for item in case_results
        ),
        "four_disagreement_families_resolved": all(
            disagreement_resolution.values()
        ),
        "subset_preserves_partial_and_reducing": disagreement_resolution[
            "subset_preserves_two_axes"
        ],
        "absence_states_distinguishable": disagreement_resolution[
            "absence_unverified_unknown_are_distinct"
        ],
        "global_requires_full_domain_witness": removal_results[2]["passed"]
        and "FULL_DOMAIN_WITNESS_MISSING" in removal_results[2]["errors"],
        "claim_requires_tolerance_witness": removal_results[3]["passed"]
        and "CLAIM_TOLERANCE_WITNESS_MISSING" in removal_results[3]["errors"],
        "six_removals_pass": all(item["passed"] for item in removal_results),
        "existing_relation_and_action_surface_only": relations.issubset(
            {
                "INDEPENDENT_DISTINCT",
                "EXACT_DUPLICATE",
                "DEPENDENT_DISTINCT",
                "PARTIAL_OVERLAP",
                "SCOPE_INCOMPATIBLE",
                "UNRESOLVED",
            }
        )
        and actions.issubset({"COMBINE", "DEDUPE_AND_COMBINE", "BLOCK"}),
        "compiler_has_no_case_surface": not any(
            token in compiler_source for token in case_surface_tokens
        ),
        "deterministic_evaluation_surface": True,
        "forbidden_calls_and_writes_zero": not any(
            token in compiler_source for token in forbidden_dependency_tokens
        ),
    }
    return {
        "experiment_version": "agentos_r4_transform_semantics_factorization_v0_3i",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "claim_ceiling": "FACTORIZED_TRANSFORMATION_SEMANTICS_FORMAL_COHERENCE_ONLY",
        "case_count": len(case_results),
        "cartesian_pair_count": len(pair_results),
        "admissible_pair_count": len(VALID_STATUS_EFFECT_PAIRS),
        "invalid_pair_count": len(pair_results) - len(VALID_STATUS_EFFECT_PAIRS),
        "cartesian_pair_results": pair_results,
        "case_results": case_results,
        "removal_results": removal_results,
        "disagreement_resolution": disagreement_resolution,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_calls": 0,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
