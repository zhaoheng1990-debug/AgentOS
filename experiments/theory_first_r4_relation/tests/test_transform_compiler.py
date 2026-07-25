from dataclasses import replace

import pytest

from theory_first_r4_relation.transform_cases import TRANSFORMATION_CASES
from theory_first_r4_relation.transform_compiler import (
    compile_transformation_relation,
)
from theory_first_r4_relation.transform_contracts import (
    TransformationRelationCandidate,
)


def test_all_frozen_cases_compile_exactly() -> None:
    for case in TRANSFORMATION_CASES:
        receipt = compile_transformation_relation(case)
        assert receipt.relation_state == case.expected_relation_state
        assert receipt.action == case.expected_action


def test_missing_transform_witness_revokes_deduplication() -> None:
    candidate = replace(
        TRANSFORMATION_CASES[0], transformation_witness_ref=None
    )
    receipt = compile_transformation_relation(candidate)
    assert receipt.relation_state == "UNRESOLVED"
    assert receipt.action == "BLOCK"
    assert "TRANSFORMATION_WITNESS_MISSING" in receipt.errors


def test_invalid_attribute_is_rejected() -> None:
    values = TRANSFORMATION_CASES[0].__dict__ | {
        "source_identity": "MAGIC_SOURCE"
    }
    with pytest.raises(ValueError, match="unknown source identity"):
        TransformationRelationCandidate(**values)


def test_case_identity_and_family_do_not_affect_compilation() -> None:
    original = TRANSFORMATION_CASES[0]
    renamed = replace(
        original,
        case_id="R43F-COUNTERFACTUAL-ID",
        case_family="counterfactual_family",
    )
    original_receipt = compile_transformation_relation(original)
    renamed_receipt = compile_transformation_relation(renamed)
    assert renamed_receipt.relation_state == original_receipt.relation_state
    assert renamed_receipt.action == original_receipt.action
    assert renamed_receipt.errors == original_receipt.errors
