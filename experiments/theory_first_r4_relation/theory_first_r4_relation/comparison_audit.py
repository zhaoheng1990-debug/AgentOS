"""Deterministic corpus and dual-compiler preflight for R4 v0.3J."""

from __future__ import annotations

import json
from typing import Any

from .comparison_cases import (
    COMPARISON_CASES,
    FACTORIZED_ATTRIBUTES,
    LEGACY_ATTRIBUTES,
    LEGACY_INVERSE,
)
from .comparison_prompts import comparison_prompt
from .comparison_scoring import private_outcomes
from .contracts import PLAN_ACTIONS, RELATION_STATES


def audit_comparison() -> dict[str, Any]:
    ids = [case.case_id for case in COMPARISON_CASES]
    prompts = [
        comparison_prompt(arm, reverse)
        for arm in ("legacy", "factorized")
        for reverse in (False, True)
    ]
    private_tokens = set(RELATION_STATES) | set(PLAN_ACTIONS) | {
        "VERIFY_ASSERTED_TRANSFORM",
        "DISCOVER_TRANSFORM_APPLICABILITY",
        "TRANSFORM_STATUS_UNRESOLVED",
    }
    outcomes = private_outcomes()
    factor_pairs = {
        (
            case.factorized_dict()["transform_status"],
            case.factorized_dict()["information_effect"],
        )
        for case in COMPARISON_CASES
    }
    gates = {
        "twelve_unique_fresh_cases": len(ids) == len(set(ids)) == 12 and all(case_id.startswith("R43J-") for case_id in ids),
        "both_private_references_complete": all(set(case.legacy_dict()) == set(LEGACY_ATTRIBUTES) and set(case.factorized_dict()) == set(FACTORIZED_ATTRIBUTES) for case in COMPARISON_CASES),
        "all_seven_factor_pairs_present": len(factor_pairs) == 7,
        "legacy_projection_ceiling_ten": sum(len(LEGACY_INVERSE[case.legacy_dict()["information_relation"]]) == 1 for case in COMPARISON_CASES) == 10,
        "dual_compilers_agree": len(outcomes) == 12,
        "identical_public_cases_across_arms": all("R43J-01" in prompt and "R43J-12" in prompt for prompt in prompts),
        "no_private_runtime_surface": not any(token in prompt for prompt in prompts for token in private_tokens),
        "no_private_tuple_exposed": not any(json.dumps(case.factorized_dict(), sort_keys=True) in prompt for prompt in prompts for case in COMPARISON_CASES),
    }
    return {"status": "PASS" if all(gates.values()) else "FAIL", "gates": gates, "gate_pass_count": sum(gates.values()), "gate_count": len(gates)}
