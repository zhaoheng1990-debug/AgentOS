import json

from theory_first_r4_relation.semantic_cases import CASES
from theory_first_r4_relation.semantic_schemas import parse_semantic_receipts


def _item(case):
    return {
        "case_id": case.case_id,
        "relation_state": case.private_relation_state,
        "evidence_refs": list(case.evidence_refs),
        "unresolved_assumptions": [],
    }


def test_root_object_and_array_are_canonicalized() -> None:
    object_result = parse_semantic_receipts(
        json.dumps({"receipts": [_item(case) for case in CASES]}), CASES
    )
    array_result = parse_semantic_receipts(
        json.dumps([_item(case) for case in CASES]), CASES
    )
    assert object_result.root_type == "object_receipts"
    assert array_result.root_type == "array"
    assert object_result.receipts == array_result.receipts


def test_single_receipt_object_is_canonicalized() -> None:
    result = parse_semantic_receipts(json.dumps(_item(CASES[0])), (CASES[0],))
    assert result.root_type == "object_single"
    assert len(result.receipts) == 1
