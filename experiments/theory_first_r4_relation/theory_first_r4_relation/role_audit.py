"""Deterministic corpus and instrument preflight for R4 v0.3K."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .comparison_cases import COMPARISON_CASES
from .contracts import PLAN_ACTIONS, RELATION_STATES
from .factor_contracts import VALID_STATUS_EFFECT_PAIRS
from .role_cases import (
    EFFECT_ATTRIBUTES,
    PROVENANCE_ATTRIBUTES,
    ROLE_CASES,
    WIDE_ATTRIBUTES,
)
from .role_composer import fail_closed_mutation_audit, private_outcomes
from .role_prompts import role_prompt


def audit_role_experiment() -> dict[str, Any]:
    ids = [case.case_id for case in ROLE_CASES]
    categories = Counter(case.category for case in ROLE_CASES)
    prompts = {
        (scope, reverse): role_prompt(scope, reverse)
        for scope in ("wide", "provenance", "effect")
        for reverse in (False, True)
    }
    old_text = {
        case.target_claim for case in COMPARISON_CASES
    } | {
        statement
        for case in COMPARISON_CASES
        for _, statement in case.evidence
    }
    new_text = {
        case.target_claim for case in ROLE_CASES
    } | {
        statement for case in ROLE_CASES for _, statement in case.evidence
    }
    private_tokens = set(RELATION_STATES) | set(PLAN_ACTIONS) | {
        "VERIFY_ASSERTED_TRANSFORM",
        "DISCOVER_TRANSFORM_APPLICABILITY",
        "NO_TRANSFORM_STATUS_REVALIDATION",
    }
    pairs = {
        (
            case.factorized_dict()["transform_status"],
            case.factorized_dict()["information_effect"],
        )
        for case in ROLE_CASES
    }
    outcomes = private_outcomes()
    fail_closed = fail_closed_mutation_audit()
    gates = {
        "sixteen_unique_fresh_case_ids": (
            len(ids) == len(set(ids)) == 16
            and ids == [f"R43K-{index:02d}" for index in range(1, 17)]
        ),
        "four_balanced_categories": categories
        == {
            "provenance_edge": 4,
            "effect_scope_edge": 4,
            "cross_role_interaction": 4,
            "null_unknown": 4,
        },
        "no_v0_3j_text_reuse": not (old_text & new_text),
        "all_factor_pairs_valid": pairs.issubset(VALID_STATUS_EFFECT_PAIRS),
        "all_seven_factor_pairs_present": pairs == VALID_STATUS_EFFECT_PAIRS,
        "private_reference_complete": all(
            set(case.factorized_dict()) == set(WIDE_ATTRIBUTES)
            and set(case.expected_refs()) == set(WIDE_ATTRIBUTES)
            for case in ROLE_CASES
        ),
        "private_compiler_complete": len(outcomes) == 16,
        "private_compiler_has_no_errors": all(
            not outcome["errors"] for outcome in outcomes.values()
        ),
        "wide_prompt_identity_forward": prompts[("wide", False)]
        == role_prompt("wide", False),
        "wide_prompt_identity_reverse": prompts[("wide", True)]
        == role_prompt("wide", True),
        "scope_contracts_distinct": (
            set(PROVENANCE_ATTRIBUTES).isdisjoint(EFFECT_ATTRIBUTES)
            and set(PROVENANCE_ATTRIBUTES) | set(EFFECT_ATTRIBUTES)
            == set(WIDE_ATTRIBUTES)
        ),
        "all_public_cases_in_every_prompt": all(
            all(case_id in prompt for case_id in ids)
            for prompt in prompts.values()
        ),
        "no_old_case_id_in_prompt": all(
            not any(case.case_id in prompt for case in COMPARISON_CASES)
            for prompt in prompts.values()
        ),
        "no_private_runtime_surface": not any(
            token in prompt
            for prompt in prompts.values()
            for token in private_tokens
        ),
        "no_private_tuple_exposed": not any(
            json.dumps(case.factorized_dict(), sort_keys=True) in prompt
            for prompt in prompts.values()
            for case in ROLE_CASES
        ),
        "no_extraction_position_disclosed": not any(
            token in prompt
            for prompt in prompts.values()
            for token in (
                "wide_source_p",
                "wide_source_e",
                "provenance fields from",
                "effect-scope fields from",
            )
        ),
        "fail_closed_mutations": all(fail_closed.values()),
    }
    return {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
        "category_counts": dict(categories),
        "factor_pairs": sorted(pairs),
        "fail_closed_mutation_audit": fail_closed,
    }
