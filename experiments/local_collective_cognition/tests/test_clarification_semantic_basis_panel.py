from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.clarification_semantic_basis_holdout import build_semantic_basis_holdout_artifact  # noqa: E402
from local_collective_cognition.clarification_semantic_basis_panel import build_semantic_basis_adjudication, build_semantic_basis_panel, build_semantic_basis_reference, validate_semantic_basis_adjudication, validate_semantic_basis_adjudication_response, validate_semantic_basis_annotation_response, validate_semantic_basis_panel, validate_semantic_basis_reference  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def test_semantic_basis_panel_is_deterministic_and_blinded():
    corpus = build_semantic_basis_holdout_artifact()
    packs, manifest = build_semantic_basis_panel(corpus_artifact=corpus)
    validate_semantic_basis_panel(packs=packs, manifest=manifest, corpus_artifact=corpus)
    assert manifest["candidate_count"] == 24
    assert manifest["criterion_count"] == 4
    assert all(pack["construction_labels"] == "WITHHELD" and pack["deepseek_outputs"] == "WITHHELD" for pack in packs)


def test_semantic_basis_panel_response_contract_and_tamper_rejection():
    packs, manifest = build_semantic_basis_panel(corpus_artifact=build_semantic_basis_holdout_artifact())
    pack = packs[0]
    labels = []
    for item in pack["items"]:
        criteria = {"SELECTED_OBJECT": "NONE", "SELECTION_BASIS": "NO_PREFERENCE", "PRAGMATIC_PREFERENCE": "NONE", "AXIS_ASSESSMENT_COMPLETE": "COMPLETE"}
        labels.append({"annotation_id": item["annotation_id"], "criteria": criteria, "criterion_notes": {key: "Fixture note." for key in criteria}, "criterion_confidence": {key: 0.8 for key in criteria}})
    response = {
        "panel_version": pack["panel_version"], "panel_id": pack["panel_id"], "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"], "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"], "annotation_session_ref": "fixture", "labels": labels,
    }
    validate_semantic_basis_annotation_response(response, pack=pack)
    tampered = deepcopy(pack)
    tampered["items"][0]["candidate_a"] = "tampered"
    tampered["pack_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "pack_hash"})
    with pytest.raises(ValueError, match="pack_binding_invalid"):
        validate_semantic_basis_panel(packs=(tampered, packs[1]), manifest=manifest)


def test_semantic_basis_disagreements_are_reduced_to_anonymous_k3_cells():
    packs, panel_manifest = build_semantic_basis_panel(corpus_artifact=build_semantic_basis_holdout_artifact())
    responses = []
    for pack in packs:
        labels = []
        for item in pack["items"]:
            criteria = {"SELECTED_OBJECT": "NONE", "SELECTION_BASIS": "NO_PREFERENCE", "PRAGMATIC_PREFERENCE": "NONE", "AXIS_ASSESSMENT_COMPLETE": "COMPLETE"}
            labels.append({"annotation_id": item["annotation_id"], "criteria": criteria, "criterion_notes": {key: "Fixture note." for key in criteria}, "criterion_confidence": {key: 0.8 for key in criteria}})
        if pack["lane_id"] == "annotation-lane-b":
            labels[0]["criteria"]["SELECTED_OBJECT"] = "CANDIDATE_A"
        responses.append({
            "panel_version": pack["panel_version"], "panel_id": pack["panel_id"], "lane_id": pack["lane_id"],
            "pack_hash": pack["pack_hash"], "annotator_provider": pack["expected_annotator"]["provider"],
            "annotator_model": pack["expected_annotator"]["model"], "annotation_session_ref": "fixture-" + pack["lane_id"], "labels": labels,
        })
    k3_pack, k3_manifest = build_semantic_basis_adjudication(packs=packs, panel_manifest=panel_manifest, responses=responses)
    validate_semantic_basis_adjudication(pack=k3_pack, manifest=k3_manifest, panel_packs=packs, panel_manifest=panel_manifest, responses=responses)
    assert k3_manifest["agreement_count"] == 95
    assert k3_manifest["disagreement_count"] == 1
    assert k3_pack["annotator_identity"] == "WITHHELD"
    item = k3_pack["items"][0]
    selected_position = item["positions"][0]
    response = {
        "panel_version": k3_pack["panel_version"], "panel_id": k3_pack["panel_id"],
        "adjudication_pack_hash": k3_pack["pack_hash"], "adjudicator_provider": "Moonshot", "adjudicator_model": "Kimi-K3",
        "adjudication_session_ref": "fixture-k3",
        "blinding_attestation": {"pack_only_context": True, "annotator_identity_unavailable": True, "source_identity_unavailable": True, "construction_labels_unavailable": True, "deepseek_outputs_unavailable": True, "prior_scores_unavailable": True, "external_pairing_not_used": True},
        "decisions": [{"adjudication_id": item["adjudication_id"], "selected_state": selected_position["state"], "decision_basis": selected_position["position_id"], "confidence": 0.8, "rationale": "Fixture adjudication."}],
    }
    validate_semantic_basis_adjudication_response(response, pack=k3_pack)
    reference = build_semantic_basis_reference(adjudication_pack=k3_pack, adjudication_manifest=k3_manifest, response=response)
    validate_semantic_basis_reference(reference, adjudication_pack=k3_pack, adjudication_manifest=k3_manifest, response=response)
    assert reference["label_count"] == 96
    assert reference["cross_axis_coherence_passed"] is False
    assert reference["candidate_state"] == "SEMANTIC_BASIS_MODEL_PANEL_REFERENCE_COHERENCE_FAILED"
