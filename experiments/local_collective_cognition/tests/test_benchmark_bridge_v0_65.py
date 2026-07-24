from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.benchmark_bridge_protocol import (
    build_preregistration,
    validate_preregistration,
)
from local_collective_cognition.benchmark_bridge_sources import (
    SOURCE_FILES,
    default_cache_dir,
)
from local_collective_cognition.evidence_inference_bridge import (
    build_calibration_panel,
    public_panel,
    validate_panel,
)


def _source_paths() -> dict[str, Path]:
    root = Path(__file__).parents[3]
    candidate = root / "outputs" / "benchmark_bridge_v0_65"
    private = candidate / "calibration_panel_private.json"
    if not private.exists():
        pytest.skip("frozen v0.65 calibration panel is not present")
    return {"private": private}


def test_source_specs_are_hash_pinned_and_cache_is_external() -> None:
    assert all(len(source.sha256) == 64 for source in SOURCE_FILES)
    assert "experiments" not in str(default_cache_dir()).lower()
    assert "logos-agentos" not in str(default_cache_dir()).lower()


def test_frozen_panel_is_balanced_partitioned_and_reproducible() -> None:
    private = json.loads(
        _source_paths()["private"].read_text(encoding="utf-8")
    )
    validate_panel(private)
    paths = {
        source.name: default_cache_dir() / source.name
        for source in SOURCE_FILES
    }
    rebuilt = build_calibration_panel(paths)
    assert rebuilt["artifact_hash"] == private["artifact_hash"]
    assert rebuilt["label_balance"] == {
        "INCREASED": 3,
        "DECREASED": 3,
        "NO_DIFFERENCE": 3,
    }


def test_public_panel_excludes_private_truth() -> None:
    private = json.loads(
        _source_paths()["private"].read_text(encoding="utf-8")
    )
    public = public_panel(private)
    assert "private_gold" not in public
    assert "label_balance" not in public
    assert "gold_rationale" not in json.dumps(public)


def test_preregistration_is_hash_bound_and_fail_closed() -> None:
    private = json.loads(
        _source_paths()["private"].read_text(encoding="utf-8")
    )
    preregistration = build_preregistration(private)
    validate_preregistration(preregistration)
    assert preregistration["external_holdout_authorized_only_after_calibration_pass"]
    assert not preregistration["core_write_allowed"]
    assert not preregistration["retention_write_allowed"]
