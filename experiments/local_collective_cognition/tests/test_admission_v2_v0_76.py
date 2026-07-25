import json
from pathlib import Path

from local_collective_cognition.admission_v2_calibration import (
    score_calibration,
    validate_calibration_projection,
)
from local_collective_cognition.admission_v2_protocol import (
    validate_preregistration,
)
from local_collective_cognition.provider_telemetry import hash_payload


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v2_v0_76"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    assert value[field] == hash_payload(commitment)


def test_admission_v2_replays_frozen_reject():
    panel = read(OUTPUT / "calibration_private.json")
    preregistration = read(
        OUTPUT / "calibration_preregistration.json"
    )
    run = read(OUTPUT / "calibration_candidate_run.json")
    score = read(OUTPUT / "calibration_score.json")
    decision = read(OUTPUT / "calibration_decision.json")

    validate_calibration_projection(panel)
    validate_preregistration(preregistration)
    validate_hash(run, "run_hash")
    validate_hash(score, "artifact_hash")
    validate_hash(decision, "artifact_hash")
    assert score_calibration(panel=panel, run=run) == score

    assert panel["v0_75_holdout_reused"] is False
    assert len(run["receipts"]) == 12
    assert len(run["partitions"]) == 12
    assert run["contract_failures"] == []
    assert run["compiler_failures"] == []
    assert run["predicted_label_authority"] is False
    assert decision["decision"] == "REJECT_ADMISSION_V2_CALIBRATION"
    assert decision["new_holdout_design_authorized"] is False
    assert decision["v0_75_holdout_reexecution_allowed"] is False


def test_admission_v2_preserves_the_semantic_failure_anatomy():
    run = read(OUTPUT / "calibration_candidate_run.json")
    score = read(OUTPUT / "calibration_score.json")
    decision = read(OUTPUT / "calibration_decision.json")

    assert score["candidate"]["context_span_count"] == 17
    assert score["candidate"]["false_no_applicable_count"] == 1
    assert score["candidate"]["evidence_f1"] == 0.8472222222222222
    assert score["harmed_case_ids"] == [
        "EI-CAL-11806",
        "EI-CAL-11995",
        "EI-CAL-6857",
    ]
    assert run["partitions"]["EI-CAL-11806"][
        "admission_state"
    ] == "NO_APPLICABLE_EVIDENCE"
    assert run["partitions"]["EI-CAL-11806"][
        "abstention_required"
    ] is True
    assert set(run["partitions"]["EI-CAL-6857"][
        "context_span_ids"
    ]) == {"EI-6857-S2", "EI-6857-S3"}
    assert decision["conditions"]["false_no_applicable"] is False
    assert decision["conditions"]["evidence_f1"] is False
    assert decision["conditions"]["no_harms"] is False
