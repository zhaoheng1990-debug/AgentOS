"""Selective rejection challenge experiment v0.52."""

from __future__ import annotations

import copy
import math

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .frontier_experiment import TASK_KIND
from .frontier_partial_admission import project_frontier_receipt
from .independent_arbitration_experiment import _replication_surface
from .lineage_displacement_contract import derive_current_stage_witnesses
from .lineage_revision_experiment import _call, _provider_failure
from .provider_telemetry import hash_payload
from .reference_completeness_audit import (
    AUDIT_VERSION as REFERENCE_AUDIT_VERSION,
    validate_reference_completeness_audit,
)
from .reference_complete_portfolio_experiment import (
    analyze_reference_complete_portfolio_experiment,
    run_reference_complete_portfolio_experiment,
)
from .selective_rejection_contract import (
    CONTRACT_VERSION,
    GATE_VERSION,
    apply_selective_rejection_gate,
    build_rejection_challenge_view,
    build_rejection_coordination_view,
    rejection_challenge_schema,
    rejection_coordination_schema,
    validate_rejection_challenge,
    validate_rejection_coordination,
)
from .selective_rejection_holdout import (
    REPLICATION_IDS,
    validate_selective_rejection_holdout,
)
from .selective_delta_policy import (
    POLICY_VERSION as LEGACY_QUALIFICATION_POLICY_VERSION,
)


RUNTIME_VERSION = "selective_rejection_experiment_v0_52"


