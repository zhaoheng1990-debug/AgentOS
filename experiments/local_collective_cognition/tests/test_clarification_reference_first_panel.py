from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.clarification_joint_holdout import CASES as V013_CASES  # noqa: E402
from local_collective_cognition.clarification_reference_first_holdout import (  # noqa: E402
    CASES,
    build_reference_first_holdout,
    validate_reference_first_holdout,
)
from local_collective_cognition.clarification_reference_first_panel import (  # noqa: E402
    ADJUDICATION_VERSION,
    PANEL_VERSION,
    adjudication_response_contract,
    annotation_response_contract,
    build_reference_first_adjudication,
    build_reference_first_agreement_analysis,
    build_reference_first_final_analysis,
    build_reference_first_panel,
    build_reference_first_reference,
    validate_reference_first_adjudication,
    validate_reference_first_adjudication_response,
    validate_reference_first_agreement_analysis,
    validate_reference_first_annotation_response,
    validate_reference_first_panel,
    validate_reference_first_final_analysis,
    validate_reference_first_reference,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


OPEN_TUPLE = {
    "SELECTED_OBJECT": "NONE",
    "SELECTION_BASIS": "NO_PREFERENCE",
    "PRAGMATIC_PREFERENCE": "NONE",
    "AXIS_ASSESSMENT_COMPLETE": "COMPLETE",
}
FIXED_A_TUPLE = {
    "SELECTED_OBJECT": "CANDIDATE_A",
    "SELECTION_BASIS": "LEXICAL_EXACT",
    "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
    "AXIS_ASSESSMENT_COMPLETE": "COMPLETE",
}


def annotation_response(pack, *, first_tuple=None):
    contract = annotation_response_contract()
    labels = []
    for index, item in enumerate(pack["items"]):
        criteria = dict(first_tuple if index == 0 and first_tuple is not None else OPEN_TUPLE)
        labels.append({
            "annotation_id": item["annotation_id"],
            "criteria": criteria,
            "criterion_notes": {criterion: "Fixture note for the complete semantic object." for criterion in criteria},
            "criterion_confidence": {criterion: 0.8 for criterion in criteria},
            "tuple_rationale": "The four criteria form one coherent fixture position.",
        })
    return {
        "panel_version": PANEL_VERSION,
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "fixture-" + pack["lane_id"],
        "blinding_attestation": contract["required_blinding_attestation"],
        "labels": labels,
    }


def adjudication_response(pack):
    contract = adjudication_response_contract()
    decisions = []
    for item in pack["items"]:
        position = item["anonymous_full_tuple_positions"][0]
        decisions.append({
            "adjudication_id": item["adjudication_id"],
            "criteria": position["criteria"],
            "decision_basis": position["position_id"],
            "confidence": 0.8,
            "rationale": "The selected anonymous position is coherent as a whole.",
        })
    return {
        "panel_version": PANEL_VERSION,
        "adjudication_version": ADJUDICATION_VERSION,
        "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": pack["expected_adjudicator"]["provider"],
        "adjudicator_model": pack["expected_adjudicator"]["model"],
        "adjudication_session_ref": "fixture-full-tuple-adjudication",
        "blinding_attestation": contract["required_blinding_attestation"],
        "decisions": decisions,
    }


def test_reference_first_holdout_is_fresh_balanced_and_has_no_semantic_oracle():
    artifact = build_reference_first_holdout()
    validate_reference_first_holdout(artifact)
    assert artifact["corpus_spec"]["semantic_labels_present"] is False
    assert artifact["corpus_spec"]["construction_truth_present"] is False
    assert artifact["candidate_run_allowed"] is False
    assert set(artifact["corpus_spec"]["object_family_counts"].values()) == {4}
    old_prompts = {case.public_prompt for case in V013_CASES}
    assert not old_prompts.intersection(case.public_prompt for case in CASES)
    assert all(set(binding) == {"case_id", "object_family", "public_item_hash"} for binding in artifact["private_provenance"]["bindings"].values())


def test_reference_first_panel_is_deterministic_and_candidate_output_blind():
    corpus = build_reference_first_holdout()
    packs, manifest = build_reference_first_panel(corpus_artifact=corpus)
    validate_reference_first_panel(packs=packs, manifest=manifest, corpus_artifact=corpus)
    assert manifest["candidate_count"] == 24
    assert manifest["reference_must_precede_candidate_run"] is True
    assert all(pack["candidate_coordinator_output"] == "NOT_YET_CREATED" for pack in packs)
    assert all(pack["construction_labels"] == "DO_NOT_EXIST" for pack in packs)


def test_reference_first_annotation_rejects_incoherent_tuple():
    packs, _ = build_reference_first_panel(corpus_artifact=build_reference_first_holdout())
    response = annotation_response(packs[0])
    response["labels"][0]["criteria"]["PRAGMATIC_PREFERENCE"] = "CANDIDATE_A"
    with pytest.raises(ValueError, match="reference_first_annotation_tuple_incoherent"):
        validate_reference_first_annotation_response(response, pack=packs[0])


def test_reference_first_disagreement_is_adjudicated_as_full_tuple():
    corpus = build_reference_first_holdout()
    packs, panel_manifest = build_reference_first_panel(corpus_artifact=corpus)
    responses = (annotation_response(packs[0]), annotation_response(packs[1], first_tuple=FIXED_A_TUPLE))
    adjudication_pack, adjudication_manifest = build_reference_first_adjudication(
        packs=packs, panel_manifest=panel_manifest, responses=responses
    )
    validate_reference_first_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        panel_inputs={"packs": packs, "panel_manifest": panel_manifest, "responses": responses},
    )
    assert adjudication_manifest["agreement_object_count"] == 23
    assert adjudication_manifest["disagreement_object_count"] == 1
    item = adjudication_pack["items"][0]
    assert set(item) == {"adjudication_id", "public_prompt", "candidate_a", "candidate_b", "anonymous_full_tuple_positions"}
    assert all(set(position["criteria"]) == set(OPEN_TUPLE) for position in item["anonymous_full_tuple_positions"])
    response = adjudication_response(adjudication_pack)
    validate_reference_first_adjudication_response(response, pack=adjudication_pack)
    reference = build_reference_first_reference(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        response=response,
    )
    validate_reference_first_reference(
        reference,
        source_inputs={"adjudication_pack": adjudication_pack, "adjudication_manifest": adjudication_manifest, "response": response},
    )
    assert reference["cross_axis_coherence_passed"] is True
    assert reference["frozen_before_candidate_run"] is True


