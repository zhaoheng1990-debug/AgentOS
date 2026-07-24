"""Frozen scoring for explicit-selection warrants v0.10."""

from __future__ import annotations

from collections import Counter

from .clarification_warrant_holdout import validate_warrant_holdout_artifact
from .clarification_warrant_runtime import BASELINE_LANE, WARRANT_LANE, validate_warrant_run
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_warrant_calibration_v0_10"
FROZEN_GATES = {
    "minimum_accuracy": 0.90,
    "minimum_explicit_recall": 0.90,
    "minimum_pragmatic_open_recall": 0.90,
    "minimum_fixed_direction_accuracy": 0.90,
    "minimum_hard_warrant_precision": 0.90,
    "minimum_pragmatic_preference_alignment": 0.75,
    "minimum_gain_over_baseline": 0.10,
    "minimum_quote_bound_rate": 0.95,
    "maximum_unresolved_rate": 0.05,
    "maximum_call_multiplier": 1.10,
}


def build_warrant_calibration(*, corpus_artifact, candidate_run):
    validate_warrant_holdout_artifact(corpus_artifact)
    validate_warrant_run(candidate_run, corpus_artifact=corpus_artifact)
    oracle = corpus_artifact["private_oracle"]["bindings"]
    predictions = {row["blind_case_id"]: row for row in candidate_run["predictions"]}
    rows = []
    for blind_id, truth in sorted(oracle.items()):
        prediction = predictions[blind_id]
        rows.append({
            "blind_case_id": blind_id,
            "construction": truth["construction"],
            "truth_category": truth["truth_category"],
            "truth_explicit_selection": truth["explicit_selection"],
            "truth_pragmatic_preference": truth["pragmatic_preference"],
            "BASELINE_TWO_AXIS": prediction["baseline_derived_category"],
            "BASELINE_object_selection": prediction["baseline_object_selection"],
            "EXPLICIT_WARRANT": prediction["warrant_derived_category"],
            "WARRANT_explicit_selection": prediction["warrant_explicit_selection"],
            "WARRANT_pragmatic_preference": prediction["warrant_pragmatic_preference"],
            "WARRANT_assessment_status": prediction["warrant_assessment_status"],
            "WARRANT_type": prediction["warrant_type"],
            "WARRANT_hard_selection": prediction["warrant_hard_selection"],
            "soft_selection_downgraded": prediction["soft_selection_downgraded"],
            "WARRANT_quote_bound": prediction["warrant_quote_bound"],
        })
    arm_metrics = {
        "BASELINE_TWO_AXIS": _baseline_score(rows, candidate_run["arm_accounting"][BASELINE_LANE]),
        "EXPLICIT_WARRANT": _warrant_score(rows, candidate_run["arm_accounting"][WARRANT_LANE]),
    }
    baseline, candidate = arm_metrics["BASELINE_TWO_AXIS"], arm_metrics["EXPLICIT_WARRANT"]
    gain = candidate["accuracy"] - baseline["accuracy"]
    call_multiplier = _ratio(candidate["attributed_provider_calls"], baseline["attributed_provider_calls"])
    gate_results = {
        "accuracy": candidate["accuracy"] >= FROZEN_GATES["minimum_accuracy"],
        "explicit_recall": candidate["explicit_recall"] >= FROZEN_GATES["minimum_explicit_recall"],
        "pragmatic_open_recall": candidate["pragmatic_open_recall"] >= FROZEN_GATES["minimum_pragmatic_open_recall"],
        "fixed_direction_accuracy": candidate["fixed_direction_accuracy"] >= FROZEN_GATES["minimum_fixed_direction_accuracy"],
        "hard_warrant_precision": candidate["hard_warrant_precision"] >= FROZEN_GATES["minimum_hard_warrant_precision"],
        "pragmatic_preference_alignment": candidate["pragmatic_preference_alignment"] >= FROZEN_GATES["minimum_pragmatic_preference_alignment"],
        "gain_over_baseline": gain >= FROZEN_GATES["minimum_gain_over_baseline"],
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
        "accuracy_gain_over_baseline": gain,
        "call_multiplier": call_multiplier,
        "gate_results": gate_results,
        "candidate_state": "EXPLICIT_SELECTION_WARRANT_CANDIDATE" if all(gate_results.values()) else "EXPLICIT_SELECTION_WARRANT_GATE_FAILED",
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
        "pragmatic_preference_is_constructed_proxy": True,
        "real_world_ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_warrant_calibration(artifact, *, corpus_artifact, candidate_run):
    if artifact != build_warrant_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run):
        raise ValueError("clarification_warrant_calibration_invalid")


def _baseline_score(rows, accounting):
    return _common_score(rows, "BASELINE_TWO_AXIS", accounting)


def _warrant_score(rows, accounting):
    metrics = _common_score(rows, "EXPLICIT_WARRANT", accounting)
    explicit = [row for row in rows if row["construction"] == "EXPLICIT"]
    pragmatic = [row for row in rows if row["construction"] == "PRAGMATIC_OPEN"]
    predicted_fixed = [row for row in rows if row["EXPLICIT_WARRANT"] == "PROMPT_FIXED"]
    metrics.update({
        "fixed_direction_accuracy": sum(row["WARRANT_hard_selection"] == row["truth_explicit_selection"] for row in explicit) / len(explicit),
        "hard_warrant_precision": sum(row["truth_category"] == "PROMPT_FIXED" for row in predicted_fixed) / len(predicted_fixed) if predicted_fixed else 0.0,
        "pragmatic_preference_alignment": sum(row["WARRANT_pragmatic_preference"] == row["truth_pragmatic_preference"] for row in pragmatic) / len(pragmatic),
        "soft_selection_downgrade_count": sum(row["soft_selection_downgraded"] for row in rows),
        "warrant_type_counts": dict(sorted(Counter(row["WARRANT_type"] for row in rows).items())),
    })
    return metrics


def _common_score(rows, arm, accounting):
    total = len(rows)
    explicit = [row for row in rows if row["construction"] == "EXPLICIT"]
    pragmatic = [row for row in rows if row["construction"] == "PRAGMATIC_OPEN"]
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    return {
        "accuracy": sum(row[arm] == row["truth_category"] for row in rows) / total,
        "explicit_recall": sum(row[arm] == row["truth_category"] for row in explicit) / len(explicit),
        "pragmatic_open_recall": sum(row[arm] == row["truth_category"] for row in pragmatic) / len(pragmatic),
        "unresolved_rate": sum(row[arm] == "UNCERTAIN" for row in rows) / total,
        "quote_bound_rate": sum(row["WARRANT_quote_bound"] for row in rows) / total if arm == "EXPLICIT_WARRANT" else 1.0,
        "prediction_counts": dict(sorted(Counter(row[arm] for row in rows).items())),
        "attributed_provider_calls": accounting["attributed_provider_calls"],
        "attributed_tokens": tokens,
        "tokens_per_item": tokens / total,
    }


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else float("inf")
