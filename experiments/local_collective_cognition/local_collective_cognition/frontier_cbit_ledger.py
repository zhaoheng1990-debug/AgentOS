"""Outcome-bound Cbit accounting shared by core and frontier candidates."""

from __future__ import annotations

from collections import Counter

from .provider_telemetry import hash_payload


LEDGER_VERSION = "frontier_realized_cbit_ledger_v0_27"
CBIT_WEIGHTS = {
    "supported_target": 2.0,
    "informative_null": 1.5,
    "primary_object": 0.5,
    "hidden_constraint": 0.5,
    "counterevidence": 0.5,
    "falsifiability": 0.25,
    "tokens_per_cost_unit": 4000.0,
    "quarantined_component_friction": 0.25,
    "unsupported_core_speculation_risk": 0.5,
}


def build_realized_cbit_ledger(*, corpus, run):
    bindings = corpus["private_provenance"]["bindings"]
    calls = {
        (value["arm_id"], value["case_id"]): value
        for value in run["task_calls"]
    }
    entries = []
    for key, projection in run["projections"].items():
        arm_id, case_id = key.split(":", 1)
        truth = bindings[case_id]
        call_tokens = _call_tokens(calls[(arm_id, case_id)])
        eligible = [
            value for value in projection["candidate_components"]
            if value["disposition"] != "QUARANTINED_COMPONENT"
        ]
        quarantine_count = sum(
            value["disposition"] == "QUARANTINED_COMPONENT"
            for value in [
                *projection["candidate_components"],
                *projection["census_components"],
            ]
        )
        for component in eligible:
            candidate = component["normalized_candidate"]
            entries.append(_entry(
                arm_id=arm_id,
                case_id=case_id,
                component=component,
                candidate=candidate,
                truth=truth,
                allocated_tokens=(
                    call_tokens / len(eligible) if eligible else call_tokens
                ),
                allocated_quarantine_friction=(
                    quarantine_count / len(eligible) if eligible else 0
                ),
            ))
    arm_metrics = {}
    for arm_id in sorted({
        value["arm_id"] for value in run["task_calls"]
    }):
        arm_entries = [
            value for value in entries if value["arm_id"] == arm_id
        ]
        arm_calls = [
            value for value in run["task_calls"]
            if value["arm_id"] == arm_id
        ]
        total_tokens = sum(_call_tokens(value) for value in arm_calls)
        state_counts = Counter(
            projection["receipt_state"]
            for key, projection in run["projections"].items()
            if key.startswith(arm_id + ":")
        )
        effective = round(sum(
            value["realized_effective_cbit"] for value in arm_entries
        ), 6)
        arm_metrics[arm_id] = {
            "task_count": len(arm_calls),
            "receipt_state_counts": dict(state_counts),
            "eligible_candidate_count": len(arm_entries),
            "frontier_candidate_count": sum(
                value["lane"] == "FRONTIER" for value in arm_entries
            ),
            "frontier_candidate_rate": round(
                sum(value["lane"] == "FRONTIER" for value in arm_entries)
                / len(arm_entries), 6
            ) if arm_entries else 0.0,
            "supported_target_count": sum(
                value["outcome_state"] == "SUPPORTED_TARGET"
                for value in arm_entries
            ),
            "informative_null_count": sum(
                value["outcome_state"] == "INFORMATIVE_NULL"
                for value in arm_entries
            ),
            "unresolved_count": sum(
                value["outcome_state"] == "UNRESOLVED"
                for value in arm_entries
            ),
            "realized_effective_cbit": effective,
            "mean_effective_cbit_per_case": round(
                effective / corpus["case_count"], 6
            ),
            "total_tokens": total_tokens,
            "realized_cbit_per_1k_tokens": round(
                effective / (total_tokens / 1000), 6
            ) if total_tokens else 0.0,
        }
    commitment = {
        "ledger_version": LEDGER_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "weights": CBIT_WEIGHTS,
        "lane_specific_score_weights_present": False,
        "failed_falsifiable_hypothesis_may_have_positive_cbit": True,
        "entries": sorted(
            entries,
            key=lambda value: (
                value["arm_id"], value["case_id"], value["candidate_id"]
            ),
        ),
        "arm_metrics": arm_metrics,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _entry(
    *,
    arm_id,
    case_id,
    component,
    candidate,
    truth,
    allocated_tokens,
    allocated_quarantine_friction,
):
    target = (
        candidate["source_object_id"], candidate["target_object_id"]
    )
    supported = {
        (value["source_object_id"], value["target_object_id"])
        for value in truth["supported_targets"]
    }
    informative_null = {
        (value["source_object_id"], value["target_object_id"])
        for value in truth["informative_null_targets"]
    }
    if target in supported:
        outcome = "SUPPORTED_TARGET"
        target_gain = CBIT_WEIGHTS["supported_target"]
        negative_value = 0.0
    elif target in informative_null:
        outcome = "INFORMATIVE_NULL"
        target_gain = 0.0
        negative_value = CBIT_WEIGHTS["informative_null"]
    else:
        outcome = "UNRESOLVED"
        target_gain = 0.0
        negative_value = 0.0
    primary_hits = len(
        set(target) & set(truth["primary_object_ids"])
    )
    constraint_hits = len(
        set(candidate["constraint_object_ids"])
        & set(truth["hidden_constraint_object_ids"])
    )
    counterevidence_hits = len(
        set(candidate["evidence_span_ids"])
        & set(truth["counterevidence_span_ids"])
    )
    positive = (
        target_gain
        + negative_value
        + primary_hits * CBIT_WEIGHTS["primary_object"]
        + constraint_hits * CBIT_WEIGHTS["hidden_constraint"]
        + counterevidence_hits * CBIT_WEIGHTS["counterevidence"]
        + CBIT_WEIGHTS["falsifiability"]
    )
    token_cost = allocated_tokens / CBIT_WEIGHTS["tokens_per_cost_unit"]
    friction_cost = (
        allocated_quarantine_friction
        * CBIT_WEIGHTS["quarantined_component_friction"]
    )
    promotion_risk = (
        CBIT_WEIGHTS["unsupported_core_speculation_risk"]
        if candidate["lane"] == "CORE"
        and candidate["epistemic_basis"] == "SPECULATIVE"
        else 0.0
    )
    effective = positive - token_cost - friction_cost - promotion_risk
    commitment = {
        "arm_id": arm_id,
        "case_id": case_id,
        "candidate_id": candidate["candidate_id"],
        "lane": candidate["lane"],
        "component_disposition": component["disposition"],
        "outcome_state": outcome,
        "target_gain": target_gain,
        "negative_result_value": negative_value,
        "primary_object_hits": primary_hits,
        "hidden_constraint_hits": constraint_hits,
        "counterevidence_hits": counterevidence_hits,
        "falsifiability_value": CBIT_WEIGHTS["falsifiability"],
        "allocated_tokens": round(allocated_tokens, 6),
        "token_cost": round(token_cost, 6),
        "coordination_friction_cost": round(friction_cost, 6),
        "unsupported_promotion_risk": promotion_risk,
        "realized_effective_cbit": round(effective, 6),
        "lane_bonus": 0.0,
        "candidate_state": "OUTCOME_SCORED_NO_PROMOTION_AUTHORITY",
    }
    return {**commitment, "entry_hash": hash_payload(commitment)}


def _call_tokens(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
