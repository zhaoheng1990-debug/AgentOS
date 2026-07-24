from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_axis_evaluation import (  # noqa: E402
    build_axis_external_evaluation,
    build_axis_external_reference,
    validate_axis_external_reference,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def coherent_tuple():
    return {"SELECTED_OBJECT": "CANDIDATE_A", "SELECTION_BASIS": "LEXICAL_EXACT", "PRAGMATIC_PREFERENCE": "CANDIDATE_A", "AXIS_ASSESSMENT_COMPLETE": "COMPLETE"}


def test_external_reference_merges_agreements_and_k3_decisions(monkeypatch):
    monkeypatch.setattr("local_collective_cognition.cognitive_action_axis_evaluation.validate_axis_external_adjudication", lambda **_: None)
    monkeypatch.setattr("local_collective_cognition.cognitive_action_axis_evaluation.validate_axis_adjudication_response", lambda *_, **__: None)
    agreements = [
        {"conflict_id": f"c{index}", "selected_tuple": coherent_tuple(), "lane_annotation_ids": {"a": f"a{index}", "b": f"b{index}"}}
        for index in range(11)
    ]
    bindings = {f"d{index}": {"conflict_id": f"c{index + 11}"} for index in range(13)}
    manifest = {"panel_id": "p", "manifest_hash": "m", "agreement_records": agreements, "private_disagreement_bindings": bindings}
    pack = {"pack_hash": "k"}
    response = {"decisions": [{"adjudication_id": f"d{index}", "criteria": coherent_tuple(), "decision_basis": "POSITION_1", "confidence": 0.9} for index in range(13)]}
    reference = build_axis_external_reference(adjudication_pack=pack, adjudication_manifest=manifest, adjudication_response=response)
    validate_axis_external_reference(reference)
    assert reference["object_count"] == 24
    assert reference["source_counts"] == {"INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT": 11, "KIMI_K3_WHOLE_TUPLE_ADJUDICATION": 13}
    tampered = deepcopy(reference)
    tampered["labels"][0]["criteria"]["SELECTED_OBJECT"] = "NONE"
    tampered["artifact_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "artifact_hash"})
    with pytest.raises(ValueError, match="incoherent"):
        validate_axis_external_reference(tampered)


def test_missing_routed_output_is_scored_incorrect_and_harms_gate():
    truth = coherent_tuple()
    labels = [{"conflict_id": f"c{index}", "criteria": truth, "reference_source": "fixture", "source_refs": ["x"]} for index in range(24)]
    commitment = {
        "reference_version": "cognitive_action_axis_external_reference_v0_17", "panel_id": "p",
        "adjudication_manifest_hash": "m", "adjudication_pack_hash": "k", "adjudication_response_hash": "r",
        "labels": labels, "object_count": 24, "criterion_count": 96, "source_counts": {"fixture": 24},
        "candidate_outputs_exposed_to_panel": False, "cross_axis_coherence_passed": True,
        "reference_revision_allowed": False, "ground_truth_claim": False, "selection_authority": False,
        "retention_authority": False, "production_authority": False,
    }
    reference = {**commitment, "artifact_hash": hash_payload(commitment)}
    payload = {"selected_object": "CANDIDATE_A", "selection_basis": "LEXICAL_EXACT", "pragmatic_preference": "CANDIDATE_A", "assessment_completeness": "COMPLETE"}
    run = {
        "run_hash": "run",
        "tuple_outputs": [{"arm": arm, "conflict_id": f"c{index}", "payload": payload} for arm in ("SINGLE_MODEL_BASELINE", "ROLE_INFORMED_COORDINATOR") for index in range(24)],
        "routed_outputs": [{"conflict_id": f"c{index}", "payload": payload} for index in range(23)],
    }
    routing = {"artifact_hash": "analysis", "routed_path_total_tokens": 200000, "baseline_total_tokens": 20000, "routed_to_baseline_token_ratio": 10.0, "failed_invocation_accounting": {}}
    prereg = {"artifact_hash": "pre", "success_gate": {"minimum_primary_correct_cell_gain_over_baseline": 3, "maximum_selected_object_case_loss": 1, "minimum_preference_case_gain": 4, "minimum_basis_case_gain": 0, "maximum_tokens_per_net_primary_correct_cell": 40000}}
    evaluation = build_axis_external_evaluation(reference=reference, run=run, routing_analysis=routing, preregistration=prereg)
    assert evaluation["arm_metrics"]["AXIS_ROUTED"]["missing_output_count"] == 1
    assert evaluation["primary_transition_counts"]["missing_output_cells"] == 3
    assert evaluation["primary_transition_counts"]["harms"] == 3
    assert evaluation["primary_transition_counts_by_axis"]["SELECTED_OBJECT"]["MISSING_OUTPUT_HARM"] == 1
    assert evaluation["anti_additive_gate"] == "REJECT"
