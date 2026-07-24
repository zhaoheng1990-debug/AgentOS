"""Private scoring and calibration gate for v0.65."""

from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Any

from .benchmark_bridge_protocol import validate_preregistration
from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)


def score_arm(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    validate_panel(panel)
    validate_preregistration(preregistration)
    _validate_run_hash(run)
    item_map = {
        item["case_id"]: item
        for item in panel["public_surface"]["items"]
    }
    cases: list[dict[str, Any]] = []
    for case_id, gold in panel["private_gold"].items():
        receipt = run["receipts"].get(case_id)
        if receipt is None:
            cases.append(_zero_case(case_id, gold["label"]))
            continue
        selected = set(
            receipt.get("primary_span_ids", [])
            + receipt.get("corroborating_span_ids", [])
            + receipt.get("counter_span_ids", [])
        )
        gold_ids = set(gold["gold_rationale_span_ids"])
        precision, recall, evidence_f1 = _prf(selected, gold_ids)
        span_text = {
            span["span_id"]: span["text"]
            for span in item_map[case_id]["candidate_spans"]
        }
        predicted_text = " ".join(
            span_text[value] for value in sorted(selected)
        )
        gold_text = " ".join(gold["gold_rationale_texts"])
        rationale_f1 = _token_f1(predicted_text, gold_text)
        label_correct = int(receipt.get("predicted_label") == gold["label"])
        object_bound = int(
            bool(receipt.get("primary_span_ids"))
            and set(receipt["primary_span_ids"]).issubset(gold_ids)
        )
        cases.append({
            "case_id": case_id,
            "expected_label": gold["label"],
            "predicted_label": receipt.get("predicted_label"),
            "label_correct": label_correct,
            "object_binding_proxy": object_bound,
            "evidence_precision": precision,
            "evidence_recall": recall,
            "evidence_f1": evidence_f1,
            "rationale_token_f1": rationale_f1,
            "effective_cbit": mean(
                [label_correct, evidence_f1, rationale_f1]
            ),
        })
    calls = run["task_calls"]
    tokens = token_count(calls)
    failures = run["contract_failures"]
    overlap_count = sum(
        "CROSS_TYPE_SPAN_OVERLAP" in failure.get(
            "contract_failures", []
        )
        for failure in failures
    )
    summary = {
        "arm_id": run["arm_id"],
        "case_count": len(cases),
        "valid_receipt_count": len(run["receipts"]),
        "contract_failure_count": len(failures),
        "cross_type_overlap_count": overlap_count,
        "label_accuracy": mean(case["label_correct"] for case in cases),
        "object_binding_accuracy": mean(
            case["object_binding_proxy"] for case in cases
        ),
        "evidence_precision": mean(
            case["evidence_precision"] for case in cases
        ),
        "evidence_recall": mean(
            case["evidence_recall"] for case in cases
        ),
        "evidence_f1": mean(case["evidence_f1"] for case in cases),
        "rationale_token_f1": mean(
            case["rationale_token_f1"] for case in cases
        ),
        "effective_cbit": mean(case["effective_cbit"] for case in cases),
        "provider_task_count": len(calls),
        "physical_attempt_count": physical_attempts(calls),
        "physical_total_tokens": tokens,
        "effective_cbit_per_1k_tokens": (
            1000 * sum(case["effective_cbit"] for case in cases) / tokens
            if tokens
            else 0.0
        ),
        "cases": cases,
    }
    commitment = {
        **summary,
        "source_run_hash": run["run_hash"],
        "source_panel_hash": panel["artifact_hash"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def calibration_decision(
    *,
    preregistration: dict[str, Any],
    one_pass_score: dict[str, Any],
    staged_score: dict[str, Any],
) -> dict[str, Any]:
    validate_preregistration(preregistration)
    gate = preregistration["calibration_gate"]
    mechanism_delta = (
        staged_score["effective_cbit"] > one_pass_score["effective_cbit"]
        or staged_score["contract_failure_count"]
        < one_pass_score["contract_failure_count"]
        or staged_score["cross_type_overlap_count"]
        < one_pass_score["cross_type_overlap_count"]
    )
    conditions = {
        "a1_contract_failures": staged_score["contract_failure_count"]
        <= gate["a1_contract_failure_count_max"],
        "a1_cross_type_overlap": staged_score["cross_type_overlap_count"]
        <= gate["a1_cross_type_overlap_count_max"],
        "a1_label_accuracy": staged_score["label_accuracy"]
        >= gate["a1_label_accuracy_min"],
        "a1_evidence_f1": staged_score["evidence_f1"]
        >= gate["a1_evidence_f1_min"],
        "a1_rationale_token_f1": staged_score["rationale_token_f1"]
        >= gate["a1_rationale_token_f1_min"],
        "a1_positive_cbit_per_token": (
            staged_score["effective_cbit_per_1k_tokens"]
            > gate["a1_effective_cbit_per_1k_tokens_min"]
        ),
        "a1_label_not_below_a0": staged_score["label_accuracy"]
        >= one_pass_score["label_accuracy"],
        "a1_rationale_not_below_a0": staged_score["rationale_token_f1"]
        >= one_pass_score["rationale_token_f1"],
        "a1_mechanism_delta_positive": mechanism_delta,
    }
    passed = all(conditions.values())
    commitment = {
        "decision_version": "benchmark_bridge_calibration_decision_v0_65",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_one_pass_score_hash": one_pass_score["artifact_hash"],
        "source_staged_score_hash": staged_score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_BENCHMARK_BRIDGE_CALIBRATION"
            if passed
            else "REJECT_BENCHMARK_BRIDGE_CALIBRATION"
        ),
        "external_holdout_authorized": passed,
        "fresh_generalization_claim": False,
        "benchmark_native_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _prf(predicted: set[str], gold: set[str]) -> tuple[float, float, float]:
    matched = len(predicted & gold)
    precision = matched / len(predicted) if predicted else 0.0
    recall = matched / len(gold) if gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return precision, recall, f1


def _token_f1(predicted: str, gold: str) -> float:
    pred = Counter(re.findall(r"[a-z0-9]+", predicted.lower()))
    target = Counter(re.findall(r"[a-z0-9]+", gold.lower()))
    overlap = sum((pred & target).values())
    precision = overlap / sum(pred.values()) if pred else 0.0
    recall = overlap / sum(target.values()) if target else 0.0
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )


def _zero_case(case_id: str, expected_label: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "expected_label": expected_label,
        "predicted_label": None,
        "label_correct": 0,
        "object_binding_proxy": 0,
        "evidence_precision": 0.0,
        "evidence_recall": 0.0,
        "evidence_f1": 0.0,
        "rationale_token_f1": 0.0,
        "effective_cbit": 0.0,
    }


def _validate_run_hash(run: dict[str, Any]) -> None:
    commitment = {
        key: value for key, value in run.items() if key != "run_hash"
    }
    if run.get("run_hash") != hash_payload(commitment):
        raise ValueError("benchmark_bridge_run_hash_mismatch")
