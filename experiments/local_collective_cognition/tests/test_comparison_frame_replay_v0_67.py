from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.comparison_frame_metrics import (
    calibration_decision,
    score_comparison_frame,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "comparison_frame_v0_67"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("completed v0.67 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_score_and_reject_decision_replay() -> None:
    panel = read("calibration_private.json")
    prereg = read("calibration_preregistration.json")
    run = read("calibration_candidate_run.json")
    score = score_comparison_frame(
        panel=panel,
        preregistration=prereg,
        baseline_run=panel["baseline_projection"],
        candidate_run=run,
    )
    decision = calibration_decision(preregistration=prereg, score=score)
    assert score["artifact_hash"] == read("calibration_score.json")[
        "artifact_hash"
    ]
    assert decision["artifact_hash"] == read(
        "calibration_decision.json"
    )["artifact_hash"]
    assert decision["decision"] == "REJECT_COMPARISON_FRAME_CALIBRATION"
    assert not decision["fresh_holdout_authorized"]


def test_observed_layer_failures_remain_explicit() -> None:
    score = read("calibration_score.json")
    assert score["corrected_case_ids"] == ["EI-CAL-5842"]
    assert score["harmed_case_ids"] == [
        "EI-CAL-13790",
        "EI-CAL-3189",
        "EI-CAL-5791",
        "EI-CAL-8861",
    ]
    assert score["unresolved_case_ids"] == [
        "EI-CAL-11179",
        "EI-CAL-13793",
    ]
    assert score["compiler_failure_count"] == 0
