"""Posthoc cost and route decomposition for v0.30."""

from __future__ import annotations

from collections import defaultdict

from .frontier_cbit_ledger import CBIT_WEIGHTS
from .provider_telemetry import hash_payload
from .selective_role_routing_holdout import REPLICATION_IDS


def analyze_routing_posthoc(*, run, analysis):
    router_costs = []
    worker_only_deltas = []
    gross_candidate_deltas = []
    by_route = defaultdict(list)
    for replication_id in REPLICATION_IDS:
        ledger = analysis["replication_ledgers"][replication_id]
        for case_id, formal_delta in analysis[
            "case_deltas"
        ][replication_id].items():
            router_call = next(
                value for value in run["task_calls"]
                if value["replication_id"] == replication_id
                and value["case_id"] == case_id
                and value["stage"] == "ROUTER"
            )
            router_cost = (
                _call_tokens(router_call)
                / CBIT_WEIGHTS["tokens_per_cost_unit"]
            )
            router_costs.append(router_cost)
            worker_delta = formal_delta + router_cost
            worker_only_deltas.append(worker_delta)
            route_id = run["route_receipts"][
                f"{replication_id}:{case_id}"
            ]["route_id"]
            by_route[route_id].append(worker_delta)
            baseline_entries = [
                value for value in ledger["entries"]
                if value["arm_id"] == "A1_BASELINE"
                and value["case_id"] == case_id
            ]
            routed_entries = [
                value for value in ledger["entries"]
                if value["arm_id"] == "A2_ROUTED"
                and value["case_id"] == case_id
            ]
            baseline_gross = sum(
                _entry_gross(value) for value in baseline_entries
            )
            routed_gross = sum(
                _entry_gross(value) for value in routed_entries
            )
            gross_candidate_deltas.append(
                routed_gross - baseline_gross
            )
    shadow = analysis["shadow_regret_audit"]
    r3_formal_mean = analysis["replication_metrics"][
        shadow["replication_id"]
    ]["contrast"]["mean"]
    commitment = {
        "diagnostic_version": "selective_role_routing_posthoc_v0_30",
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "router_token_cost_per_case": _metrics(router_costs),
        "selected_worker_delta_excluding_router_cost": _metrics(
            worker_only_deltas
        ),
        "selected_candidate_gross_delta": _metrics(
            gross_candidate_deltas
        ),
        "worker_delta_by_selected_route": {
            route_id: _metrics(values)
            for route_id, values in by_route.items()
        },
        "shadow_oracle_mean_gain_vs_baseline": round(
            r3_formal_mean + shadow["mean_regret"], 6
        ),
        "router_route_collapse": {
            "selected_route_count": len(by_route),
            "available_route_count": 4,
            "largest_route_share": round(
                max(len(values) for values in by_route.values())
                / len(worker_only_deltas),
                6,
            ),
        },
        "changes_frozen_decision": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _entry_gross(entry):
    return (
        entry["realized_effective_cbit"]
        + entry["token_cost"]
        + entry["coordination_friction_cost"]
        + entry["unsupported_promotion_risk"]
    )


def _metrics(values):
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    median = (
        ordered[midpoint]
        if len(ordered) % 2
        else (ordered[midpoint - 1] + ordered[midpoint]) / 2
    )
    return {
        "count": len(values),
        "mean": round(sum(values) / len(values), 6),
        "median": round(median, 6),
        "positive_count": sum(value > 0 for value in values),
    }


def _call_tokens(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
