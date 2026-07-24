"""Context-normalized qualification experiment v0.53."""

from __future__ import annotations

import copy
import math
from collections import Counter

from .context_qualification_holdout import (
    REPLICATION_IDS,
    validate_context_qualification_holdout,
)
from .context_qualification_policy import (
    POLICY_VERSION,
    derive_context_qualification,
)
from .provider_telemetry import hash_payload
from .reference_completeness_audit import (
    AUDIT_VERSION as REFERENCE_AUDIT_VERSION,
    validate_reference_completeness_audit,
)
from .selective_rejection_experiment import (
    analyze_selective_rejection_experiment,
    run_selective_rejection_experiment,
)


RUNTIME_VERSION = "context_qualification_experiment_v0_53"


def build_context_qualification_preregistration(
    *,
    corpus,
    reference_audit,
    calibration,
    prior_preregistration,
    prior_analysis,
    prior_closure,
    prior_posthoc,
):
    validate_context_qualification_holdout(corpus)
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
        or reference_audit.get("valid_receipt_count") != 16
        or reference_audit.get("contract_failures")
        or reference_audit.get("reference_mismatches")
        or reference_audit.get("cross_role_disagreements")
        or calibration.get("source_policy_version") != POLICY_VERSION
        or calibration.get("source_count") != 2
        or calibration.get("private_outcomes_accessed") is not False
        or calibration.get("posthoc_labels_accessed") is not False
        or calibration.get("provider_calls_added") != 0
        or calibration.get("absolute_threshold_retuned_from_v0_41")
        is not False
        or calibration.get("cross_source_rate_range", 1.0) > 0.1
        or min(
            value["new_qualified_count"]
            for value in calibration["source_metrics"].values()
        ) < 16
        or prior_analysis.get("decision")
        != "REJECT_SELECTIVE_REJECTION_REPLICATION"
        or prior_analysis.get("candidate_state")
        != "SELECTIVE_REJECTION_REJECTED_STOP"
        or prior_closure.get("candidate_state")
        != "SELECTIVE_REJECTION_REJECTED_STOP"
        or prior_analysis.get("replacement_gate_metrics", {}).get(
            "accepted_count"
        ) != 3
        or prior_analysis.get("selective_rejection_metrics", {}).get(
            "coordinated_activation_count"
        ) != 1
        or prior_analysis.get("composition_metrics", {}).get(
            "triggered_composition_gross_uplift", {}
        ).get("mean") != 2.0
        or prior_posthoc.get("classification_distribution") != {
            "BENEFICIAL_ACCEPTED": 3,
        }
        or prior_posthoc.get(
            "coordinated_recovery_beneficial_count"
        ) != 1
        or prior_posthoc.get("coordinated_recovery_harmful_count") != 0
    ):
        raise ValueError("context_qualification_prior_invalid")
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
        "minimum_accepted_composition_count": 5,
        "minimum_rejection_challenge_count": 2,
        "minimum_coordinated_activation_count": 1,
        "minimum_triggered_composition_gross_mean": 0.5,
        "minimum_triggered_composition_gross_median": 0.5,
        "minimum_triggered_composition_gross_win_rate": 1.0,
        "maximum_triggered_composition_gross_loss_rate": 0.0,
        "maximum_physical_total_tokens": math.ceil(prior_total * 2.0),
        "hard_runaway_total_tokens": math.ceil(prior_total * 2.5),
        "required_shared_standard_call_count": (
            corpus["case_count"] * len(REPLICATION_IDS)
        ),
    })
    cost_policy = copy.deepcopy(
        prior_preregistration["cost_policy"]
    )
    cost_policy.update({
        "context_qualification_adds_provider_tokens": False,
        "absolute_threshold_retuned_from_v0_41": False,
        "soft_expected_total_tokens": math.ceil(prior_total * 2.0),
        "hard_runaway_total_tokens": math.ceil(prior_total * 2.5),
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
        "source_qualification_policy_version": POLICY_VERSION,
        "frozen_hypothesis": (
            "A zero-token qualification policy based on a triggered, "
            "review-ready relation outside the current candidate set and "
            "bound to novel evidence will generalize across balanced "
            "candidate distributions better than absolute score spread. "
            "It should restore enough review volume to test selective "
            "rejection while preserving accepted-cell gross precision."
        ),
        "success_gate": success_gate,
        "cost_policy": cost_policy,
        "fresh_relation_state_positions_rotated": True,
        "unlabeled_cross_source_calibration_required": True,
        "structural_opportunity_gap_required": True,
        "absolute_threshold_retuned_from_v0_41": False,
        "context_qualification_adds_provider_calls": False,
        "selective_rejection_overlay_retained": True,
        "challenge_cannot_activate_directly": True,
        "kernel_retains_final_gate_authority": True,
        "private_truth_available_during_inference": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "baseline_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_context_qualification_experiment(
    *,
    corpus,
    preregistration,
    adapter,
    base_checkpoint_callback=None,
    overlay_checkpoint_callback=None,
):
    validate_context_qualification_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    run = run_selective_rejection_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        base_checkpoint_callback=base_checkpoint_callback,
        overlay_checkpoint_callback=overlay_checkpoint_callback,
        holdout_validator=validate_context_qualification_holdout,
        qualification_deriver=derive_context_qualification,
        qualification_policy_version=POLICY_VERSION,
        runtime_version=RUNTIME_VERSION,
    )
    commitment = {
        key: copy.deepcopy(value)
        for key, value in run.items() if key != "run_hash"
    }
    commitment.update({
        "runtime_version": RUNTIME_VERSION,
        "source_unlabeled_calibration_hash": preregistration[
            "source_unlabeled_calibration_hash"
        ],
        "source_qualification_policy_version": POLICY_VERSION,
        "context_qualification_adds_provider_calls": False,
        "absolute_threshold_retuned_from_v0_41": False,
        "private_truth_used_by_qualification": False,
    })
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_context_qualification_experiment(
    *, corpus, preregistration, run
):
    validate_context_qualification_holdout(corpus)
    _validate_preregistration(preregistration, corpus)
    base = analyze_selective_rejection_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
        holdout_validator=validate_context_qualification_holdout,
        runtime_version=RUNTIME_VERSION,
    )
    receipts = list(run["qualification_receipts"].values())
    qualified = [value for value in receipts if value["qualified"]]
    bases = Counter(
        value["qualification_basis"] for value in receipts
    )
    structural = sum(
        value["qualified"]
        and value["qualification_basis"]
        in {"STRUCTURAL_OPPORTUNITY_GAP", "BOTH"}
        for value in receipts
    )
    policy_coverage = round(
        sum(
            value["policy_version"] == POLICY_VERSION
            for value in receipts
        ) / len(receipts) if receipts else 0.0,
        6,
    )
    rate = round(
        len(qualified) / len(receipts) if receipts else 0.0, 6
    )
    metrics = {
        "receipt_count": len(receipts),
        "qualified_count": len(qualified),
        "qualification_rate": rate,
        "qualification_basis_distribution": dict(bases),
        "structural_gap_qualified_count": structural,
        "context_policy_coverage": policy_coverage,
        "additional_provider_call_count": sum(
            value["additional_provider_call_used"]
            for value in receipts
        ),
        "private_truth_use_count": sum(
            value["private_truth_used"] for value in receipts
        ),
        "absolute_threshold_retuned_from_v0_41": any(
            value["absolute_threshold_retuned_from_v0_41"]
            for value in receipts
        ),
    }
    gate = preregistration["success_gate"]
    context_conditions = {
        "minimum_context_qualified_count": (
            metrics["qualified_count"]
            >= gate["minimum_context_qualified_count"]
        ),
        "maximum_context_qualified_count": (
            metrics["qualified_count"]
            <= gate["maximum_context_qualified_count"]
        ),
        "minimum_context_qualification_rate": (
            rate >= gate["minimum_context_qualification_rate"]
        ),
        "maximum_context_qualification_rate": (
            rate <= gate["maximum_context_qualification_rate"]
        ),
        "minimum_structural_gap_qualified_count": (
            structural
            >= gate["minimum_structural_gap_qualified_count"]
        ),
        "minimum_context_policy_coverage": (
            policy_coverage >= gate["minimum_context_policy_coverage"]
        ),
        "context_qualification_boundary_preserved": (
            metrics["additional_provider_call_count"] == 0
            and metrics["private_truth_use_count"] == 0
            and metrics[
                "absolute_threshold_retuned_from_v0_41"
            ] is False
            and run["source_unlabeled_calibration_hash"]
            == preregistration["source_unlabeled_calibration_hash"]
        ),
    }
    conditions = {**base["conditions"], **context_conditions}
    passed = all(conditions.values())
    if passed:
        decision = "PASS_CONTEXT_QUALIFICATION_REPLICATION"
        state = "CONTEXT_QUALIFICATION_REPLICATED_READY_POSTHOC"
    elif (
        base["physical_total_tokens"]
        > gate["hard_runaway_total_tokens"]
    ):
        decision = "STOP_RESOURCE_RUNAWAY"
        state = "CONTEXT_QUALIFICATION_RESOURCE_STOP"
    else:
        decision = "REJECT_CONTEXT_QUALIFICATION_REPLICATION"
        state = "CONTEXT_QUALIFICATION_REJECTED_STOP"
    commitment = {
        key: copy.deepcopy(value)
        for key, value in base.items() if key != "artifact_hash"
    }
    commitment.update({
        "analysis_version": RUNTIME_VERSION,
        "source_run_hash": run["run_hash"],
        "context_qualification_metrics": metrics,
        "conditions": conditions,
        "context_qualification_gate": "PASS" if passed else "REJECT",
        "decision": decision,
        "external_semantic_panel_authorized": passed,
        "core_integration_authorized": False,
        "candidate_state": state,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    })
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _validate_artifact_hash(value):
    commitment = {
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("context_qualification_source_hash_invalid")


def _validate_preregistration(preregistration, corpus):
    _validate_artifact_hash(preregistration)
    if preregistration.get("source_corpus_hash") != corpus["artifact_hash"]:
        raise ValueError("context_qualification_preregistration_invalid")
