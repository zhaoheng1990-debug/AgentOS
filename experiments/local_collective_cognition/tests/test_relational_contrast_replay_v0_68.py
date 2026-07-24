from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.relational_contrast_metrics import (
    calibration_decision,
    score_relational_contrast,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "relational_contrast_v0_68"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("completed v0.68 artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_score_and_rejection_replay() -> None:
    panel = read("calibration_private.json")
    prereg = read("calibration_preregistration.json")
    run = read("calibration_candidate_run.json")
    score = score_relational_contrast(
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
    assert decision["decision"] == "REJECT_RELATIONAL_CONTRAST_CALIBRATION"
    assert not decision["fresh_holdout_authorized"]


def test_positive_mechanism_and_residual_errors_are_preserved() -> None:
    score = read("calibration_score.json")
    assert score["candidate"]["valid_receipt_count"] == 12
    assert score["candidate"]["effective_cbit"] > score["baseline"][
        "effective_cbit"
    ]
    assert score["corrected_case_ids"] == [
        "EI-CAL-11179",
        "EI-CAL-13793",
    ]
    assert score["harmed_case_ids"] == ["EI-CAL-8555"]
    assert score["unresolved_case_ids"] == ["EI-CAL-8555"]
    assert score["compiler_failure_count"] == 0
