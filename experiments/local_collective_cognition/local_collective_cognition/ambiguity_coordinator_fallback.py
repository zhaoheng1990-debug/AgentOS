"""Candidate-only coordinator fallback after primary transport exhaustion."""

from __future__ import annotations

from .ambiguity_coordinator_eval import validate_coordinator_artifact
from .provider_telemetry import hash_payload


FALLBACK_VERSION = "ambiguity_coordinator_fallback_role_v0_1"


def build_fallback_role_candidate(*, primary_role_artifact, judge_calibration_artifact,
                                  primary_failure_artifacts):
    _validate_hash(primary_role_artifact, "primary_role")
    _validate_hash(judge_calibration_artifact, "judge_calibration")
    failures = tuple(primary_failure_artifacts)
    if len(failures) < 2:
        raise ValueError("ambiguity_coordinator_fallback_two_failures_required")
    policy = judge_calibration_artifact["policy_candidate"]
    primary = primary_role_artifact["role_candidates"]["semantic_coordinator"]
    if (primary_role_artifact["judge_calibration_artifact_hash"] != judge_calibration_artifact["artifact_hash"]
            or primary["provider_id"] != policy["primary_judge_provider_id"]
            or primary["model_id"] != policy["primary_judge_model_id"]):
        raise ValueError("ambiguity_coordinator_fallback_primary_binding_invalid")
    hashes = []
    for artifact in failures:
        validate_coordinator_artifact(
            artifact, role_artifact=primary_role_artifact,
            judge_calibration_artifact=judge_calibration_artifact,
        )
        run = artifact["coordinator_run"]
        if (run["model_id"] != primary["model_id"] or run["profile"]["decision_count"] != 0
                or run["profile"]["failed_batches"] < 1):
            raise ValueError("ambiguity_coordinator_fallback_failure_evidence_invalid")
        hashes.append(artifact["artifact_hash"])
    roles = dict(primary_role_artifact["role_candidates"])
    roles["semantic_coordinator"] = {
        "provider_id": policy["secondary_judge_provider_id"],
        "model_id": policy["secondary_judge_model_id"],
        "binding_state": "PRIMARY_TRANSPORT_EXHAUSTED_SECONDARY_UNVALIDATED_FOR_COORDINATION",
        "primary_provider_id": primary["provider_id"], "primary_model_id": primary["model_id"],
    }
    commitment = {
        "fallback_version": FALLBACK_VERSION,
        "source_role_artifact_hash": primary_role_artifact["artifact_hash"],
        "judge_calibration_artifact_hash": judge_calibration_artifact["artifact_hash"],
        "primary_failure_artifact_hashes": hashes,
        "role_candidates": roles,
        "candidate_state": "SECONDARY_COORDINATOR_TRANSPORT_FALLBACK_CANDIDATE",
        "fallback_reason": "PRIMARY_PROVIDER_ZERO_SEMANTIC_OUTPUT_AFTER_TWO_BOUNDED_CONSTRUCTIONS",
        "selection_authority": False, "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_fallback_role_candidate(artifact, *, primary_role_artifact,
                                     judge_calibration_artifact, primary_failure_artifacts):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("ambiguity_coordinator_fallback_role_hash_invalid")
    expected = build_fallback_role_candidate(
        primary_role_artifact=primary_role_artifact,
        judge_calibration_artifact=judge_calibration_artifact,
        primary_failure_artifacts=primary_failure_artifacts,
    )
    if artifact != expected:
        raise ValueError("ambiguity_coordinator_fallback_role_semantics_invalid")


def _validate_hash(artifact, name):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError(f"ambiguity_coordinator_fallback_{name}_hash_invalid")
