from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.comparison_frame_protocol import (
    FROZEN_HOLDOUT_HASH,
    validate_comparison_frame_preregistration,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "comparison_frame_v0_67"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.67 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_v066_holdout_is_reused_byte_for_byte() -> None:
    source = (
        REPO_ROOT / "outputs" / "semantic_basis_v0_66"
        / "holdout_private.json"
    )
    if not source.exists():
        pytest.skip("v0.66 holdout is not present")
    assert (OUTPUT / "holdout_private.json").read_bytes() == source.read_bytes()
    assert read("holdout_private.json")["artifact_hash"] == FROZEN_HOLDOUT_HASH


def test_preregistration_locks_mechanism_and_no_write_boundaries() -> None:
    prereg = read("calibration_preregistration.json")
    validate_comparison_frame_preregistration(prereg)
    assert not prereg["free_provider_synthesis_allowed"]
    assert not prereg["provider_compiler_override_allowed"]
    assert not prereg["core_write_allowed"]
    assert not prereg["retention_write_allowed"]


def test_fresh_holdout_has_not_been_consumed_before_calibration_pass() -> None:
    forbidden = (
        "holdout_baseline_run.json",
        "holdout_candidate_run.json",
        "holdout_score.json",
        "holdout_decision.json",
    )
    assert all(not (OUTPUT / name).exists() for name in forbidden)
