from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_evidence_factorial_holdout import (  # noqa: E402
    build_factorial_holdout,
)
from local_collective_cognition.cognitive_action_evidence_factorial_panel import (  # noqa: E402
    build_factorial_external_adjudication,
    build_factorial_external_panel,
    validate_factorial_adjudication_response,
    validate_factorial_annotation_response,
    validate_factorial_external_adjudication,
    validate_factorial_external_panel,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def frozen_run(corpus):
    commitment = {
        "source_corpus_hash": corpus["artifact_hash"],
        "candidate_outputs_frozen_before_external_reference": True,
        "outputs": [],
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def response_for(pack, alternate_first=False):
    criteria = {
        "SELECTED_OBJECT": "NONE",
        "SELECTION_BASIS": "NO_PREFERENCE",
        "PRAGMATIC_PREFERENCE": "NONE",
        "EVIDENCE_STATE": "SOFT_AMBIGUITY",
        "ASSESSMENT_PROCESS_STATE": "COMPLETE",
    }
    labels = [{
        "annotation_id": item["annotation_id"],
        "criteria": (
            {
                "SELECTED_OBJECT": "CANDIDATE_A",
                "SELECTION_BASIS": "LEXICAL_EXACT",
                "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
                "EVIDENCE_STATE": "DIRECTLY_DEFINED",
                "ASSESSMENT_PROCESS_STATE": "COMPLETE",
            }
            if alternate_first and index == 0
            else criteria
        ),
        "criterion_notes": {
            axis: "Fixture note." for axis in criteria
        },
        "criterion_confidence": {
            axis: 0.9 for axis in criteria
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


def test_factorial_panel_hides_candidate_policies_and_validates_responses():
    corpus = build_factorial_holdout()
    run = frozen_run(corpus)
    packs, manifest = build_factorial_external_panel(
        corpus=corpus,
        run=run,
    )
    validate_factorial_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert manifest["factorial_policies_exposed_to_annotators"] is False
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )
    validate_factorial_annotation_response(
        response_for(packs[0]),
        pack=packs[0],
    )


def test_factorial_disagreements_build_anonymous_whole_tuple_pack():
    corpus = build_factorial_holdout()
    run = frozen_run(corpus)
    packs, panel_manifest = build_factorial_external_panel(
        corpus=corpus,
        run=run,
    )
    responses = (
        response_for(packs[0]),
        response_for(packs[1], alternate_first=True),
    )
    adjudication_pack, adjudication_manifest = (
        build_factorial_external_adjudication(
            packs=packs,
            panel_manifest=panel_manifest,
            responses=responses,
            corpus=corpus,
        )
    )
    validate_factorial_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs={
            "packs": packs,
            "panel_manifest": panel_manifest,
            "responses": responses,
            "corpus": corpus,
        },
    )
    assert adjudication_manifest["agreement_object_count"] == 23
    assert adjudication_manifest["disagreement_object_count"] == 1
    item = adjudication_pack["items"][0]
    position = item["anonymous_full_tuple_positions"][0]
    response = {
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
            "adjudication_id": item["adjudication_id"],
            "criteria": position["criteria"],
            "decision_basis": position["position_id"],
            "confidence": 0.9,
            "rationale": "Fixture adjudication.",
        }],
    }
    validate_factorial_adjudication_response(
        response,
        pack=adjudication_pack,
    )
