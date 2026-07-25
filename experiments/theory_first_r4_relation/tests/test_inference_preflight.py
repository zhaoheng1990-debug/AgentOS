import json

import pytest

from theory_first_r4_relation.inference_audit import audit_inference_corpus
from theory_first_r4_relation.inference_cases import ATTRIBUTE_NAMES, INFERENCE_CASES
from theory_first_r4_relation.inference_prompts import inference_batch_prompt
from theory_first_r4_relation.inference_schemas import parse_attribute_receipts


def _valid_payload() -> str:
    receipts = []
    for case in INFERENCE_CASES:
        receipts.append(
            {
                "case_id": case.case_id,
                **case.attributes(),
                "attribute_evidence_refs": {
                    name: list(refs) for name, refs in case.attribute_refs().items()
                },
                "missing_facts": list(case.true_missing_attributes),
            }
        )
    return json.dumps({"receipts": receipts})


def test_fresh_corpus_preflight_passes() -> None:
    result = audit_inference_corpus()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == result["gate_count"]


def test_prompt_exposes_attributes_but_not_runtime_authority() -> None:
    prompt = inference_batch_prompt()
    assert all(name in prompt for name in ATTRIBUTE_NAMES)
    assert '"relation_state":' not in prompt
    assert '"action":' not in prompt


def test_private_reference_payload_parses() -> None:
    parsed = parse_attribute_receipts(_valid_payload(), INFERENCE_CASES)
    assert len(parsed.receipts) == 12


def test_cross_case_evidence_reference_is_rejected() -> None:
    payload = json.loads(_valid_payload())
    payload["receipts"][0]["attribute_evidence_refs"]["source_identity"] = [
        INFERENCE_CASES[1].evidence_refs[0]
    ]
    with pytest.raises(ValueError, match="evidence scope mismatch"):
        parse_attribute_receipts(json.dumps(payload), INFERENCE_CASES)


def test_provider_relation_authority_is_rejected() -> None:
    payload = json.loads(_valid_payload())
    payload["receipts"][0]["relation_state"] = "EXACT_DUPLICATE"
    with pytest.raises(ValueError, match="forbidden Provider authority"):
        parse_attribute_receipts(json.dumps(payload), INFERENCE_CASES)

