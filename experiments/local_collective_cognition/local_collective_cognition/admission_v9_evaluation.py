"""Four-arm pre-reference evaluation for ternary review v0.84."""

from __future__ import annotations

from collections import Counter

from .admission_v3_evaluation import score_run, validate_run
from .admission_v9_fresh_holdout import (
    validate_fresh_holdout,
    validate_preregistration,
)
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)


def build_pre_reference_evaluation(
    *,
    panel,
    preregistration,
    baseline_run,
    atomic_run,
    staged_run,
    candidate_run,
):
    validate_fresh_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    runs = {
        "baseline": baseline_run,
        "atomic": atomic_run,
        "staged": staged_run,
        "candidate": candidate_run,
    }
    for run in runs.values():
        validate_run(run)
    scores = {
        name: score_run(panel, run)
        for name, run in runs.items()
    }
    distributions = {
        name: _distribution(run)
        for name, run in runs.items()
    }
    mutations = [
        {"case_id": case_id, **mutation}
        for case_id, partition in candidate_run["partitions"].items()
        for mutation in partition["mutation_ledger"]
    ]
    mutation_counts = Counter(
        f"{mutation['before']}_TO_{mutation['after']}"
        for mutation in mutations
    )
    conflicts = [
        {"case_id": case_id, **conflict}
        for case_id, partition in candidate_run["partitions"].items()
        for conflict in partition["semantic_conflict_ledger"]
    ]
    conflict_codes = Counter(
        code for conflict in conflicts for code in conflict["codes"]
    )
    reject_invariant = all(
        candidate_run["partitions"][case_id]["rejected_span_ids"]
        == partition["rejected_span_ids"]
        for case_id, partition in staged_run["partitions"].items()
    )
    mutation_policy = all(
        partition.get("reject_partition_mutation_allowed") is False
        and partition.get("not_stated_demotion_allowed") is False
        and partition.get("unwitnessed_boundary_mutation_allowed") is False
        and partition.get("conflicted_boundary_mutation_allowed") is False
        for partition in candidate_run["partitions"].values()
    )
    calls = [
        call
        for run in runs.values()
        for call in run["task_calls"]
    ]
    gate = preregistration["operational_gate"]
    conditions = {}
    for name, score in scores.items():
        conditions[f"{name}_valid_receipts"] = (
            score["valid_receipt_count"]
            >= gate["valid_receipts_min_per_arm"]
        )
        conditions[f"{name}_failures"] = (
            score["failure_count"] <= gate["failures_max_per_arm"]
        )
        conditions[f"{name}_complete_partitions"] = (
            score["complete_partition_count"]
            >= gate["complete_partitions_min_per_arm"]
        )
    conditions.update({
        "reject_partition_invariance": reject_invariant,
        "ternary_boundary_mutation_policy": mutation_policy,
        "provider_disposition_authority_absent": (
            candidate_run.get("provider_policy_authority") is False
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
    })
    value = {
        "evaluation_version": "admission_v9_pre_reference_v0_84",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hashes": {
            name: run["run_hash"] for name, run in runs.items()
        },
        **scores,
        "candidate_system_physical_total_tokens": (
            scores["atomic"]["physical_total_tokens"]
            + scores["staged"]["physical_total_tokens"]
            + scores["candidate"]["physical_total_tokens"]
        ),
        "predicted_distributions": distributions,
        "boundary_mutations": mutations,
        "boundary_mutation_count": len(mutations),
        "boundary_mutation_counts": dict(sorted(mutation_counts.items())),
        "semantic_conflict_span_count": len(conflicts),
        "semantic_conflict_code_counts": dict(sorted(
            conflict_codes.items()
        )),
        "operational_conditions": conditions,
        "operational_decision": (
            "READY_EXTERNAL_TYPED_PANEL"
            if all(conditions.values())
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


def _distribution(run):
    keys = {
        "ADMIT_EVIDENCE": "evidence_span_ids",
        "RETAIN_CONTEXT": "context_span_ids",
        "REJECT": "rejected_span_ids",
    }
    return {
        label: sum(
            len(partition[key])
            for partition in run["partitions"].values()
        )
        for label, key in keys.items()
    }
