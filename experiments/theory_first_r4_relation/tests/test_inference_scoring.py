import json

from theory_first_r4_relation.inference_cases import INFERENCE_CASES
from theory_first_r4_relation.inference_schemas import parse_attribute_receipts
from theory_first_r4_relation.inference_scoring import score_attribute_batch


def _parsed_private_reference():
    items = [
        {
            "case_id": case.case_id,
            **case.attributes(),
            "attribute_evidence_refs": {
                name: list(refs) for name, refs in case.attribute_refs().items()
            },
            "missing_facts": list(case.true_missing_attributes),
        }
        for case in INFERENCE_CASES
    ]
    return parse_attribute_receipts(json.dumps({"receipts": items}), INFERENCE_CASES)


def test_private_reference_scores_all_gates() -> None:
    ledger = [
        {
            "logical_call_id": "transform_attribute_batch",
            "attempt": 1,
            "status": "VALID",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 100,
                "total_tokens": 200,
                "cache_hit_tokens": 0,
            },
        }
    ]
    result = score_attribute_batch(_parsed_private_reference(), ledger)
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == 15
    assert result["exact_tuple_count"] == 12
    assert result["relation_correct_count"] == 12
    assert result["action_correct_count"] == 12
    assert result["false_deduplicate"] == 0