def test_reference_first_panel_and_adjudication_reject_tamper():
    packs, panel_manifest = build_reference_first_panel(corpus_artifact=build_reference_first_holdout())
    tampered = deepcopy(packs[0])
    tampered["items"][0]["candidate_a"] = "tampered"
    with pytest.raises(ValueError, match="reference_first_panel_pack_binding_invalid"):
        validate_reference_first_panel(packs=(tampered, packs[1]), manifest=panel_manifest)
    responses = (annotation_response(packs[0]), annotation_response(packs[1], first_tuple=FIXED_A_TUPLE))
    adjudication_pack, adjudication_manifest = build_reference_first_adjudication(
        packs=packs, panel_manifest=panel_manifest, responses=responses
    )
    tampered_manifest = deepcopy(adjudication_manifest)
    tampered_manifest["agreement_object_count"] = 0
    with pytest.raises(ValueError, match="reference_first_adjudication_invalid"):
        validate_reference_first_adjudication(pack=adjudication_pack, manifest=tampered_manifest)
    identity_leak = deepcopy(adjudication_pack)
    identity_leak["items"][0]["anonymous_full_tuple_positions"][0]["tuple_rationale"] = "OpenAI position"
    identity_leak["pack_hash"] = hash_payload({key: value for key, value in identity_leak.items() if key != "pack_hash"})
    leak_manifest = deepcopy(adjudication_manifest)
    leak_manifest["adjudication_pack_hash"] = identity_leak["pack_hash"]
    leak_manifest["manifest_hash"] = hash_payload({key: value for key, value in leak_manifest.items() if key != "manifest_hash"})
    with pytest.raises(ValueError, match="reference_first_adjudication_identity_leak"):
        validate_reference_first_adjudication(pack=identity_leak, manifest=leak_manifest)
    response = adjudication_response(adjudication_pack)
    response["decisions"][0]["criteria"] = dict(OPEN_TUPLE)
    response["decisions"][0]["criteria"]["PRAGMATIC_PREFERENCE"] = "CANDIDATE_B"
    response["decisions"][0]["decision_basis"] = "INDEPENDENT_REASSESSMENT"
    with pytest.raises(ValueError, match="reference_first_adjudication_tuple_incoherent"):
        validate_reference_first_adjudication_response(response, pack=adjudication_pack)


