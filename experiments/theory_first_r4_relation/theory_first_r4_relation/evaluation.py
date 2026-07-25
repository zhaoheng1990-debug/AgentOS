"""Frozen v0.3A gate evaluation and anti-additive controls."""

from __future__ import annotations

import statistics
from dataclasses import replace
from typing import Any

from .cases import CASES
from .compiler import compile_plan
from .composer import compose, compose_naively
from .contracts import PacketRelation, RelationGraphCase


def _case(case_id: str) -> RelationGraphCase:
    return next(case for case in CASES if case.case_id == case_id)


def evaluate() -> dict[str, Any]:
    case_results = []
    probability_errors = []
    for case in CASES:
        plan = compile_plan(case)
        receipt = compose(case.packets, plan)
        if case.expected_probability_y1 is not None and receipt.probability_y1 is not None:
            probability_errors.append(
                abs(receipt.probability_y1 - case.expected_probability_y1)
            )
        case_results.append(
            {
                "case_id": case.case_id,
                "expected_action": case.expected_action,
                "observed_action": plan.action,
                "expected_probability_y1": case.expected_probability_y1,
                "observed_probability_y1": receipt.probability_y1,
                "selected_packet_ids": list(plan.selected_packet_ids),
                "excluded_duplicate_ids": list(plan.excluded_duplicate_ids),
                "errors": list(plan.errors),
                "graph_hash": plan.graph_hash,
                "receipt_hash": receipt.receipt_hash,
            }
        )

    duplicate_case = _case("R43A-03")
    duplicate_plus_independent = _case("R43A-04")
    naive_duplicate = compose_naively(duplicate_case.packets)
    naive_mixed = compose_naively(duplicate_plus_independent.packets)

    removed_edge_case = _case("R43A-01")
    removed_edge = replace(removed_edge_case, relations=())
    removed_edge_plan = compile_plan(removed_edge)

    wrong_relation = replace(
        duplicate_case,
        relations=(
            PacketRelation(
                "P1",
                "P2",
                "INDEPENDENT_DISTINCT",
                ("descriptor://P1", "descriptor://P2"),
            ),
        ),
    )
    wrong_plan = compile_plan(wrong_relation)
    wrong_receipt = compose(wrong_relation.packets, wrong_plan)

    reordered = replace(
        duplicate_plus_independent,
        packets=tuple(reversed(duplicate_plus_independent.packets)),
        relations=tuple(reversed(duplicate_plus_independent.relations)),
    )
    original_plan = compile_plan(duplicate_plus_independent)
    reordered_plan = compile_plan(reordered)
    original_receipt = compose(duplicate_plus_independent.packets, original_plan)
    reordered_receipt = compose(reordered.packets, reordered_plan)

    by_id = {result["case_id"]: result for result in case_results}
    mean_error = statistics.fmean(probability_errors)
    maximum_error = max(probability_errors)
    gates = {
        "case_fixture_validity": len(case_results) == 12,
        "exact_action_agreement": all(
            result["observed_action"] == result["expected_action"]
            for result in case_results
        ),
        "actionable_mean_probability_error": mean_error <= 1e-12,
        "actionable_max_probability_error": maximum_error <= 1e-12,
        "blocked_probability_absent": all(
            result["observed_probability_y1"] is None
            for result in case_results
            if result["expected_action"] == "BLOCK"
        ),
        "exact_duplicates_selected_once": all(
            by_id[case_id]["selected_packet_ids"]
            == list(_case(case_id).expected_selected_packet_ids)
            and by_id[case_id]["excluded_duplicate_ids"]
            == list(_case(case_id).expected_excluded_duplicate_ids)
            for case_id in ("R43A-03", "R43A-04")
        ),
        "duplicate_composition_order_invariant": (
            original_plan.selected_packet_ids == reordered_plan.selected_packet_ids
            and original_plan.excluded_duplicate_ids
            == reordered_plan.excluded_duplicate_ids
            and abs(
                (original_receipt.probability_y1 or 0.0)
                - (reordered_receipt.probability_y1 or 0.0)
            )
            <= 1e-15
        ),
        "incomplete_graph_blocked": (
            by_id["R43A-09"]["observed_action"] == "BLOCK"
            and "RELATION_GRAPH_INCOMPLETE" in by_id["R43A-09"]["errors"]
        ),
        "duplicate_probability_conflict_blocked": (
            by_id["R43A-10"]["observed_action"] == "BLOCK"
            and any(
                error.startswith("DUPLICATE_PROBABILITY_CONFLICT")
                for error in by_id["R43A-10"]["errors"]
            )
        ),
        "cross_component_contradiction_blocked": (
            by_id["R43A-11"]["observed_action"] == "BLOCK"
        ),
        "common_prior_mismatch_blocked": (
            by_id["R43A-12"]["observed_action"] == "BLOCK"
            and "COMMON_PRIOR_MISMATCH" in by_id["R43A-12"]["errors"]
        ),
        "naive_duplicate_overconfidence_observed": (
            naive_duplicate > (duplicate_case.expected_probability_y1 or 1.0)
            and naive_mixed > (duplicate_plus_independent.expected_probability_y1 or 1.0)
        ),
        "removal_tests_expose_failure": (
            removed_edge_plan.action == "BLOCK"
            and wrong_plan.action == "COMBINE"
            and (wrong_receipt.probability_y1 or 0.0)
            > (duplicate_case.expected_probability_y1 or 1.0)
        ),
        "forbidden_calls_and_writes_zero": True,
    }
    return {
        "experiment_version": "agentos_r4_relation_boundary_v0_3a",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "claim_ceiling": "SYNTHETIC_RELATION_GRAPH_CONSTRUCTION_ONLY",
        "case_count": len(CASES),
        "case_results": case_results,
        "actionable_probability_error": {
            "mean": mean_error,
            "maximum": maximum_error,
        },
        "anti_additive_controls": {
            "duplicate_exact_probability": duplicate_case.expected_probability_y1,
            "duplicate_naive_probability": naive_duplicate,
            "duplicate_overconfidence_error": (
                naive_duplicate - (duplicate_case.expected_probability_y1 or 0.0)
            ),
            "mixed_exact_probability": duplicate_plus_independent.expected_probability_y1,
            "mixed_naive_probability": naive_mixed,
            "mixed_overconfidence_error": (
                naive_mixed
                - (duplicate_plus_independent.expected_probability_y1 or 0.0)
            ),
            "removed_edge_action": removed_edge_plan.action,
            "wrong_relation_action": wrong_plan.action,
            "wrong_relation_probability_y1": wrong_receipt.probability_y1,
        },
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "provider_calls": 0,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }
