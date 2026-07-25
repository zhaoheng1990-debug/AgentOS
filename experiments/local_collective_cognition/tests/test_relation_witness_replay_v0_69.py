import json
from pathlib import Path

from local_collective_cognition.relation_witness_metrics import (
    calibration_decision,
    score_witness,
)


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "relation_witness_v0_69"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def test_v069_rejection_replays():
    panel = read("calibration_private.json")
    prereg = read("calibration_preregistration.json")
    score = score_witness(
        panel=panel,
        preregistration=prereg,
        baseline_run=panel["baseline_projection"],
        candidate_run=read("calibration_candidate_run.json"),
    )
    decision = calibration_decision(preregistration=prereg, score=score)
    assert score["artifact_hash"] == read("calibration_score.json")[
        "artifact_hash"
    ]
    assert decision["decision"] == "REJECT_RELATION_WITNESS_CALIBRATION"
    assert not decision["fresh_holdout_authorized"]
    assert score["candidate"]["valid_receipt_count"] == 7
    assert score["harmed_case_ids"] == [
        "EI-CAL-1113",
        "EI-CAL-13790",
        "EI-CAL-8555",
        "EI-CAL-8861",
    ]
