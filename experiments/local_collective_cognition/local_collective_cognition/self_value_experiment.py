"""Embedded self-value and no-third-call composition experiment v0.38."""

from __future__ import annotations

import math
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .candidate_pool_arbitration import build_candidate_pool
from .candidate_value_composition import SCORE_MAP
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .independent_arbitration_experiment import (
    _case_totals,
    _find_call,
    _relation_reproducibility,
    _replication_surface,
)
from .lineage_revision_experiment import _call, _provider_failure
from .provider_telemetry import hash_payload
from .runtime_escalation_policy import (
    POLICY_VERSION,
    derive_escalation_receipt,
)
from .selective_role_routing_experiment import (
    _call_tokens,
    _combined_usage,
    _metrics,
)
from .self_value_holdout import (
    REPLICATION_IDS,
    validate_self_value_holdout,
)
from .self_valued_candidate_composition import (
    CONTRACT_VERSION,
    SOURCE_RANK_BONUS,
    compose_self_valued_pool,
    self_valued_exact_three_schema,
    validate_self_valued_receipt,
)


RUNTIME_VERSION = "self_value_experiment_v0_38"
ARM_IDS = ("A1_BASELINE", "A2_SELF_COMPOSED")


def build_self_value_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_self_value_holdout(corpus)
    gross = prior_analysis.get("composition_metrics", {}).get(
        "triggered_composition_gross_uplift", {}
    )
    if (
        prior_analysis.get("decision")
        != "REJECT_CANDIDATE_VALUE_COMPOSITION"
        or prior_analysis.get("candidate_state")
        != "CANDIDATE_VALUE_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "CANDIDATE_VALUE_REJECTED_STOP"
        or prior_posthoc.get("formal_decision_unchanged") is not True
        or gross.get("mean", 0) <= 0
        or gross.get("loss_count") != 0
        or prior_posthoc.get(
            "mean_fraction_of_positive_oracle_uplift_captured", 0
        ) < 0.5
    ):
        raise ValueError("self_value_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_self_value_contract_version": CONTRACT_VERSION,
        "source_score_map_hash": hash_payload(SCORE_MAP),
        "source_rank_bonus": list(SOURCE_RANK_BONUS),
        "frozen_hypothesis": (
            "Embedding the same factorized value receipt in standard and "
            "counterproposal generation can preserve useful candidate "
            "ranking after source-local calibration while eliminating the "
            "third Provider call that dominated v0.37 net cost."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_SELF_COMPOSED_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_prompt_identity_coverage": 1.0,
            "minimum_standard_self_value_contract_coverage": 0.95,
            "minimum_counter_self_value_contract_coverage": 0.9,
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
            "minimum_triggered_composition_gross_median": 0.25,
            "minimum_triggered_composition_gross_win_rate": 0.55,
            "maximum_triggered_composition_gross_loss_rate": 0.25,
            "maximum_mean_added_token_penalty_cbit": 1.0,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.4),
        },
        "cost_policy": {
            "first_call_provider_payload_identical_between_arms": True,
            "standard_self_value_cost_symmetric_between_arms": True,
            "runtime_trigger_adds_provider_tokens": False,
            "one_counterproposal_only_when_triggered": True,
            "separate_value_provider_call_allowed": False,
            "runtime_composition_adds_provider_tokens": False,
            "all_counterproposal_tokens_charged": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 1.1),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.4),
        },
        "trigger_policy_retuned_from_v0_33": False,
        "score_map_retuned_from_v0_37": False,
        "provider_sees_numeric_score_map": False,
        "provider_selects_final_candidates": False,
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_self_value_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_self_value_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (rep, arm, item)
        for rep in REPLICATION_IDS
        for arm in ARM_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "STANDARD", value[0], value[1],
        value[2]["case_id"],
    ]))
    calls, raw_receipts, failures = [], {}, []
    provisional_projections, final_projections = {}, {}
    trigger_receipts, candidate_pools, composition_receipts = {}, {}, {}
    standard_valid, counter_valid = [], []
    for rep, arm, canonical in matrix:
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _self_value_task(
            item=item, replication_id=rep,
            experimental_arm_id=arm, route_id="A1_ONTOLOGY",
            stage="STANDARD_SELF_VALUE", refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=arm, case_id=item["case_id"],
            stage="STANDARD_SELF_VALUE", route_id="A1_ONTOLOGY",
            task=task, envelope=envelope,
        )
        calls.append(call)
        key = f"{rep}:{arm}:{item['case_id']}"
        raw_key = f"{rep}:{arm}:STANDARD_SELF_VALUE:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            contract_failures = validate_self_valued_receipt(
                raw_receipt=raw, item=item, refs=refs
            )
            if contract_failures:
                failures.append({
                    "replication_id": rep,
                    "arm_id": arm,
                    "case_id": item["case_id"],
                    "stage": "STANDARD_SELF_VALUE_CONTRACT",
                    "failures": contract_failures,
                    "raw_receipt_hash": hash_payload(raw),
                })
            else:
                standard_valid.append(key)
            projection = project_frontier_receipt(
                raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            final_projections[key] = projection
            if arm == "A2_SELF_COMPOSED":
                provisional_projections[key] = projection
                trigger_receipts[key] = derive_escalation_receipt(
                    raw_receipt=raw, item=item
                )
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, candidate_pools, composition_receipts,
            standard_valid, counter_valid, failures,
        )
    for key, trigger in sorted(trigger_receipts.items()):
        if not trigger["triggered"]:
            continue
        rep, arm, case_id = key.split(":", 2)
        canonical = next(
            value for value in corpus["public_surface"]["items"]
            if value["case_id"] == case_id
        )
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        provisional = raw_receipts[
            f"{rep}:{arm}:STANDARD_SELF_VALUE:{case_id}"
        ]
        task = _self_value_task(
            item=item, replication_id=rep,
            experimental_arm_id=arm, route_id=trigger["route_id"],
            stage="INDEPENDENT_COUNTER_SELF_VALUE",
            refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=arm, case_id=case_id,
            stage="INDEPENDENT_COUNTER_SELF_VALUE",
            route_id=trigger["route_id"], task=task, envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{rep}:{arm}:INDEPENDENT_COUNTER_SELF_VALUE:{case_id}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            counter = envelope.normalized_result
            raw_receipts[raw_key] = counter
            contract_failures = validate_self_valued_receipt(
                raw_receipt=counter, item=item, refs=refs
            )
            if contract_failures:
                failures.append({
                    "replication_id": rep,
                    "arm_id": arm,
                    "case_id": case_id,
                    "stage": "COUNTER_SELF_VALUE_CONTRACT",
                    "failures": contract_failures,
                    "raw_receipt_hash": hash_payload(counter),
                })
            elif key not in standard_valid:
                failures.append({
                    "replication_id": rep,
                    "arm_id": arm,
                    "case_id": case_id,
                    "stage": "COMPOSITION_PRECONDITION",
                    "failures": ["STANDARD_SELF_VALUE_INVALID"],
                })
            else:
                counter_valid.append(key)
                pool = build_candidate_pool(
                    provisional_receipt=provisional,
                    counter_receipt=counter,
                    item=item,
                    replication_id=rep,
                )
                candidate_pools[key] = pool
                final_raw, composition = compose_self_valued_pool(
                    pool=pool, provisional_receipt=provisional,
                    item=item, refs=refs,
                )
                composition_receipts[key] = composition
                final_projections[key] = project_frontier_receipt(
                    raw_receipt=final_raw, item=item,
                    arm_id="A1_ONTOLOGY", evidence_refs=refs,
                )
                raw_receipts[
                    f"{rep}:{arm}:RUNTIME_COMPOSED:{case_id}"
                ] = final_raw
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, candidate_pools, composition_receipts,
            standard_valid, counter_valid, failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_self_value_contract_version": CONTRACT_VERSION,
        "source_score_map_hash": hash_payload(SCORE_MAP),
        "source_rank_bonus": list(SOURCE_RANK_BONUS),
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "candidate_pools": candidate_pools,
        "composition_receipts": composition_receipts,
        "standard_self_value_valid_keys": standard_valid,
        "counter_self_value_valid_keys": counter_valid,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "separate_value_provider_call_used": False,
        "provider_sees_numeric_score_map": False,
        "provider_selects_final_candidates": False,
        "trigger_policy_retuned_from_v0_33": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_self_value_experiment(*, corpus, preregistration, run):
    validate_self_value_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    _validate_run(run, corpus, preregistration)
    ledgers, provisional_ledgers = {}, {}
    case_deltas, replication_metrics = {}, {}
    for rep in REPLICATION_IDS:
        ledger = build_realized_cbit_ledger(
            corpus=corpus,
            run=_scoring_run(run, replication_id=rep),
        )
        provisional = build_realized_cbit_ledger(
            corpus=corpus,
            run=_scoring_run(run, replication_id=rep, provisional=True),
        )
        ledgers[rep] = ledger
        provisional_ledgers[rep] = provisional
        totals = _case_totals(ledger)
        deltas = {
            item["case_id"]: round(
                totals[(item["case_id"], "A2_SELF_COMPOSED")]["net"]
                - totals[(item["case_id"], "A1_BASELINE")]["net"], 6
            )
            for item in corpus["public_surface"]["items"]
        }
        case_deltas[rep] = deltas
        replication_metrics[rep] = {
            "arm_tokens": {
                arm: ledger["arm_metrics"][arm]["total_tokens"]
                for arm in ARM_IDS
            },
            "contrast": _metrics(list(deltas.values())),
        }
    pooled = [
        value for values in case_deltas.values() for value in values.values()
    ]
    metrics = _metrics(pooled)
    majority = round(sum(
        sum(case_deltas[rep][case] > 0 for rep in REPLICATION_IDS) >= 2
        for case in case_deltas[REPLICATION_IDS[0]]
    ) / corpus["case_count"], 6)
    positive_reps = sum(
        value["contrast"]["mean"] > 0
        for value in replication_metrics.values()
    )
    runtime = _runtime_metrics(run, corpus)
    composition = _composition_metrics(
        corpus=corpus, run=run, formal_ledgers=ledgers,
        provisional_ledgers=provisional_ledgers,
    )
    relation = {
        arm: _relation_reproducibility(
            run=run, arm_id=arm, corpus=corpus
        )
        for arm in ARM_IDS
    }
    total_tokens = sum(_call_tokens(value) for value in run["task_calls"])
    gate = preregistration["success_gate"]
    gross = composition["triggered_composition_gross_uplift"]
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
        "minimum_standard_self_value_contract_coverage": (
            runtime["standard_self_value_contract_coverage"]
            >= gate["minimum_standard_self_value_contract_coverage"]
        ),
        "minimum_counter_self_value_contract_coverage": (
            runtime["counter_self_value_contract_coverage"]
            >= gate["minimum_counter_self_value_contract_coverage"]
        ),
        "minimum_trigger_receipt_coverage": (
            runtime["trigger_receipt_coverage"]
            >= gate["minimum_trigger_receipt_coverage"]
        ),
        "minimum_trigger_execution_coverage": (
            runtime["trigger_execution_coverage"]
            >= gate["minimum_trigger_execution_coverage"]
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
        "minimum_mean_gain": metrics["mean"] >= gate["minimum_mean_gain"],
        "minimum_median_gain": (
            metrics["median"] >= gate["minimum_median_gain"]
        ),
        "minimum_win_rate": (
            metrics["win_rate"] >= gate["minimum_win_rate"]
        ),
        "minimum_positive_replications": (
            positive_reps >= gate["minimum_positive_replications"]
        ),
        "minimum_majority_positive_case_rate": (
            majority >= gate["minimum_majority_positive_case_rate"]
        ),
        "maximum_severe_loss_rate": (
            metrics["severe_loss_rate"]
            <= gate["maximum_severe_loss_rate"]
        ),
        "minimum_relation_jaccard_relative_to_baseline": (
            relation["A2_SELF_COMPOSED"][
                "mean_pairwise_relation_jaccard"
            ]
            - relation["A1_BASELINE"]["mean_pairwise_relation_jaccard"]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "minimum_triggered_composition_gross_median": (
            gross is not None
            and gross["median"]
            >= gate["minimum_triggered_composition_gross_median"]
        ),
        "minimum_triggered_composition_gross_win_rate": (
            gross is not None
            and gross["win_rate"]
            >= gate["minimum_triggered_composition_gross_win_rate"]
        ),
        "maximum_triggered_composition_gross_loss_rate": (
            gross is not None
            and gross["loss_count"] / gross["count"]
            <= gate["maximum_triggered_composition_gross_loss_rate"]
        ),
        "maximum_mean_added_token_penalty_cbit": (
            composition["mean_added_token_penalty_cbit"]
            <= gate["maximum_mean_added_token_penalty_cbit"]
        ),
        "hard_runaway_total_tokens": (
            total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "no_third_provider_call": (
            run["separate_value_provider_call_used"] is False
            and all(
                value["stage"] != "SOURCE_BLIND_CANDIDATE_VALUE"
                for value in run["task_calls"]
            )
        ),
        "runtime_composition_preserved": (
            run["provider_selects_final_candidates"] is False
            and all(
                value["runtime_deterministic_composition"]
                for value in run["composition_receipts"].values()
            )
        ),
        "authority_boundary_preserved": all(
            run.get(key) is False
            for key in (
                "selection_authority", "retention_authority",
                "production_authority",
            )
        ),
    }
    passed = all(conditions.values())
    if passed:
        decision = "PASS_SELF_VALUE_COMPOSITION"
        state = "SELF_VALUE_PASSED_READY_EXTERNAL_PANEL"
    elif total_tokens > gate["hard_runaway_total_tokens"]:
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "SELF_VALUE_RESOURCE_STOP"
    else:
        decision = "REJECT_SELF_VALUE_COMPOSITION"
        state = "SELF_VALUE_REJECTED_STOP"
    commitment = {
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "replication_ledgers": ledgers,
        "provisional_replication_ledgers": provisional_ledgers,
        "case_deltas": case_deltas,
        "replication_metrics": replication_metrics,
        "pooled_contrast_metrics": metrics,
        "majority_positive_case_rate": majority,
        "positive_replication_count": positive_reps,
        "runtime_metrics": runtime,
        "composition_metrics": composition,
        "relation_reproducibility": relation,
        "physical_total_tokens": total_tokens,
        "conditions": conditions,
        "self_value_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _self_value_task(
    *, item, replication_id, experimental_arm_id, route_id,
    stage, refs, adapter
):
    prompts = {
        "A1_ONTOLOGY": (
            "Build a compact object census and synthesize the three "
            "strongest evidence-bound problem candidates."
        ),
        "MECHANISM": (
            "Independently map interacting mechanisms and seek relations "
            "with high expected uncertainty reduction."
        ),
        "ADVERSARIAL": (
            "Independently challenge the obvious explanation using "
            "counterevidence and discriminating tests."
        ),
        "COORDINATE_SHIFT": (
            "Independently question the focal object, proxy, and coordinate "
            "and seek evidence-bounded alternative relations."
        ),
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{stage}-"
            f"{experimental_arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{prompts[route_id]} Return exactly three distinct, "
            "falsifiable candidates. For each candidate, independently "
            "record whether evidence supports an effect, supports an "
            "informative null, remains indirect or weak, or is conflicted; "
            "also record counterevidence handling, constraint binding, "
            "falsifiability, expected Cbit, verdict, and evidence spans. "
            "Do not rank candidates against another receipt. The numeric "
            "Runtime score map is unavailable."
        ),
        inputs={
            "stage": stage,
            "replication_id": replication_id,
            "route_id": route_id,
            "receipt_arm_id": "A1_ONTOLOGY",
            "public_case": item,
            "numeric_score_map_available": False,
            "other_receipt_available": False,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=self_valued_exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _scoring_run(run, *, replication_id, provisional=False):
    calls, projections = [], {}
    case_ids = sorted({
        value["case_id"]
        for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "STANDARD_SELF_VALUE"
    })
    for case_id in case_ids:
        for arm in ARM_IDS:
            base = _find_call(
                run, replication_id=replication_id, arm_id=arm,
                case_id=case_id, stage="STANDARD_SELF_VALUE",
            )
            path = [base] if base is not None else []
            if arm == "A2_SELF_COMPOSED" and not provisional:
                counter = _find_call(
                    run, replication_id=replication_id, arm_id=arm,
                    case_id=case_id,
                    stage="INDEPENDENT_COUNTER_SELF_VALUE",
                )
                if counter is not None:
                    path.append(counter)
            calls.append({
                "arm_id": arm,
                "case_id": case_id,
                "invocation_receipt": {
                    "token_usage": _combined_usage(path),
                    "derived_cost_receipt": True,
                    "source_call_hashes": [
                        value["call_hash"] for value in path
                    ],
                },
            })
            key = f"{replication_id}:{arm}:{case_id}"
            projection = (
                run["provisional_projections"].get(key)
                if arm == "A2_SELF_COMPOSED" and provisional
                else run["final_projections"].get(key)
            )
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
            if value["stage"] == "STANDARD_SELF_VALUE"
            and value["arm_id"] == arm
        ]
        completion[f"STANDARD_{arm}"] = round(
            sum(value["status"] == "COMPLETED" for value in values)
            / expected, 6
        )
    triggered = {
        key for key, value in run["trigger_receipts"].items()
        if value["triggered"]
    }
    counter_calls = [
        value for value in run["task_calls"]
        if value["stage"] == "INDEPENDENT_COUNTER_SELF_VALUE"
    ]
    if triggered:
        completion["INDEPENDENT_COUNTER_SELF_VALUE"] = round(
            sum(value["status"] == "COMPLETED" for value in counter_calls)
            / len(triggered), 6
        )
        counter_contract = round(
            len(run["counter_self_value_valid_keys"])
            / len(triggered), 6
        )
        execution = round(
            len(run["composition_receipts"]) / len(triggered), 6
        )
    else:
        completion["INDEPENDENT_COUNTER_SELF_VALUE"] = 1.0
        counter_contract, execution = 0.0, 1.0
    identity = 0
    for rep in REPLICATION_IDS:
        for item in corpus["public_surface"]["items"]:
            left = _find_call(
                run, replication_id=rep, arm_id="A1_BASELINE",
                case_id=item["case_id"], stage="STANDARD_SELF_VALUE",
            )
            right = _find_call(
                run, replication_id=rep, arm_id="A2_SELF_COMPOSED",
                case_id=item["case_id"], stage="STANDARD_SELF_VALUE",
            )
            identity += bool(
                left and right
                and left["provider_prompt_hash"]
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
            sum(
                len(value["eligible_candidate_ids"]) == 3
                for value in values
            ) / expected, 6
        )
    return {
        "provider_completion_per_required_stage": completion,
        "prompt_identity_coverage": round(identity / expected, 6),
        "standard_self_value_contract_coverage": round(
            len(run["standard_self_value_valid_keys"])
            / (expected * len(ARM_IDS)), 6
        ),
        "counter_self_value_contract_coverage": counter_contract,
        "trigger_receipt_coverage": round(
            len(run["trigger_receipts"]) / expected, 6
        ),
        "trigger_execution_coverage": execution,
        "final_nonblock_coverage_per_arm": nonblock,
        "final_exact_three_coverage_per_arm": exact,
        "failure_count": len(run["failures"]),
    }


def _composition_metrics(
    *, corpus, run, formal_ledgers, provisional_ledgers
):
    gross_uplifts, net_uplifts, token_penalties = [], [], []
    sources, routes, flags, axes = Counter(), Counter(), Counter(), Counter()
    for rep in REPLICATION_IDS:
        before = _case_totals(provisional_ledgers[rep])
        after = _case_totals(formal_ledgers[rep])
        for item in corpus["public_surface"]["items"]:
            case = item["case_id"]
            key = f"{rep}:A2_SELF_COMPOSED:{case}"
            trigger = run["trigger_receipts"].get(key)
            if trigger is None:
                continue
            routes[trigger["route_id"]] += 1
            for flag in trigger["diagnostic_flags"]:
                flags[flag] += 1
            composition = run["composition_receipts"].get(key)
            if not trigger["triggered"] or composition is None:
                continue
            gross_uplifts.append(
                after[(case, "A2_SELF_COMPOSED")]["gross"]
                - before[(case, "A2_SELF_COMPOSED")]["gross"]
            )
            net_uplifts.append(
                after[(case, "A2_SELF_COMPOSED")]["net"]
                - before[(case, "A2_SELF_COMPOSED")]["net"]
            )
            token_penalties.append(
                after[(case, "A2_SELF_COMPOSED")]["token_cost"]
                - before[(case, "A2_SELF_COMPOSED")]["token_cost"]
            )
            for lineage in composition["lineage"]:
                sources[lineage["source_id"]] += 1
            for scored in composition["scored_candidates"]:
                value = scored["provider_self_value"]
                for axis in SCORE_MAP:
                    axes[f"{axis}:{value[axis]}"] += 1
    triggered = sum(
        value["triggered"] for value in run["trigger_receipts"].values()
    )
    selected_total = sum(sources.values())
    return {
        "trigger_count": triggered,
        "trigger_rate": round(
            triggered / len(run["trigger_receipts"])
            if run["trigger_receipts"] else 0.0, 6
        ),
        "valid_composition_count": len(run["composition_receipts"]),
        "route_distribution": dict(routes),
        "diagnostic_flag_distribution": dict(flags),
        "selected_source_distribution": dict(sources),
        "counterproposal_adoption_rate": round(
            sources["COUNTER"] / selected_total if selected_total else 0.0,
            6,
        ),
        "self_value_axis_distribution": dict(axes),
        "triggered_composition_gross_uplift": (
            _metrics(gross_uplifts) if gross_uplifts else None
        ),
        "triggered_composition_net_uplift": (
            _metrics(net_uplifts) if net_uplifts else None
        ),
        "mean_added_token_penalty_cbit": round(
            sum(token_penalties) / len(token_penalties)
            if token_penalties else 0.0, 6
        ),
    }


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
        raise ValueError("self_value_preregistration_invalid")


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
        raise ValueError("self_value_run_invalid")


def _checkpoint(
    callback, corpus, preregistration, calls, raw_receipts,
    provisional_projections, final_projections, trigger_receipts,
    candidate_pools, composition_receipts, standard_valid,
    counter_valid, failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "self_value_progress_v0_38",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "candidate_pools": dict(candidate_pools),
        "composition_receipts": dict(composition_receipts),
        "standard_self_value_valid_keys": list(standard_valid),
        "counter_self_value_valid_keys": list(counter_valid),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})
