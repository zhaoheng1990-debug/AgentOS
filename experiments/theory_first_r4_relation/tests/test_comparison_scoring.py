import json

from theory_first_r4_relation.comparison_cases import COMPARISON_CASES
from theory_first_r4_relation.comparison_schemas import parse_comparison_receipts
from theory_first_r4_relation.comparison_scoring import score_comparison


def _parsed(arm: str):
    items = []
    for case in COMPARISON_CASES:
        attributes = case.legacy_dict() if arm == "legacy" else case.factorized_dict()
        items.append(
            {
                "case_id": case.case_id,
                **attributes,
                "attribute_evidence_refs": {
                    name: list(refs) for name, refs in case.expected_refs(arm).items()
                },
                "missing_facts": [],
            }
        )
    return parse_comparison_receipts(json.dumps({"receipts": items}), arm)


def test_private_reference_passes_all_comparative_gates() -> None:
    parsed = {
        "legacy_forward": _parsed("legacy"),
        "factor_forward": _parsed("factorized"),
        "factor_reverse": _parsed("factorized"),
        "legacy_reverse": _parsed("legacy"),
    }
    ledger = [
        {
            "logical_call_id": call_id,
            "status": "VALID",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 100,
                "total_tokens": 200,
                "cache_hit_tokens": 0,
            },
        }
        for call_id in parsed
    ]
    result = score_comparison(parsed, ledger)
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == result["gate_count"] == 18
    assert all(item["latent_gain"] == 2 for item in result["matched_gains"])
    assert all(item["revalidation_gain"] == 2 for item in result["matched_gains"])
