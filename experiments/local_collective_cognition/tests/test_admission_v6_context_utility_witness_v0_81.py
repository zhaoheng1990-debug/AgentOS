from local_collective_cognition.admission_v6_compiler import (
    compile_context_utility_witness,
)
from local_collective_cognition.admission_v6_contracts import (
    validate_context_utility_witness,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload


def test_grounded_context_utility_is_retained():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            context_code="EFFECT_INTERPRETATION",
            changes=True,
            quote="secondary endpoint",
        ),
        _fact("S2"),
    ])
    partition = compile_context_utility_witness(
        item=item,
        receipt=receipt,
    )

    assert partition["context_span_ids"] == ["S1"]
    assert partition["rejected_span_ids"] == ["S2"]


def test_ungrounded_context_utility_fails_closed_to_reject():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            context_code="EVIDENCE_VALIDITY",
            changes=True,
            quote="not present in source",
        ),
        _fact("S2"),
    ])
    partition = compile_context_utility_witness(
        item=item,
        receipt=receipt,
    )

    assert partition["rejected_span_ids"] == ["S1", "S2"]
    assert partition["semantic_conflict_ledger"][0][
        "context_codes"
    ] == ["UTILITY_ANCHOR_NOT_GROUNDED"]


def test_context_conflict_does_not_demote_valid_effect_evidence():
    item = _item()
    receipt = _receipt(item, [
        _fact(
            "S1",
            exact=True,
            extractable=True,
            support=True,
            basis=["QUANTITATIVE_VALUE"],
            context_code="SCOPE_OR_APPLICABILITY",
            changes=False,
        ),
        _fact("S2"),
    ])
    partition = compile_context_utility_witness(
        item=item,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["derived_records"][0][
        "conflict_resolution"
    ] == "EFFECT_PRIORITY_CONTEXT_CONFLICT_IGNORED"


def test_intrinsic_target_context_is_retained_without_utility_claim():
    item = _item()
    receipt = _receipt(item, [
        _fact("S1", exact=True),
        _fact("S2"),
    ])
    partition = compile_context_utility_witness(
        item=item,
        receipt=receipt,
    )

    assert partition["context_span_ids"] == ["S1"]
    assert partition["rejected_span_ids"] == ["S2"]


def test_provider_policy_field_fails_structural_contract():
    item = _item()
    receipt = _receipt(item, [_fact("S1"), _fact("S2")])
    receipt["records"][0]["disposition"] = "RETAIN_CONTEXT"

    failures = validate_context_utility_witness(
        receipt=receipt,
        item=item,
        refs=evidence_refs(item),
    )

    assert "ADMISSION_V6_FACT_SHAPE_INVALID" in failures


def _item():
    return {
        "case_id": "CASE-1",
        "source_pmcid": "123",
        "source_prompt_id": "456",
        "object": {
            "intervention": "drug",
            "comparator": "placebo",
            "outcome": "mortality",
        },
        "candidate_spans": [
            {
                "span_id": "S1",
                "text": "The secondary endpoint qualified interpretation.",
            },
            {
                "span_id": "S2",
                "text": "A different outcome was measured.",
            },
        ],
    }


def _receipt(item, records):
    return {
        "case_id": item["case_id"],
        "mechanism": "A15_CONTEXT_UTILITY_WITNESS",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "records": records,
        "evidence_refs": evidence_refs(item),
    }


def _fact(
    span_id,
    *,
    exact=False,
    extractable=False,
    support=False,
    basis=None,
    context_code="NO_TARGET_UTILITY",
    changes=False,
    quote="",
):
    return {
        "span_id": span_id,
        "exact_target_object_mentioned": exact,
        "target_effect_separately_extractable": extractable,
        "independent_effect_support": support,
        "effect_basis_codes": basis or ["NOT_EFFECT_BEARING"],
        "context_utility_code": context_code,
        "context_changes_downstream_decision": changes,
        "utility_anchor_quote": quote,
        "rationale": "bounded rationale",
    }
