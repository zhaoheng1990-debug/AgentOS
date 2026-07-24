from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.semantic_basis_calibration import (
    CALIBRATION_CASE_IDS,
    KNOWN_FAILURES,
    validate_calibration_projection,
)
from local_collective_cognition.semantic_basis_holdout import (
    build_semantic_basis_holdout,
    validate_semantic_basis_holdout,
)
from local_collective_cognition.semantic_basis_sources import (
    TRAIN_SPLIT_FILE,
    ensure_semantic_basis_sources,
)
from local_collective_cognition.semantic_basis_protocol import (
    validate_semantic_basis_preregistration,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "semantic_basis_v0_66"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.66 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_train_split_is_hash_pinned_and_external() -> None:
    assert len(TRAIN_SPLIT_FILE.sha256) == 64
    paths = ensure_semantic_basis_sources()
    assert "logos-agentos" not in str(
        paths["train_article_ids.txt"]
    ).lower()


def test_calibration_is_balanced_and_contains_known_failures() -> None:
    calibration = read("calibration_private.json")
    validate_calibration_projection(calibration)
    assert set(KNOWN_FAILURES).issubset(CALIBRATION_CASE_IDS)
    assert calibration["label_balance"] == {
        "INCREASED": 4,
        "DECREASED": 4,
        "NO_DIFFERENCE": 4,
    }


def test_fresh_holdout_hash_replays() -> None:
    frozen = read("holdout_private.json")
    validate_semantic_basis_holdout(frozen)
    rebuilt = build_semantic_basis_holdout(
        ensure_semantic_basis_sources()
    )
    assert rebuilt["artifact_hash"] == frozen["artifact_hash"]


def test_calibration_and_fresh_holdout_are_article_disjoint() -> None:
    calibration = read("calibration_private.json")
    holdout = read("holdout_private.json")
    calibration_articles = {
        item["source_pmcid"]
        for item in calibration["public_surface"]["items"]
    }
    holdout_articles = {
        item["source_pmcid"]
        for item in holdout["public_surface"]["items"]
    }
    assert calibration_articles.isdisjoint(holdout_articles)


def test_public_surfaces_exclude_private_truth_and_baseline() -> None:
    calibration = read("calibration_public.json")
    holdout = read("holdout_public.json")
    encoded = json.dumps([calibration, holdout])
    assert "private_gold" not in encoded
    assert "baseline_projection" not in encoded
    assert "gold_rationale" not in encoded


def test_preregistration_locks_final_mechanism_sources() -> None:
    validate_semantic_basis_preregistration(
        read("calibration_preregistration.json")
    )
