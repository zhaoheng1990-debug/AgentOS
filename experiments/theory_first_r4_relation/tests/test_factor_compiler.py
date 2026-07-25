from dataclasses import replace

import pytest

from theory_first_r4_relation.factor_cases import FACTORIZED_CASES
from theory_first_r4_relation.factor_compiler import compile_factorized_transformation
from theory_first_r4_relation.factor_contracts import FactorizedTransformationCandidate


def test_all_frozen_factorized_cases_compile_exactly() -> None:
    for case in FACTORIZED_CASES:
        receipt = compile_factorized_transformation(case)
        assert receipt.relation_state == case.expected_relation_state
        assert receipt.action == case.expected_action


def test_case_identity_does_not_change_compilation() -> None:
    original = FACTORIZED_CASES[0]
    renamed = replace(
        original,
        case_id="R43H-COUNTERFACTUAL",
        case_family="counterfactual_family",
    )
    first = compile_factorized_transformation(original)
    second = compile_factorized_transformation(renamed)
    assert (second.relation_state, second.action, second.errors) == (
        first.relation_state,
        first.action,
        first.errors,
    )


def test_invalid_status_effect_pair_fails_closed() -> None:
    candidate = replace(
        FACTORIZED_CASES[0],
        transform_status="NO_TRANSFORM",
        information_effect="GLOBAL_EQUIVALENT",
    )
    receipt = compile_factorized_transformation(candidate)
    assert receipt.relation_state == "UNRESOLVED"
    assert receipt.action == "BLOCK"
    assert "STATUS_EFFECT_INCONSISTENT" in receipt.errors


def test_unknown_enum_is_rejected() -> None:
    values = FACTORIZED_CASES[0].__dict__ | {"transform_status": "MAGIC"}
    with pytest.raises(ValueError, match="unknown transform status"):
        FactorizedTransformationCandidate(**values)
