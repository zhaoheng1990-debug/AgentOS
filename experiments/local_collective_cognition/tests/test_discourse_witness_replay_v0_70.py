import json
from pathlib import Path

from local_collective_cognition.benchmark_bridge_metrics import score_arm
from local_collective_cognition.discourse_witness_replay import (
    build_discourse_replay,
)


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "outputs" / "relation_witness_v0_69"
OUTPUT = ROOT / "outputs" / "discourse_witness_v0_70"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_zero_call_discourse_replay_is_stable():
    panel = read(SOURCE / "calibration_private.json")
    run = build_discourse_replay(
        panel=panel,
        source_run=read(SOURCE / "calibration_candidate_run.json"),
    )
    score = score_arm(
        panel=panel,
        preregistration=read(SOURCE / "calibration_preregistration.json"),
        run=run,
    )
    assert run["run_hash"] == read(OUTPUT / "replay_run.json")["run_hash"]
    assert score["artifact_hash"] == read(
        OUTPUT / "replay_score.json"
    )["artifact_hash"]
    assert run["provider_calls_added"] == 0
    assert score["valid_receipt_count"] == 8
    assert score["effective_cbit"] == 0.6111111111111112
