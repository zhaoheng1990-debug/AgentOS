from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_first import (  # noqa: E402
    EVIDENCE_FIRST_TASK_KIND,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_evidence_first_run,
    build_evidence_first_preregistration,
    run_evidence_first_selective,
    validate_witness,
)
from local_collective_cognition.cognitive_action_evidence_first_holdout import (  # noqa: E402
    build_evidence_first_holdout,
    evidence_text,
    validate_evidence_first_holdout,
)
from local_collective_cognition.cognitive_action_evidence_first_evaluation import (  # noqa: E402
    build_evidence_first_external_evaluation,
    build_evidence_first_external_reference,
    validate_evidence_first_external_evaluation,
)
from local_collective_cognition.cognitive_action_evidence_first_panel import (  # noqa: E402
    build_evidence_first_external_adjudication,
    build_evidence_first_external_panel,
    validate_evidence_first_annotation_response,
    validate_evidence_first_adjudication_response,
    validate_evidence_first_external_adjudication,
    validate_evidence_first_external_panel,
)
from local_collective_cognition.cognitive_action_source_ontology_holdout import (  # noqa: E402
    build_source_ontology_holdout,
)


class EvidenceFirstFixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-evidence-first",
            model_id="fixture-model",
            task_kinds=(EVIDENCE_FIRST_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs
        stage = item["stage"]
        conflict_id = (
            item["public_object"]["conflict_id"]
            if stage == "BASELINE_SOURCE"
            else item["conflict_id"]
        )
        refs = list(task.allowed_evidence)
        if stage == "EVIDENCE_WITNESS":
            text = item["evidence_text"]
            result = {
                "conflict_id": conflict_id,
                "witness_mode": "COMPOSITIONAL_DERIVATION",
                "support_spans": [text],
                "derivation_steps": ["Combine the displayed constraints."],
                "candidate_option_text_used_as_evidence": False,
                "rationale": "The displayed premises form a derivation.",
                "confidence": 0.8,
                "evidence_refs": refs,
            }
        else:
            result = {
                "conflict_id": conflict_id,
                "selected_object": "CANDIDATE_A",
                "definition_source": (
                    "COMPOSED_CONSTRAINTS"
                    if stage == "WITNESS_BOUND_JUDGE"
                    else "EXPLICIT_REQUEST_DEFINITION"
                ),
                "pragmatic_preference": "CANDIDATE_A",
                "assessment_process_state": "COMPLETE",
                "support_quote": "Displayed evidence.",
                "rationale": "Fixture source judgment.",
                "confidence": 0.8,
                "evidence_refs": refs,
            }
        return {
            "result": result,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 10,
                "output_tokens": 2,
                "latency_ms": 1,
            },
            "provenance_refs": refs,
        }


def source_evaluation():
    return {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": (
            "SOURCE_ONTOLOGY_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }


def test_evidence_first_holdout_is_fresh_balanced_and_unlabeled():
    corpus = build_evidence_first_holdout()
    validate_evidence_first_holdout(corpus)
    previous = build_source_ontology_holdout()
    assert corpus["case_count"] == 16
    assert set(corpus["family_counts"].values()) == {4}
    assert set(corpus["design_stratum_counts"].values()) == {4}
    assert {
        item["public_prompt"] for item in corpus["public_surface"]["items"]
    }.isdisjoint({
        item["public_prompt"] for item in previous["public_surface"]["items"]
    })
    assert corpus["v0_21_reference_available_during_inference"] is False


def test_witness_requires_exact_pre_candidate_span():
    item = build_evidence_first_holdout()["public_surface"]["items"][0]
    refs = ("corpus://x",)
    receipt = {
        "conflict_id": item["conflict_id"],
        "witness_mode": "EVIDENCE_ABSENCE",
        "support_spans": [evidence_text(item)],
        "derivation_steps": [],
        "candidate_option_text_used_as_evidence": False,
        "rationale": "Exact displayed evidence.",
        "confidence": 0.8,
        "evidence_refs": list(refs),
    }
    validate_witness(receipt, item=item, evidence_refs=refs)
    receipt["support_spans"] = [item["candidate_a"]]
    with pytest.raises(ValueError, match="witness_invalid"):
        validate_witness(receipt, item=item, evidence_refs=refs)


def test_selective_challenge_reuses_baseline_on_unchallenged_objects():
    corpus = build_evidence_first_holdout()
    preregistration = build_evidence_first_preregistration(
        source_evaluation=source_evaluation()
    )
    run = run_evidence_first_selective(
        corpus=corpus,
        preregistration=preregistration,
        adapter=EvidenceFirstFixtureProvider(),
    )
    analysis = analyze_evidence_first_run(corpus=corpus, run=run)
    assert len(run["challenge_plan"]["admitted_conflict_ids"]) == 4
    assert len(run["provider_calls"]) == 24
    assert len(run["outputs"]) == 32
    assert not run["failures"]
    assert analysis["cell_coverage"] == {
        "BASELINE_LEGACY_SOURCE_REPAIRED_GATE": 1.0,
        "EVIDENCE_FIRST_SELECTIVE_CHALLENGE": 1.0,
    }
    assert analysis["witness_validation_rate"] == 1.0
    assert analysis["changed_object_count"] == 4


def test_evidence_first_external_panel_is_blinded_and_recomputable():
    corpus = build_evidence_first_holdout()
    preregistration = build_evidence_first_preregistration(
        source_evaluation=source_evaluation()
    )
    run = run_evidence_first_selective(
        corpus=corpus,
        preregistration=preregistration,
        adapter=EvidenceFirstFixtureProvider(),
    )
    packs, manifest = build_evidence_first_external_panel(
        corpus=corpus,
        run=run,
    )
    validate_evidence_first_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )


