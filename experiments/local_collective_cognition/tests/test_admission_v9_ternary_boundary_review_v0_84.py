from local_collective_cognition.admission_v9_compiler import (
    compile_ternary_boundary_review,
)
from local_collective_cognition.admission_v9_contracts import (
    validate_ternary_boundary_review,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload


def test_not_stated_does_not_demote_upstream_evidence():
    item = _item()
    staged = _staged_partition(item)
    receipt = _receipt(item, staged, [
        _fact("S1"),
        _fact(
            "S2",
            comparator_state="NOT_STATED",
            comparator_isolation_state="NOT_APPLICABLE_OR_NOT_STATED",
        ),
        _fact("S3"),
    ])

    partition = compile_ternary_boundary_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1", "S2", "S3"]
    assert partition["mutation_count"] == 1
    assert partition["not_stated_demotion_allowed"] is False


def test_grounded_explicit_contradiction_demotes_evidence():
    item = _item()
    staged = _staged_partition(item)
    receipt = _receipt(item, staged, [
        _fact("S1"),
        _fact(
            "S2",
            comparator_isolation_state="EXPLICITLY_POOLED",
            contradiction_anchor_quote="other treatments including placebo",
        ),
        _fact("S3"),
    ])

    partition = compile_ternary_boundary_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1", "S3"]
    assert partition["context_span_ids"] == ["S2"]
    assert partition["rejected_span_ids"] == ["S4"]


def test_unanchored_explicit_contradiction_preserves_upstream():
    item = _item()
    staged = _staged_partition(item)
    receipt = _receipt(item, staged, [
        _fact("S1"),
        _fact(
            "S2",
            comparator_isolation_state="EXPLICITLY_POOLED",
            contradiction_anchor_quote="",
        ),
        _fact("S3"),
    ])

    partition = compile_ternary_boundary_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert "S2" in partition["evidence_span_ids"]
    assert partition["semantic_conflict_ledger"][0]["resolution"] == (
        "PRESERVE_UPSTREAM"
    )


def test_contract_forbids_provider_disposition():
    item = _item()
    staged = _staged_partition(item)
    receipt = _receipt(item, staged, [
        _fact("S1"),
        _fact("S2"),
        _fact("S3"),
    ])
    receipt["records"][0]["disposition"] = "ADMIT_EVIDENCE"

    failures = validate_ternary_boundary_review(
        receipt=receipt,
        item=item,
        staged_partition=staged,
        refs=evidence_refs(item),
    )

    assert "ADMISSION_V9_FACT_SHAPE_INVALID" in failures


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
                "text": "It was 12% in the target comparison.",
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
        "mechanism": "A18_TERNARY_BOUNDARY_REVIEW",
        "source_item_hash": hash_payload(item),
        "source_staged_partition_hash": staged["partition_hash"],
        "all_candidates_assessed": True,
        "records": records,
        "evidence_refs": evidence_refs(item),
    }


def _fact(
    span_id,
    *,
    intervention_state="MATCHED",
    comparator_state="MATCHED",
    outcome_state="MATCHED",
    timepoint_state="NOT_STATED",
    comparator_isolation_state="ISOLATED",
    outcome_isolation_state="ISOLATED",
    contradiction_anchor_quote="",
):
    quote = {
        "S1": "Mortality was 10% with drug versus placebo",
        "S2": "Mortality was 11%",
        "S3": "It was 12% in the target comparison",
    }[span_id]
    return {
        "span_id": span_id,
        "intervention_state": intervention_state,
        "comparator_state": comparator_state,
        "outcome_state": outcome_state,
        "timepoint_state": timepoint_state,
        "comparator_isolation_state": comparator_isolation_state,
        "outcome_isolation_state": outcome_isolation_state,
        "independent_effect_statement_present": True,
        "target_coreference_supported": True,
        "effect_anchor_quote": quote,
        "contradiction_anchor_quote": contradiction_anchor_quote,
        "rationale": "ternary boundary assessment",
    }