def build_selective_rejection_preregistration(
    *,
    corpus,
    reference_audit,
    prior_preregistration,
    prior_analysis,
    prior_closure,
    prior_posthoc,
):
    validate_selective_rejection_holdout(corpus)
    validate_reference_completeness_audit(
        audit=reference_audit, corpus=corpus
    )
    for value in (
        prior_preregistration,
        prior_analysis,
        prior_closure,
        prior_posthoc,
    ):
        _validate_artifact_hash(value)
    if (
        reference_audit.get("audit_version") != REFERENCE_AUDIT_VERSION
        or reference_audit.get("reference_complete") is not True
        or reference_audit.get("valid_receipt_count") != 16
        or reference_audit.get("required_receipt_count") != 16
        or reference_audit.get("contract_failures")
        or reference_audit.get("reference_mismatches")
        or reference_audit.get("cross_role_disagreements")
        or prior_analysis.get("decision")
        != "REJECT_REFERENCE_COMPLETE_PORTFOLIO_REPLICATION"
        or prior_analysis.get("candidate_state")
        != "REFERENCE_COMPLETE_PORTFOLIO_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "REFERENCE_COMPLETE_PORTFOLIO_REJECTED_STOP"
        or prior_analysis.get("replacement_gate_metrics", {}).get(
            "accepted_count"
        ) != 4
        or prior_analysis.get("composition_metrics", {}).get(
            "triggered_composition_gross_uplift", {}
        ).get("mean") != 1.5
        or prior_analysis.get("composition_metrics", {}).get(
            "triggered_composition_gross_uplift", {}
        ).get("win_rate") != 1.0
        or prior_posthoc.get("formal_decision_unchanged") is not True
        or prior_posthoc.get(
            "mean_fraction_of_positive_oracle_uplift_captured"
        ) != 0.5
        or prior_posthoc.get("positive_oracle_cell_count") != 8
        or prior_posthoc.get("classification_distribution") != {
            "BENEFICIAL_ACCEPTED": 4,
            "BENEFICIAL_REJECTED": 4,
        }
    ):
        raise ValueError("selective_rejection_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    success_gate = copy.deepcopy(
        prior_preregistration["success_gate"]
    )
    success_gate.update({
        "minimum_counter_compact_delta_contract_coverage": 0.9,
        "minimum_lineage_contract_coverage": 1.0,
        "minimum_opportunity_constrained_delta_coverage": 0.9,
        "minimum_accepted_composition_count": 5,
        "minimum_distinct_acceptance_lanes": 2,
        "minimum_triggered_composition_gross_mean": 0.5,
        "minimum_triggered_composition_gross_median": 0.5,
        "minimum_triggered_composition_gross_win_rate": 1.0,
        "maximum_triggered_composition_gross_loss_rate": 0.0,
        "minimum_rejection_challenge_count": 2,
        "minimum_rejection_challenge_coverage": 0.95,
        "minimum_coordination_coverage": 0.95,
        "minimum_coordinated_activation_count": 1,
        "maximum_direct_challenge_activation_count": 0,
        "maximum_physical_total_tokens": math.ceil(prior_total * 1.25),
        "hard_runaway_total_tokens": math.ceil(prior_total * 1.5),
        "required_shared_standard_call_count": (
            corpus["case_count"] * len(REPLICATION_IDS)
        ),
    })
    cost_policy = copy.deepcopy(
        prior_preregistration["cost_policy"]
    )
    cost_policy.update({
        "selective_rejection_challenge_adds_provider_tokens": True,
        "coordination_call_only_after_reopen": True,
        "soft_expected_total_tokens": math.ceil(prior_total * 1.25),
        "hard_runaway_total_tokens": math.ceil(prior_total * 1.5),
    })
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_reference_audit_version": REFERENCE_AUDIT_VERSION,
        "reference_audit_claim_ceiling": (
            "INTERNAL_PROVIDER_AUDITED_SYNTHETIC_ONLY"
        ),
        "source_prior_preregistration_hash": prior_preregistration[
            "artifact_hash"
        ],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_selective_rejection_contract_version": CONTRACT_VERSION,
        "source_selective_rejection_gate_version": GATE_VERSION,
        "source_qualification_policy_version": (
            LEGACY_QUALIFICATION_POLICY_VERSION
        ),
        "frozen_hypothesis": (
            "On a fresh reference-complete holdout with relation-state "
            "positions rotated across cases, a selective rejection "
            "challenger can detect when the initial arbiter overvalues "
            "untested novelty or discounts evidence-backed resolution. A "
            "separate coordinator may recover beneficial rejected deltas "
            "without lowering accepted-cell gross precision."
        ),
        "replication_ids": list(REPLICATION_IDS),
        "primary_contrast": "A2_COMPACT_DELTA_MINUS_A1_BASELINE",
        "success_gate": success_gate,
        "cost_policy": cost_policy,
        "fresh_relation_state_positions_rotated": True,
        "initial_acceptance_path_unchanged": True,
        "challenge_only_after_initial_rejection": True,
        "challenge_cannot_activate_directly": True,
        "coordination_required_after_reopen": True,
        "kernel_retains_final_gate_authority": True,
        "source_qualified_pool_ids_required": True,
        "dual_role_reference_audit_required": True,
        "reference_audit_not_external_gold": True,
        "private_truth_available_during_inference": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_selective_rejection_experiment(
    *,
    corpus,
    preregistration,
    adapter,
    base_checkpoint_callback=None,
    overlay_checkpoint_callback=None,
    holdout_validator=None,
    qualification_deriver=None,
    qualification_policy_version=None,
    runtime_version=RUNTIME_VERSION,
):
    validator = holdout_validator or validate_selective_rejection_holdout
    validator(corpus)
    _validate_preregistration(preregistration, corpus)
    base_run = run_reference_complete_portfolio_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        checkpoint_callback=base_checkpoint_callback,
        holdout_validator=validator,
        qualification_deriver=qualification_deriver,
        qualification_policy_version=(
            qualification_policy_version
            or preregistration.get(
                "source_qualification_policy_version",
                LEGACY_QUALIFICATION_POLICY_VERSION,
            )
        ),
    )
    refs = tuple(corpus["evidence_refs"])
    calls = list(base_run["task_calls"])
    raw_receipts = copy.deepcopy(base_run["raw_receipts"])
    final_projections = copy.deepcopy(base_run["final_projections"])
    gate_receipts = copy.deepcopy(
        base_run["replacement_gate_receipts"]
    )
    composition_receipts = copy.deepcopy(
        base_run["composition_receipts"]
    )
    failures = copy.deepcopy(base_run["failures"])
    challenge_views, challenge_receipts = {}, {}
    coordination_views, coordination_receipts = {}, {}
    challenge_valid, coordination_valid = [], []
    for key in sorted(base_run["pairwise_displacement_valid_keys"]):
        rep, arm, case_id = key.split(":", 2)
        initial = base_run["pairwise_displacement_receipts"][key]
        challenge = None
        coordination = None
        if initial["portfolio_decision"] != "ACTIVATE_DELTA":
            challenge_view = build_rejection_challenge_view(
                portfolio_view=base_run[
                    "pairwise_displacement_views"
                ][key],
                initial_receipt=initial,
            )
            challenge_views[key] = challenge_view
            task = _challenge_task(
                item=challenge_view,
                replication_id=rep,
                arm_id=arm,
                refs=refs,
                adapter=adapter,
                runtime_version=runtime_version,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = _call(
                replication_id=rep,
                arm_id=arm,
                case_id=case_id,
                stage="REJECTION_CHALLENGE",
                route_id="REJECTION_CHALLENGER",
                task=task,
                envelope=envelope,
            )
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append(_provider_failure(call))
            else:
                challenge = envelope.normalized_result
                raw_receipts[
                    f"{rep}:{arm}:REJECTION_CHALLENGE:{case_id}"
                ] = challenge
                contract_failures = validate_rejection_challenge(
                    receipt=challenge,
                    item=challenge_view,
                    refs=refs,
                )
                if contract_failures:
                    failures.append({
                        "replication_id": rep,
                        "arm_id": arm,
                        "case_id": case_id,
                        "stage": "REJECTION_CHALLENGE_CONTRACT",
                        "failures": contract_failures,
                        "raw_receipt_hash": hash_payload(challenge),
                    })
                    challenge = None
                else:
                    challenge_receipts[key] = challenge
                    challenge_valid.append(key)
        if challenge and challenge["challenge_decision"] == "REOPEN_DELTA":
            coordination_view = build_rejection_coordination_view(
                challenge_view=challenge_views[key],
                challenge_receipt=challenge,
            )
            coordination_views[key] = coordination_view
            task = _coordination_task(
                item=coordination_view,
                replication_id=rep,
                arm_id=arm,
                refs=refs,
                adapter=adapter,
                runtime_version=runtime_version,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            call = _call(
                replication_id=rep,
                arm_id=arm,
                case_id=case_id,
                stage="REJECTION_COORDINATION",
                route_id="REJECTION_COORDINATOR",
                task=task,
                envelope=envelope,
            )
            calls.append(call)
            if envelope.status != "COMPLETED":
                failures.append(_provider_failure(call))
            else:
                coordination = envelope.normalized_result
                raw_receipts[
                    f"{rep}:{arm}:REJECTION_COORDINATION:{case_id}"
                ] = coordination
                contract_failures = validate_rejection_coordination(
                    receipt=coordination,
                    item=coordination_view,
                    refs=refs,
                )
                if contract_failures:
                    failures.append({
                        "replication_id": rep,
                        "arm_id": arm,
                        "case_id": case_id,
                        "stage": "REJECTION_COORDINATION_CONTRACT",
                        "failures": contract_failures,
                        "raw_receipt_hash": hash_payload(coordination),
                    })
                    coordination = None
                else:
                    coordination_receipts[key] = coordination
                    coordination_valid.append(key)
        provisional = raw_receipts[
            f"{rep}:SHARED_STANDARD:STANDARD_OPPORTUNITY:{case_id}"
        ]
        proposed = raw_receipts[
            f"{rep}:{arm}:RUNTIME_PROPOSED:{case_id}"
        ]
        composition = base_run[
            "proposed_composition_receipts"
        ][key]
        lineage_delta = raw_receipts[
            f"{rep}:{arm}:PROVIDER_COMPACT_DELTA:{case_id}"
        ]
        counter_relation = next(
            value["relation_id"]
            for value in composition["scored_candidates"]
            if value["source_id"] == "COUNTER"
        )
        witnesses = derive_current_stage_witnesses(
            raw_receipts=raw_receipts,
            source_replication_id=rep,
            case_id=case_id,
            relation_id=counter_relation,
            standard_stage="STANDARD_OPPORTUNITY",
        )
        final_raw, accepted_composition, gate = (
            apply_selective_rejection_gate(
                provisional_receipt=provisional,
                proposed_receipt=proposed,
                composition_receipt=composition,
                portfolio_view=base_run[
                    "pairwise_displacement_views"
                ][key],
                lineage_delta=lineage_delta,
                cross_replication_witnesses=witnesses,
                initial_receipt=initial,
                challenge_receipt=challenge,
                coordination_receipt=coordination,
            )
        )
        gate_receipts[key] = gate
        composition_receipts.pop(key, None)
        if accepted_composition is not None:
            composition_receipts[key] = accepted_composition
        canonical = next(
            value for value in corpus["public_surface"]["items"]
            if value["case_id"] == case_id
        )
        item = _replication_surface(
            canonical,
            replication_id=rep,
            corpus_hash=corpus["artifact_hash"],
        )
        final_projections[key] = project_frontier_receipt(
            raw_receipt=final_raw,
            item=item,
            arm_id="A1_ONTOLOGY",
            evidence_refs=refs,
        )
        raw_receipts[
            f"{rep}:{arm}:RUNTIME_GATED:{case_id}"
        ] = final_raw
        _overlay_checkpoint(
            overlay_checkpoint_callback,
            corpus=corpus,
            preregistration=preregistration,
            base_run=base_run,
            calls=calls,
            challenge_views=challenge_views,
            challenge_receipts=challenge_receipts,
            coordination_views=coordination_views,
            coordination_receipts=coordination_receipts,
            failures=failures,
        )
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base_run.items()
        if key != "run_hash"
    }
    commitment.update({
        "runtime_version": runtime_version,
        "source_base_run_hash": base_run["run_hash"],
        "source_selective_rejection_contract_version": CONTRACT_VERSION,
        "source_selective_rejection_gate_version": GATE_VERSION,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "final_projections": final_projections,
        "replacement_gate_receipts": gate_receipts,
        "composition_receipts": composition_receipts,
        "failures": failures,
        "rejection_challenge_views": challenge_views,
        "rejection_challenge_receipts": challenge_receipts,
        "rejection_challenge_valid_keys": challenge_valid,
        "rejection_coordination_views": coordination_views,
        "rejection_coordination_receipts": coordination_receipts,
        "rejection_coordination_valid_keys": coordination_valid,
        "initial_acceptance_path_unchanged": True,
        "challenge_only_after_initial_rejection": True,
        "challenge_cannot_activate_directly": True,
        "coordination_required_after_reopen": True,
        "selective_rejection_adds_provider_calls": True,
        "private_truth_used_by_selective_roles": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_selective_rejection_experiment(
    *,
    corpus,
    preregistration,
    run,
    holdout_validator=None,
    runtime_version=RUNTIME_VERSION,
):
    validator = holdout_validator or validate_selective_rejection_holdout
    validator(corpus)
    _validate_preregistration(preregistration, corpus)
    base = analyze_reference_complete_portfolio_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
        holdout_validator=validator,
    )
    selective = _selective_metrics(run)
    gate = preregistration["success_gate"]
    selective_conditions = {
        "minimum_rejection_challenge_count": (
            selective["eligible_rejection_count"]
            >= gate["minimum_rejection_challenge_count"]
        ),
        "minimum_rejection_challenge_coverage": (
            selective["challenge_contract_coverage"]
            >= gate["minimum_rejection_challenge_coverage"]
        ),
        "minimum_coordination_coverage": (
            selective["coordination_contract_coverage"]
            >= gate["minimum_coordination_coverage"]
        ),
        "minimum_coordinated_activation_count": (
            selective["coordinated_activation_count"]
            >= gate["minimum_coordinated_activation_count"]
        ),
        "maximum_direct_challenge_activation_count": (
            selective["direct_challenge_activation_count"]
            <= gate["maximum_direct_challenge_activation_count"]
        ),
        "selective_authority_boundary_preserved": (
            run["challenge_only_after_initial_rejection"] is True
            and run["challenge_cannot_activate_directly"] is True
            and run["coordination_required_after_reopen"] is True
            and run["private_truth_used_by_selective_roles"] is False
            and all(
                value["private_truth_used"] is False
                and value["selection_authority"] is False
                for value in run["replacement_gate_receipts"].values()
            )
        ),
    }
    conditions = {**base["conditions"], **selective_conditions}
    passed = all(conditions.values())
    if passed:
        decision = "PASS_SELECTIVE_REJECTION_REPLICATION"
        state = "SELECTIVE_REJECTION_REPLICATED_READY_POSTHOC"
    elif (
        base["physical_total_tokens"]
        > gate["hard_runaway_total_tokens"]
    ):
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "SELECTIVE_REJECTION_RESOURCE_STOP"
    else:
        decision = "REJECT_SELECTIVE_REJECTION_REPLICATION"
        state = "SELECTIVE_REJECTION_REJECTED_STOP"
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base.items()
        if key != "artifact_hash"
    }
    commitment.update({
        "analysis_version": runtime_version,
        "source_run_hash": run["run_hash"],
        "source_base_run_hash": run["source_base_run_hash"],
        "selective_rejection_metrics": selective,
        "conditions": conditions,
        "selective_rejection_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _challenge_task(
    *, item, replication_id, arm_id, refs, adapter, runtime_version
):
    stage = "REJECTION_CHALLENGE"
    return ProviderCognitiveTask(
        task_id=(
            f"{runtime_version}-{replication_id}-{stage}-"
            f"{arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Act as an independent rejection challenger. Audit whether the "
            "initial arbiter overvalued an untested novel hypothesis, "
            "discounted evidence-backed resolution, or gave a truth-state "
            "category categorical priority. Compare base and delta only by "
            "evidence-bound marginal hypothesis-space reduction relative "
            "to the fixed companions. Novelty is not information gain "
            "without evidence or a discriminating test. A supported null "
            "may be less redundant than an unresolved positive hypothesis. "
            "Return REOPEN_DELTA only when the delta has higher "
            "evidence-bound marginal Cbit. You cannot activate either "
            "candidate; reopening only requests independent coordination. "
            "Echo exact source-qualified pool IDs."
        ),
        inputs={
            "stage": stage,
            "replication_id": replication_id,
            "challenge_case": item,
            "numeric_score_map_available": False,
            "private_outcome_available": False,
            "activation_authority": False,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=rejection_challenge_schema(
            item=item, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _coordination_task(
    *, item, replication_id, arm_id, refs, adapter, runtime_version
):
    stage = "REJECTION_COORDINATION"
    return ProviderCognitiveTask(
        task_id=(
            f"{runtime_version}-{replication_id}-{stage}-"
            f"{arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            "Act as an independent coordinator between the initial arbiter "
            "and rejection challenger. Resolve their evidence conflict "
            "without majority voting. Re-evaluate marginal information "
            "gain, evidence resolution, redundancy against fixed "
            "companions, constraint binding, and falsifiability. Do not use "
            "novelty alone as value and do not prioritize positive effects "
            "over informative nulls by category. ACTIVATE_DELTA only when "
            "the evidence establishes higher marginal Cbit; otherwise keep "
            "the base or return unresolved. Runtime retains final authority. "
            "Echo exact source-qualified pool IDs."
        ),
        inputs={
            "stage": stage,
            "replication_id": replication_id,
            "coordination_case": item,
            "numeric_score_map_available": False,
            "private_outcome_available": False,
            "final_runtime_authority": True,
            "provider_output_state": "CANDIDATE_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=rejection_coordination_schema(
            item=item, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _selective_metrics(run):
    initial = run["pairwise_displacement_receipts"]
    eligible = {
        key for key, value in initial.items()
        if value["portfolio_decision"] != "ACTIVATE_DELTA"
    }
    valid_challenges = set(run["rejection_challenge_valid_keys"])
    reopen = {
        key
        for key, value in run["rejection_challenge_receipts"].items()
        if value["challenge_decision"] == "REOPEN_DELTA"
    }
    valid_coordination = set(run["rejection_coordination_valid_keys"])
    coordinated = {
        key
        for key, value in run["replacement_gate_receipts"].items()
        if value.get("coordinator_approved") is True
        and value.get("accepted") is True
    }
    return {
        "eligible_rejection_count": len(eligible),
        "challenge_call_count": sum(
            value["stage"] == "REJECTION_CHALLENGE"
            for value in run["task_calls"]
        ),
        "challenge_valid_count": len(valid_challenges),
        "challenge_contract_coverage": round(
            len(valid_challenges) / len(eligible) if eligible else 1.0,
            6,
        ),
        "reopen_count": len(reopen),
        "coordination_call_count": sum(
            value["stage"] == "REJECTION_COORDINATION"
            for value in run["task_calls"]
        ),
        "coordination_valid_count": len(valid_coordination),
        "coordination_contract_coverage": round(
            len(valid_coordination) / len(reopen) if reopen else 1.0,
            6,
        ),
        "coordinated_activation_count": len(coordinated),
        "direct_challenge_activation_count": 0,
        "rejection_recovery_rate": round(
            len(coordinated) / len(eligible) if eligible else 0.0,
            6,
        ),
    }


def _validate_artifact_hash(value):
    commitment = {
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("selective_rejection_source_hash_invalid")


def _validate_preregistration(preregistration, corpus):
    _validate_artifact_hash(preregistration)
    if preregistration.get("source_corpus_hash") != corpus["artifact_hash"]:
        raise ValueError("selective_rejection_preregistration_invalid")


def _overlay_checkpoint(
    callback,
    *,
    corpus,
    preregistration,
    base_run,
    calls,
    challenge_views,
    challenge_receipts,
    coordination_views,
    coordination_receipts,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "selective_rejection_progress_v0_52",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_base_run_hash": base_run["run_hash"],
        "completed_task_count": len(calls),
        "rejection_challenge_views": copy.deepcopy(challenge_views),
        "rejection_challenge_receipts": copy.deepcopy(
            challenge_receipts
        ),
        "rejection_coordination_views": copy.deepcopy(
            coordination_views
        ),
        "rejection_coordination_receipts": copy.deepcopy(
            coordination_receipts
        ),
        "failures": copy.deepcopy(failures),
        "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})
