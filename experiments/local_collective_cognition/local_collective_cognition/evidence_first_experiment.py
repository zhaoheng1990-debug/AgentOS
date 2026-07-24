"""Decision-blind evidence-first arbitration experiment v0.54."""

from __future__ import annotations

import copy
import math
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .context_qualification_policy import (
    POLICY_VERSION as QUALIFICATION_POLICY_VERSION,
    derive_context_qualification,
)
from .evidence_first_contract import (
    AUDIT_ROLES,
    CONTRACT_VERSION,
    GATE_VERSION,
    apply_evidence_first_gate,
    blind_evidence_schema,
    build_blind_evidence_view,
    validate_blind_evidence_receipt,
)
from .evidence_first_holdout import (
    REPLICATION_IDS,
    validate_evidence_first_holdout,
)
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


RUNTIME_VERSION = "evidence_first_arbitration_experiment_v0_54"


def build_evidence_first_preregistration(
    *,
    corpus,
    reference_audit,
    calibration,
    prior_preregistration,
    prior_analysis,
    prior_closure,
    prior_posthoc,
):
    validate_evidence_first_holdout(corpus)
    validate_reference_completeness_audit(
        audit=reference_audit, corpus=corpus
    )
    for value in (
        calibration,
        prior_preregistration,
        prior_analysis,
        prior_closure,
        prior_posthoc,
    ):
        _validate_artifact_hash(value)
    if (
        reference_audit.get("audit_version") != REFERENCE_AUDIT_VERSION
        or reference_audit.get("reference_complete") is not True
        or reference_audit.get("contract_failures")
        or reference_audit.get("reference_mismatches")
        or reference_audit.get("cross_role_disagreements")
        or calibration.get("private_outcomes_accessed") is not False
        or calibration.get("posthoc_labels_accessed") is not False
        or prior_analysis.get("decision")
        != "REJECT_CONTEXT_QUALIFICATION_REPLICATION"
        or prior_analysis.get("candidate_state")
        != "CONTEXT_QUALIFICATION_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "CONTEXT_QUALIFICATION_REJECTED_STOP"
        or prior_analysis.get("context_qualification_metrics", {}).get(
            "qualified_count"
        ) != 19
        or prior_analysis.get("replacement_gate_metrics", {}).get(
            "accepted_count"
        ) != 7
        or prior_analysis.get("composition_metrics", {}).get(
            "triggered_composition_gross_uplift", {}
        ).get("mean") != 2.0
        or prior_posthoc.get("classification_distribution") != {
            "BENEFICIAL_ACCEPTED": 7,
            "BENEFICIAL_REJECTED": 7,
            "TIE_REJECTED": 3,
        }
        or prior_posthoc.get(
            "coordinated_recovery_beneficial_count"
        ) != 4
        or prior_posthoc.get("coordinated_recovery_harmful_count") != 0
    ):
        raise ValueError("evidence_first_prior_invalid")
    prior_total = int(prior_analysis["physical_total_tokens"])
    success_gate = copy.deepcopy(
        prior_preregistration["success_gate"]
    )
    success_gate.update({
        "minimum_context_qualified_count": 8,
        "maximum_context_qualified_count": 22,
        "minimum_context_qualification_rate": 0.3,
        "maximum_context_qualification_rate": 0.92,
        "minimum_structural_gap_qualified_count": 4,
        "minimum_context_policy_coverage": 1.0,
        "minimum_blind_eligible_rejection_count": 4,
        "minimum_blind_role_contract_coverage": 1.0,
        "minimum_blind_consensus_activation_count": 2,
        "maximum_blind_direct_activation_count": 0,
        "minimum_accepted_composition_count": 8,
        "minimum_triggered_composition_gross_mean": 0.5,
        "minimum_triggered_composition_gross_median": 0.5,
        "minimum_triggered_composition_gross_win_rate": 1.0,
        "maximum_triggered_composition_gross_loss_rate": 0.0,
        "maximum_physical_total_tokens": math.ceil(prior_total * 1.4),
        "hard_runaway_total_tokens": math.ceil(prior_total * 1.7),
        "required_shared_standard_call_count": (
            corpus["case_count"] * len(REPLICATION_IDS)
        ),
    })
    cost_policy = copy.deepcopy(
        prior_preregistration["cost_policy"]
    )
    cost_policy.update({
        "blind_evidence_roles_add_provider_tokens": True,
        "two_blind_roles_per_initial_rejection": True,
        "soft_expected_total_tokens": math.ceil(prior_total * 1.4),
        "hard_runaway_total_tokens": math.ceil(prior_total * 1.7),
    })
    commitment = {
        "preregistration_version": RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": reference_audit["artifact_hash"],
        "source_reference_audit_version": REFERENCE_AUDIT_VERSION,
        "reference_audit_claim_ceiling": (
            "INTERNAL_PROVIDER_AUDITED_SYNTHETIC_ONLY"
        ),
        "source_unlabeled_calibration_hash": calibration[
            "artifact_hash"
        ],
        "source_prior_preregistration_hash": prior_preregistration[
            "artifact_hash"
        ],
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_qualification_policy_version": (
            QUALIFICATION_POLICY_VERSION
        ),
        "source_evidence_first_contract_version": CONTRACT_VERSION,
        "source_evidence_first_gate_version": GATE_VERSION,
        "frozen_hypothesis": (
            "Two isolated decision-blind evidence roles that separately "
            "account for realized evidence Cbit and future test option value "
            "will reduce arbitration false negatives caused by anchoring on "
            "the initial decision. Requiring role consensus should preserve "
            "zero harmful acceptance."
        ),
        "success_gate": success_gate,
        "cost_policy": cost_policy,
        "qualification_policy_frozen_from_v0_53": True,
        "effect_lane_witness_policy_changed": False,
        "initial_decision_hidden_from_blind_roles": True,
        "initial_rationale_hidden_from_blind_roles": True,
        "blind_roles_cannot_activate_directly": True,
        "runtime_consensus_gate_required": True,
        "kernel_retains_final_gate_authority": True,
        "private_truth_available_during_inference": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_evidence_first_experiment(
    *,
    corpus,
    preregistration,
    adapter,
    base_checkpoint_callback=None,
    overlay_checkpoint_callback=None,
    holdout_validator=None,
):
    (holdout_validator or validate_evidence_first_holdout)(corpus)
    _validate_preregistration(preregistration, corpus)
    base_run = run_reference_complete_portfolio_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        checkpoint_callback=base_checkpoint_callback,
        holdout_validator=(
            holdout_validator or validate_evidence_first_holdout
        ),
        qualification_deriver=derive_context_qualification,
        qualification_policy_version=QUALIFICATION_POLICY_VERSION,
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
    blind_views, blind_receipts = {}, {}
    valid_keys = []
    for key in sorted(base_run["pairwise_displacement_valid_keys"]):
        rep, arm, case_id = key.split(":", 2)
        initial = base_run["pairwise_displacement_receipts"][key]
        role_receipts = []
        if initial["portfolio_decision"] != "ACTIVATE_DELTA":
            view = build_blind_evidence_view(
                portfolio_view=base_run[
                    "pairwise_displacement_views"
                ][key]
            )
            blind_views[key] = view
            for role in AUDIT_ROLES:
                task = _blind_task(
                    item=view,
                    role=role,
                    replication_id=rep,
                    arm_id=arm,
                    refs=refs,
                    adapter=adapter,
                )
                envelope = ProviderTaskRouter([adapter]).route(task)
                stage = (
                    "BLIND_EVIDENCE_AUDIT"
                    if role == AUDIT_ROLES[0]
                    else "BLIND_EVIDENCE_SKEPTIC"
                )
                call = _call(
                    replication_id=rep,
                    arm_id=arm,
                    case_id=case_id,
                    stage=stage,
                    route_id=role,
                    task=task,
                    envelope=envelope,
                )
                calls.append(call)
                if envelope.status != "COMPLETED":
                    failures.append(_provider_failure(call))
                    continue
                receipt = envelope.normalized_result
                raw_receipts[
                    f"{rep}:{arm}:{stage}:{case_id}"
                ] = receipt
                contract_failures = validate_blind_evidence_receipt(
                    receipt=receipt,
                    item=view,
                    role=role,
                    refs=refs,
                )
                if contract_failures:
                    failures.append({
                        "replication_id": rep,
                        "arm_id": arm,
                        "case_id": case_id,
                        "stage": f"{stage}_CONTRACT",
                        "failures": contract_failures,
                        "raw_receipt_hash": hash_payload(receipt),
                    })
                    continue
                blind_receipts[f"{key}:{role}"] = receipt
                valid_keys.append(f"{key}:{role}")
                role_receipts.append(receipt)
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
            apply_evidence_first_gate(
                provisional_receipt=provisional,
                proposed_receipt=proposed,
                composition_receipt=composition,
                portfolio_view=base_run[
                    "pairwise_displacement_views"
                ][key],
                lineage_delta=lineage_delta,
                cross_replication_witnesses=witnesses,
                initial_receipt=initial,
                blind_receipts=role_receipts,
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
        _checkpoint(
            overlay_checkpoint_callback,
            corpus=corpus,
            preregistration=preregistration,
            base_run=base_run,
            calls=calls,
            blind_views=blind_views,
            blind_receipts=blind_receipts,
            failures=failures,
        )
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base_run.items() if key != "run_hash"
    }
    commitment.update({
        "runtime_version": RUNTIME_VERSION,
        "source_base_run_hash": base_run["run_hash"],
        "source_unlabeled_calibration_hash": preregistration[
            "source_unlabeled_calibration_hash"
        ],
        "source_evidence_first_contract_version": CONTRACT_VERSION,
        "source_evidence_first_gate_version": GATE_VERSION,
        "task_calls": calls,
        "raw_receipts": raw_receipts,
        "final_projections": final_projections,
        "replacement_gate_receipts": gate_receipts,
        "composition_receipts": composition_receipts,
        "failures": failures,
        "blind_evidence_views": blind_views,
        "blind_evidence_receipts": blind_receipts,
        "blind_evidence_valid_keys": valid_keys,
        "initial_decision_hidden_from_blind_roles": True,
        "initial_rationale_hidden_from_blind_roles": True,
        "blind_roles_cannot_activate_directly": True,
        "effect_lane_witness_policy_changed": False,
        "private_truth_used_by_blind_roles": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_evidence_first_experiment(
    *, corpus, preregistration, run, holdout_validator=None
):
    (holdout_validator or validate_evidence_first_holdout)(corpus)
    _validate_preregistration(preregistration, corpus)
    base = analyze_reference_complete_portfolio_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
        holdout_validator=(
            holdout_validator or validate_evidence_first_holdout
        ),
    )
    qualifications = list(run["qualification_receipts"].values())
    qualified = [value for value in qualifications if value["qualified"]]
    structural = sum(
        value["qualified"]
        and value["qualification_basis"]
        in {"STRUCTURAL_OPPORTUNITY_GAP", "BOTH"}
        for value in qualifications
    )
    policy_coverage = round(
        sum(
            value["policy_version"] == QUALIFICATION_POLICY_VERSION
            for value in qualifications
        ) / len(qualifications) if qualifications else 0.0,
        6,
    )
    initial = run["pairwise_displacement_receipts"]
    eligible = {
        key for key, value in initial.items()
        if value["portfolio_decision"] != "ACTIVATE_DELTA"
    }
    expected_roles = len(eligible) * len(AUDIT_ROLES)
    valid_roles = len(run["blind_evidence_valid_keys"])
    consensus = sum(
        value.get("blind_evidence_consensus") is True
        and value.get("accepted") is True
        for value in run["replacement_gate_receipts"].values()
    )
    context_metrics = {
        "receipt_count": len(qualifications),
        "qualified_count": len(qualified),
        "qualification_rate": round(
            len(qualified) / len(qualifications)
            if qualifications else 0.0,
            6,
        ),
        "qualification_basis_distribution": dict(Counter(
            value["qualification_basis"] for value in qualifications
        )),
        "structural_gap_qualified_count": structural,
        "context_policy_coverage": policy_coverage,
    }
    blind_metrics = {
        "eligible_rejection_count": len(eligible),
        "expected_role_receipt_count": expected_roles,
        "valid_role_receipt_count": valid_roles,
        "role_contract_coverage": round(
            valid_roles / expected_roles if expected_roles else 1.0,
            6,
        ),
        "blind_consensus_activation_count": consensus,
        "blind_direct_activation_count": 0,
        "role_preference_distribution": dict(Counter(
            (
                f"{value['audit_role']}:"
                f"{value['marginal_information_preference']}"
            )
            for value in run["blind_evidence_receipts"].values()
        )),
    }
    gate = preregistration["success_gate"]
    extra = {
        "minimum_context_qualified_count": (
            len(qualified) >= gate["minimum_context_qualified_count"]
        ),
        "maximum_context_qualified_count": (
            len(qualified) <= gate["maximum_context_qualified_count"]
        ),
        "minimum_context_qualification_rate": (
            context_metrics["qualification_rate"]
            >= gate["minimum_context_qualification_rate"]
        ),
        "maximum_context_qualification_rate": (
            context_metrics["qualification_rate"]
            <= gate["maximum_context_qualification_rate"]
        ),
        "minimum_structural_gap_qualified_count": (
            structural >= gate["minimum_structural_gap_qualified_count"]
        ),
        "minimum_context_policy_coverage": (
            policy_coverage >= gate["minimum_context_policy_coverage"]
        ),
        "minimum_blind_eligible_rejection_count": (
            len(eligible)
            >= gate["minimum_blind_eligible_rejection_count"]
        ),
        "minimum_blind_role_contract_coverage": (
            blind_metrics["role_contract_coverage"]
            >= gate["minimum_blind_role_contract_coverage"]
        ),
        "minimum_blind_consensus_activation_count": (
            consensus
            >= gate["minimum_blind_consensus_activation_count"]
        ),
        "maximum_blind_direct_activation_count": (
            blind_metrics["blind_direct_activation_count"]
            <= gate["maximum_blind_direct_activation_count"]
        ),
        "evidence_first_boundary_preserved": (
            run["initial_decision_hidden_from_blind_roles"] is True
            and run["initial_rationale_hidden_from_blind_roles"] is True
            and run["blind_roles_cannot_activate_directly"] is True
            and run["effect_lane_witness_policy_changed"] is False
            and run["private_truth_used_by_blind_roles"] is False
        ),
    }
    conditions = {**base["conditions"], **extra}
    passed = all(conditions.values())
    if passed:
        decision = "PASS_EVIDENCE_FIRST_ARBITRATION_REPLICATION"
        state = "EVIDENCE_FIRST_ARBITRATION_REPLICATED_READY_POSTHOC"
    elif (
        base["physical_total_tokens"]
        > gate["hard_runaway_total_tokens"]
    ):
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "EVIDENCE_FIRST_ARBITRATION_RESOURCE_STOP"
    else:
        decision = "REJECT_EVIDENCE_FIRST_ARBITRATION_REPLICATION"
        state = "EVIDENCE_FIRST_ARBITRATION_REJECTED_STOP"
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base.items() if key != "artifact_hash"
    }
    commitment.update({
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "context_qualification_metrics": context_metrics,
        "blind_evidence_metrics": blind_metrics,
        "conditions": conditions,
        "evidence_first_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _blind_task(
    *, item, role, replication_id, arm_id, refs, adapter
):
    role_prompt = {
        "BLIND_EVIDENCE_AUDITOR": (
            "Independently account for realized evidence-backed information "
            "gain before considering future test option value."
        ),
        "BLIND_EVIDENCE_SKEPTIC": (
            "Independently challenge unsupported novelty and test whether "
            "apparent redundancy is relation-specific rather than merely "
            "sharing a truth-state category."
        ),
    }[role]
    stage = (
        "BLIND_EVIDENCE_AUDIT"
        if role == AUDIT_ROLES[0]
        else "BLIND_EVIDENCE_SKEPTIC"
    )
    return ProviderCognitiveTask(
        task_id=(
            f"{RUNTIME_VERSION}-{replication_id}-{stage}-"
            f"{arm_id}-{item['case_id']}"
        ),
        task_kind=TASK_KIND,
        objective=(
            f"{role_prompt} Compare base and delta relative to fixed "
            "companions. You cannot see the initial decision, its rationale, "
            "or the other blind role. Treat a supported null as realized "
            "information that rules out a specific relation; it is not "
            "redundant merely because another candidate is also a null. "
            "Keep realized evidence Cbit separate from the option value of "
            "a future test. Prefer delta only when its total evidence-bound "
            "marginal Cbit is higher. Echo exact source-qualified IDs. You "
            "cannot activate candidates."
        ),
        inputs={
            "stage": stage,
            "audit_role": role,
            "blind_case": item,
            "initial_decision_available": False,
            "initial_rationale_available": False,
            "other_audit_receipt_available": False,
            "private_outcome_available": False,
            "activation_authority": False,
            "provider_output_state": "DIAGNOSTIC_ONLY",
        },
        allowed_evidence=list(refs),
        expected_schema=blind_evidence_schema(
            item=item, role=role, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _validate_artifact_hash(value):
    commitment = {
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("evidence_first_source_hash_invalid")


def _validate_preregistration(preregistration, corpus):
    _validate_artifact_hash(preregistration)
    if preregistration.get("source_corpus_hash") != corpus["artifact_hash"]:
        raise ValueError("evidence_first_preregistration_invalid")


def _checkpoint(
    callback,
    *,
    corpus,
    preregistration,
    base_run,
    calls,
    blind_views,
    blind_receipts,
    failures,
):
    if callback is None:
        return
    commitment = {
        "progress_version": "evidence_first_progress_v0_54",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_base_run_hash": base_run["run_hash"],
        "completed_task_count": len(calls),
        "blind_evidence_views": copy.deepcopy(blind_views),
        "blind_evidence_receipts": copy.deepcopy(blind_receipts),
        "failures": copy.deepcopy(failures),
        "resume_authority": False,
    }
    callback({**commitment, "artifact_hash": hash_payload(commitment)})
