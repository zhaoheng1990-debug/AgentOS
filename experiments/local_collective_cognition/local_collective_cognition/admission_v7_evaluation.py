"""Pre-reference evaluation for staged context utility v0.82."""

from __future__ import annotations

from collections import Counter

from .admission_v3_evaluation import score_run, validate_run
from .admission_v7_fresh_holdout import (
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
    candidate_run,
):
    validate_fresh_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    runs = {
        "baseline": baseline_run,
        "atomic": atomic_run,
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
    evidence_invariant = all(
        candidate_run["partitions"][case_id]["evidence_span_ids"]
        == partition["evidence_span_ids"]
        for case_id, partition in atomic_run["partitions"].items()
    )
    changes = _changes(atomic_run, candidate_run)
    invalid_changes = [
        change for change in changes
        if "ADMIT_EVIDENCE" in {
            change["atomic"],
            change["candidate"],
        }
    ]
    conflicts = [
        {
            "case_id": case_id,
            **conflict,
        }
        for case_id, partition in candidate_run["partitions"].items()
        for conflict in partition["semantic_conflict_ledger"]
    ]
    conflict_codes = Counter(
        code
        for conflict in conflicts
        for code in conflict["context_codes"]
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
    candidate_distribution = distributions["candidate"]
    conditions.update({
        "atomic_evidence_partition_invariance": (
            evidence_invariant and not invalid_changes
        ),
        "candidate_context_and_reject_noncollapsed": (
            candidate_distribution["RETAIN_CONTEXT"] > 0
            and candidate_distribution["REJECT"] > 0
        ),
        "grounded_context_policy": all(
            partition.get("ungrounded_context_promotion_allowed") is False
            and partition.get(
                "atomic_evidence_partition_mutation_allowed"
            ) is False
            for partition in candidate_run["partitions"].values()
        ),
        "effect_rejudgment_absent": (
            candidate_run.get("provider_effect_rejudgment_authority")
            is False
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
        "evaluation_version": "admission_v7_pre_reference_v0_82",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hashes": {
            name: run["run_hash"] for name, run in runs.items()
        },
        **scores,
        "candidate_system_physical_total_tokens": (
            scores["atomic"]["physical_total_tokens"]
            + scores["candidate"]["physical_total_tokens"]
        ),
        "predicted_distributions": distributions,
        "atomic_to_candidate_changes": changes,
        "atomic_to_candidate_change_count": len(changes),
        "invalid_evidence_change_count": len(invalid_changes),
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


def _changes(atomic_run, candidate_run):
    atomic = _predictions(atomic_run)
    candidate = _predictions(candidate_run)
    return [
        {
            "case_id": key[0],
            "span_id": key[1],
            "atomic": atomic[key],
            "candidate": candidate[key],
        }
        for key in sorted(candidate)
        if atomic.get(key) != candidate[key]
    ]


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
