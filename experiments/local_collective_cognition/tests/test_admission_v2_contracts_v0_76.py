from local_collective_cognition.admission_v2_compiler import (
    compile_typed_partition,
)
from local_collective_cognition.admission_v2_contracts import (
    validate_typed_admission,
)
from local_collective_cognition.provider_telemetry import hash_payload


REFS = ("benchmark://synthetic/admission-v2",)


def test_no_applicable_evidence_is_a_valid_abstention():
    item = _item()
    receipt = _receipt(
        item,
        state="NO_APPLICABLE_EVIDENCE",
        records=[
            _record(
                "S1",
                "CONTEXTUAL_OBJECT",
                "CONTEXT_ONLY",
                "RETAIN_CONTEXT",
            ),
            _record(
                "S2",
                "IRRELEVANT_OBJECT",
                "NONE",
                "REJECT",
            ),
        ],
    )

    assert validate_typed_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_typed_partition(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == []
    assert partition["context_span_ids"] == ["S1"]
    assert partition["rejected_span_ids"] == ["S2"]
    assert partition["abstention_required"] is True
    assert partition["downstream_effect_label_authorized"] is False


def test_available_evidence_preserves_complete_three_way_partition():
    item = _item()
    receipt = _receipt(
        item,
        state="EVIDENCE_AVAILABLE",
        records=[
            _record(
                "S1",
                "EXACT_OBJECT",
                "EFFECT_BEARING",
                "ADMIT_EVIDENCE",
            ),
            _record(
                "S2",
                "CONTEXTUAL_OBJECT",
                "CONTEXT_ONLY",
                "RETAIN_CONTEXT",
            ),
        ],
    )

    assert validate_typed_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    ) == []
    partition = compile_typed_partition(item=item, receipt=receipt)
    assert partition["evidence_span_ids"] == ["S1"]
    assert partition["context_span_ids"] == ["S2"]
    assert partition["abstention_required"] is False


def test_utility_disposition_conflict_and_forced_label_fail_closed():
    item = _item()
    receipt = _receipt(
        item,
        state="EVIDENCE_AVAILABLE",
        records=[
            _record(
                "S1",
                "EXACT_OBJECT",
                "CONTEXT_ONLY",
                "ADMIT_EVIDENCE",
            ),
            _record(
                "S2",
                "IRRELEVANT_OBJECT",
                "NONE",
                "REJECT",
            ),
        ],
    )
    receipt["predicted_label"] = "INCREASED"
    failures = validate_typed_admission(
        receipt=receipt,
        item=item,
        refs=REFS,
    )
    assert "ADMISSION_V2_PREMATURE_LABEL_AUTHORITY" in failures
    assert "ADMISSION_V2_UTILITY_DISPOSITION_CONFLICT" in failures


def _item():
    return {
        "case_id": "SYNTHETIC-ADMISSION-V2",
        "object": {
            "intervention": "intervention",
            "comparator": "comparator",
            "outcome": "outcome",
        },
        "candidate_spans": [
            {"span_id": "S1", "text": "context"},
            {"span_id": "S2", "text": "unrelated"},
        ],
    }


def _receipt(item, *, state, records):
    return {
        "case_id": item["case_id"],
        "mechanism": "A11_TYPED_EVIDENCE_ADMISSION",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "admission_state": state,
        "records": records,
        "evidence_refs": list(REFS),
    }


def _record(span_id, relation, utility, disposition):
    return {
        "span_id": span_id,
        "object_relation": relation,
        "evidence_utility": utility,
        "disposition": disposition,
        "rationale": "bounded synthetic rationale",
    }
