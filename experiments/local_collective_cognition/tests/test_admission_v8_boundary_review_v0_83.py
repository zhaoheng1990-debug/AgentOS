from local_collective_cognition.admission_v8_compiler import (
    compile_boundary_review,
)
from local_collective_cognition.admission_v8_contracts import (
    validate_boundary_review,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload


def test_grounded_boundary_review_mutates_only_evidence_context():
    item = _item()
    staged = _staged_partition(item)
    receipt = _receipt(item, staged, [
        _positive("S1", "mortality was 10%"),
        _negative(
            "S2",
            issues=["COMPARATOR_POOLED_NOT_ISOLATED"],
            quote="other treatments including placebo",
            comparator_isolated=False,
        ),
        _positive("S3", "mortality was 12%"),
    ])
    partition = compile_boundary_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1", "S3"]
    assert partition["context_span_ids"] == ["S2"]
    assert partition["rejected_span_ids"] == ["S4"]
    assert partition["mutation_count"] == 2
    assert partition["reject_partition_mutation_allowed"] is False


def test_conflicted_negative_witness_preserves_upstream_evidence():
    item = _item()
    staged = _staged_partition(item)
    conflicted = _negative(
        "S2",
        issues=["COMPARATOR_POOLED_NOT_ISOLATED"],
        quote="",
        comparator_isolated=False,
    )
    receipt = _receipt(item, staged, [
        _positive("S1", "mortality was 10%"),
        conflicted,
        _positive("S3", "mortality was 12%"),
    ])
    partition = compile_boundary_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert "S2" in partition["evidence_span_ids"]
    assert partition["semantic_conflict_ledger"][0]["resolution"] == (
        "PRESERVE_UPSTREAM"
    )
    assert partition["conflicted_boundary_mutation_allowed"] is False


def test_boundary_contract_forbids_provider_disposition():
    item = _item()
    staged = _staged_partition(item)
    receipt = _receipt(item, staged, [
        _positive("S1", "mortality was 10%"),
        _positive("S2", "mortality was 11%"),
        _positive("S3", "mortality was 12%"),
    ])
    receipt["records"][0]["disposition"] = "ADMIT_EVIDENCE"

    failures = validate_boundary_review(
        receipt=receipt,
        item=item,
        staged_partition=staged,
        refs=evidence_refs(item),
    )

    assert "ADMISSION_V8_FACT_SHAPE_INVALID" in failures


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
                "text": "Mortality was 10% with drug versus placebo.",
            },
            {
                "span_id": "S2",
                "text": (
                    "Mortality was 11% versus other treatments including "
                    "placebo."
                ),
            },
            {
                "span_id": "S3",
                "text": "Mortality was 12% with drug versus placebo.",
            },
            {
                "span_id": "S4",
                "text": "An unrelated outcome was reported.",
            },
        ],
    }


def _staged_partition(item):
    value = {
        "case_id": item["case_id"],
        "evidence_span_ids": ["S1", "S2"],
        "context_span_ids": ["S3"],
        "rejected_span_ids": ["S4"],
        "admission_state": "EVIDENCE_AVAILABLE",
        "downstream_effect_label_authorized": True,
        "abstention_required": False,
    }
    return {**value, "partition_hash": hash_payload(value)}


def _receipt(item, staged, records):
    return {
        "case_id": item["case_id"],
        "mechanism": "A17_SELECTIVE_EVIDENCE_BOUNDARY_REVIEW",
        "source_item_hash": hash_payload(item),
        "source_staged_partition_hash": staged["partition_hash"],
        "all_candidates_assessed": True,
        "records": records,
        "evidence_refs": evidence_refs(item),
    }


def _positive(span_id, quote):
    return {
        "span_id": span_id,
        "exact_intervention_matched": True,
        "exact_comparator_matched": True,
        "comparator_separately_isolated": True,
        "exact_outcome_matched": True,
        "target_timepoint_matched": True,
        "outcome_separately_isolated": True,
        "independent_effect_statement_present": True,
        "boundary_issue_codes": ["NONE"],
        "support_anchor_quote": quote,
        "boundary_anchor_quote": "",
        "rationale": "complete positive boundary witness",
    }


def _negative(
    span_id,
    *,
    issues,
    quote,
    comparator_isolated=True,
):
    return {
        "span_id": span_id,
        "exact_intervention_matched": True,
        "exact_comparator_matched": True,
        "comparator_separately_isolated": comparator_isolated,
        "exact_outcome_matched": True,
        "target_timepoint_matched": True,
        "outcome_separately_isolated": True,
        "independent_effect_statement_present": True,
        "boundary_issue_codes": issues,
        "support_anchor_quote": "",
        "boundary_anchor_quote": quote,
        "rationale": "complete negative boundary witness",
    }
