"""Preregistered typed-reference scoring for staged context v0.82."""

from __future__ import annotations

from .admission_v5_typed_scoring import (
    score_run_against_typed_reference,
)
from .provider_telemetry import hash_payload


def score_staged_context_reference(
    *,
    reference,
    baseline_run,
    atomic_run,
    candidate_run,
):
    scores = {
        "baseline": score_run_against_typed_reference(
            reference=reference,
            run=baseline_run,
        ),
        "atomic": score_run_against_typed_reference(
            reference=reference,
            run=atomic_run,
        ),
        "candidate": score_run_against_typed_reference(
            reference=reference,
            run=candidate_run,
        ),
    }
    atomic_predictions = _predictions(atomic_run)
    candidate_predictions = _predictions(candidate_run)
    corrected, harmed = [], []
    for label in reference["labels"]:
        key = (label["case_id"], label["span_id"])
        expected = label["disposition"]
        before = atomic_predictions[key] == expected
        after = candidate_predictions[key] == expected
        record = {
            "case_id": key[0],
            "span_id": key[1],
            "reference": expected,
            "atomic": atomic_predictions[key],
            "candidate": candidate_predictions[key],
        }
        if after and not before:
            corrected.append(record)
        if before and not after:
            harmed.append(record)
    atomic = scores["atomic"]
    candidate = scores["candidate"]
    context_metrics = candidate["per_class"]["RETAIN_CONTEXT"]
    context_count = candidate["reference_distribution"]["RETAIN_CONTEXT"]
    conditions = {
        "typed_accuracy_improves": (
            candidate["accuracy"] > atomic["accuracy"]
        ),
        "typed_macro_f1_improves": (
            candidate["macro_f1"] > atomic["macro_f1"]
        ),
        "reject_f1_improves": (
            candidate["per_class"]["REJECT"]["f1"]
            > atomic["per_class"]["REJECT"]["f1"]
        ),
        "evidence_f1_preserved": (
            candidate["per_class"]["ADMIT_EVIDENCE"]["f1"]
            == atomic["per_class"]["ADMIT_EVIDENCE"]["f1"]
        ),
        "valid_context_recall_floor": (
            context_count == 0 or context_metrics["recall"] >= 0.5
        ),
        "net_span_corrections_positive": len(corrected) > len(harmed),
    }
    passes = all(conditions.values())
    value = {
        "score_version": "admission_v7_typed_score_v0_82",
        "source_reference_hash": reference["artifact_hash"],
        "source_run_hashes": {
            "baseline": baseline_run["run_hash"],
            "atomic": atomic_run["run_hash"],
            "candidate": candidate_run["run_hash"],
        },
        **scores,
        "atomic_to_candidate_corrected_spans": corrected,
        "atomic_to_candidate_harmed_spans": harmed,
        "accuracy_delta_vs_atomic": (
            candidate["accuracy"] - atomic["accuracy"]
        ),
        "macro_f1_delta_vs_atomic": (
            candidate["macro_f1"] - atomic["macro_f1"]
        ),
        "preregistered_semantic_conditions": conditions,
        "experimental_decision": (
            "READY_PM_REVIEW_STAGED_CONTEXT_GAIN"
            if passes
            else "REJECT_STAGED_CONTEXT_TYPED_GATE"
        ),
        "candidate_acceptance_authorized": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _predictions(run):
    keys = {
        "ADMIT_EVIDENCE": "evidence_span_ids",
        "RETAIN_CONTEXT": "context_span_ids",
        "REJECT": "rejected_span_ids",
    }
    return {
        (case_id, span_id): label
        for case_id, partition in run["partitions"].items()
        for label, key in keys.items()
        for span_id in partition[key]
    }
