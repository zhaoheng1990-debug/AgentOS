import json

import pytest

from local_collective_cognition.factorized_benchmarks.acquisition import (
    verify_external_artifact,
)
from local_collective_cognition.factorized_benchmarks.catalog import (
    BENCHMARK_SOURCES,
    source_by_id,
)
from local_collective_cognition.factorized_benchmarks.contracts import (
    BenchmarkLayer,
    LicenseDisposition,
)
from local_collective_cognition.factorized_benchmarks.ebm_nlp import (
    build_case as build_ebm_case,
)
from local_collective_cognition.factorized_benchmarks.qasper import (
    build_cases as build_qasper_cases,
)
from local_collective_cognition.factorized_benchmarks.scifact import (
    build_case as build_scifact_case,
)


def test_catalog_factorizes_roles_and_forbids_redistribution():
    assert {source.layer for source in BENCHMARK_SOURCES} == {
        BenchmarkLayer.STUDY_OBJECT_BINDING,
        BenchmarkLayer.SEMANTIC_WARRANT,
        BenchmarkLayer.CONTEXT_UTILITY,
    }
    assert not any(source.redistribution_allowed for source in BENCHMARK_SOURCES)
    assert (
        source_by_id("EBM_NLP_2_00").license_disposition
        is LicenseDisposition.BLOCKED_LICENSE_UNCLEAR
    )


def test_acquisition_fails_closed_on_hash_mismatch(tmp_path):
    path = tmp_path / "artifact"
    path.write_bytes(b"wrong")

    receipt = verify_external_artifact(
        path,
        source_by_id("QASPER_LED_FIXTURE_AFD0FB9"),
    )

    assert receipt["verified"] is False
    assert receipt["failures"] == [
        "ARTIFACT_SIZE_MISMATCH",
        "ARTIFACT_SHA256_MISMATCH",
    ]
    assert receipt["core_write_allowed"] is False


def test_scifact_keeps_gold_out_of_public_surface():
    claim = {
        "id": 7,
        "claim": "Treatment reduces mortality.",
        "cited_doc_ids": [10],
        "evidence": {
            "10": [{"label": "SUPPORT", "sentences": [1]}],
        },
    }
    corpus = {
        10: {
            "title": "Trial",
            "abstract": ["Methods.", "Mortality was reduced."],
        }
    }

    public, private = build_scifact_case(claim, corpus)

    assert public.layer is BenchmarkLayer.SEMANTIC_WARRANT
    assert public.to_dict()["private_reference_exposed"] is False
    public_json = json.dumps(public.to_dict())
    assert "SUPPORT" not in public_json
    assert "supporting_unit_ids" not in public_json
    assert "gold_labels" not in public_json
    assert private.expected_state == "SUPPORTED"
    assert private.supporting_unit_ids == ("10:1",)


def test_ebm_nlp_keeps_object_spans_private():
    public, private = build_ebm_case(
        pmid="1",
        tokens=["Adults", "received", "drug", "for", "pain"],
        labels_by_kind={
            "participants": [1, 0, 0, 0, 0],
            "interventions": [0, 0, 3, 0, 0],
            "outcomes": [0, 0, 0, 0, 2],
        },
    )

    assert public.layer is BenchmarkLayer.STUDY_OBJECT_BINDING
    assert "gold_spans" not in public.to_dict()
    assert len(private.metadata["gold_spans"]) == 3


def test_ebm_nlp_rejects_misaligned_labels():
    with pytest.raises(
        ValueError,
        match="ebm_nlp_outcomes_label_length_mismatch",
    ):
        build_ebm_case(
            pmid="1",
            tokens=["Adults", "improved"],
            labels_by_kind={
                "participants": [1, 0],
                "interventions": [0, 0],
                "outcomes": [1],
            },
        )


def test_qasper_context_utility_maps_evidence_without_answers():
    article = {
        "abstract": "Abstract.",
        "full_text": [
            {
                "section_name": "Method",
                "paragraphs": ["The seed lexicon is a vocabulary."],
            }
        ],
        "qas": [
            {
                "question_id": "q1",
                "question": "What is the seed lexicon?",
                "answers": [
                    {
                        "answer": {
                            "unanswerable": False,
                            "extractive_spans": [],
                            "yes_no": None,
                            "free_form_answer": "a vocabulary",
                            "evidence": [
                                "The seed lexicon is a vocabulary.",
                            ],
                        }
                    }
                ],
            }
        ],
    }

    [(public, private)] = build_qasper_cases("paper", article)

    assert public.layer is BenchmarkLayer.CONTEXT_UTILITY
    assert public.cognitive_object == {
        "question": "What is the seed lexicon?"
    }
    assert "free_form_answer" not in json.dumps(public.to_dict())
    assert private.expected_state == "ANSWERABLE_WITH_CONTEXT"
    assert private.supporting_unit_ids == ("paper:paragraph:0",)
