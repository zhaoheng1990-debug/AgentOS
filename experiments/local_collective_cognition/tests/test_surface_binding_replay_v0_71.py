import json
from pathlib import Path

from local_collective_cognition.benchmark_bridge_metrics import score_arm


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "surface_binding_v0_71"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def test_v071_score_is_stable_and_holdout_blocked():
    panel = read("calibration_private.json")
    prereg = read("calibration_preregistration.json")
    run = read("calibration_candidate_run.json")
    score = score_arm(panel=panel, preregistration=prereg, run=run)
    frozen = read("calibration_score.json")
    assert score["artifact_hash"] == frozen["candidate"]["artifact_hash"]
    assert frozen["decision"] == "REJECT_SURFACE_BINDING_CALIBRATION"
    assert not frozen["fresh_holdout_authorized"]
    assert frozen["corrected_case_ids"] == [
        "EI-CAL-11179",
        "EI-CAL-13793",
        "EI-CAL-5842",
    ]
    assert frozen["harmed_case_ids"] == ["EI-CAL-6743", "EI-CAL-8861"]
