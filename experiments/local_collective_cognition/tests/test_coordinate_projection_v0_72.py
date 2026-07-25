import json
from pathlib import Path

from local_collective_cognition.benchmark_bridge_metrics import score_arm
from local_collective_cognition.coordinate_projection_replay import (
    build_projection_replay,
)


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "outputs" / "surface_binding_v0_71"
OUTPUT = ROOT / "outputs" / "coordinate_projection_v0_72"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_coordinate_projection_replays_without_provider_calls():
    panel = read(SOURCE / "calibration_private.json")
    prereg = read(OUTPUT / "calibration_preregistration.json")
    run = build_projection_replay(
        panel=panel,
        preregistration=prereg,
        source_run=read(SOURCE / "calibration_candidate_run.json"),
    )
    score = score_arm(panel=panel, preregistration=prereg, run=run)
    assert run["run_hash"] == read(
        OUTPUT / "calibration_replay_run.json"
    )["run_hash"]
    assert score["artifact_hash"] == read(
        OUTPUT / "calibration_score.json"
    )["candidate"]["artifact_hash"]
    assert run["provider_calls_added"] == 0
    assert sum(
        len(value["changes"])
        for value in run["projection_receipts"].values()
    ) == 17
    assert score["label_accuracy"] == 1.0
    assert read(OUTPUT / "calibration_score.json")[
        "fresh_holdout_authorized"
    ] is False
