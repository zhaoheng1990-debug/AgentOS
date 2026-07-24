from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_source_ontology import (  # noqa: E402
    AXIS_SOURCE,
    BASELINE_CELL,
    BASELINE_SOURCE,
    CELLS,
    COLLAPSED_CELL,
    NATIVE_CELL,
)
from local_collective_cognition.cognitive_action_source_ontology_evaluation import (  # noqa: E402
    build_source_ontology_external_evaluation,
    build_source_ontology_external_reference,
    validate_source_ontology_external_evaluation,
    validate_source_ontology_external_reference,
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
        "local_collective_cognition.cognitive_action_source_ontology_evaluation.validate_source_ontology_external_adjudication",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "local_collective_cognition.cognitive_action_source_ontology_evaluation.validate_source_ontology_adjudication_response",
        lambda *_, **__: None,
    )
    agreements = [{
        "conflict_id": f"c{index}",
        "selected_tuple": coherent_tuple(),
        "lane_annotation_ids": {"a": f"a{index}", "b": f"b{index}"},
    } for index in range(12)]
    bindings = {
        f"d{index}": {"conflict_id": f"c{index + 12}"}
        for index in range(12)
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
    } for index in range(12)]}
    return build_source_ontology_external_reference(
        adjudication_pack={"pack_hash": "k"},
        adjudication_manifest=manifest,
        adjudication_response=response,
    )


def test_source_ontology_reference_merges_agreements_and_k3(monkeypatch):
    reference = candidate_reference(monkeypatch)
    validate_source_ontology_external_reference(reference)
    assert reference["object_count"] == 24
    assert reference["criterion_count"] == 120
    assert reference["source_counts"] == {
        "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT": 12,
        "KIMI_K3_WHOLE_TUPLE_ADJUDICATION": 12,
    }
    tampered = deepcopy(reference)
    tampered["labels"][0]["criteria"]["SELECTED_OBJECT"] = "CANDIDATE_B"
    tampered["artifact_hash"] = hash_payload({
        key: value for key, value in tampered.items()
        if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="reference_tuple_invalid"):
        validate_source_ontology_external_reference(tampered)


def test_source_ontology_evaluation_scores_three_cells(monkeypatch):
    reference = candidate_reference(monkeypatch)
    payload = {
        "selected_object": "NONE",
        "selection_basis": "PRAGMATIC_DEFAULT",
        "pragmatic_preference": "CANDIDATE_A",
        "evidence_state": "SOFT_AMBIGUITY",
        "assessment_process_state": "COMPLETE",
    }
    counts = {
        BASELINE_CELL: 20,
        COLLAPSED_CELL: 24,
        NATIVE_CELL: 24,
    }
    run = {
        "run_hash": "run",
        "outputs": [{
            "cell": cell,
            "conflict_id": f"c{index}",
            "payload": payload,
        } for cell, count in counts.items() for index in range(count)],
        "failures": [],
    }
    analysis = {
        "artifact_hash": "analysis",
        "source_total_tokens": {
            BASELINE_SOURCE: 100,
            AXIS_SOURCE: 120,
        },
        "axis_to_baseline_source_token_ratio": 1.2,
    }
    preregistration = {
        "artifact_hash": "pre",
        "success_gate": {
            "minimum_native_admission_precision": 0.75,
            "minimum_native_soft_ambiguity_recall": 0.67,
            "minimum_native_evidence_state_accuracy": 0.75,
            "minimum_native_evidence_correct_gain_over_baseline": 3,
            "maximum_native_selected_object_loss_vs_baseline": 1,
            "minimum_native_output_coverage": 0.95,
            "maximum_axis_to_baseline_source_token_ratio": 1.35,
            "maximum_native_false_soft_admissions": 1,
        },
    }
    evaluation = build_source_ontology_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    validate_source_ontology_external_evaluation(
        evaluation,
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    assert evaluation["cell_metrics"][NATIVE_CELL][
        "full_tuple_correct"
    ] == 24
    assert evaluation["metric_deltas"][NATIVE_CELL][
        "full_tuple_correct"
    ] == 4
    assert evaluation["anti_additive_gate"] == "PASS"
    assert evaluation["retention_write_allowed"] is False

    tampered = deepcopy(evaluation)
    tampered["anti_additive_gate"] = "REJECT"
    with pytest.raises(ValueError, match="evaluation_invalid"):
        validate_source_ontology_external_evaluation(
            tampered,
            reference=reference,
            run=run,
            analysis=analysis,
            preregistration=preregistration,
        )
