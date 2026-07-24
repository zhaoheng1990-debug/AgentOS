"""Frozen gates and report for the unstated-ambiguity discovery holdout."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_elicitor_fresh_eval import calibration_route
from .unstated_ambiguity_holdout import HOLDOUT_SPEC, TRUTH_COMMITMENT


REPORT_VERSION = "unstated_ambiguity_discovery_report_v0_1"


def build_discovery_report(*, experiment_id, calibration_artifact, judge_calibration_artifact, profiles):
    selected, comparator, strong, _ = calibration_route(calibration_artifact)
    profiles = tuple(profiles)
    index = {profile["model_id"]: profile for profile in profiles}
    if set(index) != {selected, comparator, strong} or len(index) != len(profiles):
        raise ValueError("ambiguity_discovery_profile_surface_invalid")
    for profile in profiles:
        _validate_profile(profile)
    gates = HOLDOUT_SPEC["frozen_gates"]
    selected_profile = index[selected]
    passed = (
        selected_profile["balanced_accuracy"] >= gates["minimum_balanced_accuracy"]
        and selected_profile["positive_recall"] >= gates["minimum_positive_recall"]
        and selected_profile["null_specificity"] >= gates["minimum_null_specificity"]
        and selected_profile["null_false_positive_rate"] <= gates["maximum_null_false_positive_rate"]
        and selected_profile["balanced_accuracy"] >= index[comparator]["balanced_accuracy"]
    )
    commitment = {
        "report_version": REPORT_VERSION, "experiment_id": experiment_id,
        "truth_commitment": TRUTH_COMMITMENT, "holdout_spec_hash": HOLDOUT_SPEC["spec_hash"],
        "calibration_artifact_hash": calibration_artifact["artifact_hash"],
        "judge_calibration_artifact_hash": judge_calibration_artifact["artifact_hash"],
        "profiles": list(profiles), "selected_small_model_id": selected,
        "comparator_small_model_id": comparator, "strong_model_id": strong,
        "selected_route_replicated": selected_profile["balanced_accuracy"] >= index[comparator]["balanced_accuracy"],
        "selected_to_strong_balanced_ratio": (
            selected_profile["balanced_accuracy"] / index[strong]["balanced_accuracy"]
            if index[strong]["balanced_accuracy"] else None
        ),
        "semantic_packet_quality_pending": True,
        "candidate_state": (
            "ENDOGENOUS_OBJECT_DISCOVERY_EVIDENCE_CANDIDATE"
            if passed else "UNSTATED_AMBIGUITY_DISCOVERY_GATE_FAILED"
        ),
        "evidence_coordinate": "INTERNAL_SYNTHETIC_PAIRED_HOLDOUT",
        "ground_truth_claim": False, "selection_authority": False,
        "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "report_hash": hash_payload(commitment)}


def validate_discovery_report(report, *, calibration_artifact, judge_calibration_artifact):
    commitment = {key: value for key, value in report.items() if key != "report_hash"}
    if report.get("report_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_discovery_report_hash_invalid")
    expected = build_discovery_report(
        experiment_id=report["experiment_id"], calibration_artifact=calibration_artifact,
        judge_calibration_artifact=judge_calibration_artifact, profiles=tuple(report["profiles"]),
    )
    if report != expected:
        raise ValueError("ambiguity_discovery_report_semantics_invalid")


def validate_discovery_artifact(artifact, *, calibration_artifact, judge_calibration_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_discovery_artifact_hash_invalid")
    validate_discovery_report(
        artifact["report"], calibration_artifact=calibration_artifact,
        judge_calibration_artifact=judge_calibration_artifact,
    )
    runs = artifact.get("model_runs", [])
    if [run["profile"] for run in runs] != artifact["report"]["profiles"]:
        raise ValueError("ambiguity_discovery_run_profile_binding_invalid")
    for run in runs:
        run_commitment = {key: value for key, value in run.items() if key != "model_run_hash"}
        if (run.get("model_run_hash") != hash_payload(run_commitment)
                or run.get("experiment_id") != artifact.get("experiment_id")):
            raise ValueError("ambiguity_discovery_model_run_hash_invalid")
        outcome_hashes = []
        for trial in run["trials"]:
            outcome = trial["outcome"]
            outcome_commitment = {key: value for key, value in outcome.items() if key != "outcome_hash"}
            if outcome.get("outcome_hash") != hash_payload(outcome_commitment):
                raise ValueError("ambiguity_discovery_outcome_hash_invalid")
            outcome_hashes.append(outcome["outcome_hash"])
        if outcome_hashes != run["profile"]["outcome_hashes"]:
            raise ValueError("ambiguity_discovery_outcome_profile_binding_invalid")


def _validate_profile(profile):
    commitment = {key: value for key, value in profile.items() if key != "profile_hash"}
    if profile.get("profile_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_discovery_profile_hash_invalid")
