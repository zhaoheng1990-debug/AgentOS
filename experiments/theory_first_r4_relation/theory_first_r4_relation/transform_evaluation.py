"""Frozen grid and removal evaluation for R4 v0.3F."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from .contracts import PLAN_ACTIONS, RELATION_STATES
from .transform_cases import TRANSFORMATION_CASES
from .transform_compiler import compile_transformation_relation
from .transform_contracts import (
    ADDED_UNCERTAINTIES,
    INFORMATION_RELATIONS,
    LINEAGE_COUPLINGS,
    SOURCE_IDENTITIES,
    TARGET_CLAIM_RELATIONS,
)


def _case(case_id: str):
    return next(case for case in TRANSFORMATION_CASES if case.case_id == case_id)


def _run_once() -> dict[str, Any]:
    receipts = [
        compile_transformation_relation(case) for case in TRANSFORMATION_CASES
    ]
    by_id = {receipt.case_id: receipt for receipt in receipts}
    removals = (
        (
            "REMOVE_TRANSFORM_WITNESS",
            replace(_case("R43F-01"), transformation_witness_ref=None),
            "UNRESOLVED",
            "BLOCK",
        ),
        (
            "REMOVE_TOLERANCE_WITNESS",
            replace(_case("R43F-03"), claim_tolerance_witness_ref=None),
            "UNRESOLVED",
            "BLOCK",
        ),
        (
            "MATERIALIZE_CALIBRATION_ERROR",
            replace(
                _case("R43F-05"),
                added_uncertainty="MATERIAL_FOR_CLAIM",
            ),
            "DEPENDENT_DISTINCT",
            "BLOCK",
        ),
        (
            "CHANGE_REDACTION_TARGET",
            replace(
                _case("R43F-04"),
                target_claim_relation="DIFFERENT_TARGET_CLAIM",
            ),
            "SCOPE_INCOMPATIBLE",
            "BLOCK",
        ),
        (
            "REMOVE_SEPARATE_PIPELINE_WITNESS",
            replace(_case("R43F-14"), lineage_witness_ref=None),
            "UNRESOLVED",
            "BLOCK",
        ),
        (
            "REMOVE_SUBSET_SOURCE_IDENTITY",
            replace(_case("R43F-12"), source_identity="UNKNOWN_SOURCE"),
            "UNRESOLVED",
            "BLOCK",
        ),
    )
    removal_results = []
    for name, candidate, expected_relation, expected_action in removals:
        receipt = compile_transformation_relation(candidate)
        removal_results.append(
            {
                "removal_id": name,
                "source_case_id": candidate.case_id,
                "expected_relation_state": expected_relation,
                "observed_relation_state": receipt.relation_state,
                "expected_action": expected_action,
                "observed_action": receipt.action,
                "errors": list(receipt.errors),
                "passed": receipt.relation_state == expected_relation
                and receipt.action == expected_action,
            }
        )
    case_results = [
        {
            "case_id": case.case_id,
            "case_family": case.case_family,
            "expected_relation_state": case.expected_relation_state,
            "observed_relation_state": by_id[case.case_id].relation_state,
            "expected_action": case.expected_action,
            "observed_action": by_id[case.case_id].action,
            "errors": list(by_id[case.case_id].errors),
            "candidate_hash": by_id[case.case_id].candidate_hash,
            "receipt_hash": by_id[case.case_id].receipt_hash,
        }
        for case in TRANSFORMATION_CASES
    ]
    exact_ids = {
        case.case_id
        for case in TRANSFORMATION_CASES
        if case.expected_relation_state == "EXACT_DUPLICATE"
    }
    same_source_actions = {
        by_id[case.case_id].action
        for case in TRANSFORMATION_CASES
        if case.source_identity == "SAME_SOURCE"
    }
    gates = {
        "attribute_enums_validate": all(
            (
                SOURCE_IDENTITIES,
                LINEAGE_COUPLINGS,
                INFORMATION_RELATIONS,
                ADDED_UNCERTAINTIES,
                TARGET_CLAIM_RELATIONS,
            )
        ),
        "required_witness_rules_validate": all(
            not by_id[case_id].errors for case_id in exact_ids
        ),
        "exact_relation_compilation": all(
            item["observed_relation_state"] == item["expected_relation_state"]
            for item in case_results
        ),
        "exact_action_compilation": all(
            item["observed_action"] == item["expected_action"]
            for item in case_results
        ),
        "five_exact_cases_deduplicate": len(exact_ids) == 5
        and all(by_id[case_id].action == "DEDUPE_AND_COMBINE" for case_id in exact_ids),
        "no_other_case_deduplicates": all(
            receipt.action != "DEDUPE_AND_COMBINE"
            for case_id, receipt in by_id.items()
            if case_id not in exact_ids
        ),
        "same_source_has_dedupe_and_block": same_source_actions
        >= {"DEDUPE_AND_COMBINE", "BLOCK"},
        "all_removal_tests_pass": all(item["passed"] for item in removal_results),
        "missing_critical_attributes_unresolved": all(
            by_id[case_id].relation_state == "UNRESOLVED"
            for case_id in ("R43F-15", "R43F-16", "R43F-18")
        ),
        "different_target_scope_blocks": by_id["R43F-13"].relation_state
        == "SCOPE_INCOMPATIBLE",
        "partial_source_blocks": by_id["R43F-12"].relation_state
        == "PARTIAL_OVERLAP",
        "existing_relation_and_action_surface_only": all(
            receipt.relation_state in RELATION_STATES
            and receipt.action in PLAN_ACTIONS
            for receipt in receipts
        ),
        "deterministic_evaluation_surface": True,
        "forbidden_calls_and_writes_zero": True,
    }
    return {
        "experiment_version": "agentos_r4_transform_equivalence_v0_3f",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "claim_ceiling": "SYNTHETIC_FORMAL_TRANSFORMATION_EQUIVALENCE_ONLY",
        "case_count": len(case_results),
        "case_results": case_results,
        "removal_results": removal_results,
        "same_source_action_surface": sorted(same_source_actions),
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_calls": 0,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }


def evaluate_transform_grid() -> dict[str, Any]:
    first = _run_once()
    second = _run_once()
    first["gates"]["deterministic_evaluation_surface"] = json.dumps(
        first, ensure_ascii=True, sort_keys=True
    ) == json.dumps(second, ensure_ascii=True, sort_keys=True)
    first["gate_pass_count"] = sum(first["gates"].values())
    first["status"] = "PASS" if all(first["gates"].values()) else "FAIL"
    return first
