from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_axis_holdout import build_axis_routing_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_axis_panel import (  # noqa: E402
    build_axis_external_adjudication,
    build_axis_external_panel,
    validate_axis_annotation_response,
    validate_axis_external_adjudication,
    validate_axis_external_panel,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def fixture_run(corpus):
    commitment = {
        "source_corpus_hash": corpus["artifact_hash"],
        "tuple_outputs": [],
        "basis_outputs": [],
        "routed_outputs": [],
        "failures": [],
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
    }
    # Panel construction only needs a validated freeze boundary; detailed run
    # validation is exercised by the routing tests.
    return {**commitment, "run_hash": hash_payload(commitment)}


def test_axis_panel_keeps_candidate_outputs_out_of_public_lane_packs(monkeypatch):
    corpus = build_axis_routing_holdout()
    run = fixture_run(corpus)
    monkeypatch.setattr("local_collective_cognition.cognitive_action_axis_panel.validate_axis_routing_run", lambda **_: None)
    packs, manifest = build_axis_external_panel(corpus=corpus, run=run)
    validate_axis_external_panel(packs=packs, manifest=manifest)
    assert len(packs) == 2
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert set(packs[0]["response_contract"]["criteria"]) == {
        "SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"
    }
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )


def response_for(pack, *, alternate_first=False):
    criteria = {
        "SELECTED_OBJECT": "CANDIDATE_A",
        "SELECTION_BASIS": "LEXICAL_EXACT",
        "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
        "AXIS_ASSESSMENT_COMPLETE": "COMPLETE",
    }
    labels = []
    for index, item in enumerate(pack["items"]):
        selected = criteria
        if alternate_first and index == 0:
            selected = {
                "SELECTED_OBJECT": "NONE",
                "SELECTION_BASIS": "NO_PREFERENCE",
                "PRAGMATIC_PREFERENCE": "NONE",
                "AXIS_ASSESSMENT_COMPLETE": "COMPLETE",
            }
        labels.append({
            "annotation_id": item["annotation_id"],
            "criteria": dict(selected),
            "criterion_notes": {criterion: "Fixture note." for criterion in criteria},
            "criterion_confidence": {criterion: 0.9 for criterion in criteria},
            "tuple_rationale": "Fixture full-tuple rationale.",
        })
    return {
        "panel_version": pack["panel_version"],
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "fixture-session",
        "blinding_attestation": pack["response_contract"]["required_blinding_attestation"],
        "labels": labels,
    }


def test_axis_annotations_build_identity_blind_whole_tuple_adjudication(monkeypatch):
    corpus = build_axis_routing_holdout()
    run = fixture_run(corpus)
    monkeypatch.setattr("local_collective_cognition.cognitive_action_axis_panel.validate_axis_routing_run", lambda **_: None)
    packs, panel_manifest = build_axis_external_panel(corpus=corpus, run=run)
    responses = (response_for(packs[0]), response_for(packs[1], alternate_first=True))
    for response, pack in zip(responses, packs):
        validate_axis_annotation_response(response, pack=pack)
    adjudication_pack, adjudication_manifest = build_axis_external_adjudication(
        packs=packs, panel_manifest=panel_manifest, responses=responses, corpus=corpus
    )
    validate_axis_external_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    assert adjudication_manifest["agreement_object_count"] == 23
    assert adjudication_manifest["disagreement_object_count"] == 1
    assert len(adjudication_pack["items"]) == 1
    public = str(adjudication_pack).casefold()
    assert "gpt-5.6" not in public and "gemini-3.1" not in public
