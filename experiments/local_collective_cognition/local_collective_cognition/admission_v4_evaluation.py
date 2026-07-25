"""Pre-reference evaluation for minimal witness admission v0.79."""

from __future__ import annotations

from .admission_v3_evaluation import score_run, validate_run
from .admission_v4_fresh_holdout import (
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
    validate_run(baseline_run)
    validate_run(candidate_run)
    baseline = score_run(panel, baseline_run)
    candidate = score_run(panel, candidate_run)
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
    calls = [
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
            len(calls) <= preregistration["maximum_total_provider_tasks"]
        ),
        "attempt_budget": (
            physical_attempts(calls)
            <= preregistration["maximum_total_physical_attempts"]
        ),
        "token_budget": (
            token_count(calls)
            <= preregistration["hard_total_token_ceiling"]
        ),
    }
    operational_pass = all(conditions.values())
    value = {
        "evaluation_version": "admission_v4_pre_reference_v0_79",
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
