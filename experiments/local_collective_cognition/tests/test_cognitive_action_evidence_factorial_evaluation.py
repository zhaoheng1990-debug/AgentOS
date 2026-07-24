from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_evidence_factorial import (  # noqa: E402
    CELLS,
)
from local_collective_cognition.cognitive_action_evidence_factorial_evaluation import (  # noqa: E402
    COMBINED_CELL,
    build_factorial_external_evaluation,
    build_factorial_external_reference,
    validate_factorial_external_evaluation,
    validate_factorial_external_reference,
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
        "local_collective_cognition.cognitive_action_evidence_factorial_evaluation.validate_factorial_external_adjudication",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "local_collective_cognition.cognitive_action_evidence_factorial_evaluation.validate_factorial_adjudication_response",
        lambda *_, **__: None,
    )
    agreements = [{
        "conflict_id": f"c{index}",
        "selected_tuple": coherent_tuple(),
        "lane_annotation_ids": {"a": f"a{index}", "b": f"b{index}"},
    } for index in range(13)]
    bindings = {
        f"d{index}": {"conflict_id": f"c{index + 13}"}
        for index in range(11)
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
    } for index in range(11)]}
    return build_factorial_external_reference(
        adjudication_pack={"pack_hash": "k"},
        adjudication_manifest=manifest,
        adjudication_response=response,
    )


def test_factorial_reference_merges_agreements_and_k3(monkeypatch):
    reference = candidate_reference(monkeypatch)
    validate_factorial_external_reference(reference)
    assert reference["object_count"] == 24
    assert reference["criterion_count"] == 120
    assert reference["source_counts"] == {
        "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT": 13,
        "KIMI_K3_WHOLE_TUPLE_ADJUDICATION": 11,
    }
    tampered = deepcopy(reference)
    tampered["labels"][0]["criteria"]["SELECTED_OBJECT"] = "CANDIDATE_B"
    tampered["artifact_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="reference_tuple_invalid"):
        validate_factorial_external_reference(tampered)


def test_factorial_evaluation_scores_four_cells_and_interaction(monkeypatch):
    reference = candidate_reference(monkeypatch)
    payload = {
        "selected_object": "NONE",
        "selection_basis": "PRAGMATIC_DEFAULT",
        "pragmatic_preference": "CANDIDATE_A",
        "evidence_state": "SOFT_AMBIGUITY",
        "assessment_process_state": "COMPLETE",
    }
    counts = dict(zip(CELLS, (20, 21, 22, 24)))
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
            "LEGACY_SOURCE_PROMPT_V0_19": 100,
            "REPAIRED_SOURCE_PROMPT_V0_20": 120,
        },
        "repaired_to_legacy_source_token_ratio": 1.2,
    }
    preregistration = {
        "artifact_hash": "pre",
        "success_gate": {
            "minimum_combined_admission_precision": 0.75,
            "minimum_combined_soft_ambiguity_recall": 0.67,
            "minimum_combined_evidence_state_accuracy": 0.70,
            "minimum_combined_evidence_correct_gain_over_legacy": 4,
            "maximum_combined_selected_object_loss_vs_legacy": 1,
            "minimum_combined_output_coverage": 0.95,
            "maximum_repaired_to_legacy_source_token_ratio": 1.30,
            "maximum_false_soft_admissions": 1,
        },
    }
    evaluation = build_factorial_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    validate_factorial_external_evaluation(
        evaluation,
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    assert evaluation["cell_metrics"][COMBINED_CELL][
        "full_tuple_correct"
    ] == 24
    assert evaluation["factor_effects"]["full_tuple_correct"][
        "interaction"
    ] == 1
    assert evaluation["anti_additive_gate"] == "PASS"
    assert evaluation["retention_write_allowed"] is False

    tampered = deepcopy(evaluation)
    tampered["anti_additive_gate"] = "REJECT"
    with pytest.raises(ValueError, match="evaluation_invalid"):
        validate_factorial_external_evaluation(
            tampered,
            reference=reference,
            run=run,
            analysis=analysis,
            preregistration=preregistration,
        )
