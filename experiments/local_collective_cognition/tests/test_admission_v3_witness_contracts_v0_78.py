from local_collective_cognition.admission_v3_compiler import (
    compile_witness_partition,
)
from local_collective_cognition.admission_v3_contracts import (
    validate_witness_admission,
)
from local_collective_cognition.provider_telemetry import hash_payload


REFS = ("benchmark://synthetic/admission-v3",)


def test_null_effect_and_corroboration_are_effect_bearing():
    item = _item()
    receipt = _receipt(item, [
        _record(
            "S1",
            bases=[
                "NULL_OR_NO_DIFFERENCE",
                "SIGNIFICANCE_OR_UNCERTAINTY",
            ],
        ),
        _record(
            "S2",
            bases=[
                "DIRECTION_OR_MAGNITUDE",
                "QUANTITATIVE_CORROBORATION",
            ],
        ),
    ])

    assert validate_witness_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_witness_partition(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == ["S1", "S2"]


def test_nonseparable_composite_must_remain_context():
    item = _item()
    receipt = _receipt(item, [
        _record(
            "S1",
            binding="TARGET_IN_NONSEPARABLE_COMPOSITE",
            separable=False,
            relation="CONTEXTUAL_OBJECT",
            support=False,
            bases=["NOT_EFFECT_BEARING"],
            utility="CONTEXT_ONLY",
            disposition="RETAIN_CONTEXT",
        ),
        _record("S2"),
    ])

    assert validate_witness_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_witness_partition(item=item, receipt=receipt)
    assert partition["context_span_ids"] == ["S1"]


def test_composite_promoted_to_effect_fails_closed():
    item = _item()
    receipt = _receipt(item, [
        _record(
            "S1",
            binding="TARGET_IN_NONSEPARABLE_COMPOSITE",
            separable=False,
            bases=["DIRECTION_OR_MAGNITUDE"],
        ),
        _record("S2"),
    ])

    failures = validate_witness_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    )
    assert "ADMISSION_V3_OUTCOME_RELATION_CONFLICT" in failures
    assert "ADMISSION_V3_EFFECT_SUPPORT_CONFLICT" in failures


def test_non_effect_span_cannot_carry_effect_basis():
    item = _item()
    receipt = _receipt(item, [
        _record(
            "S1",
            binding="RELATED_OUTCOME",
            separable=False,
            relation="CONTEXTUAL_OBJECT",
            support=False,
            bases=["SIGNIFICANCE_OR_UNCERTAINTY"],
            utility="CONTEXT_ONLY",
            disposition="RETAIN_CONTEXT",
        ),
        _record("S2"),
    ])

    failures = validate_witness_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    )
    assert "ADMISSION_V3_NON_EFFECT_BASIS_CONFLICT" in failures


def _item():
    return {
        "case_id": "SYNTHETIC-ADMISSION-V3",
        "object": {
            "intervention": "intervention",
            "comparator": "comparator",
            "outcome": "outcome",
        },
        "candidate_spans": [
            {"span_id": "S1", "text": "first"},
            {"span_id": "S2", "text": "second"},
        ],
    }


def _receipt(item, records):
    return {
        "case_id": item["case_id"],
        "mechanism": "A12_WITNESS_BACKED_ADMISSION",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "admission_state": (
            "EVIDENCE_AVAILABLE"
            if any(
                record["disposition"] == "ADMIT_EVIDENCE"
                for record in records
            )
            else "NO_APPLICABLE_EVIDENCE"
        ),
        "records": records,
        "evidence_refs": list(REFS),
    }


def _record(
    span_id,
    *,
    binding="EXACT_SEPARABLE_TARGET",
    separable=True,
    relation="EXACT_OBJECT",
    support=True,
    bases=None,
    utility="EFFECT_BEARING",
    disposition="ADMIT_EVIDENCE",
):
    return {
        "span_id": span_id,
        "outcome_binding": binding,
        "target_effect_separable": separable,
        "object_relation": relation,
        "independent_effect_support": support,
        "effect_basis_codes": bases or ["DIRECTION_OR_MAGNITUDE"],
        "evidence_utility": utility,
        "disposition": disposition,
        "rationale": "bounded synthetic rationale",
    }
