"""Independent counterproposal and candidate-wise arbitration v0.36."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import combinations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .candidate_pool_arbitration import (
    CONTRACT_VERSION,
    arbitration_schema,
    build_candidate_pool,
    materialize_arbitrated_receipt,
    validate_arbitration,
)
from .collaborative_stability_experiment import exact_three_schema
from .frontier_cbit_ledger import build_realized_cbit_ledger
from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .independent_arbitration_holdout import (
    REPLICATION_IDS,
    validate_independent_arbitration_holdout,
)
from .lineage_revision_experiment import (
    _call,
    _provider_failure,
    _provider_prompt_hash,
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
)


RUNTIME_VERSION = "independent_arbitration_experiment_v0_36"
ARM_IDS = ("A1_BASELINE", "A2_ARBITRATED")


def build_independent_arbitration_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_recovery
):
    validate_independent_arbitration_holdout(corpus)
    if (
        prior_analysis.get("decision") != "REJECT_RUNTIME_DIFF"
        or prior_analysis.get("candidate_state")
        != "RUNTIME_DIFF_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "RUNTIME_DIFF_REJECTED_STOP"
        or prior_recovery.get("provider_calls_replayed") is not False
        or prior_analysis.get("runtime_metrics", {}).get(
            "lineage_contract_coverage"
        ) != 1.0
    ):
        raise ValueError("independent_arbitration_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_recovery_hash": prior_recovery["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_arbitration_contract_version": CONTRACT_VERSION,
        "frozen_hypothesis": (
            "A counterproposal generated without seeing provisional "
            "candidates can recover exploration, while a separate "
            "candidate-only arbiter can preserve useful baseline candidates "
            "and admit only higher-Cbit alternatives."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_ARBITRATED_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_prompt_identity_coverage": 1.0,
            "minimum_trigger_receipt_coverage": 0.95,
            "minimum_trigger_execution_coverage": 0.9,
            "minimum_arbitration_contract_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.9,
            "minimum_mean_gain": 0.15,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.55,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.5,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.05,
            "minimum_triggered_arbitration_gross_median": 0.25,
            "minimum_triggered_arbitration_gross_win_rate": 0.55,
            "maximum_triggered_arbitration_gross_loss_rate": 0.25,
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.9),
        },
        "cost_policy": {
            "first_call_provider_payload_identical_between_arms": True,
            "runtime_trigger_adds_provider_tokens": False,
            "counterproposal_only_when_triggered": True,
            "arbiter_only_after_counterproposal": True,
            "all_counterproposal_and_arbiter_tokens_charged": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "cbit_per_token_is_diagnostic_not_acceptance_gate": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 1.5),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.9),
        },
        "trigger_policy_retuned_from_v0_33": False,
        "counterproposal_sees_provisional_candidates": False,
        "counterproposal_sees_trigger_diagnostics": False,
        "arbiter_may_rewrite_or_generate_candidates": False,
        "fresh_labels_available_during_inference": False,
        "external_semantic_panel_required": True,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_independent_arbitration_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_independent_arbitration_holdout(corpus)
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
    trigger_receipts, candidate_pools = {}, {}
    selection_receipts, arbitration_receipts = {}, {}

    for rep, arm, canonical in matrix:
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _standard_task(
            item=item, replication_id=rep,
            experimental_arm_id=arm, refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=arm, case_id=item["case_id"],
            stage="STANDARD_ONTOLOGY", route_id="A1_ONTOLOGY",
            task=task, envelope=envelope,
        )
        calls.append(call)
        raw_key = f"{rep}:{arm}:STANDARD_ONTOLOGY:{item['case_id']}"
        key = f"{rep}:{arm}:{item['case_id']}"
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            projection = project_frontier_receipt(
                raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            final_projections[key] = projection
            if arm == "A2_ARBITRATED":
                provisional_projections[key] = projection
                trigger_receipts[key] = derive_escalation_receipt(
                    raw_receipt=raw, item=item
                )
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, candidate_pools, selection_receipts,
            arbitration_receipts, failures,
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
            f"{rep}:{arm}:STANDARD_ONTOLOGY:{case_id}"
        ]
        counter_task = _counterproposal_task(
            item=item, replication_id=rep, route_id=trigger["route_id"],
            refs=refs, adapter=adapter,
        )
        counter_envelope = ProviderTaskRouter([adapter]).route(counter_task)
        counter_call = _call(
            replication_id=rep, arm_id=arm, case_id=case_id,
            stage="INDEPENDENT_COUNTERPROPOSAL",
            route_id=trigger["route_id"], task=counter_task,
            envelope=counter_envelope,
        )
        calls.append(counter_call)
        counter_key = (
            f"{rep}:{arm}:INDEPENDENT_COUNTERPROPOSAL:{case_id}"
        )
        if counter_envelope.status != "COMPLETED":
            failures.append(_provider_failure(counter_call))
            _checkpoint(
                checkpoint_callback, corpus, preregistration, calls,
                raw_receipts, provisional_projections, final_projections,
                trigger_receipts, candidate_pools, selection_receipts,
                arbitration_receipts, failures,
            )
            continue
        counter = counter_envelope.normalized_result
        raw_receipts[counter_key] = counter
        pool = build_candidate_pool(
            provisional_receipt=provisional,
            counter_receipt=counter,
            item=item,
            replication_id=rep,
        )
        candidate_pools[key] = pool
        arbiter_task = _arbiter_task(
            item=item, replication_id=rep, pool=pool, refs=refs,
            adapter=adapter,
        )
        arbiter_envelope = ProviderTaskRouter([adapter]).route(arbiter_task)
        arbiter_call = _call(
            replication_id=rep, arm_id=arm, case_id=case_id,
            stage="CANDIDATE_WISE_ARBITER", route_id="ARBITER",
            task=arbiter_task, envelope=arbiter_envelope,
        )
        calls.append(arbiter_call)
        selection_key = f"{rep}:{arm}:CANDIDATE_WISE_ARBITER:{case_id}"
        if arbiter_envelope.status != "COMPLETED":
            failures.append(_provider_failure(arbiter_call))
        else:
            selection = arbiter_envelope.normalized_result
            raw_receipts[selection_key] = selection
            selection_receipts[key] = selection
            contract_failures = validate_arbitration(
                selection=selection, pool=pool, item=item, refs=refs
            )
            if contract_failures:
                failures.append({
                    "replication_id": rep,
                    "arm_id": arm,
                    "case_id": case_id,
                    "stage": "ARBITRATION_CONTRACT",
                    "failures": contract_failures,
                    "selection_hash": hash_payload(selection),
                })
            else:
                final_raw, receipt = materialize_arbitrated_receipt(
                    selection=selection, pool=pool,
                    provisional_receipt=provisional, item=item, refs=refs,
                )
                arbitration_receipts[key] = receipt
                final_projections[key] = project_frontier_receipt(
                    raw_receipt=final_raw, item=item,
                    arm_id="A1_ONTOLOGY", evidence_refs=refs,
                )
                raw_receipts[
                    f"{rep}:{arm}:RUNTIME_MATERIALIZED:{case_id}"
                ] = final_raw
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, candidate_pools, selection_receipts,
            arbitration_receipts, failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_trigger_policy_version": POLICY_VERSION,
        "source_arbitration_contract_version": CONTRACT_VERSION,
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "candidate_pools": candidate_pools,
        "selection_receipts": selection_receipts,
        "arbitration_receipts": arbitration_receipts,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "counterproposal_sees_provisional_candidates": False,
        "counterproposal_sees_trigger_diagnostics": False,
        "arbiter_candidate_generation_allowed": False,
        "trigger_policy_retuned_from_v0_33": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_independent_arbitration_experiment(
    *, corpus, preregistration, run
):
    validate_independent_arbitration_holdout(corpus)
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
                totals[(item["case_id"], "A2_ARBITRATED")]["net"]
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
    arbitration = _arbitration_metrics(
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
    gross = arbitration["triggered_arbitration_gross_uplift"]
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
        "minimum_arbitration_contract_coverage": (
            runtime["arbitration_contract_coverage"]
            >= gate["minimum_arbitration_contract_coverage"]
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
            relation["A2_ARBITRATED"]["mean_pairwise_relation_jaccard"]
            - relation["A1_BASELINE"]["mean_pairwise_relation_jaccard"]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "minimum_triggered_arbitration_gross_median": (
            gross is not None
            and gross["median"]
            >= gate["minimum_triggered_arbitration_gross_median"]
        ),
        "minimum_triggered_arbitration_gross_win_rate": (
            gross is not None
            and gross["win_rate"]
            >= gate["minimum_triggered_arbitration_gross_win_rate"]
        ),
        "maximum_triggered_arbitration_gross_loss_rate": (
            gross is not None
            and gross["loss_count"] / gross["count"]
            <= gate["maximum_triggered_arbitration_gross_loss_rate"]
        ),
        "hard_runaway_total_tokens": (
            total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "counterproposal_isolation_preserved": (
            run["counterproposal_sees_provisional_candidates"] is False
            and run["counterproposal_sees_trigger_diagnostics"] is False
        ),
        "arbiter_did_not_generate_candidates": (
            run["arbiter_candidate_generation_allowed"] is False
            and all(
                receipt["runtime_mechanical_materialization"]
                and not receipt["provider_generated_final_candidates"]
                for receipt in run["arbitration_receipts"].values()
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
        decision = "PASS_INDEPENDENT_ARBITRATION"
        state = "INDEPENDENT_ARBITRATION_PASSED_READY_EXTERNAL_PANEL"
    elif total_tokens > gate["hard_runaway_total_tokens"]:
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "INDEPENDENT_ARBITRATION_RESOURCE_STOP"
    else:
        decision = "REJECT_INDEPENDENT_ARBITRATION"
        state = "INDEPENDENT_ARBITRATION_REJECTED_STOP"
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
        "arbitration_metrics": arbitration,
        "relation_reproducibility": relation,
        "physical_total_tokens": total_tokens,
        "conditions": conditions,
        "independent_arbitration_gate": "PASS" if passed else "REJECT",
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
            "arm_id": "A1_ONTOLOGY",
            "public_case": item,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _counterproposal_task(
    *, item, replication_id, route_id, refs, adapter
):
    prompts = {
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
        "A1_ONTOLOGY": (
            "Independently build the strongest evidence-bound object model."
        ),
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-COUNTER-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{prompts[route_id]} Return exactly three distinct, falsifiable "
            "problem candidates. You are an independent counterproposer: no "
            "provisional candidate set is available, and novelty alone has "
            "no value."
        ),
        inputs={
            "stage": "INDEPENDENT_COUNTERPROPOSAL",
            "replication_id": replication_id,
            "route_id": route_id,
            "receipt_arm_id": "A1_ONTOLOGY",
            "public_case": item,
            "provisional_candidates_available": False,
            "trigger_diagnostics_available": False,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _arbiter_task(*, item, replication_id, pool, refs, adapter):
    ordered_pool = sorted(
        pool["candidates"],
        key=lambda value: hash_payload([
            RUNTIME_VERSION, replication_id, "POOL",
            value["pool_candidate_id"],
        ]),
    )
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-ARBITER-"
            f"{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Select exactly three candidates from the supplied pool. You may "
            "not rewrite or generate candidates. Return the pool candidate "
            "IDs and their canonical relation IDs in the same order. Select "
            "three distinct relations that maximize evidence support, "
            "counterevidence coverage, constraint awareness, "
            "falsifiability, and expected uncertainty reduction. Preserve "
            "a baseline candidate whenever the counterproposal is not "
            "clearly better."
        ),
        inputs={
            "stage": "CANDIDATE_WISE_ARBITRATION",
            "replication_id": replication_id,
            "arm_id": "A2_ARBITRATED",
            "public_case": item,
            "candidate_pool": ordered_pool,
            "candidate_pool_hash": pool["artifact_hash"],
            "selection_criteria": [
                "EVIDENCE_SUPPORT",
                "COUNTEREVIDENCE_COVERAGE",
                "CONSTRAINT_COVERAGE",
                "FALSIFIABILITY",
                "RELATION_DIVERSITY",
                "EXPECTED_UNCERTAINTY_REDUCTION",
            ],
            "candidate_rewrite_allowed": False,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=arbitration_schema(
            item=item, pool=pool, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _scoring_run(run, *, replication_id, provisional=False):
    calls, projections = [], {}
    for item_case in sorted({
        value["case_id"]
        for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "STANDARD_ONTOLOGY"
    }):
        for arm in ARM_IDS:
            base = _find_call(
                run, replication_id=replication_id, arm_id=arm,
                case_id=item_case, stage="STANDARD_ONTOLOGY",
            )
            path = [base] if base is not None else []
            if arm == "A2_ARBITRATED" and not provisional:
                for stage in (
                    "INDEPENDENT_COUNTERPROPOSAL",
                    "CANDIDATE_WISE_ARBITER",
                ):
                    call = _find_call(
                        run, replication_id=replication_id, arm_id=arm,
                        case_id=item_case, stage=stage,
                    )
                    if call is not None:
                        path.append(call)
            calls.append({
                "arm_id": arm,
                "case_id": item_case,
                "invocation_receipt": {
                    "token_usage": _combined_usage(path),
                    "derived_cost_receipt": True,
                    "source_call_hashes": [
                        value["call_hash"] for value in path
                    ],
                },
            })
            key = f"{replication_id}:{arm}:{item_case}"
            projection = (
                run["provisional_projections"].get(key)
                if arm == "A2_ARBITRATED" and provisional
                else run["final_projections"].get(key)
            )
            if projection is not None:
                projections[f"{arm}:{item_case}"] = projection
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
        completion[f"STANDARD_{arm}"] = round(
            sum(value["status"] == "COMPLETED" for value in values)
            / expected, 6
        )
    triggered = {
        key for key, value in run["trigger_receipts"].items()
        if value["triggered"]
    }
    if triggered:
        for stage in (
            "INDEPENDENT_COUNTERPROPOSAL",
            "CANDIDATE_WISE_ARBITER",
        ):
            completion[stage] = round(
                sum(
                    value["stage"] == stage
                    and value["status"] == "COMPLETED"
                    for value in run["task_calls"]
                ) / len(triggered), 6
            )
        execution = round(
            len(run["arbitration_receipts"]) / len(triggered), 6
        )
        contract = execution
    else:
        completion["INDEPENDENT_COUNTERPROPOSAL"] = 1.0
        completion["CANDIDATE_WISE_ARBITER"] = 1.0
        execution, contract = 1.0, 0.0
    identity = 0
    for rep in REPLICATION_IDS:
        for item in corpus["public_surface"]["items"]:
            left = _find_call(
                run, replication_id=rep, arm_id="A1_BASELINE",
                case_id=item["case_id"], stage="STANDARD_ONTOLOGY",
            )
            right = _find_call(
                run, replication_id=rep, arm_id="A2_ARBITRATED",
                case_id=item["case_id"], stage="STANDARD_ONTOLOGY",
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
        "trigger_receipt_coverage": round(
            len(run["trigger_receipts"]) / expected, 6
        ),
        "trigger_execution_coverage": execution,
        "arbitration_contract_coverage": contract,
        "final_nonblock_coverage_per_arm": nonblock,
        "final_exact_three_coverage_per_arm": exact,
        "failure_count": len(run["failures"]),
    }


def _arbitration_metrics(
    *, corpus, run, formal_ledgers, provisional_ledgers
):
    gross_uplifts, net_uplifts, token_penalties = [], [], []
    sources, routes, flags = Counter(), Counter(), Counter()
    valid = 0
    for rep in REPLICATION_IDS:
        before = _case_totals(provisional_ledgers[rep])
        after = _case_totals(formal_ledgers[rep])
        for item in corpus["public_surface"]["items"]:
            case = item["case_id"]
            key = f"{rep}:A2_ARBITRATED:{case}"
            trigger = run["trigger_receipts"].get(key)
            if trigger is None:
                continue
            routes[trigger["route_id"]] += 1
            for flag in trigger["diagnostic_flags"]:
                flags[flag] += 1
            receipt = run["arbitration_receipts"].get(key)
            if not trigger["triggered"] or receipt is None:
                continue
            valid += 1
            gross_uplifts.append(
                after[(case, "A2_ARBITRATED")]["gross"]
                - before[(case, "A2_ARBITRATED")]["gross"]
            )
            net_uplifts.append(
                after[(case, "A2_ARBITRATED")]["net"]
                - before[(case, "A2_ARBITRATED")]["net"]
            )
            token_penalties.append(
                after[(case, "A2_ARBITRATED")]["token_cost"]
                - before[(case, "A2_ARBITRATED")]["token_cost"]
            )
            for lineage in receipt["lineage"]:
                sources[lineage["source_id"]] += 1
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
        "valid_arbitration_count": valid,
        "route_distribution": dict(routes),
        "diagnostic_flag_distribution": dict(flags),
        "selected_source_distribution": dict(sources),
        "counterproposal_adoption_rate": round(
            sources["COUNTER"] / selected_total if selected_total else 0.0,
            6,
        ),
        "triggered_arbitration_gross_uplift": (
            _metrics(gross_uplifts) if gross_uplifts else None
        ),
        "triggered_arbitration_net_uplift": (
            _metrics(net_uplifts) if net_uplifts else None
        ),
        "mean_added_token_penalty_cbit": round(
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


def _relation_reproducibility(*, run, arm_id, corpus):
    scores, exact = [], 0
    for item in corpus["public_surface"]["items"]:
        relations = {}
        for rep in REPLICATION_IDS:
            projection = run["final_projections"].get(
                f"{rep}:{arm_id}:{item['case_id']}"
            )
            relations[rep] = {
                (
                    value["normalized_candidate"]["source_object_id"],
                    value["normalized_candidate"]["target_object_id"],
                )
                for value in (
                    projection["candidate_components"] if projection else ()
                )
                if value["disposition"] != "QUARANTINED_COMPONENT"
            }
        for left, right in combinations(REPLICATION_IDS, 2):
            union = relations[left] | relations[right]
            scores.append(
                len(relations[left] & relations[right]) / len(union)
                if union else 1.0
            )
            exact += relations[left] == relations[right]
    return {
        "pair_count": len(scores),
        "mean_pairwise_relation_jaccard": round(
            sum(scores) / len(scores), 6
        ),
        "exact_pair_match_count": exact,
    }


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
                corpus_hash, replication_id, "SPAN", value["span_id"],
            ]),
        ),
    }


def _find_call(run, *, replication_id, arm_id, case_id, stage):
    return next((
        value for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["arm_id"] == arm_id
        and value["case_id"] == case_id
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
        raise ValueError("independent_arbitration_preregistration_invalid")


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
        raise ValueError("independent_arbitration_run_invalid")


def _checkpoint(
    callback, corpus, preregistration, calls, raw_receipts,
    provisional_projections, final_projections, trigger_receipts,
    candidate_pools, selection_receipts, arbitration_receipts,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "independent_arbitration_progress_v0_36",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "candidate_pools": dict(candidate_pools),
        "selection_receipts": dict(selection_receipts),
        "arbitration_receipts": dict(arbitration_receipts),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})
