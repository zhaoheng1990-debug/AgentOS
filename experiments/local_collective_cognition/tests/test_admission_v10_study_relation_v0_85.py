from local_collective_cognition.admission_v10_compiler import (
    compile_study_relation_review,
)
from local_collective_cognition.admission_v10_contracts import (
    validate_study_relation_review,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload


def test_direct_target_comparison_is_preserved_as_evidence():
    item = _item()
    staged = _staged(item)
    receipt = _receipt(item, staged)

    partition = compile_study_relation_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert partition["evidence_span_ids"] == ["S1", "S3"]
    assert partition["mutation_count"] == 3
    assert partition["evidence_to_reject_allowed"] is False


def test_context_witness_can_recover_reject_but_not_promote_to_evidence():
    item = _item()
    staged = _staged(item)
    receipt = _receipt(item, staged)

    partition = compile_study_relation_review(
        item=item,
        staged_partition=staged,
        receipt=receipt,
    )

    assert partition["context_span_ids"] == ["S2", "S4"]
    assert partition["rejected_span_ids"] == []
    assert partition["reject_to_context_allowed"] is True
    assert partition["reject_to_evidence_allowed"] is False


def test_contract_forbids_provider_disposition():
    item = _item()
    staged = _staged(item)
    receipt = _receipt(item, staged)
    receipt["span_records"][0]["disposition"] = "ADMIT_EVIDENCE"

    failures = validate_study_relation_review(
        receipt=receipt,
        item=item,
        staged_partition=staged,
        refs=evidence_refs(item),
    )

    assert "ADMISSION_V10_SPAN_FACT_SHAPE_INVALID" in failures


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
                "text": "Mortality did not differ between drug and placebo.",
            },
            {
                "span_id": "S2",
                "text": "Mortality or admission was lower with drug.",
            },
            {
                "span_id": "S3",
                "text": "Mortality was lower with drug than placebo.",
            },
            {
                "span_id": "S4",
                "text": "Drug dosing was completed before assessment.",
            },
        ],
    }


def _staged(item):
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


def _receipt(item, staged):
    bindings = [
        _binding("B1", "drug", "TARGET_INTERVENTION_ALIAS", "drug"),
        _binding("B2", "placebo", "TARGET_COMPARATOR_ALIAS", "placebo"),
        _binding("B3", "mortality", "TARGET_OUTCOME_ALIAS", "Mortality"),
        _binding(
            "B4",
            "Mortality or admission",
            "COMPOSITE_OUTCOME_ALIAS",
            "Mortality or admission",
        ),
        _binding(
            "B5",
            "Drug dosing",
            "RELATED_OUTCOME_ALIAS",
            "Drug dosing",
        ),
    ]
    records = [
        _fact("S1", ["B1", "B2", "B3"], effect=True),
        _fact(
            "S2",
            ["B1", "B4"],
            comparison="TARGET_SINGLE_ARM",
            outcome="COMPOSITE_CONTAINS_TARGET",
            effect=False,
            effect_relation="TARGET_RELATED_CONTEXT",
            pooling="NONSEPARABLE_AGGREGATE",
        ),
        _fact("S3", ["B1", "B2", "B3"], effect=True),
        _fact(
            "S4",
            ["B1", "B5"],
            comparison="TARGET_SINGLE_ARM",
            outcome="RELATED_OUTCOME",
            effect=False,
            effect_relation="TARGET_RELATED_CONTEXT",
            pooling="NOT_APPLICABLE",
        ),
    ]
    return {
        "case_id": item["case_id"],
        "mechanism": "A19_STUDY_RELATION_REVIEW",
        "source_item_hash": hash_payload(item),
        "source_staged_partition_hash": staged["partition_hash"],
        "all_spans_assessed": True,
        "bindings": bindings,
        "span_records": records,
        "evidence_refs": evidence_refs(item),
    }


def _binding(binding_id, surface, relation, anchor):
    return {
        "binding_id": binding_id,
        "surface_form": surface,
        "relation": relation,
        "anchor_quote": anchor,
        "rationale": "synthetic relation binding",
    }


def _fact(
    span_id,
    refs,
    *,
    comparison="TARGET_CONTRAST",
    outcome="EXACT_TARGET_OUTCOME",
    effect,
    effect_relation="INDEPENDENT_COMPARATIVE_EFFECT",
    pooling="DIRECT_ARM_COMPARISON",
):
    text = {
        "S1": "Mortality did not differ between drug and placebo.",
        "S2": "Mortality or admission was lower with drug.",
        "S3": "Mortality was lower with drug than placebo.",
        "S4": "Drug dosing was completed before assessment.",
    }[span_id]
    return {
        "span_id": span_id,
        "binding_refs": refs,
        "comparison_relation": comparison,
        "outcome_relation": outcome,
        "effect_relation": effect_relation,
        "pooling_relation": pooling,
        "coreference_relation": "SUPPORTED",
        "effect_anchor_quote": text if effect else "",
        "relation_anchor_quote": text,
        "rationale": "synthetic span relation",
    }
