from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.clarification_joint_tuple_repair import (  # noqa: E402
    REPAIR_VERSION,
    build_joint_tuple_repair_analysis,
    build_joint_tuple_repair_pack,
    build_joint_tuple_repaired_reference,
    joint_tuple_repair_response_contract,
    validate_joint_tuple_repair_pack,
    validate_joint_tuple_repair_response,
    validate_joint_tuple_repair_analysis,
    validate_joint_tuple_repaired_reference,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


SOURCE = ROOT / "outputs" / "clarification_joint_fresh_v0_13"


def read(name):
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def source_inputs():
    return {
        "corpus_artifact": read("private_joint_corpus.json"),
        "panel_packs": (read("gpt_5_6_joint_fresh_pack.json"), read("gemini_3_1_joint_fresh_pack.json")),
        "panel_manifest": read("private_joint_fresh_panel_manifest.json"),
        "panel_responses": (read("gpt_5_6_joint_fresh_response.json"), read("gemini_3_1_joint_fresh_response.json")),
        "cell_adjudication_pack": read("kimi_k3_joint_fresh_adjudication_pack.json"),
        "cell_adjudication_manifest": read("private_joint_fresh_adjudication_manifest.json"),
        "cell_adjudication_response": read("kimi_k3_joint_fresh_response.json"),
        "panel_reference": read("joint_fresh_model_panel_reference_candidate.json"),
    }


def repaired_response(pack):
    contract = joint_tuple_repair_response_contract()
    decisions = []
    for item in pack["items"]:
        current = item["current_incoherent_tuple"]
        decisions.append({
            "repair_id": item["repair_id"],
            "selected_object": current["SELECTED_OBJECT"],
            "selection_basis": "PRAGMATIC_DEFAULT",
            "pragmatic_preference": current["PRAGMATIC_PREFERENCE"],
            "assessment_completeness": current["AXIS_ASSESSMENT_COMPLETE"],
            "changed_criteria": ["SELECTION_BASIS"],
            "confidence": 0.8,
            "rationale": "The object remains open while the directional preference is retained as pragmatic only.",
        })
    return {
        "repair_version": REPAIR_VERSION,
        "source_panel_id": pack["source_panel_id"],
        "repair_pack_hash": pack["pack_hash"],
        "adjudicator_provider": pack["expected_adjudicator"]["provider"],
        "adjudicator_model": pack["expected_adjudicator"]["model"],
        "repair_session_ref": "fixture-joint-tuple-repair",
        "blinding_attestation": contract["required_blinding_attestation"],
        "decisions": decisions,
    }


def test_joint_tuple_repair_pack_is_deterministic_and_identity_blind():
    inputs = source_inputs()
    pack, manifest = build_joint_tuple_repair_pack(**inputs)
    validate_joint_tuple_repair_pack(pack=pack, manifest=manifest, source_inputs=inputs)
    assert manifest["repair_count"] == 5
    assert all(set(item["criterion_evidence"]) == {"SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"} for item in pack["items"])
    assert all(item["coherence_violations"] for item in pack["items"])
    assert all(value == "WITHHELD" for key, value in pack.items() if key in {"source_identity", "annotator_identity", "prior_cell_adjudicator_identity", "construction_labels", "locked_consensus_axes", "deepseek_outputs", "prior_scores"})


def test_joint_tuple_repair_closes_all_reference_inconsistencies():
    inputs = source_inputs()
    pack, manifest = build_joint_tuple_repair_pack(**inputs)
    response = repaired_response(pack)
    validate_joint_tuple_repair_response(response, pack=pack)
    reference = build_joint_tuple_repaired_reference(
        source_reference=inputs["panel_reference"],
        repair_pack=pack,
        repair_manifest=manifest,
        repair_response=response,
    )
    validate_joint_tuple_repaired_reference(
        reference,
        source_reference=inputs["panel_reference"],
        repair_pack=pack,
        repair_manifest=manifest,
        repair_response=response,
    )
    assert reference["repair_count"] == 5
    assert reference["cross_axis_coherence_passed"] is True
    assert reference["cross_axis_inconsistency_count"] == 0
    assert reference["candidate_state"] == "JOINT_TUPLE_REPAIRED_MODEL_PANEL_REFERENCE_CANDIDATE"


def test_joint_tuple_repair_rejects_tamper_and_incoherent_response():
    inputs = source_inputs()
    pack, manifest = build_joint_tuple_repair_pack(**inputs)
    tampered = deepcopy(pack)
    tampered["items"][0]["candidate_a"] = "tampered"
    with pytest.raises(ValueError, match="joint_tuple_repair_hash_invalid"):
        validate_joint_tuple_repair_pack(pack=tampered, manifest=manifest)
    response = repaired_response(pack)
    response["decisions"][0]["changed_criteria"] = []
    with pytest.raises(ValueError, match="joint_tuple_repair_changed_criteria_invalid"):
        validate_joint_tuple_repair_response(response, pack=pack)
    response = repaired_response(pack)
    response["decisions"][0]["selection_basis"] = "NO_PREFERENCE"
    response["decisions"][0]["changed_criteria"] = ["SELECTION_BASIS"]
    with pytest.raises(ValueError, match="joint_tuple_repair_still_incoherent"):
        validate_joint_tuple_repair_response(response, pack=pack)


def test_joint_tuple_repaired_reference_rejects_hash_tamper():
    inputs = source_inputs()
    pack, manifest = build_joint_tuple_repair_pack(**inputs)
    response = repaired_response(pack)
    reference = build_joint_tuple_repaired_reference(
        source_reference=inputs["panel_reference"],
        repair_pack=pack,
        repair_manifest=manifest,
        repair_response=response,
    )
    tampered = deepcopy(reference)
    tampered["repair_records"][0]["confidence"] = 0.1
    with pytest.raises(ValueError, match="joint_tuple_repaired_reference_invalid"):
        validate_joint_tuple_repaired_reference(tampered)


def test_joint_tuple_repair_analysis_is_lineage_bound():
    from local_collective_cognition.clarification_joint_fresh_panel_calibration import build_joint_fresh_panel_calibration

    inputs = source_inputs()
    pack, manifest = build_joint_tuple_repair_pack(**inputs)
    response = repaired_response(pack)
    reference = build_joint_tuple_repaired_reference(
        source_reference=inputs["panel_reference"],
        repair_pack=pack,
        repair_manifest=manifest,
        repair_response=response,
    )
    run = read("candidate_run.json")
    prior = read("panel_recalibration.json")
    repaired = build_joint_fresh_panel_calibration(
        corpus_artifact=inputs["corpus_artifact"], run=run, panel_reference=reference
    )
    analysis = build_joint_tuple_repair_analysis(
        source_reference=inputs["panel_reference"],
        repaired_reference=reference,
        repair_response=response,
        prior_calibration=prior,
        repaired_calibration=repaired,
    )
    validate_joint_tuple_repair_analysis(
        analysis,
        source_reference=inputs["panel_reference"],
        repaired_reference=reference,
        repair_response=response,
        prior_calibration=prior,
        repaired_calibration=repaired,
    )
    tampered = deepcopy(repaired)
    tampered["candidate_metrics"]["full_tuple_accuracy"] = 0.0
    with pytest.raises(ValueError, match="joint_tuple_repair_analysis_lineage_invalid"):
        build_joint_tuple_repair_analysis(
            source_reference=inputs["panel_reference"],
            repaired_reference=reference,
            repair_response=response,
            prior_calibration=prior,
            repaired_calibration=tampered,
        )
