from local_collective_cognition.admission_v4_compiler import (
    compile_minimal_witness,
)
from local_collective_cognition.admission_v4_contracts import (
    validate_minimal_witness,
)
from local_collective_cognition.provider_telemetry import hash_payload


REFS = ("benchmark://synthetic/admission-v4",)


def test_runtime_derives_policy_and_state_from_semantic_facts():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            support=True,
            bases=[
                "NULL_OR_NO_DIFFERENCE",
                "SIGNIFICANCE_OR_UNCERTAINTY",
            ],
        ),
        _fact(
            "S2",
            scope="TARGET_COMPONENT_OF_COMPOSITE",
            context=True,
        ),
        _fact(
            "S3",
            scope="TARGET_ABSENT",
            context=False,
        ),
    ])

    assert validate_minimal_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_minimal_witness(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["context_span_ids"] == ["S2"]
    assert partition["rejected_span_ids"] == ["S3"]
    assert partition["admission_state"] == "EVIDENCE_AVAILABLE"
    assert partition["provider_policy_override_allowed"] is False


def test_absent_target_can_still_supply_mechanistic_context():
    item = _item()
    receipt = _receipt(item, [
        _fact("S1", scope="TARGET_ABSENT", context=True),
        _fact("S2", scope="TARGET_ABSENT", context=False),
        _fact("S3", scope="RELATED_OUTCOME_ONLY", context=False),
    ])

    assert validate_minimal_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_minimal_witness(item=item, receipt=receipt)
    assert partition["context_span_ids"] == ["S1"]
    assert partition["rejected_span_ids"] == ["S2", "S3"]
    assert partition["admission_state"] == "NO_APPLICABLE_EVIDENCE"


def test_nonseparable_composite_cannot_claim_independent_support():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            scope="TARGET_COMPONENT_OF_COMPOSITE",
            support=True,
            bases=["DIRECTION_OR_MAGNITUDE"],
        ),
        _fact("S2"),
        _fact("S3"),
    ])

    failures = validate_minimal_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    )
    assert "ADMISSION_V4_SUPPORT_SCOPE_CONFLICT" in failures


def test_provider_policy_fields_fail_closed():
    item = _item()
    fact = _fact("S1")
    fact["disposition"] = "REJECT"
    receipt = _receipt(item, [
        fact,
        _fact("S2"),
        _fact("S3"),
    ])

    failures = validate_minimal_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    )
    assert "ADMISSION_V4_FACT_SHAPE_INVALID" in failures


def _item():
    return {
        "case_id": "SYNTHETIC-ADMISSION-V4",
        "object": {
            "intervention": "intervention",
            "comparator": "comparator",
            "outcome": "outcome",
        },
        "candidate_spans": [
            {"span_id": "S1", "text": "first"},
            {"span_id": "S2", "text": "second"},
            {"span_id": "S3", "text": "third"},
        ],
    }


def _receipt(item, records):
    return {
        "case_id": item["case_id"],
        "mechanism": "A13_MINIMAL_SEMANTIC_WITNESS",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "records": records,
        "evidence_refs": list(REFS),
    }


def _fact(
    span_id,
    *,
    scope="TARGET_SEPARATELY_REPORTED",
    support=False,
    bases=None,
    context=True,
):
    return {
        "span_id": span_id,
        "outcome_scope": scope,
        "independent_effect_support": support,
        "effect_basis_codes": (
            bases
            if bases is not None
            else (
                ["DIRECTION_OR_MAGNITUDE"]
                if support
                else ["NOT_EFFECT_BEARING"]
            )
        ),
        "non_effect_context_relevance": context,
        "rationale": "bounded synthetic fact",
    }
