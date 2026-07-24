"""Zero-marginal-token Runtime escalation experiment v0.33."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collaborative_stability_experiment import exact_three_schema
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .provider_telemetry import hash_payload
from .runtime_escalation_holdout import (
    REPLICATION_IDS,
    validate_runtime_escalation_holdout,
)
from .runtime_escalation_policy import (
    POLICY_VERSION,
    derive_escalation_receipt,
)
from .selective_role_routing_experiment import (
    _call_tokens,
    _combined_usage,
    _generation_task,
    _metrics,
    _relation_reproducibility,
    _replication_surface,
)


RUNTIME_VERSION = "runtime_escalation_experiment_v0_33"
ARM_IDS = ("A1_BASELINE", "A2_RUNTIME")


def build_runtime_escalation_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_runtime_escalation_holdout(corpus)
    if (
        prior_analysis.get("decision") != "REJECT_LAZY_METACOGNITION"
        or prior_analysis.get("candidate_state")
        != "LAZY_METACOGNITION_REJECTED_STOP"
        or prior_analysis.get("trigger_metrics", {}).get("trigger_count") != 0
        or prior_closure.get("candidate_state")
        != "LAZY_METACOGNITION_REJECTED_STOP"
        or prior_posthoc.get("status")
        != "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE"
        or prior_posthoc.get("gross_candidate_delta", {}).get("median")
        != 0
        or prior_posthoc.get(
            "incremental_token_penalty", {}
        ).get("mean_cbit_per_cell", 0) <= 0
    ):
        raise ValueError("runtime_escalation_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "frozen_hypothesis": (
            "A replayable Runtime policy can derive escalation opportunity "
            "from an otherwise standard ontology receipt, preserving exact "
            "first-call Provider payload identity and paying additional "
            "tokens only when one specialized worker is actually executed."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_RUNTIME_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_prompt_identity_coverage": 1.0,
            "minimum_trigger_receipt_coverage": 0.95,
            "minimum_trigger_execution_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_mean_gain": 0.15,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.55,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.05,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.65),
        },
        "cost_policy": {
            "first_call_provider_payload_identical_between_arms": True,
            "runtime_trigger_adds_provider_tokens": False,
            "specialized_calls_only_when_triggered": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 1.25),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.65),
        },
        "trigger_rate_is_acceptance_gate": False,
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_runtime_escalation_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_runtime_escalation_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    first_stage = [
        (replication_id, arm_id, item)
        for replication_id in REPLICATION_IDS
        for arm_id in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    first_stage.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION,
        "FIRST_STAGE",
        value[0],
        value[1],
        value[2]["case_id"],
    ]))
    calls = []
    raw_receipts = {}
    provisional_projections = {}
    final_projections = {}
    trigger_receipts = {}
    failures = []
    for replication_id, arm_id, canonical_item in first_stage:
        item = _replication_surface(
            canonical_item,
            replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _standard_task(
            item=item,
            replication_id=replication_id,
            experimental_arm_id=arm_id,
            refs=refs,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            arm_id=arm_id,
            case_id=item["case_id"],
            stage="STANDARD_ONTOLOGY",
            route_id="A1_ONTOLOGY",
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{replication_id}:{arm_id}:STANDARD_ONTOLOGY:"
            f"{item['case_id']}"
        )
        final_key = f"{replication_id}:{arm_id}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            projection = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            if arm_id == "A1_BASELINE":
                final_projections[final_key] = projection
            else:
                provisional_projections[final_key] = projection
                trigger = derive_escalation_receipt(
                    raw_receipt=raw,
                    item=item,
                )
                trigger_receipts[final_key] = trigger
                if not trigger["triggered"]:
                    final_projections[final_key] = projection
        _checkpoint(
            checkpoint_callback,
            corpus,
            preregistration,
            calls,
            raw_receipts,
            provisional_projections,
            final_projections,
            trigger_receipts,
            failures,
        )

    escalations = sorted(
        (
            key,
            trigger,
        )
        for key, trigger in trigger_receipts.items()
        if trigger["triggered"]
    )
    for key, trigger in escalations:
        replication_id, arm_id, case_id = key.split(":", 2)
        canonical_item = next(
            value for value in corpus["public_surface"]["items"]
            if value["case_id"] == case_id
        )
        item = _replication_surface(
            canonical_item,
            replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        route_id = trigger["route_id"]
        task = _generation_task(
            item=item,
            replication_id=replication_id,
            route_id=route_id,
            refs=refs,
            adapter=adapter,
            stage="RUNTIME_TRIGGERED_WORKER",
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id,
            arm_id=arm_id,
            case_id=case_id,
            stage="RUNTIME_TRIGGERED_WORKER",
            route_id=route_id,
            task=task,
            envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{replication_id}:{arm_id}:RUNTIME_TRIGGERED_WORKER:"
            f"{case_id}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            final_projections[key] = project_frontier_receipt(
                raw_receipt=raw,
                item=item,
                arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
        _checkpoint(
            checkpoint_callback,
            corpus,
            preregistration,
            calls,
            raw_receipts,
            provisional_projections,
            final_projections,
            trigger_receipts,
            failures,
        )

    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "provider_generated_trigger_text_used": False,
        "trigger_rate_changes_acceptance_gate": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_runtime_escalation_experiment(
    *, corpus, preregistration, run
):
    validate_runtime_escalation_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    _validate_run(run, corpus, preregistration)
    ledgers = {}
    case_deltas = {}
    replication_metrics = {}
    for replication_id in REPLICATION_IDS:
        scoring_run = _scoring_run(run, replication_id=replication_id)
        ledger = build_realized_cbit_ledger(
            corpus=corpus,
            run=scoring_run,
        )
        ledgers[replication_id] = ledger
        totals = defaultdict(float)
        for entry in ledger["entries"]:
            totals[(entry["case_id"], entry["arm_id"])] += entry[
                "realized_effective_cbit"
            ]
        deltas = {
            item["case_id"]: round(
                totals[(item["case_id"], "A2_RUNTIME")]
                - totals[(item["case_id"], "A1_BASELINE")],
                6,
            )
            for item in corpus["public_surface"]["items"]
        }
        case_deltas[replication_id] = deltas
        replication_metrics[replication_id] = {
            "arm_cbit_per_case": {
                arm_id: ledger["arm_metrics"][arm_id][
                    "mean_effective_cbit_per_case"
                ]
                for arm_id in ARM_IDS
            },
            "arm_tokens": {
                arm_id: ledger["arm_metrics"][arm_id]["total_tokens"]
                for arm_id in ARM_IDS
            },
            "contrast": _metrics(list(deltas.values())),
        }
    pooled = [
        value
        for replication in case_deltas.values()
        for value in replication.values()
    ]
    pooled_metrics = _metrics(pooled)
    majority_positive_case_rate = round(
        sum(
            sum(
                case_deltas[replication_id][case_id] > 0
                for replication_id in REPLICATION_IDS
            ) >= 2
            for case_id in case_deltas[REPLICATION_IDS[0]]
        )
        / corpus["case_count"],
        6,
    )
    positive_replications = sum(
        value["contrast"]["mean"] > 0
        for value in replication_metrics.values()
    )
    relation_reproducibility = {
        arm_id: _relation_reproducibility(
            {"formal_projections": run["final_projections"]},
            arm_id=arm_id,
            corpus=corpus,
        )
        for arm_id in ARM_IDS
    }
    runtime_metrics = _runtime_metrics(run, corpus)
    trigger_metrics = _trigger_metrics(run, case_deltas)
    physical_total_tokens = sum(
        _call_tokens(value) for value in run["task_calls"]
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_provider_completion_per_required_stage": all(
            value >= gate["minimum_provider_completion_per_required_stage"]
            for value in runtime_metrics[
                "provider_completion_per_required_stage"
            ].values()
        ),
        "minimum_prompt_identity_coverage": (
            runtime_metrics["prompt_identity_coverage"]
            >= gate["minimum_prompt_identity_coverage"]
        ),
        "minimum_trigger_receipt_coverage": (
            runtime_metrics["trigger_receipt_coverage"]
            >= gate["minimum_trigger_receipt_coverage"]
        ),
        "minimum_trigger_execution_coverage": (
            runtime_metrics["trigger_execution_coverage"]
            >= gate["minimum_trigger_execution_coverage"]
        ),
        "minimum_nonblock_coverage_per_arm": all(
            value >= gate["minimum_nonblock_coverage_per_arm"]
            for value in runtime_metrics[
                "final_nonblock_coverage_per_arm"
            ].values()
        ),
        "minimum_exact_three_coverage_per_arm": all(
            value >= gate["minimum_exact_three_coverage_per_arm"]
            for value in runtime_metrics[
                "final_exact_three_coverage_per_arm"
            ].values()
        ),
        "minimum_mean_gain": (
            pooled_metrics["mean"] >= gate["minimum_mean_gain"]
        ),
        "minimum_median_gain": (
            pooled_metrics["median"] >= gate["minimum_median_gain"]
        ),
        "minimum_win_rate": (
            pooled_metrics["win_rate"] >= gate["minimum_win_rate"]
        ),
        "minimum_positive_replications": (
            positive_replications >= gate["minimum_positive_replications"]
        ),
        "minimum_majority_positive_case_rate": (
            majority_positive_case_rate
            >= gate["minimum_majority_positive_case_rate"]
        ),
        "maximum_severe_loss_rate": (
            pooled_metrics["severe_loss_rate"]
            <= gate["maximum_severe_loss_rate"]
        ),
        "minimum_relation_jaccard_relative_to_baseline": (
            relation_reproducibility["A2_RUNTIME"][
                "mean_pairwise_relation_jaccard"
            ]
            - relation_reproducibility["A1_BASELINE"][
                "mean_pairwise_relation_jaccard"
            ]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "hard_runaway_total_tokens": (
            physical_total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "authority_boundary_preserved": all(
            run.get(key) is False
            for key in (
                "selection_authority",
                "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    decision = (
        "PASS_RUNTIME_ESCALATION"
        if passed
        else "REJECT_RUNTIME_ESCALATION"
    )
    state = (
        "RUNTIME_ESCALATION_PASSED_READY_EXTERNAL_PANEL"
        if passed
        else "RUNTIME_ESCALATION_REJECTED_STOP"
    )
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "case_deltas": case_deltas,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": pooled_metrics,
        "majority_positive_case_rate": majority_positive_case_rate,
        "positive_replication_count": positive_replications,
        "runtime_metrics": runtime_metrics,
        "trigger_metrics": trigger_metrics,
        "relation_reproducibility": relation_reproducibility,
        "physical_total_tokens": physical_total_tokens,
        "soft_cost_warning": (
            physical_total_tokens
            > preregistration["cost_policy"]["soft_expected_total_tokens"]
        ),
        "conditions": conditions,
        "runtime_escalation_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _standard_task(
    *, item, replication_id, experimental_arm_id, refs, adapter
):
    objective = (
        "Build a compact object census and return exactly three strongest "
        "evidence-bound, distinct, falsifiable problem candidates."
    )
    inputs = {
        "stage": "STANDARD_ONTOLOGY",
        "replication_id": replication_id,
        "arm_id": "A1_ONTOLOGY",
        "public_case": item,
        "private_outcome_available": False,
        "provider_output_state": "CANDIDATE_ONLY",
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-"
            f"{experimental_arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=objective,
        inputs=inputs,
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item,
            arm_id="A1_ONTOLOGY",
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _provider_prompt_hash(task):
    return hash_payload({
        "objective": task.objective,
        "expected_schema": task.expected_schema,
        "inputs": task.inputs,
        "allowed_evidence": task.allowed_evidence,
    })


def _scoring_run(run, *, replication_id):
    task_calls = []
    projections = {}
    case_ids = sorted({
        value["case_id"]
        for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "STANDARD_ONTOLOGY"
    })
    for case_id in case_ids:
        baseline = _find_call(
            run,
            replication_id=replication_id,
            arm_id="A1_BASELINE",
            case_id=case_id,
            stage="STANDARD_ONTOLOGY",
        )
        runtime_base = _find_call(
            run,
            replication_id=replication_id,
            arm_id="A2_RUNTIME",
            case_id=case_id,
            stage="STANDARD_ONTOLOGY",
        )
        worker = _find_call(
            run,
            replication_id=replication_id,
            arm_id="A2_RUNTIME",
            case_id=case_id,
            stage="RUNTIME_TRIGGERED_WORKER",
        )
        if baseline is not None:
            task_calls.append({
                "arm_id": "A1_BASELINE",
                "case_id": case_id,
                "invocation_receipt": baseline["invocation_receipt"],
            })
        path_calls = [
            value for value in (runtime_base, worker)
            if value is not None
        ]
        if path_calls:
            task_calls.append({
                "arm_id": "A2_RUNTIME",
                "case_id": case_id,
                "invocation_receipt": {
                    "token_usage": _combined_usage(path_calls),
                    "derived_cost_receipt": True,
                    "source_call_hashes": [
                        value["call_hash"] for value in path_calls
                    ],
                },
            })
        for arm_id in ARM_IDS:
            source = f"{replication_id}:{arm_id}:{case_id}"
            if source in run["final_projections"]:
                projections[f"{arm_id}:{case_id}"] = run[
                    "final_projections"
                ][source]
    commitment = {
        "task_calls": task_calls,
        "projections": projections,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _runtime_metrics(run, corpus):
    expected = corpus["case_count"] * len(REPLICATION_IDS)
    standard_calls = [
        value for value in run["task_calls"]
        if value["stage"] == "STANDARD_ONTOLOGY"
    ]
    completion = {
        arm_id: round(
            sum(
                value["status"] == "COMPLETED"
                for value in standard_calls
                if value["arm_id"] == arm_id
            )
            / expected,
            6,
        )
        for arm_id in ARM_IDS
    }
    triggered_keys = {
        key for key, value in run["trigger_receipts"].items()
        if value["triggered"]
    }
    workers = [
        value for value in run["task_calls"]
        if value["stage"] == "RUNTIME_TRIGGERED_WORKER"
    ]
    if triggered_keys:
        completion["RUNTIME_TRIGGERED_WORKER"] = round(
            sum(value["status"] == "COMPLETED" for value in workers)
            / len(triggered_keys),
            6,
        )
        execution_coverage = round(
            sum(key in run["final_projections"] for key in triggered_keys)
            / len(triggered_keys),
            6,
        )
    else:
        execution_coverage = 1.0
    identity_matches = 0
    for replication_id in REPLICATION_IDS:
        for item in corpus["public_surface"]["items"]:
            left = _find_call(
                run,
                replication_id=replication_id,
                arm_id="A1_BASELINE",
                case_id=item["case_id"],
                stage="STANDARD_ONTOLOGY",
            )
            right = _find_call(
                run,
                replication_id=replication_id,
                arm_id="A2_RUNTIME",
                case_id=item["case_id"],
                stage="STANDARD_ONTOLOGY",
            )
            identity_matches += bool(
                left
                and right
                and left["provider_prompt_hash"]
                == right["provider_prompt_hash"]
            )
    nonblock = {}
    exact = {}
    for arm_id in ARM_IDS:
        values = [
            value
            for key, value in run["final_projections"].items()
            if f":{arm_id}:" in key
        ]
        nonblock[arm_id] = round(
            sum(value["receipt_state"] != "BLOCK" for value in values)
            / expected,
            6,
        )
        exact[arm_id] = round(
            sum(len(value["eligible_candidate_ids"]) == 3 for value in values)
            / expected,
            6,
        )
    return {
        "provider_completion_per_required_stage": completion,
        "prompt_identity_coverage": round(
            identity_matches / expected,
            6,
        ),
        "trigger_receipt_coverage": round(
            len(run["trigger_receipts"]) / expected,
            6,
        ),
        "trigger_execution_coverage": execution_coverage,
        "final_nonblock_coverage_per_arm": nonblock,
        "final_exact_three_coverage_per_arm": exact,
        "failure_count": len(run["failures"]),
    }


def _trigger_metrics(run, case_deltas):
    routes = Counter()
    flags = Counter()
    triggered_deltas = []
    untriggered_deltas = []
    coverage = []
    for key, trigger in run["trigger_receipts"].items():
        replication_id, _arm_id, case_id = key.split(":", 2)
        routes[trigger["route_id"]] += 1
        for flag in trigger["diagnostic_flags"]:
            flags[flag] += 1
        coverage.append(trigger["metrics"]["evidence_span_coverage"])
        target = (
            triggered_deltas
            if trigger["triggered"]
            else untriggered_deltas
        )
        target.append(case_deltas[replication_id][case_id])
    total = len(run["trigger_receipts"])
    triggered_count = len(triggered_deltas)
    return {
        "trigger_count": triggered_count,
        "trigger_rate": round(
            triggered_count / total if total else 0.0,
            6,
        ),
        "route_distribution": dict(routes),
        "diagnostic_flag_distribution": dict(flags),
        "mean_first_receipt_evidence_coverage": round(
            sum(coverage) / len(coverage) if coverage else 0.0,
            6,
        ),
        "triggered_contrast": (
            _metrics(triggered_deltas) if triggered_deltas else None
        ),
        "untriggered_contrast": (
            _metrics(untriggered_deltas) if untriggered_deltas else None
        ),
        "triggered_win_precision": round(
            sum(value > 0 for value in triggered_deltas)
            / triggered_count
            if triggered_count
            else 0.0,
            6,
        ),
    }


def _call(
    *,
    replication_id,
    arm_id,
    case_id,
    stage,
    route_id,
    task,
    envelope,
):
    commitment = {
        "replication_id": replication_id,
        "arm_id": arm_id,
        "case_id": case_id,
        "stage": stage,
        "route_id": route_id,
        "status": envelope.status,
        "task_contract_hash": task.contract_hash(),
        "provider_prompt_hash": _provider_prompt_hash(task),
        "private_truth_exposed": False,
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _provider_failure(call):
    return {
        "replication_id": call["replication_id"],
        "arm_id": call["arm_id"],
        "case_id": call["case_id"],
        "stage": call["stage"],
        "route_id": call["route_id"],
        "status": call["status"],
        "invocation_receipt": call["invocation_receipt"],
    }


def _find_call(
    run, *, replication_id, arm_id, case_id, stage
):
    return next(
        (
            value for value in run["task_calls"]
            if value["replication_id"] == replication_id
            and value["arm_id"] == arm_id
            and value["case_id"] == case_id
            and value["stage"] == stage
        ),
        None,
    )


def _validate_preregistration(preregistration, corpus):
    commitment = {
        key: value
        for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if (
        preregistration.get("artifact_hash") != hash_payload(commitment)
        or preregistration.get("source_corpus_hash")
        != corpus["artifact_hash"]
    ):
        raise ValueError("runtime_escalation_preregistration_invalid")


def _validate_run(run, corpus, preregistration):
    commitment = {
        key: value for key, value in run.items() if key != "run_hash"
    }
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("source_corpus_hash") != corpus["artifact_hash"]
        or run.get("source_preregistration_hash")
        != preregistration["artifact_hash"]
    ):
        raise ValueError("runtime_escalation_run_invalid")


def _checkpoint(
    callback,
    corpus,
    preregistration,
    calls,
    raw_receipts,
    provisional_projections,
    final_projections,
    trigger_receipts,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "runtime_escalation_progress_v0_33",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({
        **commitment,
        "artifact_hash": hash_payload(commitment),
    })
