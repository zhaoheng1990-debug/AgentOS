from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.benchmark_bridge_contracts import (
    validate_admission,
    validate_one_pass,
    validate_staged_binding,
)
from local_collective_cognition.benchmark_bridge_metrics import (
    calibration_decision,
    score_arm,
)
from local_collective_cognition.benchmark_bridge_protocol import (
    build_preregistration,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload


REPO_ROOT = Path(__file__).parents[3]


def _panel() -> dict:
    path = (
        REPO_ROOT
        / "outputs"
        / "benchmark_bridge_v0_65"
        / "calibration_panel_private.json"
    )
    if not path.exists():
        pytest.skip("frozen v0.65 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def _receipts(panel: dict) -> tuple[dict, dict, dict]:
    item = panel["public_surface"]["items"][0]
    gold = panel["private_gold"][item["case_id"]]
    refs = evidence_refs(item)
    gold_ids = gold["gold_rationale_span_ids"]
    distractors = gold["distractor_span_ids"]
    one_pass = {
        "case_id": item["case_id"],
        "mechanism": "A0_ONE_PASS",
        "source_item_hash": hash_payload(item),
        "predicted_label": gold["label"],
        "primary_span_ids": gold_ids[:1],
        "corroborating_span_ids": gold_ids[1:],
        "counter_span_ids": [],
        "irrelevant_span_ids": distractors,
        "rationale": "direct target evidence",
        "evidence_refs": list(refs),
    }
    admission = {
        "case_id": item["case_id"],
        "mechanism": "A1_SPAN_ADMISSION",
        "source_item_hash": hash_payload(item),
        "all_candidates_assessed": True,
        "decisions": [
            {
                "span_id": span["span_id"],
                "decision": (
                    "ADMIT" if span["span_id"] in gold_ids else "REJECT"
                ),
                "relation": (
                    "DIRECT"
                    if span["span_id"] in gold_ids
                    else "IRRELEVANT"
                ),
                "rationale": "bounded test receipt",
            }
            for span in item["candidate_spans"]
        ],
        "evidence_refs": list(refs),
    }
    staged = {
        "case_id": item["case_id"],
        "mechanism": "A1_STAGED_BINDING",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "predicted_label": gold["label"],
        "primary_span_ids": gold_ids[:1],
        "corroborating_span_ids": gold_ids[1:],
        "counter_span_ids": [],
        "rejected_span_ids": sorted(distractors),
        "rationale": "direct target evidence",
        "evidence_refs": list(refs),
    }
    return one_pass, admission, staged


def test_valid_receipts_cover_each_candidate_once() -> None:
    panel = _panel()
    item = panel["public_surface"]["items"][0]
    refs = evidence_refs(item)
    one_pass, admission, staged = _receipts(panel)
    assert validate_one_pass(one_pass, item, refs) == []
    assert validate_admission(admission, item, refs) == []
    assert validate_staged_binding(
        receipt=staged,
        item=item,
        admission=admission,
        refs=refs,
    ) == []


def test_cross_type_overlap_fails_closed() -> None:
    panel = _panel()
    item = panel["public_surface"]["items"][0]
    refs = evidence_refs(item)
    one_pass, _, _ = _receipts(panel)
    one_pass["counter_span_ids"] = list(one_pass["primary_span_ids"])
    assert "CROSS_TYPE_SPAN_OVERLAP" in validate_one_pass(
        one_pass, item, refs
    )


def test_rejected_span_cannot_be_promoted_by_staged_binding() -> None:
    panel = _panel()
    item = panel["public_surface"]["items"][0]
    refs = evidence_refs(item)
    _, admission, staged = _receipts(panel)
    rejected = staged["rejected_span_ids"][0]
    staged["corroborating_span_ids"].append(rejected)
    assert "SPAN_PARTITION_INCOMPLETE" in validate_staged_binding(
        receipt=staged,
        item=item,
        admission=admission,
        refs=refs,
    )


def test_private_scoring_and_positive_delta_gate() -> None:
    panel = _panel()
    preregistration = build_preregistration(panel)
    staged_receipts = {}
    for item in panel["public_surface"]["items"]:
        gold = panel["private_gold"][item["case_id"]]
        staged_receipts[item["case_id"]] = {
            "predicted_label": gold["label"],
            "primary_span_ids": gold["gold_rationale_span_ids"][:1],
            "corroborating_span_ids": gold["gold_rationale_span_ids"][1:],
            "counter_span_ids": [],
        }
    staged_run = _run("A1_STAGED_ADMISSION_BINDING", staged_receipts)
    one_pass_run = _run("A0_ONE_PASS", {})
    staged_score = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=staged_run,
    )
    one_pass_score = score_arm(
        panel=panel,
        preregistration=preregistration,
        run=one_pass_run,
    )
    decision = calibration_decision(
        preregistration=preregistration,
        one_pass_score=one_pass_score,
        staged_score=staged_score,
    )
    assert staged_score["label_accuracy"] == 1.0
    assert staged_score["evidence_f1"] == 1.0
    assert decision["external_holdout_authorized"]


def _run(arm_id: str, receipts: dict) -> dict:
    commitment = {
        "arm_id": arm_id,
        "receipts": receipts,
        "contract_failures": [],
        "task_calls": [{
            "token_usage": {"total_tokens": 100, "provider_calls": 1}
        }],
    }
    return {**commitment, "run_hash": hash_payload(commitment)}
