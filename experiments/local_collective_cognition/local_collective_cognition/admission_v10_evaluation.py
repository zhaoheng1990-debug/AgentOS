"""Four-arm development-screen evaluation for v0.85."""

from __future__ import annotations

from collections import Counter

from .admission_v10_development_holdout import (
    validate_development_holdout,
    validate_preregistration,
)
from .admission_v3_evaluation import score_run, validate_run
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)


ALLOWED_MUTATIONS = {
    ("ADMIT_EVIDENCE", "RETAIN_CONTEXT"),
    ("RETAIN_CONTEXT", "ADMIT_EVIDENCE"),
    ("REJECT", "RETAIN_CONTEXT"),
}


def build_development_evaluation(
    *,
    panel,
    preregistration,
    baseline_run,
    atomic_run,
    staged_run,
    candidate_run,
):
    validate_development_holdout(panel)
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
    mutations = [
        {"case_id": case_id, **mutation}
        for case_id, partition in candidate_run["partitions"].items()
        for mutation in partition["mutation_ledger"]
    ]
    mutation_counts = Counter(
        f"{value['before']}_TO_{value['after']}" for value in mutations
    )
    unauthorized = [
        value for value in mutations
        if (value["before"], value["after"]) not in ALLOWED_MUTATIONS
    ]
    conflict_counts = Counter(
        code
        for partition in candidate_run["partitions"].values()
        for code in partition["semantic_conflict_codes"]
    )
    policy_ok = all(
        partition.get("evidence_to_reject_allowed") is False
        and partition.get("context_to_reject_allowed") is False
        and partition.get("reject_to_evidence_allowed") is False
        and partition.get("conflicted_mutation_allowed") is False
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
        "bounded_mutation_policy": policy_ok and not unauthorized,
        "provider_disposition_authority_absent": (
            candidate_run.get("provider_policy_authority") is False
        ),
        "external_acceptance_disabled": (
            preregistration["external_acceptance_allowed"] is False
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
        "evaluation_version": "admission_v10_development_v0_85",
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
        "predicted_distributions": {
            name: _distribution(run)
            for name, run in runs.items()
        },
        "relation_mutations": mutations,
        "relation_mutation_count": len(mutations),
        "relation_mutation_counts": dict(sorted(mutation_counts.items())),
        "unauthorized_mutation_count": len(unauthorized),
        "semantic_conflict_code_counts": dict(sorted(
            conflict_counts.items()
        )),
        "operational_conditions": conditions,
        "operational_decision": (
            "DEVELOPMENT_SCREEN_COMPLETE"
            if all(conditions.values())
            else "REJECT_RUNTIME_INTEGRITY"
        ),
        "semantic_decision": (
            "DEFERRED_EXTERNAL_TYPED_REFERENCE_REQUIRED"
        ),
        "external_acceptance_eligible": False,
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
