"""Two-replication stability test for higher-Cbit ontology cognition v0.28."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import ARM_IDS, TASK_KIND, native_schema
from .frontier_partial_admission import project_frontier_receipt
from .frontier_stability_holdout import (
    validate_frontier_stability_holdout,
)
from .provider_telemetry import hash_payload


RUNTIME_VERSION = "frontier_stability_experiment_v0_28"
REPLICATION_IDS = ("R1", "R2")


def build_stability_preregistration(
    *, corpus, prior_analysis, prior_closure
):
    validate_frontier_stability_holdout(corpus)
    if (
        prior_closure.get("candidate_state")
        != "FRONTIER_GRAY_HOLDOUT_REJECTED_STOP"
        or prior_closure.get("frontier_holdout_gate") != "REJECT"
        or prior_closure.get("core_integration_authorized") is not False
        or prior_analysis.get("source_run_hash") is None
        or prior_analysis.get("a1_cbit_gain_per_case") is None
        or prior_analysis.get("conditions", {}).get(
            "maximum_total_tokens"
        ) is not False
        or any(
            value is not True
            for key, value in prior_analysis.get("conditions", {}).items()
            if key != "maximum_total_tokens"
        )
    ):
        raise ValueError("frontier_stability_prior_invalid")
    prior_total = int(prior_analysis["total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "frozen_hypothesis": (
            "Ontology-first cognition produces higher net realized Cbit than "
            "direct problem generation across both independent order/context "
            "replications, even when it uses more tokens."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "primary_metric": "net_realized_cbit_gain_per_case",
        "cost_policy": {
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": prior_total * 2,
            "hard_runaway_total_tokens": math.ceil(prior_total * 3),
            "higher_cbit_higher_cost_can_pass": True,
        },
        "success_gate": {
            "minimum_provider_completion_per_cell": 0.95,
            "minimum_nonblock_projection_per_cell": 0.9,
            "minimum_gain_per_case_each_replication": 0.1,
            "minimum_pooled_case_win_rate": 0.6,
            "minimum_cross_replication_positive_consistency": 0.5,
            "maximum_pooled_severe_loss_rate": 0.2,
            "minimum_pooled_frontier_cbit_delta": 0.0,
            "hard_runaway_total_tokens": math.ceil(prior_total * 3),
        },
        "same_v0_27_cbit_weights_required": True,
        "fresh_labels_available_during_inference": False,
        "cross_provider_stability_claimed": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_stability_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_frontier_stability_holdout(corpus)
    _validate_preregistration(preregistration, corpus=corpus)
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (replication_id, arm_id, item)
        for replication_id in REPLICATION_IDS
        for arm_id in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, value[0], value[1], value[2]["case_id"]
    ]))
    calls, raw_receipts, projections, failures = [], {}, {}, []
    for replication_id, arm_id, canonical_item in matrix:
        item = _replication_surface(
            canonical_item, replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _task(
            item, replication_id, arm_id, refs, adapter
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id, arm_id, item["case_id"], task, envelope
        )
        calls.append(call)
        key = f"{replication_id}:{arm_id}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append({
                "replication_id": replication_id,
                "arm_id": arm_id,
                "case_id": item["case_id"],
                "stage": "PROVIDER_INVOCATION",
                "status": envelope.status,
                "invocation_receipt": envelope.invocation_receipt.as_dict(),
            })
        else:
            raw = envelope.normalized_result
            raw_receipts[key] = raw
            projections[key] = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id=arm_id,
                evidence_refs=refs,
            )
        _checkpoint(
            checkpoint_callback,
            corpus=corpus,
            preregistration=preregistration,
            calls=calls,
            raw_receipts=raw_receipts,
            projections=projections,
            failures=failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "replication_ids": list(REPLICATION_IDS),
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "projections": projections,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "replication_surfaces_are_order_only_transformations": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_stability_experiment(*, corpus, preregistration, run):
    validate_frontier_stability_holdout(corpus)
    _validate_preregistration(preregistration, corpus=corpus)
    _validate_run(run, corpus=corpus, preregistration=preregistration)
    ledgers = {}
    replication_metrics = {}
    case_deltas = {}
    all_deltas = []
    for replication_id in REPLICATION_IDS:
        subrun = _subrun(run, replication_id=replication_id)
        ledger = build_realized_cbit_ledger(
            corpus=corpus, run=subrun
        )
        ledgers[replication_id] = ledger
        by_case_arm = defaultdict(float)
        for entry in ledger["entries"]:
            by_case_arm[(entry["case_id"], entry["arm_id"])] += entry[
                "realized_effective_cbit"
            ]
        deltas = {
            case_id: round(
                by_case_arm[(case_id, "A1_ONTOLOGY")]
                - by_case_arm[(case_id, "A0_DIRECT")],
                6,
            )
            for case_id in sorted(
                item["case_id"]
                for item in corpus["public_surface"]["items"]
            )
        }
        case_deltas[replication_id] = deltas
        all_deltas.extend(deltas.values())
        runtime = _replication_runtime_metrics(
            run, replication_id=replication_id,
            expected=corpus["case_count"],
        )
        a0 = ledger["arm_metrics"]["A0_DIRECT"]
        a1 = ledger["arm_metrics"]["A1_ONTOLOGY"]
        frontier_delta = _frontier_mean(ledger, "A1_ONTOLOGY") - _frontier_mean(
            ledger, "A0_DIRECT"
        )
        replication_metrics[replication_id] = {
            "arm_runtime": runtime,
            "a0_cbit_per_case": a0["mean_effective_cbit_per_case"],
            "a1_cbit_per_case": a1["mean_effective_cbit_per_case"],
            "a1_gain_per_case": round(
                a1["mean_effective_cbit_per_case"]
                - a0["mean_effective_cbit_per_case"],
                6,
            ),
            "case_win_count": sum(value > 0 for value in deltas.values()),
            "case_tie_count": sum(value == 0 for value in deltas.values()),
            "case_loss_count": sum(value < 0 for value in deltas.values()),
            "severe_loss_count": sum(
                value < -1.0 for value in deltas.values()
            ),
            "a1_frontier_cbit_delta": round(frontier_delta, 6),
            "a0_total_tokens": a0["total_tokens"],
            "a1_total_tokens": a1["total_tokens"],
        }
    expected_pairs = corpus["case_count"] * len(REPLICATION_IDS)
    positive_consistency = sum(
        case_deltas["R1"][case_id] > 0
        and case_deltas["R2"][case_id] > 0
        for case_id in case_deltas["R1"]
    ) / corpus["case_count"]
    pooled_win_rate = sum(value > 0 for value in all_deltas) / expected_pairs
    severe_loss_rate = sum(
        value < -1.0 for value in all_deltas
    ) / expected_pairs
    total_tokens = sum(
        _call_tokens(value) for value in run["task_calls"]
    )
    a0_tokens = sum(
        value["a0_total_tokens"]
        for value in replication_metrics.values()
    )
    a1_tokens = sum(
        value["a1_total_tokens"]
        for value in replication_metrics.values()
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_provider_completion_per_cell": all(
            value["provider_completion_coverage"]
            >= gate["minimum_provider_completion_per_cell"]
            for replication in replication_metrics.values()
            for value in replication["arm_runtime"].values()
        ),
        "minimum_nonblock_projection_per_cell": all(
            value["nonblock_projection_coverage"]
            >= gate["minimum_nonblock_projection_per_cell"]
            for replication in replication_metrics.values()
            for value in replication["arm_runtime"].values()
        ),
        "minimum_gain_per_case_each_replication": all(
            value["a1_gain_per_case"]
            >= gate["minimum_gain_per_case_each_replication"]
            for value in replication_metrics.values()
        ),
        "minimum_pooled_case_win_rate": (
            pooled_win_rate >= gate["minimum_pooled_case_win_rate"]
        ),
        "minimum_cross_replication_positive_consistency": (
            positive_consistency
            >= gate["minimum_cross_replication_positive_consistency"]
        ),
        "maximum_pooled_severe_loss_rate": (
            severe_loss_rate <= gate["maximum_pooled_severe_loss_rate"]
        ),
        "minimum_pooled_frontier_cbit_delta": (
            sum(
                value["a1_frontier_cbit_delta"]
                for value in replication_metrics.values()
            ) / len(REPLICATION_IDS)
            >= gate["minimum_pooled_frontier_cbit_delta"]
        ),
        "hard_runaway_total_tokens": (
            total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "same_v0_27_cbit_weights": (
            len({
                hash_payload(value["weights"])
                for value in ledgers.values()
            }) == 1
            and all(
                value["lane_specific_score_weights_present"] is False
                for value in ledgers.values()
            )
        ),
        "authority_boundary_preserved": all(
            run.get(value) is False
            for value in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    if passed:
        decision = (
            "PASS_HIGHER_CBIT_HIGHER_COST"
            if a1_tokens > a0_tokens else "PASS_EFFICIENT_GAIN"
        )
        state = (
            "FRONTIER_STABILITY_PASSED_READY_EXTERNAL_PANEL"
        )
    elif total_tokens > gate["hard_runaway_total_tokens"]:
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "FRONTIER_STABILITY_RESOURCE_STOP"
    else:
        decision = "REJECT_NO_STABLE_CBIT_GAIN"
        state = "FRONTIER_STABILITY_REJECTED_STOP"
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "replication_metrics": replication_metrics,
        "case_deltas": case_deltas,
        "pooled_case_win_rate": round(pooled_win_rate, 6),
        "cross_replication_positive_consistency": round(
            positive_consistency, 6
        ),
        "pooled_severe_loss_rate": round(severe_loss_rate, 6),
        "pooled_frontier_cbit_delta": round(
            sum(
                value["a1_frontier_cbit_delta"]
                for value in replication_metrics.values()
            ) / len(REPLICATION_IDS),
            6,
        ),
        "a0_total_tokens": a0_tokens,
        "a1_total_tokens": a1_tokens,
        "total_tokens": total_tokens,
        "soft_expected_total_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "soft_cost_warning": (
            total_tokens
            > preregistration["cost_policy"]["soft_expected_total_tokens"]
        ),
        "conditions": conditions,
        "stability_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "cross_provider_stability_established": False,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _replication_surface(item, *, replication_id, corpus_hash):
    return {
        **item,
        "object_registry": sorted(
            item["object_registry"],
            key=lambda value: hash_payload([
                corpus_hash, replication_id, "OBJECT",
                value["object_id"],
            ]),
        ),
        "evidence_spans": sorted(
            item["evidence_spans"],
            key=lambda value: hash_payload([
                corpus_hash, replication_id, "SPAN",
                value["span_id"],
            ]),
        ),
    }


def _task(item, replication_id, arm_id, refs, adapter):
    if arm_id == "A0_DIRECT":
        method = (
            "Generate problem candidates directly. Do not construct or return "
            "an ontology."
        )
    else:
        method = (
            "First build a compact object census using only registered objects, "
            "then generate problem candidates while preserving constraints."
        )
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{arm_id}-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{method} Return two or three candidates. CORE and FRONTIER use "
            "the same quality standard. A weakly supported candidate must be "
            "marked SPECULATIVE, identify a structural origin, include a "
            "falsifier and required observation, and remain candidate-only."
        ),
        inputs={
            "stage": "STABILITY_GRAY_PROBLEM_ADMISSION",
            "replication_id": replication_id,
            "arm_id": arm_id,
            "public_case": item,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=native_schema(
            item=item, arm_id=arm_id, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _call(replication_id, arm_id, case_id, task, envelope):
    commitment = {
        "replication_id": replication_id,
        "arm_id": arm_id,
        "case_id": case_id,
        "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "schema_has_object_census": (
            "object_census" in task.expected_schema["properties"]
        ),
        "private_truth_exposed": False,
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _subrun(run, *, replication_id):
    calls = [
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
    ]
    projections = {
        key.split(":", 1)[1]: value
        for key, value in run["projections"].items()
        if key.startswith(replication_id + ":")
    }
    commitment = {
        "task_calls": calls,
        "projections": projections,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _replication_runtime_metrics(run, *, replication_id, expected):
    metrics = {}
    for arm_id in ARM_IDS:
        projections = [
            value for key, value in run["projections"].items()
            if key.startswith(f"{replication_id}:{arm_id}:")
        ]
        metrics[arm_id] = {
            "provider_completion_coverage": round(
                len(projections) / expected, 6
            ),
            "nonblock_projection_coverage": round(
                sum(
                    value["receipt_state"] != "BLOCK"
                    for value in projections
                ) / expected,
                6,
            ),
            "receipt_state_counts": dict(Counter(
                value["receipt_state"] for value in projections
            )),
        }
    return metrics


def _frontier_mean(ledger, arm_id):
    entries = [
        value for value in ledger["entries"]
        if value["arm_id"] == arm_id and value["lane"] == "FRONTIER"
    ]
    return (
        sum(value["realized_effective_cbit"] for value in entries)
        / len(entries)
        if entries else 0.0
    )


def _validate_preregistration(preregistration, *, corpus):
    commitment = {
        key: value for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if (
        preregistration.get("artifact_hash") != hash_payload(commitment)
        or preregistration.get("source_corpus_hash")
        != corpus["artifact_hash"]
    ):
        raise ValueError("frontier_stability_preregistration_invalid")


def _validate_run(run, *, corpus, preregistration):
    commitment = {
        key: value for key, value in run.items() if key != "run_hash"
    }
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
        or run.get("source_preregistration_hash")
        != preregistration["artifact_hash"]
    ):
        raise ValueError("frontier_stability_run_invalid")


def _checkpoint(
    callback, *, corpus, preregistration, calls, raw_receipts,
    projections, failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "frontier_stability_progress_v0_28",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "projections": dict(projections),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({
        **commitment,
        "artifact_hash": hash_payload(commitment),
    })


def _call_tokens(call):
    usage = call["invocation_receipt"].get("token_usage") or {}
    return int(
        usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    ) + int(
        usage.get("completion_tokens") or usage.get("output_tokens") or 0
    )
