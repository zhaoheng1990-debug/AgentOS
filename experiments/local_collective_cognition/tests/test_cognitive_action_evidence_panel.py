from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_evidence_calibrator import build_evidence_preregistration, run_evidence_arms, SOURCE_EVALUATION_HASH, SOURCE_REFERENCE_HASH  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_holdout import build_evidence_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_panel import (  # noqa: E402
    build_evidence_external_adjudication,
    build_evidence_external_panel,
    validate_evidence_annotation_response,
    validate_evidence_external_adjudication,
    validate_evidence_external_panel,
)
from tests.test_cognitive_action_evidence_calibrator import FixtureProvider  # noqa: E402


def test_evidence_panel_is_candidate_blind_and_lane_separated():
    corpus = build_evidence_holdout()
    prereg = build_evidence_preregistration(source_evaluation={
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": "SELECTIVE_ESCALATION_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION",
    })
    run = run_evidence_arms(corpus=corpus, preregistration=prereg, adapter=FixtureProvider())
    packs, manifest = build_evidence_external_panel(corpus=corpus, run=run)
    validate_evidence_external_panel(packs=packs, manifest=manifest)
    assert len(packs) == 2
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )


def response_for(pack, alternate_first=False):
    labels = []
    for index, item in enumerate(pack["items"]):
        criteria = {
            "SELECTED_OBJECT": "CANDIDATE_A",
            "SELECTION_BASIS": "LEXICAL_EXACT",
            "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
            "EVIDENCE_STATE": "DIRECTLY_DEFINED",
            "ASSESSMENT_PROCESS_STATE": "COMPLETE",
        }
        if alternate_first and index == 0:
            criteria = {
                "SELECTED_OBJECT": "NONE",
                "SELECTION_BASIS": "NO_PREFERENCE",
                "PRAGMATIC_PREFERENCE": "NONE",
                "EVIDENCE_STATE": "SOFT_AMBIGUITY",
                "ASSESSMENT_PROCESS_STATE": "COMPLETE",
            }
        labels.append({
            "annotation_id": item["annotation_id"],
            "criteria": criteria,
            "criterion_notes": {axis: "Fixture note." for axis in criteria},
            "criterion_confidence": {axis: 0.9 for axis in criteria},
            "tuple_rationale": "Fixture rationale.",
        })
    return {
        "panel_version": pack["panel_version"],
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "fixture",
        "blinding_attestation": pack["response_contract"]["required_blinding_attestation"],
        "labels": labels,
    }


def test_evidence_responses_build_anonymous_adjudication():
    corpus = build_evidence_holdout()
    prereg = build_evidence_preregistration(source_evaluation={
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": "SELECTIVE_ESCALATION_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION",
    })
    run = run_evidence_arms(corpus=corpus, preregistration=prereg, adapter=FixtureProvider())
    packs, manifest = build_evidence_external_panel(corpus=corpus, run=run)
    responses = (response_for(packs[0]), response_for(packs[1], True))
    for response, pack in zip(responses, packs):
        validate_evidence_annotation_response(response, pack=pack)
    adjudication_pack, adjudication_manifest = build_evidence_external_adjudication(
        packs=packs, panel_manifest=manifest, responses=responses, corpus=corpus
    )
    validate_evidence_external_adjudication(
        pack=adjudication_pack, manifest=adjudication_manifest
    )
    assert adjudication_manifest["agreement_object_count"] == 23
    assert adjudication_manifest["disagreement_object_count"] == 1
