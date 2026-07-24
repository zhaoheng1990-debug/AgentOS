"""Lineage-aware role revision experiment v0.34."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .collaborative_stability_experiment import exact_three_schema
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .lineage_revision_contracts import (
    lineage_failures,
    lineage_revision_schema,
)
from .lineage_revision_holdout import (
    REPLICATION_IDS,
    validate_lineage_revision_holdout,
)
from .provider_telemetry import hash_payload
from .runtime_escalation_policy import (
    POLICY_VERSION,
    derive_escalation_receipt,
)
from .selective_role_routing_experiment import (
    _call_tokens,
    _combined_usage,
    _metrics,
    _relation_reproducibility,
    _replication_surface,
)


RUNTIME_VERSION = "lineage_revision_experiment_v0_34"
ARM_IDS = ("A1_BASELINE", "A2_REVISION")


def build_lineage_revision_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_lineage_revision_holdout(corpus)
    gross = prior_posthoc.get(
        "triggered_worker_gross_candidate_uplift", {}
    )
    net = prior_posthoc.get("triggered_worker_net_uplift", {})
    if (
        prior_analysis.get("decision") != "REJECT_RUNTIME_ESCALATION"
        or prior_analysis.get("candidate_state")
        != "RUNTIME_ESCALATION_REJECTED_STOP"
        or prior_analysis.get("runtime_metrics", {}).get(
            "prompt_identity_coverage"
        ) != 1
        or prior_closure.get("candidate_state")
        != "RUNTIME_ESCALATION_REJECTED_STOP"
        or prior_posthoc.get("status")
        != "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE"
        or gross.get("mean", 0) <= 0
        or net.get("median", 0) >= 0
    ):
        raise ValueError("lineage_revision_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "frozen_hypothesis": (
            "A triggered specialist that can inspect the provisional "
            "candidates and must declare KEEP, REVISE, or REPLACE lineage can "
            "retain prior Cbit while repairing structural defects more "
            "reliably than blind whole-receipt replacement."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_REVISION_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_prompt_identity_coverage": 1.0,
            "minimum_trigger_receipt_coverage": 0.95,
            "minimum_trigger_execution_coverage": 0.9,
            "minimum_lineage_contract_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_mean_gain": 0.15,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.55,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.05,
            "minimum_triggered_revision_gross_median": 0.25,
            "minimum_triggered_revision_gross_win_rate": 0.55,
            "maximum_triggered_revision_gross_loss_rate": 0.25,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.65),
        },
        "cost_policy": {
            "first_call_provider_payload_identical_between_arms": True,
            "runtime_trigger_adds_provider_tokens": False,
            "one_revision_worker_only_when_triggered": True,
            "no_separate_selector_call": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 1.25),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.65),
        },
        "trigger_policy_retuned_from_v0_33": False,
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False, "retention_write_allowed": False,
        "baseline_write_allowed": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_lineage_revision_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_lineage_revision_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (replication_id, arm_id, item)
        for replication_id in REPLICATION_IDS
        for arm_id in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "STANDARD", value[0], value[1],
        value[2]["case_id"],
    ]))
    calls, raw_receipts = [], {}
    provisional_projections, final_projections = {}, {}
    trigger_receipts, revision_receipts, failures = {}, {}, []
    for replication_id, arm_id, canonical_item in matrix:
        item = _replication_surface(
            canonical_item, replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _standard_task(
            item=item, replication_id=replication_id,
            experimental_arm_id=arm_id, refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id, arm_id=arm_id,
            case_id=item["case_id"], stage="STANDARD_ONTOLOGY",
            route_id="A1_ONTOLOGY", task=task, envelope=envelope,
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
                raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            if arm_id == "A1_BASELINE":
                final_projections[final_key] = projection
            else:
                provisional_projections[final_key] = projection
                trigger = derive_escalation_receipt(
                    raw_receipt=raw, item=item,
                )
                trigger_receipts[final_key] = trigger
                if not trigger["triggered"]:
                    final_projections[final_key] = projection
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, revision_receipts, failures,
        )

    for key, trigger in sorted(trigger_receipts.items()):
        if not trigger["triggered"]:
            continue
        replication_id, arm_id, case_id = key.split(":", 2)
        canonical_item = next(
            value for value in corpus["public_surface"]["items"]
            if value["case_id"] == case_id
        )
        item = _replication_surface(
            canonical_item, replication_id=replication_id,
            corpus_hash=corpus["artifact_hash"],
        )
        provisional_key = (
            f"{replication_id}:{arm_id}:STANDARD_ONTOLOGY:{case_id}"
        )
        provisional = raw_receipts[provisional_key]
        task = _revision_task(
            item=item, replication_id=replication_id,
            trigger=trigger, provisional=provisional, refs=refs,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=replication_id, arm_id=arm_id,
            case_id=case_id, stage="LINEAGE_REVISION_WORKER",
            route_id=trigger["route_id"], task=task, envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{replication_id}:{arm_id}:LINEAGE_REVISION_WORKER:"
            f"{case_id}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            contract_failures = lineage_failures(
                final_receipt=raw, provisional_receipt=provisional,
                trigger=trigger, item=item,
            )
            if contract_failures:
                failures.append({
                    "replication_id": replication_id, "arm_id": arm_id,
                    "case_id": case_id, "stage": "LINEAGE_CONTRACT",
                    "failures": contract_failures,
                    "raw_receipt_hash": hash_payload(raw),
                })
            else:
                revision_receipts[key] = {
                    "worker_route_id": raw["worker_route_id"],
                    "revision_actions": raw["revision_actions"],
                    "revision_summary": raw["revision_summary"],
                    "raw_receipt_hash": hash_payload(raw),
                }
                final_projections[key] = project_frontier_receipt(
                    raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                    evidence_refs=refs,
                )
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, revision_receipts, failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id, "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "revision_receipts": revision_receipts, "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "provider_generated_trigger_text_used": False,
        "trigger_policy_retuned_from_v0_33": False,
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_lineage_revision_experiment(
    *, corpus, preregistration, run
):
    validate_lineage_revision_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    _validate_run(run, corpus, preregistration)
    ledgers, case_deltas, replication_metrics = {}, {}, {}
    for replication_id in REPLICATION_IDS:
        ledger = build_realized_cbit_ledger(
            corpus=corpus,
            run=_scoring_run(run, replication_id=replication_id),
        )
        ledgers[replication_id] = ledger
        totals = _case_totals(ledger)
        deltas = {
            item["case_id"]: round(
                totals[(item["case_id"], "A2_REVISION")]["net"]
                - totals[(item["case_id"], "A1_BASELINE")]["net"], 6
            )
            for item in corpus["public_surface"]["items"]
        }
        case_deltas[replication_id] = deltas
        replication_metrics[replication_id] = {
            "arm_cbit_per_case": {
                arm: ledger["arm_metrics"][arm][
                    "mean_effective_cbit_per_case"
                ] for arm in ARM_IDS
            },
            "arm_tokens": {
                arm: ledger["arm_metrics"][arm]["total_tokens"]
                for arm in ARM_IDS
            },
            "contrast": _metrics(list(deltas.values())),
        }
    pooled = [
        value for replication in case_deltas.values()
        for value in replication.values()
    ]
    pooled_metrics = _metrics(pooled)
    majority = round(sum(
        sum(case_deltas[rep][case] > 0 for rep in REPLICATION_IDS) >= 2
        for case in case_deltas[REPLICATION_IDS[0]]
    ) / corpus["case_count"], 6)
    positive_reps = sum(
        value["contrast"]["mean"] > 0
        for value in replication_metrics.values()
    )
    runtime = _runtime_metrics(run, corpus)
    revision = _revision_metrics(corpus, run, ledgers)
    relation = {
        arm: _relation_reproducibility(
            {"formal_projections": run["final_projections"]},
            arm_id=arm, corpus=corpus,
        ) for arm in ARM_IDS
    }
    total_tokens = sum(_call_tokens(value) for value in run["task_calls"])
    gate = preregistration["success_gate"]
    gross = revision["triggered_gross_candidate_uplift"]
    conditions = {
        "minimum_provider_completion_per_required_stage": all(
            value >= gate["minimum_provider_completion_per_required_stage"]
            for value in runtime[
                "provider_completion_per_required_stage"
            ].values()
        ),
        "minimum_prompt_identity_coverage": (
            runtime["prompt_identity_coverage"]
            >= gate["minimum_prompt_identity_coverage"]
        ),
        "minimum_trigger_receipt_coverage": (
            runtime["trigger_receipt_coverage"]
            >= gate["minimum_trigger_receipt_coverage"]
        ),
        "minimum_trigger_execution_coverage": (
            runtime["trigger_execution_coverage"]
            >= gate["minimum_trigger_execution_coverage"]
        ),
        "minimum_lineage_contract_coverage": (
            runtime["lineage_contract_coverage"]
            >= gate["minimum_lineage_contract_coverage"]
        ),
        "minimum_nonblock_coverage_per_arm": all(
            value >= gate["minimum_nonblock_coverage_per_arm"]
            for value in runtime["final_nonblock_coverage_per_arm"].values()
        ),
        "minimum_exact_three_coverage_per_arm": all(
            value >= gate["minimum_exact_three_coverage_per_arm"]
            for value in runtime[
                "final_exact_three_coverage_per_arm"
            ].values()
        ),
        "minimum_mean_gain": pooled_metrics["mean"]
        >= gate["minimum_mean_gain"],
        "minimum_median_gain": pooled_metrics["median"]
        >= gate["minimum_median_gain"],
        "minimum_win_rate": pooled_metrics["win_rate"]
        >= gate["minimum_win_rate"],
        "minimum_positive_replications": positive_reps
        >= gate["minimum_positive_replications"],
        "minimum_majority_positive_case_rate": majority
        >= gate["minimum_majority_positive_case_rate"],
        "maximum_severe_loss_rate": pooled_metrics["severe_loss_rate"]
        <= gate["maximum_severe_loss_rate"],
        "minimum_relation_jaccard_relative_to_baseline": (
            relation["A2_REVISION"]["mean_pairwise_relation_jaccard"]
            - relation["A1_BASELINE"]["mean_pairwise_relation_jaccard"]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "minimum_triggered_revision_gross_median": (
            gross is not None and gross["median"]
            >= gate["minimum_triggered_revision_gross_median"]
        ),
        "minimum_triggered_revision_gross_win_rate": (
            gross is not None and gross["win_rate"]
            >= gate["minimum_triggered_revision_gross_win_rate"]
        ),
        "maximum_triggered_revision_gross_loss_rate": (
            gross is not None and gross["loss_count"] / gross["count"]
            <= gate["maximum_triggered_revision_gross_loss_rate"]
        ),
        "hard_runaway_total_tokens": total_tokens
        <= gate["hard_runaway_total_tokens"],
        "authority_boundary_preserved": all(
            run.get(key) is False for key in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    decision = (
        "PASS_LINEAGE_REVISION" if passed else "REJECT_LINEAGE_REVISION"
    )
    state = (
        "LINEAGE_REVISION_PASSED_READY_EXTERNAL_PANEL"
        if passed else "LINEAGE_REVISION_REJECTED_STOP"
    )
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers, "case_deltas": case_deltas,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": pooled_metrics,
        "majority_positive_case_rate": majority,
        "positive_replication_count": positive_reps,
        "runtime_metrics": runtime, "revision_metrics": revision,
        "relation_reproducibility": relation,
        "physical_total_tokens": total_tokens,
        "soft_cost_warning": total_tokens > preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "conditions": conditions,
        "lineage_revision_gate": "PASS" if passed else "REJECT",
        "decision": decision, "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False, "candidate_state": state,
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _standard_task(
    *, item, replication_id, experimental_arm_id, refs, adapter
):
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-"
            f"{experimental_arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Build a compact object census and return exactly three strongest "
            "evidence-bound, distinct, falsifiable problem candidates."
        ),
        inputs={
            "stage": "STANDARD_ONTOLOGY",
            "replication_id": replication_id,
            "arm_id": "A1_ONTOLOGY", "public_case": item,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _revision_task(
    *, item, replication_id, trigger, provisional, refs, adapter
):
    route_prompts = {
        "MECHANISM": (
            "Repair mechanism coverage while preserving sound candidates."
        ),
        "ADVERSARIAL": (
            "Use counterevidence and discriminating tests to repair only "
            "weak candidates."
        ),
        "COORDINATE_SHIFT": (
            "Repair collapsed object coordinates while preserving sound "
            "relations."
        ),
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-REVISION-"
            f"{trigger['route_id']}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{route_prompts[trigger['route_id']]} Inspect the supplied "
            "provisional receipt. For each candidate slot choose KEEP, "
            "REVISE, or REPLACE. KEEP must copy the candidate exactly; "
            "REVISE must preserve its object relation; REPLACE must change "
            "that relation. Prefer KEEP when a change lacks clear expected "
            "Cbit. Return exactly three final candidates and complete lineage."
        ),
        inputs={
            "stage": "LINEAGE_AWARE_REVISION",
            "replication_id": replication_id,
            "worker_route_id": trigger["route_id"],
            "runtime_diagnostic": trigger,
            "provisional_receipt": provisional,
            "public_case": item, "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=lineage_revision_schema(
            item=item, refs=refs, provisional_receipt=provisional,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _provider_prompt_hash(task):
    return hash_payload({
        "objective": task.objective, "expected_schema": task.expected_schema,
        "inputs": task.inputs, "allowed_evidence": task.allowed_evidence,
    })


def _scoring_run(run, *, replication_id, provisional=False):
    calls, projections = [], {}
    case_ids = sorted({
        value["case_id"] for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "STANDARD_ONTOLOGY"
    })
    for case_id in case_ids:
        for arm in ARM_IDS:
            base = _find_call(
                run, replication_id=replication_id, arm_id=arm,
                case_id=case_id, stage="STANDARD_ONTOLOGY",
            )
            path = [base]
            if arm == "A2_REVISION" and not provisional:
                worker = _find_call(
                    run, replication_id=replication_id, arm_id=arm,
                    case_id=case_id, stage="LINEAGE_REVISION_WORKER",
                )
                if worker is not None:
                    path.append(worker)
            calls.append({
                "arm_id": arm, "case_id": case_id,
                "invocation_receipt": {
                    "token_usage": _combined_usage(path),
                    "derived_cost_receipt": True,
                    "source_call_hashes": [value["call_hash"] for value in path],
                },
            })
            source = f"{replication_id}:{arm}:{case_id}"
            if arm == "A2_REVISION" and provisional:
                projection = run["provisional_projections"].get(source)
            else:
                projection = run["final_projections"].get(source)
            if projection is not None:
                projections[f"{arm}:{case_id}"] = projection
    commitment = {"task_calls": calls, "projections": projections}
    return {**commitment, "run_hash": hash_payload(commitment)}


def _runtime_metrics(run, corpus):
    expected = corpus["case_count"] * len(REPLICATION_IDS)
    completion = {}
    for arm in ARM_IDS:
        values = [
            value for value in run["task_calls"]
            if value["stage"] == "STANDARD_ONTOLOGY"
            and value["arm_id"] == arm
        ]
        completion[arm] = round(
            sum(value["status"] == "COMPLETED" for value in values)
            / expected, 6
        )
    triggered = {
        key for key, value in run["trigger_receipts"].items()
        if value["triggered"]
    }
    workers = [
        value for value in run["task_calls"]
        if value["stage"] == "LINEAGE_REVISION_WORKER"
    ]
    if triggered:
        completion["LINEAGE_REVISION_WORKER"] = round(
            sum(value["status"] == "COMPLETED" for value in workers)
            / len(triggered), 6
        )
        execution = round(
            sum(key in run["final_projections"] for key in triggered)
            / len(triggered), 6
        )
        lineage = round(
            len(run["revision_receipts"]) / len(triggered), 6
        )
    else:
        execution, lineage = 1.0, 0.0
    identity = 0
    for rep in REPLICATION_IDS:
        for item in corpus["public_surface"]["items"]:
            left = _find_call(
                run, replication_id=rep, arm_id="A1_BASELINE",
                case_id=item["case_id"], stage="STANDARD_ONTOLOGY",
            )
            right = _find_call(
                run, replication_id=rep, arm_id="A2_REVISION",
                case_id=item["case_id"], stage="STANDARD_ONTOLOGY",
            )
            identity += bool(
                left and right and left["provider_prompt_hash"]
                == right["provider_prompt_hash"]
            )
    nonblock, exact = {}, {}
    for arm in ARM_IDS:
        values = [
            value for key, value in run["final_projections"].items()
            if f":{arm}:" in key
        ]
        nonblock[arm] = round(
            sum(value["receipt_state"] != "BLOCK" for value in values)
            / expected, 6
        )
        exact[arm] = round(
            sum(len(value["eligible_candidate_ids"]) == 3 for value in values)
            / expected, 6
        )
    return {
        "provider_completion_per_required_stage": completion,
        "prompt_identity_coverage": round(identity / expected, 6),
        "trigger_receipt_coverage": round(
            len(run["trigger_receipts"]) / expected, 6
        ),
        "trigger_execution_coverage": execution,
        "lineage_contract_coverage": lineage,
        "final_nonblock_coverage_per_arm": nonblock,
        "final_exact_three_coverage_per_arm": exact,
        "failure_count": len(run["failures"]),
    }


def _revision_metrics(corpus, run, formal_ledgers):
    gross_uplifts, net_uplifts, token_penalties = [], [], []
    actions, routes, flags = Counter(), Counter(), Counter()
    for rep in REPLICATION_IDS:
        provisional = build_realized_cbit_ledger(
            corpus=corpus,
            run=_scoring_run(run, replication_id=rep, provisional=True),
        )
        before = _case_totals(provisional)
        after = _case_totals(formal_ledgers[rep])
        for item in corpus["public_surface"]["items"]:
            case = item["case_id"]
            key = f"{rep}:A2_REVISION:{case}"
            trigger = run["trigger_receipts"].get(key)
            if trigger is None:
                continue
            routes[trigger["route_id"]] += 1
            for flag in trigger["diagnostic_flags"]:
                flags[flag] += 1
            if not trigger["triggered"] or key not in run[
                "revision_receipts"
            ]:
                continue
            gross_uplifts.append(
                after[(case, "A2_REVISION")]["gross"]
                - before[(case, "A2_REVISION")]["gross"]
            )
            net_uplifts.append(
                after[(case, "A2_REVISION")]["net"]
                - before[(case, "A2_REVISION")]["net"]
            )
            token_penalties.append(
                after[(case, "A2_REVISION")]["token_cost"]
                - before[(case, "A2_REVISION")]["token_cost"]
            )
            for action in run["revision_receipts"][key][
                "revision_actions"
            ]:
                actions[action["action"]] += 1
    triggered = sum(value["triggered"] for value in run[
        "trigger_receipts"
    ].values())
    return {
        "trigger_count": triggered,
        "trigger_rate": round(
            triggered / len(run["trigger_receipts"]), 6
        ),
        "route_distribution": dict(routes),
        "diagnostic_flag_distribution": dict(flags),
        "revision_action_distribution": dict(actions),
        "keep_action_rate": round(
            actions["KEEP"] / sum(actions.values())
            if actions else 0.0, 6
        ),
        "triggered_gross_candidate_uplift": (
            _metrics(gross_uplifts) if gross_uplifts else None
        ),
        "triggered_net_uplift": (
            _metrics(net_uplifts) if net_uplifts else None
        ),
        "mean_worker_token_penalty": round(
            sum(token_penalties) / len(token_penalties)
            if token_penalties else 0.0, 6
        ),
    }


def _case_totals(ledger):
    totals = defaultdict(lambda: {
        "net": 0.0, "gross": 0.0, "token_cost": 0.0,
    })
    for entry in ledger["entries"]:
        key = (entry["case_id"], entry["arm_id"])
        totals[key]["net"] += entry["realized_effective_cbit"]
        totals[key]["token_cost"] += entry["token_cost"]
        totals[key]["gross"] += (
            entry["realized_effective_cbit"] + entry["token_cost"]
        )
    return totals


def _call(
    *, replication_id, arm_id, case_id, stage, route_id, task, envelope
):
    commitment = {
        "replication_id": replication_id, "arm_id": arm_id,
        "case_id": case_id, "stage": stage, "route_id": route_id,
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
        "arm_id": call["arm_id"], "case_id": call["case_id"],
        "stage": call["stage"], "route_id": call["route_id"],
        "status": call["status"],
        "invocation_receipt": call["invocation_receipt"],
    }


def _find_call(run, *, replication_id, arm_id, case_id, stage):
    return next((
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["arm_id"] == arm_id and value["case_id"] == case_id
        and value["stage"] == stage
    ), None)


def _validate_preregistration(preregistration, corpus):
    commitment = {
        key: value for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if (
        preregistration.get("artifact_hash") != hash_payload(commitment)
        or preregistration.get("source_corpus_hash")
        != corpus["artifact_hash"]
    ):
        raise ValueError("lineage_revision_preregistration_invalid")


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
        raise ValueError("lineage_revision_run_invalid")


def _checkpoint(
    callback, corpus, preregistration, calls, raw_receipts,
    provisional_projections, final_projections, trigger_receipts,
    revision_receipts, failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "lineage_revision_progress_v0_34",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls), "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "revision_receipts": dict(revision_receipts),
        "failures": list(failures),
        "original_receipts_preserved": True, "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})
