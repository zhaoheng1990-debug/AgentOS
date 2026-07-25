"""Typed-reference scoring for ternary boundary review v0.84."""

from __future__ import annotations

from .admission_v5_typed_scoring import (
    score_run_against_typed_reference,
)
from .provider_telemetry import hash_payload


def score_ternary_boundary_reference(
    *,
    reference,
    baseline_run,
    atomic_run,
    staged_run,
    candidate_run,
):
    runs = {
        "baseline": baseline_run,
        "atomic": atomic_run,
        "staged": staged_run,
        "candidate": candidate_run,
    }
    scores = {
        name: score_run_against_typed_reference(
            reference=reference,
            run=run,
        )
        for name, run in runs.items()
    }
    atomic_to_staged = _paired_changes(
        reference=reference,
        before_run=atomic_run,
        after_run=staged_run,
        before_name="atomic",
        after_name="staged",
    )
    staged_to_candidate = _paired_changes(
        reference=reference,
        before_run=staged_run,
        after_run=candidate_run,
        before_name="staged",
        after_name="candidate",
    )
    staged = scores["staged"]
    candidate = scores["candidate"]
    harmful = (
        not staged_to_candidate["corrected"]
        and bool(staged_to_candidate["harmed"])
    )
    value = {
        "score_version": "admission_v9_typed_score_v0_84",
        "source_reference_hash": reference["artifact_hash"],
        "source_run_hashes": {
            name: run["run_hash"] for name, run in runs.items()
        },
        **scores,
        "atomic_to_staged": atomic_to_staged,
        "staged_to_candidate": staged_to_candidate,
        "candidate_accuracy_delta_vs_staged": (
            candidate["accuracy"] - staged["accuracy"]
        ),
        "candidate_macro_f1_delta_vs_staged": (
            candidate["macro_f1"] - staged["macro_f1"]
        ),
        "semantic_conditions": {
            "candidate_accuracy_not_worse": (
                candidate["accuracy"] >= staged["accuracy"]
            ),
            "candidate_macro_f1_not_worse": (
                candidate["macro_f1"] >= staged["macro_f1"]
            ),
            "net_span_corrections_positive": (
                len(staged_to_candidate["corrected"])
                > len(staged_to_candidate["harmed"])
            ),
            "all_candidate_mutations_bounded": (
                len(staged_to_candidate["corrected"])
                + len(staged_to_candidate["harmed"])
                == 4
            ),
        },
        "experimental_decision": (
            "REJECT_A18_TYPED_REFERENCE_HARM"
            if harmful
            else "DEFER_A18_TYPED_REFERENCE_DECISION"
        ),
        "candidate_acceptance_authorized": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _paired_changes(
    *,
    reference,
    before_run,
    after_run,
    before_name,
    after_name,
):
    before_predictions = _predictions(before_run)
    after_predictions = _predictions(after_run)
    corrected, harmed = [], []
    for label in reference["labels"]:
        key = (label["case_id"], label["span_id"])
        expected = label["disposition"]
        before_correct = before_predictions[key] == expected
        after_correct = after_predictions[key] == expected
        record = {
            "case_id": key[0],
            "span_id": key[1],
            "reference": expected,
            before_name: before_predictions[key],
            after_name: after_predictions[key],
        }
        if after_correct and not before_correct:
            corrected.append(record)
        if before_correct and not after_correct:
            harmed.append(record)
    return {
        "corrected": corrected,
        "harmed": harmed,
        "corrected_count": len(corrected),
        "harmed_count": len(harmed),
    }


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
