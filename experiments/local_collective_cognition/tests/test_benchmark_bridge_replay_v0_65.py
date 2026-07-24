from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.benchmark_bridge_holdout import (
    holdout_decision,
    validate_holdout_preregistration,
)
from local_collective_cognition.benchmark_bridge_metrics import score_arm
from local_collective_cognition.benchmark_bridge_sources import (
    ensure_holdout_source,
    ensure_sources,
    holdout_source_manifest,
)
from local_collective_cognition.evidence_inference_bridge import (
    LABEL_MAP,
    SELECTED_PROMPT_IDS,
    build_selected_panel,
    validate_panel,
)
from local_collective_cognition.evidence_inference_selection import (
    select_balanced_prompt_ids,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "benchmark_bridge_v0_65"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.65 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_calibration_and_holdout_are_split_disjoint() -> None:
    calibration = read("calibration_panel_private.json")
    holdout = read("holdout_panel_private.json")
    calibration_prompts = {
        item["source_prompt_id"]
        for item in calibration["public_surface"]["items"]
    }
    holdout_prompts = {
        item["source_prompt_id"]
        for item in holdout["public_surface"]["items"]
    }
    calibration_articles = {
        item["source_pmcid"]
        for item in calibration["public_surface"]["items"]
    }
    holdout_articles = {
        item["source_pmcid"]
        for item in holdout["public_surface"]["items"]
    }
    assert calibration_prompts.isdisjoint(holdout_prompts)
    assert calibration_articles.isdisjoint(holdout_articles)


def test_holdout_selection_and_panel_hash_replay() -> None:
    frozen = read("holdout_panel_private.json")
    paths = ensure_sources()
    paths["test_article_ids.txt"] = ensure_holdout_source()
    selected = select_balanced_prompt_ids(
        paths=paths,
        split_ids_name="test_article_ids.txt",
        per_label=12,
        label_map=LABEL_MAP,
        excluded_prompt_ids=SELECTED_PROMPT_IDS,
    )
    rebuilt = build_selected_panel(
        paths=paths,
        selected_prompt_ids=selected,
        split_ids_name="test_article_ids.txt",
        benchmark_id="evidence-inference-candidate-rationale-test-transfer",
        split="test_frozen_transfer_holdout",
        manifest=holdout_source_manifest(),
        external_transfer_claim=True,
    )
    assert rebuilt["artifact_hash"] == frozen["artifact_hash"]
    assert rebuilt["label_balance"] == {
        "INCREASED": 12,
        "DECREASED": 12,
        "NO_DIFFERENCE": 12,
    }


def test_runs_scores_and_negative_decision_replay() -> None:
    panel = read("holdout_panel_private.json")
    preregistration = read("holdout_preregistration.json")
    a0_run = read("holdout_a0_run.json")
    a1_run = read("holdout_a1_run.json")
    validate_panel(panel)
    validate_holdout_preregistration(preregistration)
    assert not a0_run["private_gold_exposed"]
    assert not a1_run["private_gold_exposed"]
    assert not a0_run["core_write_allowed"]
    assert not a1_run["retention_write_allowed"]
    a0_score = score_arm(
        panel=panel, preregistration=preregistration, run=a0_run
    )
    a1_score = score_arm(
        panel=panel, preregistration=preregistration, run=a1_run
    )
    decision = holdout_decision(
        preregistration=preregistration,
        one_pass_score=a0_score,
        staged_score=a1_score,
    )
    assert a0_score["artifact_hash"] == read(
        "holdout_a0_score.json"
    )["artifact_hash"]
    assert a1_score["artifact_hash"] == read(
        "holdout_a1_score.json"
    )["artifact_hash"]
    assert decision["artifact_hash"] == read(
        "holdout_decision.json"
    )["artifact_hash"]
    assert decision["decision"] == (
        "REJECT_BENCHMARK_BRIDGE_TEST_SPLIT_TRANSFER"
    )
    assert not decision["test_split_transfer_supported"]


def test_raw_benchmark_files_are_absent_from_repository() -> None:
    forbidden = {
        "prompts.csv",
        "annotations.csv",
        "validation_article_ids.txt",
        "test_article_ids.txt",
    }
    present = {
        path.name
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and path.name in forbidden
    }
    assert present == set()
