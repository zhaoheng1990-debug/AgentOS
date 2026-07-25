"""Typed-reference scoring for atomic witness admission v0.80."""

from __future__ import annotations

from .admission_v3_evaluation import validate_run
from .provider_telemetry import hash_payload


CLASSES = ("ADMIT_EVIDENCE", "RETAIN_CONTEXT", "REJECT")


def score_typed_reference(*, reference, baseline_run, candidate_run):
    _validate_reference(reference)
    validate_run(baseline_run)
    validate_run(candidate_run)
    baseline = _score(reference, baseline_run)
    candidate = _score(reference, candidate_run)
    baseline_predictions = _predictions(baseline_run)
    candidate_predictions = _predictions(candidate_run)
    corrected, harmed = [], []
    for label in reference["labels"]:
        key = (label["case_id"], label["span_id"])
        expected = label["disposition"]
        before = baseline_predictions[key] == expected
        after = candidate_predictions[key] == expected
        record = {
            "case_id": key[0],
            "span_id": key[1],
            "reference": expected,
            "baseline": baseline_predictions[key],
            "candidate": candidate_predictions[key],
        }
        if after and not before:
            corrected.append(record)
        if before and not after:
            harmed.append(record)
    value = {
        "score_version": "admission_v5_typed_score_v0_80",
        "source_reference_hash": reference["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "corrected_spans": corrected,
        "harmed_spans": harmed,
        "accuracy_delta": (
            candidate["accuracy"] - baseline["accuracy"]
        ),
        "macro_f1_delta": (
            candidate["macro_f1"] - baseline["macro_f1"]
        ),
        "semantic_result": (
            "PARTIAL_GAIN_EVIDENCE_PERFECT_CONTEXT_REJECT_COLLAPSE"
        ),
        "automatic_promotion_decision": (
            "REJECT_AUTOMATIC_PROMOTION_CONTEXT_COLLAPSE"
        ),
        "candidate_acceptance_authorized": False,
        "fresh_acceptance_gate_preregistered": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _score(reference, run):
    predictions = _predictions(run)
    expected = [
        label["disposition"] for label in reference["labels"]
    ]
    observed = [
        predictions[(label["case_id"], label["span_id"])]
        for label in reference["labels"]
    ]
    per_class = {}
    for name in CLASSES:
        true_positive = sum(
            left == name and right == name
            for left, right in zip(expected, observed)
        )
        false_positive = sum(
            left != name and right == name
            for left, right in zip(expected, observed)
        )
        false_negative = sum(
            left == name and right != name
            for left, right in zip(expected, observed)
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        per_class[name] = {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    value = {
        "arm_id": run["arm_id"],
        "span_count": len(expected),
        "accuracy": sum(
            left == right for left, right in zip(expected, observed)
        ) / len(expected),
        "macro_f1": sum(
            per_class[name]["f1"] for name in CLASSES
        ) / len(CLASSES),
        "per_class": per_class,
        "predicted_distribution": {
            name: observed.count(name) for name in CLASSES
        },
        "reference_distribution": {
            name: expected.count(name) for name in CLASSES
        },
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _predictions(run):
    result = {}
    for case_id, partition in run["partitions"].items():
        for span_id in partition["evidence_span_ids"]:
            result[(case_id, span_id)] = "ADMIT_EVIDENCE"
        for span_id in partition["context_span_ids"]:
            result[(case_id, span_id)] = "RETAIN_CONTEXT"
        for span_id in partition["rejected_span_ids"]:
            result[(case_id, span_id)] = "REJECT"
    return result


def _validate_reference(reference):
    commitment = {
        key: item for key, item in reference.items()
        if key != "artifact_hash"
    }
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_status")
        != "EXTERNAL_TYPED_REFERENCE_CANDIDATE"
        or reference.get("label_count") != len(reference.get("labels", []))
    ):
        raise ValueError("admission_v5_typed_reference_invalid")
