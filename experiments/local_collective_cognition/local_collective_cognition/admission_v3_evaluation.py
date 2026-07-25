"""Pre-reference diagnostics for witness admission v0.78."""

from __future__ import annotations

from statistics import mean

from .admission_v3_fresh_holdout import (
    validate_fresh_holdout,
    validate_preregistration,
)
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)


def build_pre_reference_evaluation(
    *, panel, preregistration, baseline_run, candidate_run
):
    validate_fresh_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    _validate_run(baseline_run)
    _validate_run(candidate_run)
    baseline = _score_run(panel, baseline_run)
    candidate = _score_run(panel, candidate_run)
    old = {item["case_id"]: item for item in baseline["cases"]}
    new = {item["case_id"]: item for item in candidate["cases"]}
    improved = sorted(
        case_id for case_id in new
        if new[case_id]["evidence_f1"] > old[case_id]["evidence_f1"]
    )
    harmed = sorted(
        case_id for case_id in new
        if new[case_id]["evidence_f1"] < old[case_id]["evidence_f1"]
    )
    total_calls = [
        *baseline_run["task_calls"],
        *candidate_run["task_calls"],
    ]
    gate = preregistration["operational_gate"]
    conditions = {
        "baseline_valid_receipts": (
            baseline["valid_receipt_count"]
            >= gate["valid_receipts_min_per_arm"]
        ),
        "candidate_valid_receipts": (
            candidate["valid_receipt_count"]
            >= gate["valid_receipts_min_per_arm"]
        ),
        "baseline_failures": (
            baseline["failure_count"] <= gate["failures_max_per_arm"]
        ),
        "candidate_failures": (
            candidate["failure_count"] <= gate["failures_max_per_arm"]
        ),
        "baseline_complete_partitions": (
            baseline["complete_partition_count"]
            >= gate["complete_partitions_min_per_arm"]
        ),
        "candidate_complete_partitions": (
            candidate["complete_partition_count"]
            >= gate["complete_partitions_min_per_arm"]
        ),
        "task_budget": (
            len(total_calls)
            <= preregistration["maximum_total_provider_tasks"]
        ),
        "attempt_budget": (
            physical_attempts(total_calls)
            <= preregistration["maximum_total_physical_attempts"]
        ),
        "token_budget": (
            token_count(total_calls)
            <= preregistration["hard_total_token_ceiling"]
        ),
    }
    operational_pass = all(conditions.values())
    value = {
        "evaluation_version": "admission_v3_pre_reference_v0_78",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "improved_case_ids": improved,
        "harmed_case_ids": harmed,
        "operational_conditions": conditions,
        "operational_decision": (
            "READY_EXTERNAL_TYPED_PANEL"
            if operational_pass
            else "REJECT_RUNTIME_INTEGRITY"
        ),
        "semantic_decision": "DEFERRED_EXTERNAL_TYPED_REFERENCE_REQUIRED",
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "candidate_acceptance_authorized": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _score_run(panel, run):
    cases = []
    items = {
        item["case_id"]: item
        for item in panel["public_surface"]["items"]
    }
    for case_id, gold in panel["private_gold"].items():
        partition = run["partitions"].get(case_id)
        expected = set(gold["gold_rationale_span_ids"])
        if partition is None:
            cases.append({
                "case_id": case_id,
                "evidence_precision": 0.0,
                "evidence_recall": 0.0,
                "evidence_f1": 0.0,
                "partition_complete": 0,
                "admission_state": "MISSING",
            })
            continue
        predicted = set(partition["evidence_span_ids"])
        matched = len(predicted & expected)
        precision = matched / len(predicted) if predicted else 0.0
        recall = matched / len(expected) if expected else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        observed = set(
            partition["evidence_span_ids"]
            + partition["context_span_ids"]
            + partition["rejected_span_ids"]
        )
        expected_ids = {
            span["span_id"]
            for span in items[case_id]["candidate_spans"]
        }
        cases.append({
            "case_id": case_id,
            "evidence_precision": precision,
            "evidence_recall": recall,
            "evidence_f1": f1,
            "partition_complete": int(observed == expected_ids),
            "admission_state": partition["admission_state"],
        })
    failures = (
        len(run["contract_failures"])
        + len(run["compiler_failures"])
    )
    value = {
        "arm_id": run["arm_id"],
        "case_count": len(cases),
        "valid_receipt_count": len(run["receipts"]),
        "failure_count": failures,
        "complete_partition_count": sum(
            item["partition_complete"] for item in cases
        ),
        "evidence_precision": mean(
            item["evidence_precision"] for item in cases
        ),
        "evidence_recall": mean(
            item["evidence_recall"] for item in cases
        ),
        "evidence_f1": mean(
            item["evidence_f1"] for item in cases
        ),
        "provider_task_count": len(run["task_calls"]),
        "physical_attempt_count": physical_attempts(run["task_calls"]),
        "physical_total_tokens": token_count(run["task_calls"]),
        "cases": cases,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _validate_run(run):
    commitment = {
        key: item for key, item in run.items() if key != "run_hash"
    }
    if run.get("run_hash") != hash_payload(commitment):
        raise ValueError("admission_v3_run_hash_invalid")


# Stable read-only scoring entry points shared by later admission experiments.
score_run = _score_run
validate_run = _validate_run
