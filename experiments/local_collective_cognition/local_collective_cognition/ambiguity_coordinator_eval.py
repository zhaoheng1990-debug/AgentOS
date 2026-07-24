"""Harness-owned scoring and artifact validation for coordinator calibration."""

from __future__ import annotations

from .ambiguity_coordinator_holdout import (
    CASES, HOLDOUT_SPEC, NULL, POSITIVE, validate_coordinator_holdout_spec,
)
from .ambiguity_coordinator_runtime import validate_coordinator_run
from .ambiguity_coordinator_surface import build_coordinator_surface, validate_coordinator_surface
from .provider_telemetry import hash_payload


REPORT_VERSION = "ambiguity_coordinator_report_v0_1"


def build_coordinator_report(*, role_artifact, model_runs, surface, coordinator_run):
    validate_coordinator_holdout_spec()
    validate_coordinator_surface(surface, role_artifact=role_artifact, model_runs=model_runs)
    validate_coordinator_run(coordinator_run, surface=surface)
    runs = {run["model_id"]: run for run in model_runs}
    roles = role_artifact["role_candidates"]
    proposer_id = roles["ambiguity_proposer"]["model_id"]
    skeptic_id = roles["null_skeptic"]["model_id"]
    expected = {case.item_id: case.expected_state for case in CASES}
    proposer = _run_states(runs[proposer_id])
    skeptic = _run_states(runs[skeptic_id])
    fixed_predictions = {
        "PROPOSER_ONLY": proposer,
        "SKEPTIC_ONLY": skeptic,
        "OR_POSITIVE": {item: POSITIVE if POSITIVE in {proposer[item], skeptic[item]} else NULL for item in expected},
        "AND_POSITIVE": {item: POSITIVE if proposer[item] == skeptic[item] == POSITIVE else NULL for item in expected},
    }
    fixed_profiles = {name: _score(expected, predictions) for name, predictions in fixed_predictions.items()}
    coordinator_states = _coordinator_states(surface, coordinator_run)
    coordinator_profile = _score(expected, coordinator_states)
    frozen_name = HOLDOUT_SPEC["frozen_comparator"]
    frozen_profile = fixed_profiles[frozen_name]
    fixed_calls = sum(run["profile"]["total_provider_calls"] for run in model_runs)
    fixed_tokens = sum(run["profile"]["total_tokens"] for run in model_runs)
    coordinator_calls = coordinator_run["profile"]["total_provider_calls"]
    coordinator_tokens = coordinator_run["profile"]["total_tokens"]
    route_calls, route_tokens = fixed_calls + coordinator_calls, fixed_tokens + coordinator_tokens
    call_ratio = route_calls / fixed_calls if fixed_calls else None
    token_ratio = route_tokens / fixed_tokens if fixed_tokens else None
    balanced_gain = coordinator_profile["balanced_accuracy"] - frozen_profile["balanced_accuracy"]
    uncertain_rate = sum(
        coordinator_states.get(item) not in {POSITIVE, NULL} for item in expected
    ) / len(expected)
    gates = HOLDOUT_SPEC["frozen_gates"]
    gate_results = {
        "balanced_accuracy": coordinator_profile["balanced_accuracy"] >= gates["minimum_balanced_accuracy"],
        "positive_recall": coordinator_profile["positive_recall"] >= gates["minimum_positive_recall"],
        "null_specificity": coordinator_profile["null_specificity"] >= gates["minimum_null_specificity"],
        "balanced_gain": balanced_gain >= gates["minimum_balanced_gain_vs_frozen_comparator"],
        "uncertainty": uncertain_rate <= gates["maximum_uncertain_or_unavailable_rate"],
        "provider_call_budget": call_ratio is not None and call_ratio <= gates["maximum_provider_call_ratio"],
        "token_budget": token_ratio is not None and token_ratio <= gates["maximum_token_ratio"],
        "complete_decision_surface": len(coordinator_states) == len(expected),
    }
    passed = all(gate_results.values())
    commitment = {
        "report_version": REPORT_VERSION, "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
        "role_artifact_hash": role_artifact["artifact_hash"], "surface_hash": surface["surface_hash"],
        "coordinator_run_hash": coordinator_run["coordinator_run_hash"],
        "fixed_strategy_profiles": fixed_profiles, "frozen_comparator": frozen_name,
        "coordinator_profile": coordinator_profile,
        "balanced_gain_vs_frozen_comparator": balanced_gain,
        "corrected_vs_frozen_comparator": sum(
            coordinator_states.get(item) == expected[item]
            and fixed_predictions[frozen_name][item] != expected[item]
            for item in expected
        ),
        "harmed_vs_frozen_comparator": sum(
            coordinator_states.get(item) != expected[item]
            and fixed_predictions[frozen_name][item] == expected[item]
            for item in expected
        ),
        "uncertain_or_unavailable_rate": uncertain_rate,
        "cost_profile": {
            "fixed_provider_calls": fixed_calls, "fixed_tokens": fixed_tokens,
            "coordinator_provider_calls": coordinator_calls, "coordinator_tokens": coordinator_tokens,
            "coordinated_route_provider_calls": route_calls, "coordinated_route_tokens": route_tokens,
            "provider_call_ratio": call_ratio, "token_ratio": token_ratio,
            "balanced_gain_per_1000_incremental_tokens": (
                balanced_gain * 1000 / coordinator_tokens if coordinator_tokens else None
            ),
        },
        "gate_results": gate_results,
        "candidate_state": (
            "COORDINATOR_GAIN_EVIDENCE_CANDIDATE" if passed else "COORDINATOR_CALIBRATION_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_SYNTHETIC_PAIRED_FRESH_HOLDOUT",
        "ground_truth_claim": False, "selection_authority": False,
        "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "report_hash": hash_payload(commitment)}


def build_coordinator_artifact(*, experiment_id, role_artifact, judge_calibration_artifact,
                               model_runs, surface, coordinator_run, construction_intervention=None):
    _validate_artifact_hash(role_artifact, "role")
    _validate_artifact_hash(judge_calibration_artifact, "judge_calibration")
    coordinator_role = role_artifact["role_candidates"]["semantic_coordinator"]
    policy = judge_calibration_artifact["policy_candidate"]
    primary_binding = (
        coordinator_role["model_id"] == policy["primary_judge_model_id"]
        and coordinator_role["provider_id"] == policy["primary_judge_provider_id"]
    )
    fallback_binding = (
        role_artifact.get("candidate_state") == "SECONDARY_COORDINATOR_TRANSPORT_FALLBACK_CANDIDATE"
        and coordinator_role["model_id"] == policy["secondary_judge_model_id"]
        and coordinator_role["provider_id"] == policy["secondary_judge_provider_id"]
        and len(role_artifact.get("primary_failure_artifact_hashes", [])) >= 2
    )
    if (role_artifact["judge_calibration_artifact_hash"] != judge_calibration_artifact["artifact_hash"]
            or not (primary_binding or fallback_binding)
            or coordinator_run["model_id"] != coordinator_role["model_id"]
            or coordinator_run["provider_id"] != coordinator_role["provider_id"]):
        raise ValueError("ambiguity_coordinator_candidate_binding_invalid")
    for run in model_runs:
        _validate_model_run(run)
    report = build_coordinator_report(
        role_artifact=role_artifact, model_runs=model_runs, surface=surface,
        coordinator_run=coordinator_run,
    )
    commitment = {
        "experiment_id": experiment_id, "holdout_spec": HOLDOUT_SPEC,
        "role_artifact_hash": role_artifact["artifact_hash"],
        "judge_calibration_artifact_hash": judge_calibration_artifact["artifact_hash"],
        "model_runs": list(model_runs), "blind_surface": surface,
        "coordinator_run": coordinator_run, "report": report,
        "claim_boundary": (
            "fresh internal synthetic coordinator calibration only; model identities and hidden labels were "
            "withheld from the coordinator; no accepted baseline, retention, or production authority"
        ),
    }
    if construction_intervention:
        commitment["construction_intervention"] = construction_intervention
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_coordinator_artifact(artifact, *, role_artifact, judge_calibration_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_coordinator_artifact_hash_invalid")
    expected = build_coordinator_artifact(
        experiment_id=artifact["experiment_id"], role_artifact=role_artifact,
        judge_calibration_artifact=judge_calibration_artifact,
        model_runs=tuple(artifact["model_runs"]), surface=artifact["blind_surface"],
        coordinator_run=artifact["coordinator_run"],
        construction_intervention=artifact.get("construction_intervention"),
    )
    if artifact != expected:
        raise ValueError("ambiguity_coordinator_artifact_semantics_invalid")


def _score(expected, predicted):
    positives = [item for item, state in expected.items() if state == POSITIVE]
    nulls = [item for item, state in expected.items() if state == NULL]
    recall = sum(predicted.get(item) == POSITIVE for item in positives) / len(positives)
    specificity = sum(predicted.get(item) == NULL for item in nulls) / len(nulls)
    return {"positive_recall": recall, "null_specificity": specificity,
            "balanced_accuracy": (recall + specificity) / 2,
            "accuracy": sum(predicted.get(item) == state for item, state in expected.items()) / len(expected)}


def _run_states(run):
    return {trial["item_id"]: trial["outcome"]["observed_state"] for trial in run["trials"]}


def _coordinator_states(surface, run):
    binding = surface["private_position_bindings"]
    states = {}
    for judgment in run["judgments"]:
        forbidden = {run["model_id"], run["provider_id"], "PROPOSER", "SKEPTIC"}
        rendered = str(judgment["provider_input"])
        if any(value and value in rendered for value in forbidden):
            raise ValueError("ambiguity_coordinator_identity_blinding_failed")
        for decision in judgment["payload"]["decisions"]:
            item_id = binding[decision["coordination_item_id"]]["source_item_id"]
            states[item_id] = decision["final_state"]
    return states


def _validate_model_run(run):
    commitment = {key: value for key, value in run.items() if key != "model_run_hash"}
    if run.get("model_run_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_coordinator_model_run_hash_invalid")
    profile = run["profile"]
    profile_commitment = {key: value for key, value in profile.items() if key != "profile_hash"}
    if profile.get("profile_hash") != hash_payload(profile_commitment):
        raise ValueError("ambiguity_coordinator_model_profile_hash_invalid")
    for trial in run["trials"]:
        outcome = trial["outcome"]
        outcome_commitment = {key: value for key, value in outcome.items() if key != "outcome_hash"}
        if outcome.get("outcome_hash") != hash_payload(outcome_commitment):
            raise ValueError("ambiguity_coordinator_model_outcome_hash_invalid")


def _validate_artifact_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"ambiguity_coordinator_{name}_artifact_hash_invalid")
