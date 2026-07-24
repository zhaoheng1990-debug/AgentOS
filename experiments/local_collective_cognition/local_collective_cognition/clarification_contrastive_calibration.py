"""Frozen scoring for clarification representation v0.8."""

from __future__ import annotations

from collections import Counter

from .clarification_contrastive_holdout import validate_contrastive_holdout_artifact
from .clarification_contrastive_runtime import CATEGORY_LANE, SELECTION_LANE, validate_contrastive_run
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_contrastive_calibration_v0_8"
FROZEN_GATES = {
    "minimum_accuracy": 0.90,
    "minimum_open_recall": 0.90,
    "minimum_fixed_recall": 0.90,
    "minimum_pair_flip_rate": 0.80,
    "minimum_gain_over_category_fingerprint": 0.10,
    "minimum_quote_bound_rate": 0.95,
    "maximum_unresolved_rate": 0.05,
    "maximum_call_multiplier": 1.10,
}


def build_contrastive_calibration(*, corpus_artifact, candidate_run):
    validate_contrastive_holdout_artifact(corpus_artifact)
    validate_contrastive_run(candidate_run, corpus_artifact=corpus_artifact)
    oracle = corpus_artifact["private_oracle"]["bindings"]
    predictions = {row["blind_case_id"]: row for row in candidate_run["predictions"]}
    rows = []
    for blind_id, truth in sorted(oracle.items()):
        prediction = predictions[blind_id]
        rows.append({
            "blind_case_id": blind_id,
            "pair_token": truth["pair_token"],
            "truth": truth["category"],
            "CATEGORY_FINGERPRINT": prediction["category_fingerprint"],
            "REQUEST_SELECTION": prediction["selection_derived_category"],
            "request_selection": prediction["request_selection"],
            "selection_quote_bound": prediction["selection_quote_bound"],
        })
    arm_metrics = {
        "CATEGORY_FINGERPRINT": _score(rows, "CATEGORY_FINGERPRINT", candidate_run["arm_accounting"][CATEGORY_LANE]),
        "REQUEST_SELECTION": _score(rows, "REQUEST_SELECTION", candidate_run["arm_accounting"][SELECTION_LANE]),
    }
    candidate = arm_metrics["REQUEST_SELECTION"]
    baseline = arm_metrics["CATEGORY_FINGERPRINT"]
    call_multiplier = _ratio(candidate["attributed_provider_calls"], baseline["attributed_provider_calls"])
    gain = candidate["accuracy"] - baseline["accuracy"]
    gate_results = {
        "accuracy": candidate["accuracy"] >= FROZEN_GATES["minimum_accuracy"],
        "open_recall": candidate["open_recall"] >= FROZEN_GATES["minimum_open_recall"],
        "fixed_recall": candidate["fixed_recall"] >= FROZEN_GATES["minimum_fixed_recall"],
        "pair_flip_rate": candidate["pair_flip_rate"] >= FROZEN_GATES["minimum_pair_flip_rate"],
        "gain_over_category_fingerprint": gain >= FROZEN_GATES["minimum_gain_over_category_fingerprint"],
        "quote_bound_rate": candidate["quote_bound_rate"] >= FROZEN_GATES["minimum_quote_bound_rate"],
        "unresolved_rate": candidate["unresolved_rate"] <= FROZEN_GATES["maximum_unresolved_rate"],
        "call_multiplier": call_multiplier <= FROZEN_GATES["maximum_call_multiplier"],
    }
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "source_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "frozen_gates": FROZEN_GATES,
        "rows": rows,
        "arm_metrics": arm_metrics,
        "accuracy_gain_over_category_fingerprint": gain,
        "call_multiplier": call_multiplier,
        "gate_results": gate_results,
        "candidate_state": "CONTRASTIVE_REPRESENTATION_CANDIDATE" if all(gate_results.values()) else "CONTRASTIVE_REPRESENTATION_GATE_FAILED",
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
        "real_world_ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_contrastive_calibration(artifact, *, corpus_artifact, candidate_run):
    expected = build_contrastive_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run)
    if artifact != expected:
        raise ValueError("clarification_contrastive_calibration_invalid")


def _score(rows, arm, accounting):
    total = len(rows)
    open_rows = [row for row in rows if row["truth"] == "OPEN_RIVALS"]
    fixed_rows = [row for row in rows if row["truth"] == "PROMPT_FIXED"]
    pair_tokens = sorted({row["pair_token"] for row in rows})
    correct = sum(row[arm] == row["truth"] for row in rows)
    unresolved = sum(row[arm] == "UNCERTAIN" for row in rows)
    quote_bound = sum(row["selection_quote_bound"] for row in rows) if arm == "REQUEST_SELECTION" else total
    return {
        "accuracy": correct / total,
        "open_recall": sum(row[arm] == row["truth"] for row in open_rows) / len(open_rows),
        "fixed_recall": sum(row[arm] == row["truth"] for row in fixed_rows) / len(fixed_rows),
        "pair_flip_rate": sum(all(row[arm] == row["truth"] for row in rows if row["pair_token"] == token) for token in pair_tokens) / len(pair_tokens),
        "unresolved_rate": unresolved / total,
        "quote_bound_rate": quote_bound / total,
        "prediction_counts": dict(sorted(Counter(row[arm] for row in rows).items())),
        "attributed_provider_calls": accounting["attributed_provider_calls"],
        "attributed_tokens": accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"],
        "tokens_per_item": (accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]) / total,
    }


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else float("inf")
