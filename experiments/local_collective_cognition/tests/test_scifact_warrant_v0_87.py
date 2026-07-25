from local_collective_cognition.factorized_benchmarks.kernel_utility import (
    compile_warrant_candidate,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_87_evaluation import (
    _best_rationale_score,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_87_posthoc import (
    _score_official_sentences,
)
from local_collective_cognition.factorized_benchmarks.semantic_warrant import (
    validate_warrant,
)
from local_collective_cognition.provider_telemetry import hash_payload


def test_alternative_complete_rationale_set_scores_perfectly():
    assert _best_rationale_score(
        {"10:7"},
        [["10:2", "10:5"], ["10:7"]],
    ) == (1.0, 1.0, 1.0)


def test_official_sentence_metric_counts_all_overselection():
    row = _score_official_sentences(
        case_id="7",
        gold_state="SUPPORTED",
        gold_sets=[["10:0"], ["10:1"]],
        receipt={
            "claim_state": "SUPPORTED",
            "selected_unit_ids": ["10:0", "10:1", "10:2"],
        },
    )

    assert row["correct_sentence_count"] == 2
    assert row["predicted_sentence_count"] == 3
    assert row["overselected_sentence_count"] == 1


def test_official_sentence_metric_requires_complete_gold_set():
    row = _score_official_sentences(
        case_id="7",
        gold_state="REFUTED",
        gold_sets=[["10:0", "10:1"]],
        receipt={
            "claim_state": "REFUTED",
            "selected_unit_ids": ["10:1"],
        },
    )

    assert row["correct_sentence_count"] == 0
    assert row["incomplete_gold_set_count"] == 1


def test_strong_warrant_requires_grounding():
    case = _public_case()
    receipt = _receipt(case, state="SUPPORTED", selected=[])

    failures = validate_warrant(receipt, public_case=case)

    assert "SEMANTIC_WARRANT_STRONG_STATE_UNGROUNDED" in failures


def test_nei_rejects_selected_rationale():
    case = _public_case()
    receipt = _receipt(
        case,
        state="NOT_ENOUGH_INFO",
        selected=["10:0"],
    )

    failures = validate_warrant(receipt, public_case=case)

    assert "SEMANTIC_WARRANT_NEI_HAS_RATIONALE" in failures


def test_provider_cannot_add_policy_action():
    case = _public_case()
    receipt = _receipt(case, state="SUPPORTED", selected=["10:0"])
    receipt["promotion"] = "ACCEPT"

    failures = validate_warrant(receipt, public_case=case)

    assert "SEMANTIC_WARRANT_SHAPE_INVALID" in failures
    assert "SEMANTIC_WARRANT_POLICY_AUTHORITY_PRESENT" in failures


def test_kernel_compiles_candidate_without_write_authority():
    case = _public_case()
    receipt = _receipt(case, state="REFUTED", selected=["10:0"])

    candidate = compile_warrant_candidate(
        public_case=case,
        receipt=receipt,
    )

    assert candidate["runtime_action"] == "OPEN_REFUTATION_CANDIDATE"
    assert candidate["candidate_only"] is True
    assert candidate["promotion_authorized"] is False
    assert candidate["core_write_allowed"] is False
    assert candidate["retention_write_allowed"] is False


def _public_case():
    return {
        "benchmark_id": "SCIFACT",
        "case_id": "7",
        "layer": "SEMANTIC_WARRANT",
        "cognitive_object": {"claim": "Treatment reduces mortality."},
        "evidence_units": [
            {
                "unit_id": "10:0",
                "text": "Mortality was reduced.",
                "source_object_id": "10",
                "metadata": {"title": "Trial", "sentence_index": 0},
            }
        ],
        "source_revision": "a" * 40,
        "private_reference_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }


def _receipt(case, *, state, selected):
    return {
        "case_id": case["case_id"],
        "receipt_kind": "SEMANTIC_WARRANT",
        "source_public_case_hash": hash_payload(case),
        "claim_state": state,
        "selected_unit_ids": selected,
        "all_units_assessed": True,
        "uncertainty_state": "RESOLVED",
        "rationale": "The selected sentence directly resolves the claim.",
    }