def annotation_response(pack, *, alternate_first=False):
    soft = {
        "SELECTED_OBJECT": "NONE",
        "SELECTION_BASIS": "NO_PREFERENCE",
        "PRAGMATIC_PREFERENCE": "NONE",
        "EVIDENCE_STATE": "SOFT_AMBIGUITY",
        "ASSESSMENT_PROCESS_STATE": "COMPLETE",
    }
    direct = {
        "SELECTED_OBJECT": "CANDIDATE_A",
        "SELECTION_BASIS": "LEXICAL_EXACT",
        "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
        "EVIDENCE_STATE": "DIRECTLY_DEFINED",
        "ASSESSMENT_PROCESS_STATE": "COMPLETE",
    }
    labels = [{
        "annotation_id": item["annotation_id"],
        "criteria": direct if alternate_first and index == 0 else soft,
        "criterion_notes": {
            axis: "Fixture note." for axis in soft
        },
        "criterion_confidence": {
            axis: 0.9 for axis in soft
        },
        "tuple_rationale": "Fixture rationale.",
    } for index, item in enumerate(pack["items"])]
    return {
        "panel_version": pack["panel_version"],
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "fixture",
        "blinding_attestation": (
            pack["response_contract"]["required_blinding_attestation"]
        ),
        "labels": labels,
    }


def test_evidence_first_annotations_build_anonymous_adjudication_pack():
    corpus = build_evidence_first_holdout()
    preregistration = build_evidence_first_preregistration(
        source_evaluation=source_evaluation()
    )
    run = run_evidence_first_selective(
        corpus=corpus,
        preregistration=preregistration,
        adapter=EvidenceFirstFixtureProvider(),
    )
    packs, panel_manifest = build_evidence_first_external_panel(
        corpus=corpus,
        run=run,
    )
    responses = (
        annotation_response(packs[0]),
        annotation_response(packs[1], alternate_first=True),
    )
    for response, pack in zip(responses, packs):
        validate_evidence_first_annotation_response(response, pack=pack)
    adjudication_pack, adjudication_manifest = (
        build_evidence_first_external_adjudication(
            packs=packs,
            panel_manifest=panel_manifest,
            responses=responses,
            corpus=corpus,
        )
    )
    validate_evidence_first_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs={
            "packs": packs,
            "panel_manifest": panel_manifest,
            "responses": responses,
            "corpus": corpus,
        },
    )
    assert adjudication_manifest["agreement_object_count"] == 15
    assert adjudication_manifest["disagreement_object_count"] == 1
    assert {
        position["position_id"]
        for position in adjudication_pack["items"][0][
            "anonymous_full_tuple_positions"
        ]
    } == {"POSITION_1", "POSITION_2"}
    assert "GPT-5.6" not in str(adjudication_pack)
    assert "Gemini-3.1" not in str(adjudication_pack)
    position = adjudication_pack["items"][0][
        "anonymous_full_tuple_positions"
    ][0]
    k3_response = {
        "panel_version": adjudication_pack["panel_version"],
        "adjudication_version": adjudication_pack["adjudication_version"],
        "panel_id": adjudication_pack["panel_id"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudicator_provider": "Moonshot",
        "adjudicator_model": "Kimi-K3",
        "adjudication_session_ref": "fixture",
        "blinding_attestation": (
            adjudication_pack["response_contract"][
                "required_blinding_attestation"
            ]
        ),
        "decisions": [{
            "adjudication_id": adjudication_pack["items"][0][
                "adjudication_id"
            ],
            "criteria": position["criteria"],
            "decision_basis": position["position_id"],
            "confidence": 0.9,
            "rationale": "Fixture adjudication.",
        }],
    }
    validate_evidence_first_adjudication_response(
        k3_response,
        pack=adjudication_pack,
    )
    reference = build_evidence_first_external_reference(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        adjudication_response=k3_response,
    )
    analysis = analyze_evidence_first_run(corpus=corpus, run=run)
    evaluation = build_evidence_first_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    validate_evidence_first_external_evaluation(
        evaluation,
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    assert reference["object_count"] == 16
    assert evaluation["anti_additive_gate"] == "REJECT"
