import json

import pytest

from theory_first_r4_relation.comparison_audit import audit_comparison
from theory_first_r4_relation.comparison_cases import COMPARISON_CASES
from theory_first_r4_relation.comparison_prompts import comparison_prompt
from theory_first_r4_relation.comparison_schemas import parse_comparison_receipts


def _payload(arm: str) -> str:
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
    return json.dumps({"receipts": items})


def test_comparison_preflight_passes() -> None:
    result = audit_comparison()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == result["gate_count"] == 8


def test_both_arm_private_references_parse() -> None:
    for arm in ("legacy", "factorized"):
        assert len(parse_comparison_receipts(_payload(arm), arm).receipts) == 12


def test_prompts_share_cases_but_not_runtime_authority() -> None:
    legacy = comparison_prompt("legacy", False)
    factor = comparison_prompt("factorized", False)
    for case in COMPARISON_CASES:
        assert case.case_id in legacy and case.case_id in factor
    assert '"relation_state":' not in legacy + factor
    assert '"action":' not in legacy + factor


def test_cross_case_reference_is_rejected() -> None:
    payload = json.loads(_payload("factorized"))
    payload["receipts"][0]["attribute_evidence_refs"]["source_identity"] = [
        COMPARISON_CASES[1].refs[0]
    ]
    with pytest.raises(ValueError, match="evidence scope mismatch"):
        parse_comparison_receipts(json.dumps(payload), "factorized")
