"""Post-hoc worker uplift decomposition for Runtime escalation v0.33."""

from __future__ import annotations

from collections import defaultdict

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .provider_telemetry import hash_payload
from .runtime_escalation_holdout import REPLICATION_IDS
from .selective_role_routing_experiment import (
    _combined_usage,
    _metrics,
)


POSTHOC_VERSION = "runtime_escalation_worker_uplift_posthoc_v0_33"


def analyze_worker_uplift(*, corpus, run, formal_analysis):
    if formal_analysis.get("source_run_hash") != run.get("run_hash"):
        raise ValueError("runtime_escalation_posthoc_source_invalid")
    base_deltas = {}
    worker_net_uplifts = []
    worker_gross_uplifts = []
    worker_token_penalties = []
    route_uplifts = defaultdict(list)
    flag_uplifts = defaultdict(list)
    for replication_id in REPLICATION_IDS:
        provisional_ledger = build_realized_cbit_ledger(
            corpus=corpus,
            run=_provisional_scoring_run(
                run,
                replication_id=replication_id,
            ),
        )
        formal_ledger = formal_analysis["replication_ledgers"][
            replication_id
        ]
        provisional = _arm_case_totals(provisional_ledger)
        formal = _arm_case_totals(formal_ledger)
        base_deltas[replication_id] = {}
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            base_delta = (
                provisional[(case_id, "A2_RUNTIME")]["net"]
                - provisional[(case_id, "A1_BASELINE")]["net"]
            )
            base_deltas[replication_id][case_id] = round(base_delta, 6)
            trigger = run["trigger_receipts"][
                f"{replication_id}:A2_RUNTIME:{case_id}"
            ]
            if not trigger["triggered"]:
                continue
            net_uplift = (
                formal[(case_id, "A2_RUNTIME")]["net"]
                - provisional[(case_id, "A2_RUNTIME")]["net"]
            )
            gross_uplift = (
                formal[(case_id, "A2_RUNTIME")]["gross"]
                - provisional[(case_id, "A2_RUNTIME")]["gross"]
            )
            token_penalty = (
                formal[(case_id, "A2_RUNTIME")]["token_cost"]
                - provisional[(case_id, "A2_RUNTIME")]["token_cost"]
            )
            worker_net_uplifts.append(net_uplift)
            worker_gross_uplifts.append(gross_uplift)
            worker_token_penalties.append(token_penalty)
            route_uplifts[trigger["route_id"]].append(net_uplift)
            for flag in trigger["diagnostic_flags"]:
                flag_uplifts[flag].append(net_uplift)
    pooled_base = [
        value
        for replication in base_deltas.values()
        for value in replication.values()
    ]
    commitment = {
        "posthoc_version": POSTHOC_VERSION,
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": formal_analysis["artifact_hash"],
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "counterfactual_no_escalation_contrast": _metrics(pooled_base),
        "triggered_worker_net_uplift": _metrics(worker_net_uplifts),
        "triggered_worker_gross_candidate_uplift": _metrics(
            worker_gross_uplifts
        ),
        "triggered_worker_token_penalty": _distribution(
            worker_token_penalties
        ),
        "net_uplift_by_route": {
            key: _metrics(values)
            for key, values in sorted(route_uplifts.items())
        },
        "net_uplift_by_diagnostic_flag": {
            key: _metrics(values)
            for key, values in sorted(flag_uplifts.items())
        },
        "base_case_deltas": base_deltas,
        "frozen_decision_changed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _provisional_scoring_run(run, *, replication_id):
    task_calls = []
    projections = {}
    case_ids = sorted({
        value["case_id"]
        for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "STANDARD_ONTOLOGY"
    })
    for case_id in case_ids:
        baseline = _find_standard_call(
            run,
            replication_id=replication_id,
            arm_id="A1_BASELINE",
            case_id=case_id,
        )
        runtime = _find_standard_call(
            run,
            replication_id=replication_id,
            arm_id="A2_RUNTIME",
            case_id=case_id,
        )
        for arm_id, call in (
            ("A1_BASELINE", baseline),
            ("A2_RUNTIME", runtime),
        ):
            task_calls.append({
                "arm_id": arm_id,
                "case_id": case_id,
                "invocation_receipt": {
                    "token_usage": _combined_usage([call]),
                    "derived_cost_receipt": True,
                    "source_call_hashes": [call["call_hash"]],
                },
            })
        baseline_key = f"{replication_id}:A1_BASELINE:{case_id}"
        runtime_key = f"{replication_id}:A2_RUNTIME:{case_id}"
        projections[f"A1_BASELINE:{case_id}"] = run[
            "final_projections"
        ][baseline_key]
        projections[f"A2_RUNTIME:{case_id}"] = run[
            "provisional_projections"
        ][runtime_key]
    commitment = {
        "task_calls": task_calls,
        "projections": projections,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _find_standard_call(
    run, *, replication_id, arm_id, case_id
):
    return next(
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["arm_id"] == arm_id
        and value["case_id"] == case_id
        and value["stage"] == "STANDARD_ONTOLOGY"
    )


def _arm_case_totals(ledger):
    totals = defaultdict(lambda: {
        "net": 0.0,
        "gross": 0.0,
        "token_cost": 0.0,
    })
    for entry in ledger["entries"]:
        key = (entry["case_id"], entry["arm_id"])
        totals[key]["net"] += entry["realized_effective_cbit"]
        totals[key]["token_cost"] += entry["token_cost"]
        totals[key]["gross"] += (
            entry["realized_effective_cbit"] + entry["token_cost"]
        )
    return totals


def _distribution(values):
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
        "minimum": round(min(values), 6),
        "maximum": round(max(values), 6),
    }
