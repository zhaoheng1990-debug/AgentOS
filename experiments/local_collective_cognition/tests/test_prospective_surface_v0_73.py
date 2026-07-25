import json
from pathlib import Path

from local_collective_cognition.benchmark_bridge_metrics import score_arm
from local_collective_cognition.prospective_surface_protocol import (
    validate_preregistration,
)
from local_collective_cognition.provider_telemetry import hash_payload


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "prospective_surface_v0_73"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    assert value[field] == hash_payload(commitment)


def test_prospective_surface_replay_preserves_reject_boundary():
    panel = read(OUTPUT / "calibration_private.json")
    preregistration = read(
        OUTPUT / "calibration_preregistration.json"
    )
    run = read(OUTPUT / "calibration_candidate_run.json")
    recorded_score = read(OUTPUT / "calibration_score.json")
    decision = read(OUTPUT / "calibration_decision.json")

    validate_preregistration(preregistration)
    validate_hash(run, "run_hash")
    validate_hash(recorded_score, "artifact_hash")
    validate_hash(decision, "artifact_hash")

    replayed = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=run,
    )
    assert (
        replayed["artifact_hash"]
        == recorded_score["candidate"]["artifact_hash"]
    )
    assert len(run["task_calls"]) == 23
    assert len(run["receipts"]) == 11
    assert run["compiler_failures"] == []
    assert run["contract_failures"][0]["case_id"] == "EI-CAL-3189"
    assert run["contract_failures"][0]["contract_failures"] == [
        "WITNESS_INTERVENTION_ALIASES_UNGROUNDED"
    ]
    assert sum(
        len(value["changes"])
        for value in run["projection_receipts"].values()
    ) == 17

    assert decision["decision"] == (
        "REJECT_PROSPECTIVE_SURFACE_CALIBRATION"
    )
    assert decision["fresh_holdout_authorized"] is False
    assert decision["fresh_holdout_executed"] is False
    assert run["private_gold_exposed"] is False
    assert run["core_write_allowed"] is False
    assert run["retention_write_allowed"] is False
    assert not (OUTPUT / "holdout_candidate_run.json").exists()


def test_prospective_surface_records_corrections_and_harm():
    score = read(OUTPUT / "calibration_score.json")
    decision = read(OUTPUT / "calibration_decision.json")

    assert score["corrected_case_ids"] == [
        "EI-CAL-11179",
        "EI-CAL-13793",
        "EI-CAL-5842",
    ]
    assert score["harmed_case_ids"] == ["EI-CAL-3189"]
    assert score["candidate"]["effective_cbit"] > (
        score["baseline"]["effective_cbit"]
    )
    assert score["candidate"]["evidence_f1"] < (
        score["baseline"]["evidence_f1"]
    )
    assert decision["conditions"] == {
        "attempt_budget": True,
        "effective_cbit": True,
        "evidence_f1": False,
        "failures": False,
        "label_accuracy": True,
        "no_harms": False,
        "required_labels": True,
        "task_budget": True,
        "token_budget": True,
        "valid_receipts": False,
    }
