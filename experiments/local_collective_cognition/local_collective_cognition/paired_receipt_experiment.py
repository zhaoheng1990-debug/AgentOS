"""Paired common-receipt experiment v0.45."""

from __future__ import annotations

import math
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .candidate_pool_arbitration import build_candidate_pool
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
    POLICY_VERSION as ESCALATION_POLICY_VERSION,
    derive_escalation_receipt,
)
from .selective_role_routing_experiment import (
    _call_tokens,
    _combined_usage,
    _metrics,
)
from .paired_receipt_holdout import (
    REPLICATION_IDS,
    validate_paired_receipt_holdout,
)
from .tri_lane_replacement_gate import (
    GATE_VERSION as REPLACEMENT_GATE_VERSION,
    apply_tri_lane_replacement_gate,
    derive_cross_replication_witnesses,
)
from .null_role_candidate_composition import (
    CONTRACT_VERSION as COMPOSITION_CONTRACT_VERSION,
    SCORE_MAP,
    SOURCE_RANK_BONUS,
    compose_null_role_valued_pool,
    null_role_valued_exact_three_schema,
    validate_null_role_valued_receipt,
)
from .selective_delta_policy import (
    POLICY_VERSION as QUALIFICATION_POLICY_VERSION,
    derive_selective_qualification,
)
from .compact_delta_contract import (
    CONTRACT_VERSION as DELTA_CONTRACT_VERSION,
    build_compact_delta_view,
    compact_delta_schema,
    materialize_compact_delta,
    validate_compact_delta,
)


RUNTIME_VERSION = "paired_receipt_experiment_v0_45"
ARM_IDS = ("A1_BASELINE", "A2_COMPACT_DELTA")
SHARED_ARM_ID = "SHARED_STANDARD"