def test_reference_first_agreement_analysis_separates_material_disagreement():
    corpus = build_reference_first_holdout()
    packs, panel_manifest = build_reference_first_panel(corpus_artifact=corpus)
    responses = (annotation_response(packs[0]), annotation_response(packs[1], first_tuple=FIXED_A_TUPLE))
    adjudication_pack, adjudication_manifest = build_reference_first_adjudication(
        packs=packs, panel_manifest=panel_manifest, responses=responses
    )
    analysis = build_reference_first_agreement_analysis(
        corpus_artifact=corpus,
        panel_manifest=panel_manifest,
        responses=responses,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    validate_reference_first_agreement_analysis(
        analysis,
        corpus_artifact=corpus,
        panel_manifest=panel_manifest,
        responses=responses,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    assert analysis["full_tuple_agreement_count"] == 23
    assert analysis["disagreement_object_counts_by_class"] == {"MATERIAL_SEMANTIC_COMMITMENT": 1}
    tampered = deepcopy(analysis)
    tampered["full_tuple_agreement_count"] = 24
    with pytest.raises(ValueError, match="reference_first_agreement_analysis_invalid"):
        validate_reference_first_agreement_analysis(
            tampered,
            corpus_artifact=corpus,
            panel_manifest=panel_manifest,
            responses=responses,
            adjudication_pack=adjudication_pack,
            adjudication_manifest=adjudication_manifest,
        )


def test_reference_first_final_analysis_freezes_reference_before_candidate_run():
    corpus = build_reference_first_holdout()
    packs, panel_manifest = build_reference_first_panel(corpus_artifact=corpus)
    responses = (annotation_response(packs[0]), annotation_response(packs[1], first_tuple=FIXED_A_TUPLE))
    adjudication_pack, adjudication_manifest = build_reference_first_adjudication(
        packs=packs, panel_manifest=panel_manifest, responses=responses
    )
    agreement = build_reference_first_agreement_analysis(
        corpus_artifact=corpus,
        panel_manifest=panel_manifest,
        responses=responses,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    response = adjudication_response(adjudication_pack)
    reference = build_reference_first_reference(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        response=response,
    )
    analysis = build_reference_first_final_analysis(
        corpus_artifact=corpus,
        agreement_analysis=agreement,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        response=response,
        reference=reference,
    )
    validate_reference_first_final_analysis(
        analysis,
        corpus_artifact=corpus,
        agreement_analysis=agreement,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        response=response,
        reference=reference,
    )
    assert analysis["candidate_state"] == "REFERENCE_FIRST_MODEL_PANEL_REFERENCE_FROZEN"
    assert analysis["local_role_collection_allowed"] is True
    assert analysis["coordinator_run_allowed"] is False
    assert analysis["reference_revision_allowed"] is False
