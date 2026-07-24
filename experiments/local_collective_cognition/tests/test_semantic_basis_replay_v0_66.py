from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.semantic_basis_metrics import (
    calibration_decision,
    score_semantic_basis,
)
from local_collective_cognition.semantic_basis_protocol import (
    validate_semantic_basis_preregistration,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "semantic_basis_v0_66"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("completed v0.66 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_calibration_score_and_reject_decision_replay() -> None:
    panel = read("calibration_private.json")
    preregistration = read("calibration_preregistration.json")
    run = read("calibration_candidate_run.json")
    validate_semantic_basis_preregistration(preregistration)
    score = score_semantic_basis(
        panel=panel,
        preregistration=preregistration,
        baseline_run=panel["baseline_projection"],
        candidate_run=run,
    )
    decision = calibration_decision(
        preregistration=preregistration, score=score
    )
    assert score["artifact_hash"] == read(
        "calibration_score.json"
    )["artifact_hash"]
    assert decision["artifact_hash"] == read(
        "calibration_decision.json"
    )["artifact_hash"]
    assert decision["decision"] == (
        "REJECT_TYPED_SEMANTIC_BASIS_CALIBRATION"
    )
    assert not decision["fresh_holdout_authorized"]


def test_known_semantic_effects_are_preserved() -> None:
    score = read("calibration_score.json")
    assert score["corrected_case_ids"] == ["EI-CAL-11179"]
    assert score["harmed_case_ids"] == [
        "EI-CAL-3189",
        "EI-CAL-9330",
    ]
    assert score["unresolved_case_ids"] == [
        "EI-CAL-13793",
        "EI-CAL-9330",
    ]
    assert score["candidate_total_failure_count"] == 2


def test_fresh_holdout_provider_execution_was_blocked() -> None:
    forbidden = (
        "holdout_baseline_run.json",
        "holdout_candidate_run.json",
        "holdout_score.json",
        "holdout_decision.json",
    )
    assert all(not (OUTPUT / name).exists() for name in forbidden)


def test_no_raw_benchmark_file_entered_repository() -> None:
    forbidden = {
        "prompts.csv",
        "annotations.csv",
        "validation_article_ids.txt",
        "test_article_ids.txt",
        "train_article_ids.txt",
    }
    present = {
        path.name
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and path.name in forbidden
    }
    assert present == set()