def build_paired_receipt_preregistration(
    *, corpus, prior_analysis, prior_closure, prior_posthoc
):
    validate_paired_receipt_holdout(corpus)
    if (
        prior_analysis.get("decision")
        != "REJECT_TRI_LANE_REPLACEMENT_GATE"
        or prior_analysis.get("candidate_state")
        != "TRI_LANE_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "TRI_LANE_REJECTED_STOP"
        or prior_analysis.get("runtime_metrics", {}).get(
            "standard_compact_delta_contract_coverage"
        ) != 1.0
        or prior_analysis.get("runtime_metrics", {}).get(
            "counter_compact_delta_contract_coverage"
        ) != 1.0
        or prior_analysis.get("composition_metrics", {}).get(
            "triggered_composition_gross_uplift", {}
        ).get("loss_count") != 0
        or prior_analysis.get("replacement_gate_metrics", {}).get(
            "accepted_count"
        ) != 4
        or prior_analysis.get("composition_metrics", {}).get(
            "mean_delta_token_penalty_cbit", 0.0
        ) <= 0.6
        or prior_posthoc.get("formal_decision_unchanged") is not True
        or prior_posthoc.get(
            "mean_fraction_of_positive_oracle_uplift_captured", 0.0
        ) != 0.438596
        or prior_posthoc.get("positive_oracle_cell_count") != 9
        or prior_posthoc.get(
            "classification_distribution", {}
        ).get("BENEFICIAL_ACCEPTED") != 4
        or prior_posthoc.get(
            "classification_distribution", {}
        ).get("BENEFICIAL_REJECTED") != 5
    ):
        raise ValueError("paired_receipt_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_escalation_policy_version": ESCALATION_POLICY_VERSION,
        "source_qualification_policy_version": (
            QUALIFICATION_POLICY_VERSION
        ),
        "source_delta_contract_version": DELTA_CONTRACT_VERSION,
        "source_composition_contract_version": (
            COMPOSITION_CONTRACT_VERSION
        ),
        "source_replacement_gate_version": REPLACEMENT_GATE_VERSION,
        "source_score_map_hash": hash_payload(SCORE_MAP),
        "source_rank_bonus": list(SOURCE_RANK_BONUS),
        "frozen_hypothesis": (
            "A paired common-receipt design will isolate the causal net Cbit "
            "of delta generation and tri-lane admission by sharing one "
            "standard Provider receipt between both arms. It will halve "
            "standard calls, cancel standard-call variance and cost in the "
            "contrast, preserve zero gross loss among accepted deltas, and "
            "produce non-negative pooled net gain."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "candidate_count_per_final_receipt": 3,
        "primary_contrast": "A2_COMPACT_DELTA_MINUS_A1_BASELINE",
        "success_gate": {
            "minimum_provider_completion_per_required_stage": 0.95,
            "minimum_prompt_identity_coverage": 1.0,
            "minimum_standard_compact_delta_contract_coverage": 0.95,
            "minimum_counter_compact_delta_contract_coverage": 0.9,
            "minimum_trigger_receipt_coverage": 0.95,
            "minimum_qualification_receipt_coverage": 0.95,
            "minimum_trigger_execution_coverage": 0.9,
            "minimum_nonblock_coverage_per_arm": 0.9,
            "minimum_exact_three_coverage_per_arm": 0.85,
            "minimum_mean_gain": 0.0,
            "minimum_median_gain": 0.0,
            "minimum_win_rate": 0.15,
            "minimum_positive_replications": 2,
            "minimum_majority_positive_case_rate": 0.125,
            "maximum_severe_loss_rate": 0.2,
            "minimum_relation_jaccard_relative_to_baseline": -0.1,
            "minimum_accepted_composition_count": 2,
            "minimum_distinct_acceptance_lanes": 2,
            "minimum_triggered_composition_gross_mean": 0.25,
            "minimum_triggered_composition_gross_median": 0.0,
            "minimum_triggered_composition_gross_win_rate": 0.5,
            "maximum_triggered_composition_gross_loss_rate": 0.0,
            "maximum_mean_added_token_penalty_cbit": 1.0,
            "maximum_mean_delta_token_penalty_cbit": 0.75,
            "maximum_physical_total_tokens": math.floor(
                prior_total * 0.75
            ),
            "required_shared_standard_call_count": (
                corpus["case_count"] * len(REPLICATION_IDS)
            ),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.4),
        },
        "cost_policy": {
            "first_call_provider_payload_identical_between_arms": True,
            "one_physical_standard_call_shared_between_arms": True,
            "standard_compact_delta_cost_symmetric_between_arms": True,
            "runtime_trigger_adds_provider_tokens": False,
            "one_delta_candidate_only_when_qualified": True,
            "maximum_delta_candidates_per_call": 1,
            "maximum_delta_evidence_spans": 4,
            "separate_value_provider_call_allowed": False,
            "runtime_composition_adds_provider_tokens": False,
            "all_counterproposal_tokens_charged": True,
            "token_cost_already_subtracted_inside_realized_cbit": True,
            "soft_expected_total_tokens": math.ceil(prior_total * 1.1),
            "hard_runaway_total_tokens": math.ceil(prior_total * 1.4),
        },
        "trigger_policy_retuned_from_v0_33": False,
        "qualification_thresholds_frozen_from_v0_41": True,
        "compact_contract_fields_tuned_after_freeze": False,
        "replacement_gate_tuned_after_freeze": False,
        "replacement_gate_adds_provider_calls": False,
        "focal_object_id_public_before_inference": True,
        "cross_replication_witnesses_use_private_truth": False,
        "informative_null_lane_independent_of_effect_lane": True,
        "paired_standard_receipt_shared_between_arms": True,
        "paired_standard_cost_cancels_in_contrast": True,
        "independent_standard_arm_calls_forbidden": True,
        "existing_axis_weights_retuned_from_v0_38": False,
        "truth_state_research_value_separated": True,
        "null_information_role_independent_of_current_truth_state": True,
        "non_null_prospective_role_allowed": True,
        "discriminating_null_discard_forbidden": True,
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


def run_paired_receipt_experiment(
    *, corpus, preregistration, adapter, checkpoint_callback=None
):
    validate_paired_receipt_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    refs = tuple(corpus["evidence_refs"])
    matrix = [
        (rep, item)
        for rep in REPLICATION_IDS
        for item in corpus["public_surface"]["items"]
    ]
    matrix.sort(key=lambda value: hash_payload([
        RUNTIME_VERSION, "SHARED_STANDARD", value[0],
        value[1]["case_id"],
    ]))
    calls, raw_receipts, failures = [], {}, []
    provisional_projections, final_projections = {}, {}
    trigger_receipts, qualification_receipts = {}, {}
    delta_views, materialization_receipts = {}, {}
    candidate_pools, proposed_composition_receipts = {}, {}
    gate_receipts, composition_receipts = {}, {}
    standard_valid, counter_valid = [], []
    for rep, canonical in matrix:
        item = _replication_surface(
            canonical, replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        task = _standard_task(
            item=item, replication_id=rep,
            experimental_arm_id=SHARED_ARM_ID,
            route_id="A1_ONTOLOGY",
            stage="STANDARD_COMPACT_DELTA", refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=SHARED_ARM_ID,
            case_id=item["case_id"],
            stage="STANDARD_COMPACT_DELTA", route_id="A1_ONTOLOGY",
            task=task, envelope=envelope,
        )
        calls.append(call)
        base_key = f"{rep}:A1_BASELINE:{item['case_id']}"
        delta_key = f"{rep}:A2_COMPACT_DELTA:{item['case_id']}"
        raw_key = (
            f"{rep}:{SHARED_ARM_ID}:STANDARD_COMPACT_DELTA:"
            f"{item['case_id']}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            raw = envelope.normalized_result
            raw_receipts[raw_key] = raw
            contract_failures = validate_null_role_valued_receipt(
                raw_receipt=raw, item=item, refs=refs
            )
            if contract_failures:
                failures.append({
                    "replication_id": rep,
                    "arm_id": SHARED_ARM_ID,
                    "case_id": item["case_id"],
                    "stage": "STANDARD_COMPACT_DELTA_CONTRACT",
                    "failures": contract_failures,
                    "raw_receipt_hash": hash_payload(raw),
                })
            else:
                standard_valid.extend((base_key, delta_key))
            projection = project_frontier_receipt(
                raw_receipt=raw, item=item, arm_id="A1_ONTOLOGY",
                evidence_refs=refs,
            )
            final_projections[base_key] = projection
            final_projections[delta_key] = projection
            provisional_projections[delta_key] = projection
            trigger_receipts[delta_key] = derive_escalation_receipt(
                raw_receipt=raw, item=item
            )
            qualification_receipts[delta_key] = (
                derive_selective_qualification(
                    raw_receipt=raw,
                    item=item,
                    escalation_receipt=trigger_receipts[delta_key],
                )
            )
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, qualification_receipts, delta_views,
            materialization_receipts,
            candidate_pools, proposed_composition_receipts,
            gate_receipts, composition_receipts,
            standard_valid, counter_valid, failures,
        )
    for key, qualification in sorted(
        qualification_receipts.items()
    ):
        if not qualification["qualified"]:
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
            f"{rep}:{SHARED_ARM_ID}:STANDARD_COMPACT_DELTA:{case_id}"
        ]
        delta_view = build_compact_delta_view(
            raw_receipt=provisional,
            item=item,
            qualification_receipt=qualification,
        )
        delta_views[key] = delta_view
        task = _delta_task(
            item=delta_view, replication_id=rep,
            experimental_arm_id=arm,
            route_id=qualification["route_id"],
            stage="INDEPENDENT_COUNTER_COMPACT_DELTA",
            refs=refs, adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call(
            replication_id=rep, arm_id=arm, case_id=case_id,
            stage="INDEPENDENT_COUNTER_COMPACT_DELTA",
            route_id=qualification["route_id"],
            task=task, envelope=envelope,
        )
        calls.append(call)
        raw_key = (
            f"{rep}:{arm}:INDEPENDENT_COUNTER_COMPACT_DELTA:{case_id}"
        )
        if envelope.status != "COMPLETED":
            failures.append(_provider_failure(call))
        else:
            delta = envelope.normalized_result
            raw_receipts[
                f"{rep}:{arm}:PROVIDER_COMPACT_DELTA:{case_id}"
            ] = delta
            contract_failures = validate_compact_delta(
                delta=delta,
                item=delta_view,
                refs=refs,
            )
            if contract_failures:
                failures.append({
                    "replication_id": rep,
                    "arm_id": arm,
                    "case_id": case_id,
                    "stage": "COUNTER_COMPACT_DELTA_CONTRACT",
                    "failures": contract_failures,
                    "raw_receipt_hash": hash_payload(delta),
                })
            elif key not in standard_valid:
                failures.append({
                    "replication_id": rep,
                    "arm_id": arm,
                    "case_id": case_id,
                    "stage": "COMPOSITION_PRECONDITION",
                    "failures": ["STANDARD_COMPACT_DELTA_INVALID"],
                })
            else:
                counter, materialization = materialize_compact_delta(
                    delta=delta,
                    item=delta_view,
                    refs=refs,
                    route_id=qualification["route_id"],
                )
                raw_receipts[raw_key] = counter
                materialization_receipts[key] = materialization
                counter_valid.append(key)
                pool = build_candidate_pool(
                    provisional_receipt=provisional,
                    counter_receipt=counter,
                    item=item,
                    replication_id=rep,
                )
                candidate_pools[key] = pool
                proposed_raw, proposed_composition = (
                    compose_null_role_valued_pool(
                        pool=pool, provisional_receipt=provisional,
                        item=item, refs=refs,
                    )
                )
                proposed_composition_receipts[key] = (
                    proposed_composition
                )
                raw_receipts[
                    f"{rep}:{arm}:RUNTIME_PROPOSED:{case_id}"
                ] = proposed_raw
                witnesses = derive_cross_replication_witnesses(
                    raw_receipts=raw_receipts,
                    source_replication_id=rep,
                    case_id=case_id,
                    relation_id=next(
                        value["relation_id"]
                        for value in proposed_composition[
                            "scored_candidates"
                        ]
                        if value["source_id"] == "COUNTER"
                    ),
                )
                final_raw, accepted_composition, gate_receipt = (
                    apply_tri_lane_replacement_gate(
                        provisional_receipt=provisional,
                        provisional_projection=(
                            provisional_projections[key]
                        ),
                        proposed_receipt=proposed_raw,
                        composition_receipt=proposed_composition,
                        item=item,
                        cross_replication_witnesses=witnesses,
                    )
                )
                gate_receipts[key] = gate_receipt
                if accepted_composition is not None:
                    composition_receipts[key] = accepted_composition
                final_projections[key] = project_frontier_receipt(
                    raw_receipt=final_raw, item=item,
                    arm_id="A1_ONTOLOGY", evidence_refs=refs,
                )
                raw_receipts[
                    f"{rep}:{arm}:RUNTIME_GATED:{case_id}"
                ] = final_raw
        _checkpoint(
            checkpoint_callback, corpus, preregistration, calls,
            raw_receipts, provisional_projections, final_projections,
            trigger_receipts, qualification_receipts, delta_views,
            materialization_receipts,
            candidate_pools, proposed_composition_receipts,
            gate_receipts, composition_receipts,
            standard_valid, counter_valid, failures,
        )
    commitment = {
        "runtime_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_escalation_policy_version": ESCALATION_POLICY_VERSION,
        "source_qualification_policy_version": (
            QUALIFICATION_POLICY_VERSION
        ),
        "source_delta_contract_version": DELTA_CONTRACT_VERSION,
        "source_composition_contract_version": (
            COMPOSITION_CONTRACT_VERSION
        ),
        "source_replacement_gate_version": REPLACEMENT_GATE_VERSION,
        "source_score_map_hash": hash_payload(SCORE_MAP),
        "source_rank_bonus": list(SOURCE_RANK_BONUS),
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "provisional_projections": provisional_projections,
        "final_projections": final_projections,
        "trigger_receipts": trigger_receipts,
        "qualification_receipts": qualification_receipts,
        "delta_views": delta_views,
        "materialization_receipts": materialization_receipts,
        "candidate_pools": candidate_pools,
        "proposed_composition_receipts": (
            proposed_composition_receipts
        ),
        "replacement_gate_receipts": gate_receipts,
        "composition_receipts": composition_receipts,
        "standard_compact_delta_valid_keys": standard_valid,
        "counter_compact_delta_valid_keys": counter_valid,
        "failures": failures,
        "raw_receipts_preserved_before_projection": True,
        "private_truth_exposed": False,
        "separate_value_provider_call_used": False,
        "provider_sees_numeric_score_map": False,
        "provider_selects_final_candidates": False,
        "truth_state_research_value_separated": True,
        "null_information_role_independent_of_current_truth_state": True,
        "non_null_prospective_role_allowed": True,
        "discriminating_null_discard_forbidden": True,
        "trigger_policy_retuned_from_v0_33": False,
        "qualification_uses_private_truth": False,
        "delta_candidate_limit": 1,
        "compact_semantic_provider_contract_used": True,
        "runtime_materialization_rewrites_semantics": False,
        "replacement_gate_adds_provider_calls": False,
        "replacement_gate_uses_private_truth": False,
        "focal_object_id_public_before_inference": True,
        "cross_replication_witnesses_use_private_truth": False,
        "informative_null_lane_independent_of_effect_lane": True,
        "paired_standard_receipt_shared_between_arms": True,
        "paired_standard_cost_cancels_in_contrast": True,
        "independent_standard_arm_calls_forbidden": True,
        "physical_shared_standard_call_count": sum(
            value["stage"] == "STANDARD_COMPACT_DELTA"
            and value["arm_id"] == SHARED_ARM_ID
            for value in calls
        ),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_paired_receipt_experiment(*, corpus, preregistration, run):
    validate_paired_receipt_holdout(corpus)
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
                totals[(item["case_id"], "A2_COMPACT_DELTA")]["net"]
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
    replacement = _replacement_gate_metrics(run)
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
        "minimum_standard_compact_delta_contract_coverage": (
            runtime["standard_compact_delta_contract_coverage"]
            >= gate["minimum_standard_compact_delta_contract_coverage"]
        ),
        "minimum_counter_compact_delta_contract_coverage": (
            runtime["counter_compact_delta_contract_coverage"]
            >= gate["minimum_counter_compact_delta_contract_coverage"]
        ),
        "minimum_trigger_receipt_coverage": (
            runtime["trigger_receipt_coverage"]
            >= gate["minimum_trigger_receipt_coverage"]
        ),
        "minimum_qualification_receipt_coverage": (
            runtime["qualification_receipt_coverage"]
            >= gate["minimum_qualification_receipt_coverage"]
        ),
        "minimum_trigger_execution_coverage": (
            runtime["trigger_execution_coverage"]
            >= gate["minimum_trigger_execution_coverage"]
        ),
        "minimum_replacement_gate_receipt_coverage": (
            replacement["receipt_coverage"] >= 1.0
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
            relation["A2_COMPACT_DELTA"][
                "mean_pairwise_relation_jaccard"
            ]
            - relation["A1_BASELINE"]["mean_pairwise_relation_jaccard"]
            >= gate["minimum_relation_jaccard_relative_to_baseline"]
        ),
        "minimum_accepted_composition_count": (
            replacement["accepted_count"]
            >= gate["minimum_accepted_composition_count"]
        ),
        "minimum_distinct_acceptance_lanes": (
            replacement["distinct_acceptance_lane_count"]
            >= gate["minimum_distinct_acceptance_lanes"]
        ),
        "minimum_triggered_composition_gross_mean": (
            gross is not None
            and gross["mean"]
            >= gate["minimum_triggered_composition_gross_mean"]
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
        "maximum_mean_delta_token_penalty_cbit": (
            composition["mean_delta_token_penalty_cbit"]
            <= gate["maximum_mean_delta_token_penalty_cbit"]
        ),
        "hard_runaway_total_tokens": (
            total_tokens <= gate["hard_runaway_total_tokens"]
        ),
        "maximum_physical_total_tokens": (
            total_tokens <= gate["maximum_physical_total_tokens"]
        ),
        "required_shared_standard_call_count": (
            run["physical_shared_standard_call_count"]
            == gate["required_shared_standard_call_count"]
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
                for value in run[
                    "proposed_composition_receipts"
                ].values()
            )
        ),
        "replacement_gate_boundary_preserved": (
            run["replacement_gate_adds_provider_calls"] is False
            and run["replacement_gate_uses_private_truth"] is False
            and run["focal_object_id_public_before_inference"] is True
            and run[
                "cross_replication_witnesses_use_private_truth"
            ] is False
            and run[
                "informative_null_lane_independent_of_effect_lane"
            ] is True
            and all(
                value["provider_call_added_by_gate"] is False
                and value["private_truth_used"] is False
                and value["selection_authority"] is False
                for value in run[
                    "replacement_gate_receipts"
                ].values()
            )
        ),
        "paired_common_receipt_boundary_preserved": (
            run["paired_standard_receipt_shared_between_arms"] is True
            and run["paired_standard_cost_cancels_in_contrast"] is True
            and run["independent_standard_arm_calls_forbidden"] is True
            and not any(
                value["stage"] == "STANDARD_COMPACT_DELTA"
                and value["arm_id"] in ARM_IDS
                for value in run["task_calls"]
            )
        ),
        "compact_delta_boundary_preserved": (
            run["truth_state_research_value_separated"] is True
            and run[
                "null_information_role_independent_of_current_truth_state"
            ] is True
            and run["non_null_prospective_role_allowed"] is True
            and run["discriminating_null_discard_forbidden"] is True
            and run["qualification_uses_private_truth"] is False
            and run["delta_candidate_limit"] == 1
            and run["compact_semantic_provider_contract_used"] is True
            and run[
                "runtime_materialization_rewrites_semantics"
            ] is False
            and all(
                value["semantic_fields_copied_without_rewrite"]
                for value in run[
                    "materialization_receipts"
                ].values()
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
        decision = "PASS_PAIRED_COMMON_RECEIPT"
        state = "PAIRED_RECEIPT_PASSED_READY_POSTHOC"
    elif total_tokens > gate["hard_runaway_total_tokens"]:
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "COMPACT_DELTA_RESOURCE_STOP"
    else:
        decision = "REJECT_PAIRED_COMMON_RECEIPT"
        state = "PAIRED_RECEIPT_REJECTED_STOP"
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
        "replacement_gate_metrics": replacement,
        "relation_reproducibility": relation,
        "physical_total_tokens": total_tokens,
        "conditions": conditions,
        "paired_receipt_gate": "PASS" if passed else "REJECT",
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
            "falsifiable candidates. For each candidate, record current "
            "relation_truth_state, prospective null_information_role, and "
            "research_value_disposition as independent axes. The null role "
            "asks what a future null result would rule out or constrain, so "
            "it may be informative even when current evidence is indirect "
            "or weak. If current evidence already supports a null, classify "
            "its information role explicitly. A supported null that rules "
            "out a plausible cause can have positive Cbit and must not be "
            "discarded merely because the effect is absent. Also record "
            "counterevidence handling, constraint binding, falsifiability, "
            "expected Cbit, and evidence spans. "
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
        expected_schema=null_role_valued_exact_three_schema(
            item=item, arm_id="A1_ONTOLOGY", refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _delta_task(
    *, item, replication_id, experimental_arm_id, route_id,
    stage, refs, adapter
):
    prompts = {
        "MECHANISM": (
            "Find one mechanism relation that adds the most information."
        ),
        "ADVERSARIAL": (
            "Find one counterexample or discriminating relation with the "
            "highest expected information gain."
        ),
        "COORDINATE_SHIFT": (
            "Find one relation from a different focal object or coordinate."
        ),
    }
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{stage}-"
            f"{experimental_arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{prompts[route_id]} Return one compact semantic delta whose "
            "source_object_id and target_object_id pair is not listed in "
            "excluded_relations. Use only the supplied evidence subset. "
            "Record current "
            "relation_truth_state, prospective null_information_role, "
            "research_value_disposition, counterevidence handling, "
            "constraint binding, falsifiability, expected Cbit, and bound "
            "evidence spans. Runtime will materialize fixed IDs, lineage, "
            "FRONTIER/SPECULATIVE state, and duplicate evidence/rationale "
            "fields without semantic rewriting. Do not reconstruct the base "
            "candidate set or an object census. The numeric Runtime score "
            "map and private outcomes are unavailable."
        ),
        inputs={
            "stage": stage,
            "replication_id": replication_id,
            "route_id": route_id,
            "receipt_arm_id": "A1_ONTOLOGY",
            "delta_case": item,
            "excluded_relations": item["excluded_relations"],
            "maximum_candidate_count": 1,
            "numeric_score_map_available": False,
            "private_outcome_available": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=compact_delta_schema(item=item, refs=refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _scoring_run(run, *, replication_id, provisional=False):
    calls, projections = [], {}
    case_ids = sorted({
        value["case_id"]
        for value in run["task_calls"]
        if value["replication_id"] == replication_id
        and value["stage"] == "STANDARD_COMPACT_DELTA"
    })
    for case_id in case_ids:
        for arm in ARM_IDS:
            base = _find_call(
                run, replication_id=replication_id,
                arm_id=SHARED_ARM_ID,
                case_id=case_id, stage="STANDARD_COMPACT_DELTA",
            )
            path = [base] if base is not None else []
            if arm == "A2_COMPACT_DELTA" and not provisional:
                counter = _find_call(
                    run, replication_id=replication_id, arm_id=arm,
                    case_id=case_id,
                    stage="INDEPENDENT_COUNTER_COMPACT_DELTA",
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
                if arm == "A2_COMPACT_DELTA" and provisional
                else run["final_projections"].get(key)
            )
            if projection is not None:
                projections[f"{arm}:{case_id}"] = projection
    commitment = {"task_calls": calls, "projections": projections}
    return {**commitment, "run_hash": hash_payload(commitment)}


def _runtime_metrics(run, corpus):
    expected = corpus["case_count"] * len(REPLICATION_IDS)
    shared_values = [
        value for value in run["task_calls"]
        if value["stage"] == "STANDARD_COMPACT_DELTA"
        and value["arm_id"] == SHARED_ARM_ID
    ]
    completion = {
        "SHARED_STANDARD": round(
            sum(value["status"] == "COMPLETED"
                for value in shared_values) / expected,
            6,
        )
    }
    qualified = {
        key for key, value in run["qualification_receipts"].items()
        if value["qualified"]
    }
    counter_calls = [
        value for value in run["task_calls"]
        if value["stage"] == "INDEPENDENT_COUNTER_COMPACT_DELTA"
    ]
    if qualified:
        completion["INDEPENDENT_COUNTER_COMPACT_DELTA"] = round(
            sum(value["status"] == "COMPLETED" for value in counter_calls)
            / len(qualified), 6
        )
        counter_contract = round(
            len(run["counter_compact_delta_valid_keys"])
            / len(qualified), 6
        )
        execution = round(
            len(run["replacement_gate_receipts"]) / len(qualified), 6
        )
    else:
        completion["INDEPENDENT_COUNTER_COMPACT_DELTA"] = 1.0
        counter_contract, execution = 0.0, 1.0
    identity = 0
    for rep in REPLICATION_IDS:
        for item in corpus["public_surface"]["items"]:
            left = run["final_projections"].get(
                f"{rep}:A1_BASELINE:{item['case_id']}"
            )
            right = run["provisional_projections"].get(
                f"{rep}:A2_COMPACT_DELTA:{item['case_id']}"
            )
            identity += bool(
                left and right
                and left["artifact_hash"] == right["artifact_hash"]
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
        "physical_shared_standard_call_count": len(shared_values),
        "standard_compact_delta_contract_coverage": round(
            len(run["standard_compact_delta_valid_keys"])
            / (expected * len(ARM_IDS)), 6
        ),
        "counter_compact_delta_contract_coverage": counter_contract,
        "trigger_receipt_coverage": round(
            len(run["trigger_receipts"]) / expected, 6
        ),
        "qualification_receipt_coverage": round(
            len(run["qualification_receipts"]) / expected, 6
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
            key = f"{rep}:A2_COMPACT_DELTA:{case}"
            trigger = run["trigger_receipts"].get(key)
            qualification = run["qualification_receipts"].get(key)
            if trigger is None or qualification is None:
                continue
            routes[qualification["route_id"]] += 1
            for flag in trigger["diagnostic_flags"]:
                flags[flag] += 1
            composition = run["composition_receipts"].get(key)
            if not qualification["qualified"] or composition is None:
                continue
            gross_uplifts.append(
                after[(case, "A2_COMPACT_DELTA")]["gross"]
                - before[(case, "A2_COMPACT_DELTA")]["gross"]
            )
            net_uplifts.append(
                after[(case, "A2_COMPACT_DELTA")]["net"]
                - before[(case, "A2_COMPACT_DELTA")]["net"]
            )
            token_penalties.append(
                after[(case, "A2_COMPACT_DELTA")]["token_cost"]
                - before[(case, "A2_COMPACT_DELTA")]["token_cost"]
            )
            for lineage in composition["lineage"]:
                sources[lineage["source_id"]] += 1
            for scored in composition["scored_candidates"]:
                value = scored["provider_candidate_value"]
                for axis in SCORE_MAP:
                    axes[f"{axis}:{value[axis]}"] += 1
    raw_triggered = sum(
        value["triggered"] for value in run["trigger_receipts"].values()
    )
    qualified = sum(
        value["qualified"]
        for value in run["qualification_receipts"].values()
    )
    selected_total = sum(sources.values())
    return {
        "raw_trigger_count": raw_triggered,
        "qualified_count": qualified,
        "trigger_count": qualified,
        "trigger_rate": round(
            qualified / len(run["qualification_receipts"])
            if run["qualification_receipts"] else 0.0, 6
        ),
        "valid_composition_count": len(run["composition_receipts"]),
        "route_distribution": dict(routes),
        "diagnostic_flag_distribution": dict(flags),
        "selected_source_distribution": dict(sources),
        "counterproposal_adoption_rate": round(
            sources["COUNTER"] / selected_total if selected_total else 0.0,
            6,
        ),
        "compact_delta_axis_distribution": dict(axes),
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
        "mean_delta_token_penalty_cbit": round(
            sum(token_penalties) / len(token_penalties)
            if token_penalties else 0.0, 6
        ),
    }


def _replacement_gate_metrics(run):
    receipts = run["replacement_gate_receipts"]
    valid_counter_count = len(
        run["counter_compact_delta_valid_keys"]
    )
    reasons = Counter(
        value["reason"] for value in receipts.values()
    )
    lanes = Counter(
        value["lane"] for value in receipts.values()
        if value["accepted"]
    )
    accepted = sum(value["accepted"] for value in receipts.values())
    return {
        "valid_counter_count": valid_counter_count,
        "receipt_count": len(receipts),
        "receipt_coverage": round(
            len(receipts) / valid_counter_count
            if valid_counter_count else 1.0, 6
        ),
        "accepted_count": accepted,
        "rejected_count": len(receipts) - accepted,
        "acceptance_rate": round(
            accepted / len(receipts) if receipts else 0.0, 6
        ),
        "reason_distribution": dict(reasons),
        "accepted_lane_distribution": dict(lanes),
        "distinct_acceptance_lane_count": len(lanes),
        "private_truth_use_count": sum(
            value["private_truth_used"] for value in receipts.values()
        ),
        "provider_call_added_count": sum(
            value["provider_call_added_by_gate"]
            for value in receipts.values()
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
        raise ValueError("paired_receipt_preregistration_invalid")


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
        raise ValueError("paired_receipt_run_invalid")


def _checkpoint(
    callback, corpus, preregistration, calls, raw_receipts,
    provisional_projections, final_projections, trigger_receipts,
    qualification_receipts, delta_views, materialization_receipts,
    candidate_pools, proposed_composition_receipts,
    gate_receipts, composition_receipts, standard_valid,
    counter_valid, failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "paired_receipt_progress_v0_45",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "completed_task_count": len(calls),
        "task_calls": list(calls),
        "raw_receipts": dict(raw_receipts),
        "provisional_projections": dict(provisional_projections),
        "final_projections": dict(final_projections),
        "trigger_receipts": dict(trigger_receipts),
        "qualification_receipts": dict(qualification_receipts),
        "delta_views": dict(delta_views),
        "materialization_receipts": dict(
            materialization_receipts
        ),
        "candidate_pools": dict(candidate_pools),
        "proposed_composition_receipts": dict(
            proposed_composition_receipts
        ),
        "replacement_gate_receipts": dict(gate_receipts),
        "composition_receipts": dict(composition_receipts),
        "standard_compact_delta_valid_keys": list(standard_valid),
        "counter_compact_delta_valid_keys": list(counter_valid),
        "failures": list(failures),
        "original_receipts_preserved": True,
        "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})

