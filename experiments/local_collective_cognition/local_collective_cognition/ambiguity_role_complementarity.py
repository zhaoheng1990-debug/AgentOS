"""Candidate-only role topology inferred from the unstated-ambiguity holdout."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .unstated_ambiguity_holdout import HOLDOUT_SPEC, NULL, POSITIVE


ANALYSIS_VERSION = "ambiguity_role_complementarity_v0_1"


def build_role_complementarity_candidate(*, holdout_artifact, judge_calibration_artifact):
    _validate_source_hash(holdout_artifact, "holdout")
    _validate_source_hash(judge_calibration_artifact, "judge_calibration")
    if holdout_artifact["report"]["candidate_state"] != "UNSTATED_AMBIGUITY_DISCOVERY_GATE_FAILED":
        raise ValueError("role_complementarity_requires_failed_single_model_gate")
    intervention = holdout_artifact.get("construction_intervention", {})
    if not (intervention.get("concrete_state_and_confidence_template_removed")
            and intervention.get("state_menu_order_counterbalanced_by_item")):
        raise ValueError("role_complementarity_prompt_control_missing")

    runs = {run["model_id"]: run for run in holdout_artifact["model_runs"]}
    profiles = {profile["model_id"]: profile for profile in holdout_artifact["report"]["profiles"]}
    if set(runs) != set(profiles):
        raise ValueError("role_complementarity_model_surface_invalid")
    gates = HOLDOUT_SPEC["frozen_gates"]
    proposers = [profile for profile in profiles.values()
                 if profile["positive_recall"] >= gates["minimum_positive_recall"]]
    skeptics = [profile for profile in profiles.values()
                if profile["null_specificity"] >= gates["minimum_null_specificity"]]
    if not proposers or not skeptics:
        raise ValueError("role_complementarity_orientation_not_observed")
    proposer = min(proposers, key=lambda item: (
        -item["positive_recall"], item["total_provider_calls"], item["total_tokens"], item["model_id"],
    ))
    skeptic = min(skeptics, key=lambda item: (
        -item["null_specificity"], item["total_provider_calls"], item["total_tokens"], item["model_id"],
    ))
    if proposer["model_id"] == skeptic["model_id"]:
        raise ValueError("role_complementarity_distinct_roles_required")

    item_surface = _item_surface(runs)
    proposer_states = _states(runs[proposer["model_id"]])
    skeptic_states = _states(runs[skeptic["model_id"]])
    all_states = {model_id: _states(run) for model_id, run in runs.items()}
    disagreement_count = sum(proposer_states[item] != skeptic_states[item] for item in item_surface)
    simulations = {
        "OR_POSITIVE": _score(item_surface, {
            item: POSITIVE if POSITIVE in {proposer_states[item], skeptic_states[item]} else NULL
            for item in item_surface
        }),
        "AND_POSITIVE": _score(item_surface, {
            item: POSITIVE if proposer_states[item] == skeptic_states[item] == POSITIVE else NULL
            for item in item_surface
        }),
        "ALL_MODEL_MAJORITY_POSITIVE": _score(item_surface, {
            item: POSITIVE if sum(states[item] == POSITIVE for states in all_states.values()) > len(all_states) / 2
            else NULL for item in item_surface
        }),
    }
    oracle = _score(item_surface, {
        item: item_surface[item] if item_surface[item] in {proposer_states[item], skeptic_states[item]} else NULL
        for item in item_surface
    })
    best_naive_balanced_accuracy = max(item["balanced_accuracy"] for item in simulations.values())
    policy = judge_calibration_artifact["policy_candidate"]
    commitment = {
        "analysis_version": ANALYSIS_VERSION,
        "source_holdout_artifact_hash": holdout_artifact["artifact_hash"],
        "judge_calibration_artifact_hash": judge_calibration_artifact["artifact_hash"],
        "item_count": len(item_surface),
        "role_candidates": {
            "ambiguity_proposer": _role_profile(proposer, "HIGH_SENSITIVITY_LOW_SPECIFICITY"),
            "null_skeptic": _role_profile(skeptic, "HIGH_SPECIFICITY_LOW_SENSITIVITY"),
            "semantic_coordinator": {
                "provider_id": policy["primary_judge_provider_id"],
                "model_id": policy["primary_judge_model_id"],
                "binding_state": "UNVALIDATED_FOR_AMBIGUITY_COORDINATION",
                "required_escalation": policy["escalation_action"],
            },
        },
        "proposer_skeptic_disagreement_count": disagreement_count,
        "proposer_skeptic_disagreement_rate": disagreement_count / len(item_surface),
        "naive_ensemble_simulations": simulations,
        "best_naive_balanced_accuracy": best_naive_balanced_accuracy,
        "naive_ensemble_gate_passed": any(item["passes_frozen_gates"] for item in simulations.values()),
        "oracle_choice_upper_bound": {
            **oracle, "operational_policy": False,
            "interpretation": "upper bound only; hidden labels choose the correct role",
        },
        "coordination_policy_candidate": {
            "sequence": ["AMBIGUITY_PROPOSER", "NULL_SKEPTIC", "SEMANTIC_COORDINATOR_ON_DISAGREEMENT"],
            "coordinator_receipt_must_be_identity_blind": True,
            "kernel_owns_final_candidate_state": True,
            "abstain_on_missing_or_unresolved_receipt": True,
            "fresh_holdout_required": True,
            "current_holdout_reuse_for_validation_forbidden": True,
        },
        "candidate_state": "ROLE_COMPLEMENTARITY_OBSERVED_COORDINATOR_VALIDATION_REQUIRED",
        "claim_boundary": (
            "opposed error orientations are observed after prompt controls; naive voting may improve one "
            "aggregate metric but does not pass the frozen gates, and the oracle upper bound is not an "
            "executable coordination result"
        ),
        "selection_authority": False, "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_role_complementarity_candidate(artifact, *, holdout_artifact,
                                             judge_calibration_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("role_complementarity_artifact_hash_invalid")
    expected = build_role_complementarity_candidate(
        holdout_artifact=holdout_artifact,
        judge_calibration_artifact=judge_calibration_artifact,
    )
    if artifact != expected:
        raise ValueError("role_complementarity_artifact_semantics_invalid")


def _validate_source_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"role_complementarity_{name}_hash_invalid")


def _item_surface(runs):
    surfaces = [{trial["item_id"]: trial["outcome"]["expected_state"] for trial in run["trials"]}
                for run in runs.values()]
    if not surfaces or any(surface != surfaces[0] for surface in surfaces[1:]):
        raise ValueError("role_complementarity_item_surface_invalid")
    return surfaces[0]


def _states(run):
    return {trial["item_id"]: trial["outcome"]["observed_state"] for trial in run["trials"]}


def _score(expected, predicted):
    positive = [item for item, state in expected.items() if state == POSITIVE]
    null = [item for item, state in expected.items() if state == NULL]
    recall = sum(predicted[item] == POSITIVE for item in positive) / len(positive)
    specificity = sum(predicted[item] == NULL for item in null) / len(null)
    gates = HOLDOUT_SPEC["frozen_gates"]
    balanced = (recall + specificity) / 2
    return {"positive_recall": recall, "null_specificity": specificity,
            "balanced_accuracy": balanced, "passes_frozen_gates": (
                balanced >= gates["minimum_balanced_accuracy"]
                and recall >= gates["minimum_positive_recall"]
                and specificity >= gates["minimum_null_specificity"]
                and (1 - specificity) <= gates["maximum_null_false_positive_rate"]
            )}


def _role_profile(profile, orientation):
    return {
        "provider_id": profile["provider_id"], "model_id": profile["model_id"],
        "orientation": orientation, "positive_recall": profile["positive_recall"],
        "null_specificity": profile["null_specificity"],
        "balanced_accuracy": profile["balanced_accuracy"],
        "total_provider_calls": profile["total_provider_calls"], "total_tokens": profile["total_tokens"],
    }
