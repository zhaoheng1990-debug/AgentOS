"""Frozen scoring for the v0.9 two-axis and visibility ablation."""

from __future__ import annotations

from collections import Counter

from .clarification_two_axis_holdout import validate_two_axis_holdout_artifact
from .clarification_two_axis_runtime import CATEGORY_LANE, PAIRED_AXIS_LANE, SHUFFLED_AXIS_LANE, validate_two_axis_run
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_two_axis_calibration_v0_9"
FROZEN_GATES = {
    "minimum_accuracy": 0.90,
    "minimum_open_recall": 0.90,
    "minimum_fixed_recall": 0.90,
    "minimum_fixed_direction_accuracy": 0.90,
    "minimum_pair_flip_rate": 0.80,
    "minimum_gain_over_category_fingerprint": 0.10,
    "minimum_quote_bound_rate": 0.95,
    "maximum_unresolved_rate": 0.05,
    "maximum_paired_visibility_advantage": 0.10,
    "maximum_call_multiplier": 1.10,
}


def build_two_axis_calibration(*, corpus_artifact, candidate_run):
    validate_two_axis_holdout_artifact(corpus_artifact)
    validate_two_axis_run(candidate_run, corpus_artifact=corpus_artifact)
    oracle = corpus_artifact["private_oracle"]["bindings"]
    predictions = {row["blind_case_id"]: row for row in candidate_run["predictions"]}
    selection_map = {"ANSWER_A": "CANDIDATE_A", "ANSWER_B": "CANDIDATE_B", "NONE": "NONE"}
    rows = []
    for blind_id, truth in sorted(oracle.items()):
        prediction = predictions[blind_id]
        rows.append({
            "blind_case_id": blind_id,
            "pair_token": truth["pair_token"],
            "truth_category": truth["category"],
            "truth_object_selection": selection_map[truth["object_selection"]],
            "CATEGORY_FINGERPRINT": prediction["category_fingerprint"],
            "PAIRED_TWO_AXIS": prediction["paired_derived_category"],
            "PAIRED_object_selection": prediction["paired_object_selection"],
            "PAIRED_assessment_status": prediction["paired_assessment_status"],
            "PAIRED_quote_bound": prediction["paired_quote_bound"],
            "SHUFFLED_TWO_AXIS": prediction["shuffled_derived_category"],
            "SHUFFLED_object_selection": prediction["shuffled_object_selection"],
            "SHUFFLED_assessment_status": prediction["shuffled_assessment_status"],
            "SHUFFLED_quote_bound": prediction["shuffled_quote_bound"],
        })
    arm_metrics = {
        "CATEGORY_FINGERPRINT": _score(rows, "CATEGORY_FINGERPRINT", candidate_run["arm_accounting"][CATEGORY_LANE]),
        "PAIRED_TWO_AXIS": _score(rows, "PAIRED_TWO_AXIS", candidate_run["arm_accounting"][PAIRED_AXIS_LANE], axis_prefix="PAIRED"),
        "SHUFFLED_TWO_AXIS": _score(rows, "SHUFFLED_TWO_AXIS", candidate_run["arm_accounting"][SHUFFLED_AXIS_LANE], axis_prefix="SHUFFLED"),
    }
    baseline = arm_metrics["CATEGORY_FINGERPRINT"]
    paired = arm_metrics["PAIRED_TWO_AXIS"]
    candidate = arm_metrics["SHUFFLED_TWO_AXIS"]
    gain = candidate["accuracy"] - baseline["accuracy"]
    visibility_advantage = paired["accuracy"] - candidate["accuracy"]
    call_multiplier = _ratio(candidate["attributed_provider_calls"], baseline["attributed_provider_calls"])
    gate_results = {
        "accuracy": candidate["accuracy"] >= FROZEN_GATES["minimum_accuracy"],
        "open_recall": candidate["open_recall"] >= FROZEN_GATES["minimum_open_recall"],
        "fixed_recall": candidate["fixed_recall"] >= FROZEN_GATES["minimum_fixed_recall"],
        "fixed_direction_accuracy": candidate["fixed_direction_accuracy"] >= FROZEN_GATES["minimum_fixed_direction_accuracy"],
        "pair_flip_rate": candidate["pair_flip_rate"] >= FROZEN_GATES["minimum_pair_flip_rate"],
        "gain_over_category_fingerprint": gain >= FROZEN_GATES["minimum_gain_over_category_fingerprint"],
        "quote_bound_rate": candidate["quote_bound_rate"] >= FROZEN_GATES["minimum_quote_bound_rate"],
        "unresolved_rate": candidate["unresolved_rate"] <= FROZEN_GATES["maximum_unresolved_rate"],
        "paired_visibility_advantage": visibility_advantage <= FROZEN_GATES["maximum_paired_visibility_advantage"],
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
        "paired_visibility_advantage": visibility_advantage,
        "call_multiplier": call_multiplier,
        "gate_results": gate_results,
        "candidate_state": "TWO_AXIS_REPRESENTATION_CANDIDATE" if all(gate_results.values()) else "TWO_AXIS_REPRESENTATION_GATE_FAILED",
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
        "real_world_ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_two_axis_calibration(artifact, *, corpus_artifact, candidate_run):
    if artifact != build_two_axis_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run):
        raise ValueError("clarification_two_axis_calibration_invalid")


def _score(rows, arm, accounting, axis_prefix=None):
    total = len(rows)
    open_rows = [row for row in rows if row["truth_category"] == "OPEN_RIVALS"]
    fixed_rows = [row for row in rows if row["truth_category"] == "PROMPT_FIXED"]
    pair_tokens = sorted({row["pair_token"] for row in rows})
    unresolved = sum(row[arm] == "UNCERTAIN" for row in rows)
    direction = (
        sum(row[f"{axis_prefix}_object_selection"] == row["truth_object_selection"] for row in fixed_rows) / len(fixed_rows)
        if axis_prefix else None
    )
    quote_rate = sum(row[f"{axis_prefix}_quote_bound"] for row in rows) / total if axis_prefix else 1.0
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    return {
        "accuracy": sum(row[arm] == row["truth_category"] for row in rows) / total,
        "open_recall": sum(row[arm] == row["truth_category"] for row in open_rows) / len(open_rows),
        "fixed_recall": sum(row[arm] == row["truth_category"] for row in fixed_rows) / len(fixed_rows),
        "fixed_direction_accuracy": direction,
        "pair_flip_rate": sum(all(row[arm] == row["truth_category"] for row in rows if row["pair_token"] == token) for token in pair_tokens) / len(pair_tokens),
        "unresolved_rate": unresolved / total,
        "quote_bound_rate": quote_rate,
        "prediction_counts": dict(sorted(Counter(row[arm] for row in rows).items())),
        "attributed_provider_calls": accounting["attributed_provider_calls"],
        "attributed_tokens": tokens,
        "tokens_per_item": tokens / total,
    }


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else float("inf")
