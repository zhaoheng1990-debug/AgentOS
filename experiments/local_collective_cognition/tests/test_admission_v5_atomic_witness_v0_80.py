from local_collective_cognition.admission_v5_compiler import (
    compile_atomic_witness,
)
from local_collective_cognition.admission_v5_contracts import (
    validate_atomic_witness,
)
from local_collective_cognition.provider_telemetry import hash_payload


REFS = ("benchmark://synthetic/admission-v5",)


def test_atomic_facts_derive_complete_policy_locally():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            exact=True,
            extractable=True,
            support=True,
            bases=["NULL_OR_NO_DIFFERENCE"],
        ),
        _fact("S2", exact=True, extractable=False, context=True),
        _fact("S3"),
    ])

    assert validate_atomic_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_atomic_witness(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["context_span_ids"] == ["S2"]
    assert partition["rejected_span_ids"] == ["S3"]
    assert partition["semantic_conflict_count"] == 0


def test_multi_outcome_list_with_separate_value_is_admitted():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            exact=True,
            extractable=True,
            support=True,
            bases=[
                "DIRECTION_OR_MAGNITUDE",
                "QUANTITATIVE_CORROBORATION",
            ],
        ),
        _fact("S2"),
        _fact("S3"),
    ])

    assert validate_atomic_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_atomic_witness(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == ["S1"]


def test_semantic_conflict_is_recorded_and_fails_closed():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            exact=True,
            extractable=False,
            support=True,
            bases=["DIRECTION_OR_MAGNITUDE"],
            context=True,
        ),
        _fact("S2"),
        _fact("S3"),
    ])

    assert validate_atomic_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_atomic_witness(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == []
    assert partition["context_span_ids"] == ["S1"]
    assert partition["conflicted_span_ids"] == ["S1"]
    assert partition["semantic_conflict_ledger"][0]["codes"] == [
        "SUPPORT_WITHOUT_EXTRACTABILITY",
    ]
    assert partition["conflicted_effect_promotion_allowed"] is False


def test_effect_basis_conflict_does_not_invalidate_receipt():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            exact=True,
            extractable=True,
            support=False,
            bases=["SIGNIFICANCE_OR_UNCERTAINTY"],
            context=True,
        ),
        _fact("S2"),
        _fact("S3"),
    ])

    assert validate_atomic_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_atomic_witness(item=item, receipt=receipt)
    assert partition["context_span_ids"] == ["S1"]
    assert partition["semantic_conflict_count"] == 1


def test_provider_policy_field_still_fails_structural_contract():
    item = _item()
    fact = _fact("S1")
    fact["admission_state"] = "EVIDENCE_AVAILABLE"
    receipt = _receipt(item, [fact, _fact("S2"), _fact("S3")])

    failures = validate_atomic_witness(
        receipt=receipt,
        item=item,
        refs=REFS,
    )
    assert "ADMISSION_V5_FACT_SHAPE_INVALID" in failures


def _item():
    return {
        "case_id": "SYNTHETIC-ADMISSION-V5",
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
        "mechanism": "A14_ATOMIC_SEMANTIC_WITNESS",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "records": records,
        "evidence_refs": list(REFS),
    }


def _fact(
    span_id,
    *,
    exact=False,
    extractable=False,
    support=False,
    bases=None,
    context=False,
):
    return {
        "span_id": span_id,
        "exact_target_object_mentioned": exact,
        "target_effect_separately_extractable": extractable,
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
        "rationale": "bounded synthetic atomic fact",
    }
