from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    K3_SPEC,
    build_selective_external_adjudication,
    build_selective_external_panel,
    validate_selective_adjudication_response,
    validate_selective_annotation_response,
    validate_selective_external_adjudication,
    validate_selective_external_panel,
)
from local_collective_cognition.tests_support import build_selective_fixture_bundle  # noqa: E402


def test_selective_panel_blinds_design_and_candidate_outputs():
    corpus, baseline, run = build_selective_fixture_bundle()
    packs, manifest = build_selective_external_panel(
        corpus=corpus,
        baseline_run=baseline,
        selective_run=run,
    )
    validate_selective_external_panel(packs=packs, manifest=manifest)
    assert len(packs) == 2
    assert manifest["criterion_count"] == 5
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )
    assert "design_stratum_counts" not in str(packs)


def response_for(pack, *, alternate_first=False):
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
                "EVIDENCE_STATE": "OPAQUE_REFERENCE",
                "ASSESSMENT_PROCESS_STATE": "COMPLETE",
            }
        labels.append({
            "annotation_id": item["annotation_id"],
            "criteria": criteria,
            "criterion_notes": {
                criterion: "Fixture note." for criterion in criteria
            },
            "criterion_confidence": {
                criterion: 0.9 for criterion in criteria
            },
            "tuple_rationale": "Fixture rationale.",
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


def test_selective_annotations_build_anonymous_whole_tuple_adjudication():
    corpus, baseline, run = build_selective_fixture_bundle()
    packs, panel_manifest = build_selective_external_panel(
        corpus=corpus,
        baseline_run=baseline,
        selective_run=run,
    )
    responses = (
        response_for(packs[0]),
        response_for(packs[1], alternate_first=True),
    )
    for response, pack in zip(responses, packs):
        validate_selective_annotation_response(response, pack=pack)
    adjudication_pack, adjudication_manifest = build_selective_external_adjudication(
        packs=packs,
        panel_manifest=panel_manifest,
        responses=responses,
        corpus=corpus,
    )
    validate_selective_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    assert adjudication_manifest["agreement_object_count"] == 23
    assert adjudication_manifest["disagreement_object_count"] == 1
    assert "gpt-5.6" not in str(adjudication_pack).casefold()
    item = adjudication_pack["items"][0]
    position = item["anonymous_full_tuple_positions"][0]
    response = {
        "panel_version": adjudication_pack["panel_version"],
        "adjudication_version": adjudication_pack["adjudication_version"],
        "panel_id": adjudication_pack["panel_id"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudicator_provider": K3_SPEC[0],
        "adjudicator_model": K3_SPEC[1],
        "adjudication_session_ref": "fixture-k3-session",
        "blinding_attestation": adjudication_pack["response_contract"]["required_blinding_attestation"],
        "decisions": [{
            "adjudication_id": item["adjudication_id"],
            "criteria": position["criteria"],
            "decision_basis": position["position_id"],
            "confidence": 0.9,
            "rationale": "Fixture whole-tuple selection.",
        }],
    }
    validate_selective_adjudication_response(response, pack=adjudication_pack)
