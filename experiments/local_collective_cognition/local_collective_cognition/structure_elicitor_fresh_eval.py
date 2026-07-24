"""Calibration-bound report and gates for the independent fresh holdout."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_elicitor_calibration_eval import validate_profile, validate_report


FRESH_EVALUATION_VERSION = "structure_elicitor_fresh_holdout_v0_1"
FRESH_SCOPE = "FRESH_HOLDOUT"


def validate_calibration_artifact(artifact):
    committed = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(committed):
        raise ValueError("structure_elicitor_calibration_artifact_hash_invalid")
    validate_report(artifact["report"])
    return artifact["report"]


def calibration_route(artifact):
    report = validate_calibration_artifact(artifact)
    if report.get("selection_authority") is not False or not report.get("fresh_holdout_required"):
        raise ValueError("structure_elicitor_calibration_authority_invalid")
    profiles = {item["model_id"]: item for item in report["profiles"]}
    selected = report["selected_small_model_id"]
    strong = report["strong_model_id"]
    eligible = [item for model_id, item in profiles.items() if model_id not in {selected, strong}
                and item["successful_provider_trials"] == item["independent_trials"]]
    if selected not in profiles or strong not in profiles or not eligible:
        raise ValueError("structure_elicitor_calibration_route_incomplete")
    if profiles[selected]["successful_provider_trials"] != profiles[selected]["independent_trials"]:
        raise ValueError("structure_elicitor_calibration_selected_model_unusable")
    comparator = max(eligible, key=_rank_key)["model_id"]
    excluded = [{
        "model_id": item["model_id"],
        "reason": (
            "CALIBRATION_TRANSPORT_FAILURE_BUDGET_BLOCK"
            if item["successful_provider_trials"] < item["independent_trials"]
            else "CALIBRATION_LOWER_RANKED_BUDGET_BLOCK"
        ),
        "calibration_profile_hash": item["profile_hash"],
        "calibration_provider_calls": item["total_provider_calls"],
        "calibration_tokens": item["total_tokens"],
    } for item in profiles.values() if item["model_id"] not in {selected, strong, comparator}]
    return selected, comparator, strong, tuple(excluded)


def build_fresh_report(*, experiment_id, calibration_artifact, profiles, truth_commitment):
    selected, comparator, strong, excluded = calibration_route(calibration_artifact)
    profiles = tuple(profiles)
    index = {item["model_id"]: item for item in profiles}
    if set(index) != {selected, comparator, strong} or len(index) != len(profiles):
        raise ValueError("structure_elicitor_fresh_profile_surface_invalid")
    for profile in profiles:
        validate_profile(profile)
        if profile.get("scope") != FRESH_SCOPE:
            raise ValueError("structure_elicitor_fresh_profile_scope_invalid")
    selected_profile, comparator_profile = index[selected], index[comparator]
    strong_profile = index[strong]
    replicated = selected_profile["mean_quality_score"] >= comparator_profile["mean_quality_score"]
    complete = selected_profile["successful_provider_trials"] == selected_profile["independent_trials"]
    candidate = replicated and complete and selected_profile["mean_quality_score"] > 0
    calibration_report = calibration_artifact["report"]
    commitment = {
        "evaluation_version": FRESH_EVALUATION_VERSION,
        "experiment_id": experiment_id,
        "truth_commitment": truth_commitment,
        "calibration_artifact_hash": calibration_artifact["artifact_hash"],
        "calibration_report_hash": calibration_report["report_hash"],
        "profiles": list(profiles),
        "selected_small_model_id": selected,
        "comparator_small_model_id": comparator,
        "strong_model_id": strong,
        "selected_fresh_quality": selected_profile["mean_quality_score"],
        "comparator_fresh_quality": comparator_profile["mean_quality_score"],
        "strong_fresh_quality_ceiling": strong_profile["mean_quality_score"],
        "selection_replicated": replicated,
        "small_model_routing_regret": max(
            selected_profile["mean_quality_score"], comparator_profile["mean_quality_score"]
        ) - selected_profile["mean_quality_score"],
        "selected_to_strong_quality_ratio": (
            selected_profile["mean_quality_score"] / strong_profile["mean_quality_score"]
            if strong_profile["mean_quality_score"] else None
        ),
        "selected_to_strong_quality_gap": (
            strong_profile["mean_quality_score"] - selected_profile["mean_quality_score"]
        ),
        "total_provider_calls": sum(item["total_provider_calls"] for item in profiles),
        "total_tokens": sum(item["total_tokens"] for item in profiles),
        "excluded_models": list(excluded),
        "candidate_state": (
            "PROJECT_CAPABILITY_EVIDENCE_CANDIDATE"
            if candidate else "CALIBRATION_ROUTE_NOT_REPLICATED"
        ),
        "selection_authority": False,
        "retention_authority": False,
        "human_audit_required": True,
    }
    return {**commitment, "report_hash": hash_payload(commitment)}


def validate_fresh_report(report, *, calibration_artifact=None):
    committed = {key: value for key, value in report.items() if key != "report_hash"}
    if report.get("report_hash") != hash_payload(committed):
        raise ValueError("structure_elicitor_fresh_report_hash_invalid")
    for profile in report["profiles"]:
        validate_profile(profile)
        if profile.get("scope") != FRESH_SCOPE:
            raise ValueError("structure_elicitor_fresh_profile_scope_invalid")
    if calibration_artifact is not None:
        calibration = validate_calibration_artifact(calibration_artifact)
        if (report["calibration_artifact_hash"] != calibration_artifact["artifact_hash"]
                or report["calibration_report_hash"] != calibration["report_hash"]):
            raise ValueError("structure_elicitor_fresh_calibration_binding_invalid")
        expected = build_fresh_report(
            experiment_id=report["experiment_id"], calibration_artifact=calibration_artifact,
            profiles=tuple(report["profiles"]), truth_commitment=report["truth_commitment"],
        )
        if report != expected:
            raise ValueError("structure_elicitor_fresh_report_semantics_invalid")


def validate_fresh_artifact(artifact, *, calibration_artifact):
    committed = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(committed):
        raise ValueError("structure_elicitor_fresh_artifact_hash_invalid")
    validate_fresh_report(artifact["report"], calibration_artifact=calibration_artifact)
    runs = artifact.get("model_runs", [])
    if [run.get("profile") for run in runs] != artifact["report"]["profiles"]:
        raise ValueError("structure_elicitor_fresh_run_profile_binding_invalid")
    for run in runs:
        run_commitment = {key: value for key, value in run.items() if key != "model_run_hash"}
        if (run.get("model_run_hash") != hash_payload(run_commitment)
                or run.get("experiment_id") != artifact.get("experiment_id")):
            raise ValueError("structure_elicitor_fresh_model_run_hash_invalid")
        outcome_hashes = []
        for trial in run.get("trials", []):
            outcome = trial.get("outcome", {})
            outcome_commitment = {key: value for key, value in outcome.items() if key != "outcome_hash"}
            if outcome.get("outcome_hash") != hash_payload(outcome_commitment):
                raise ValueError("structure_elicitor_fresh_outcome_hash_invalid")
            outcome_hashes.append(outcome["outcome_hash"])
        if outcome_hashes != run["profile"].get("outcome_hashes"):
            raise ValueError("structure_elicitor_fresh_outcome_profile_binding_invalid")


def _rank_key(profile):
    return (profile["mean_quality_score"], profile["successful_provider_trials"],
            -profile["total_tokens"], profile["model_id"])
