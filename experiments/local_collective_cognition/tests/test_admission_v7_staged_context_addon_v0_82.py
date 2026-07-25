from local_collective_cognition.admission_v5_compiler import (
    compile_atomic_witness,
)
from local_collective_cognition.admission_v7_compiler import (
    compile_context_addon,
)
from local_collective_cognition.admission_v7_contracts import (
    validate_context_addon,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload


def test_staged_addon_preserves_evidence_and_splits_context_reject():
    item = _item()
    atomic_receipt = _atomic_receipt(item)
    atomic_partition = compile_atomic_witness(
        item=item,
        receipt=atomic_receipt,
    )
    receipt = _context_receipt(
        item,
        atomic_receipt,
        atomic_partition,
        [_context_fact("S2"), _context_fact("S3")],
    )
    partition = compile_context_addon(
        item=item,
        atomic_receipt=atomic_receipt,
        atomic_partition=atomic_partition,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["context_span_ids"] == ["S2"]
    assert partition["rejected_span_ids"] == ["S3"]
    assert partition["atomic_evidence_partition_mutation_allowed"] is False


def test_grounded_non_target_context_is_retained():
    item = _item()
    atomic_receipt = _atomic_receipt(item)
    atomic_partition = compile_atomic_witness(
        item=item,
        receipt=atomic_receipt,
    )
    receipt = _context_receipt(
        item,
        atomic_receipt,
        atomic_partition,
        [
            _context_fact("S2"),
            _context_fact(
                "S3",
                code="EVIDENCE_VALIDITY",
                changes=True,
                quote="assay was unreliable",
            ),
        ],
    )
    partition = compile_context_addon(
        item=item,
        atomic_receipt=atomic_receipt,
        atomic_partition=atomic_partition,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["context_span_ids"] == ["S2", "S3"]
    assert partition["rejected_span_ids"] == []


def test_ungrounded_context_fails_closed_without_touching_evidence():
    item = _item()
    atomic_receipt = _atomic_receipt(item)
    atomic_partition = compile_atomic_witness(
        item=item,
        receipt=atomic_receipt,
    )
    receipt = _context_receipt(
        item,
        atomic_receipt,
        atomic_partition,
        [
            _context_fact("S2"),
            _context_fact(
                "S3",
                code="EVIDENCE_VALIDITY",
                changes=True,
                quote="invented quote",
            ),
        ],
    )
    partition = compile_context_addon(
        item=item,
        atomic_receipt=atomic_receipt,
        atomic_partition=atomic_partition,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["rejected_span_ids"] == ["S3"]
    assert partition["semantic_conflict_ledger"][0][
        "context_codes"
    ] == ["UTILITY_ANCHOR_NOT_GROUNDED"]


def test_context_contract_forbids_effect_or_policy_fields():
    item = _item()
    atomic_receipt = _atomic_receipt(item)
    atomic_partition = compile_atomic_witness(
        item=item,
        receipt=atomic_receipt,
    )
    receipt = _context_receipt(
        item,
        atomic_receipt,
        atomic_partition,
        [_context_fact("S2"), _context_fact("S3")],
    )
    receipt["records"][0]["independent_effect_support"] = True

    failures = validate_context_addon(
        receipt=receipt,
        item=item,
        atomic_receipt=atomic_receipt,
        atomic_partition=atomic_partition,
        refs=evidence_refs(item),
    )

    assert "ADMISSION_V7_FACT_SHAPE_INVALID" in failures


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
                "text": "Mortality was 10% with drug and 20% with placebo.",
            },
            {
                "span_id": "S2",
                "text": "Mortality was the prespecified primary endpoint.",
            },
            {
                "span_id": "S3",
                "text": "The unrelated assay was unreliable.",
            },
        ],
    }


def _atomic_receipt(item):
    return {
        "case_id": item["case_id"],
        "mechanism": "A14_ATOMIC_SEMANTIC_WITNESS",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "records": [
            _atomic_fact(
                "S1",
                exact=True,
                extractable=True,
                support=True,
                bases=["QUANTITATIVE_VALUE"],
            ),
            _atomic_fact("S2", exact=True),
            _atomic_fact("S3", context=True),
        ],
        "evidence_refs": evidence_refs(item),
    }


def _atomic_fact(
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
        "effect_basis_codes": bases or ["NOT_EFFECT_BEARING"],
        "non_effect_context_relevance": context,
        "rationale": "bounded atomic rationale",
    }


def _context_receipt(
    item,
    atomic_receipt,
    atomic_partition,
    records,
):
    return {
        "case_id": item["case_id"],
        "mechanism": "A16_STAGED_CONTEXT_UTILITY_ADDON",
        "source_item_hash": hash_payload(item),
        "source_atomic_receipt_hash": hash_payload(atomic_receipt),
        "source_atomic_partition_hash": atomic_partition["partition_hash"],
        "all_candidates_assessed": True,
        "records": records,
        "evidence_refs": evidence_refs(item),
    }


def _context_fact(
    span_id,
    *,
    code="NO_TARGET_UTILITY",
    changes=False,
    quote="",
):
    return {
        "span_id": span_id,
        "context_utility_code": code,
        "context_changes_downstream_decision": changes,
        "utility_anchor_quote": quote,
        "rationale": "bounded context rationale",
    }
