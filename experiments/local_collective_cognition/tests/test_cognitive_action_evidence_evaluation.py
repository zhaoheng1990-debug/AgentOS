from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_evidence_evaluation import (  # noqa: E402
    build_evidence_external_evaluation,
    build_evidence_external_reference,
    validate_evidence_external_evaluation,
    validate_evidence_external_reference,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def coherent_tuple():
    return {
        "SELECTED_OBJECT": "NONE",
        "SELECTION_BASIS": "PRAGMATIC_DEFAULT",
        "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
        "EVIDENCE_STATE": "SOFT_AMBIGUITY",
        "ASSESSMENT_PROCESS_STATE": "COMPLETE",
    }


def candidate_reference(monkeypatch):
    monkeypatch.setattr(
        "local_collective_cognition.cognitive_action_evidence_evaluation.validate_evidence_external_adjudication",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "local_collective_cognition.cognitive_action_evidence_evaluation.validate_evidence_adjudication_response",
        lambda *_, **__: None,
    )
    agreements = [{
        "conflict_id": f"c{index}",
        "selected_tuple": coherent_tuple(),
        "lane_annotation_ids": {"a": f"a{index}", "b": f"b{index}"},
    } for index in range(14)]
    bindings = {
        f"d{index}": {"conflict_id": f"c{index + 14}"}
        for index in range(10)
    }
    manifest = {
        "panel_id": "p",
        "manifest_hash": "m",
        "agreement_records": agreements,
        "private_disagreement_bindings": bindings,
    }
    response = {"decisions": [{
        "adjudication_id": f"d{index}",
        "criteria": coherent_tuple(),
        "decision_basis": "POSITION_1",
        "confidence": 0.9,
    } for index in range(10)]}
    return build_evidence_external_reference(
        adjudication_pack={"pack_hash": "k"},
        adjudication_manifest=manifest,
        adjudication_response=response,
    )


def test_reference_merges_lane_agreements_and_whole_tuple_adjudications(monkeypatch):
    reference = candidate_reference(monkeypatch)
    validate_evidence_external_reference(reference)
    assert reference["object_count"] == 24
    assert reference["criterion_count"] == 120
    assert reference["source_counts"] == {
        "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT": 14,
        "KIMI_K3_WHOLE_TUPLE_ADJUDICATION": 10,
    }
    assert reference["retention_authority"] is False
    tampered = deepcopy(reference)
    tampered["labels"][0]["criteria"]["SELECTED_OBJECT"] = "CANDIDATE_B"
    tampered["artifact_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="tuple_invalid"):
        validate_evidence_external_reference(tampered)


def test_evaluation_scores_missing_outputs_incorrect_and_recomputes(monkeypatch):
    reference = candidate_reference(monkeypatch)
    payload = {
        "selected_object": "NONE",
        "selection_basis": "PRAGMATIC_DEFAULT",
        "pragmatic_preference": "CANDIDATE_A",
        "evidence_state": "SOFT_AMBIGUITY",
        "assessment_process_state": "COMPLETE",
    }
    run = {
        "run_hash": "run",
        "outputs": [
            {"arm": arm, "conflict_id": f"c{index}", "payload": payload}
            for arm, count in (
                ("FREE_LABEL_CONTROL", 24),
                ("CONTRASTIVE_SOURCE_CALIBRATOR", 23),
            )
            for index in range(count)
        ],
    }
    analysis = {
        "artifact_hash": "analysis",
        "total_tokens": {
            "FREE_LABEL_CONTROL": 100,
            "CONTRASTIVE_SOURCE_CALIBRATOR": 120,
        },
        "calibrator_to_control_token_ratio": 1.2,
    }
    preregistration = {
        "artifact_hash": "pre",
        "success_gate": {
            "minimum_admission_precision": 0.75,
            "minimum_soft_ambiguity_recall": 0.67,
            "minimum_evidence_state_accuracy": 0.70,
            "minimum_evidence_correct_case_gain_over_control": 4,
            "maximum_selected_object_case_loss_vs_control": 1,
            "minimum_output_coverage": 0.95,
            "maximum_calibrator_to_control_token_ratio": 1.5,
        },
    }
    evaluation = build_evidence_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    validate_evidence_external_evaluation(
        evaluation,
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    calibrated = evaluation["arm_metrics"]["CONTRASTIVE_SOURCE_CALIBRATOR"]
    assert calibrated["missing_output_count"] == 1
    assert calibrated["all_correct_cell_count"] == 115
    records = evaluation["admission_records"]["CONTRASTIVE_SOURCE_CALIBRATOR"]
    assert sum(item["output_missing"] for item in records) == 1
    assert evaluation["anti_additive_gate"] == "REJECT"
    assert evaluation["baseline_promotion_allowed"] is False
    assert evaluation["retention_write_allowed"] is False

    tampered = deepcopy(evaluation)
    tampered["anti_additive_gate"] = "PASS"
    with pytest.raises(ValueError, match="evaluation_invalid"):
        validate_evidence_external_evaluation(
            tampered,
            reference=reference,
            run=run,
            analysis=analysis,
            preregistration=preregistration,
        )
