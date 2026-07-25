import json
from pathlib import Path

from local_collective_cognition.benchmark_bridge_metrics import score_arm
from local_collective_cognition.grouped_alias_surface_protocol import (
    validate_preregistration,
)
from local_collective_cognition.provider_telemetry import hash_payload


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "grouped_alias_surface_v0_74"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    assert value[field] == hash_payload(commitment)


def test_grouped_alias_surface_replays_full_calibration_pass():
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
    assert len(run["task_calls"]) == 24
    assert len(run["receipts"]) == 12
    assert run["contract_failures"] == []
    assert run["compiler_failures"] == []
    assert recorded_score["candidate"]["label_accuracy"] == 1.0
    assert recorded_score["candidate"]["evidence_f1"] == (
        0.9555555555555556
    )
    assert recorded_score["candidate"]["effective_cbit"] == (
        0.9666262142935571
    )
    assert recorded_score["harmed_case_ids"] == []
    assert all(decision["conditions"].values())
    assert decision["decision"] == (
        "PASS_GROUPED_ALIAS_SURFACE_CALIBRATION"
    )
    assert decision["fresh_holdout_authorized"] is True
    assert decision["fresh_holdout_executed"] is False
    assert not (OUTPUT / "holdout_candidate_run.json").exists()


def test_grouped_alias_surface_records_bounded_normalization():
    run = read(OUTPUT / "calibration_candidate_run.json")
    grouped = {
        case_id: [
            arm
            for arm in value["arms"]
            if arm["group_split_applied"]
        ]
        for case_id, value in run[
            "frame_validation_metadata"
        ].items()
    }
    grouped = {
        case_id: arms for case_id, arms in grouped.items() if arms
    }

    assert set(grouped) == {
        "EI-CAL-13790",
        "EI-CAL-13793",
        "EI-CAL-3189",
    }
    assert grouped["EI-CAL-3189"][0]["accepted_aliases"] == [
        "Kuntai, Tibolone, Control",
        "Kuntai",
        "Tibolone",
        "Control",
    ]
    assert all(
        value["semantic_synonyms_allowed"] is False
        and value["provider_alias_expansion_allowed"] is False
        for value in run["frame_validation_metadata"].values()
    )
    assert run["private_gold_exposed"] is False
    assert run["core_write_allowed"] is False
    assert run["retention_write_allowed"] is False
