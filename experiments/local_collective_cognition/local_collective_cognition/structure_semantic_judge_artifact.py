"""Whole-artifact validation for semantic judge experiment outputs."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_semantic_judge_consensus import validate_semantic_report


def validate_semantic_artifact(artifact, *, calibration_artifact, fresh_artifact):
    committed = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(committed):
        raise ValueError("semantic_judge_artifact_hash_invalid")
    if (artifact.get("calibration_source_hash") != calibration_artifact.get("artifact_hash")
            or artifact.get("fresh_source_hash") != fresh_artifact.get("artifact_hash")):
        raise ValueError("semantic_judge_artifact_source_binding_invalid")
    surface = artifact["blind_surface"]
    if surface.get("source_artifact_hash") != fresh_artifact["artifact_hash"]:
        raise ValueError("semantic_judge_artifact_blind_source_invalid")
    validate_semantic_report(
        artifact["report"], fresh_artifact=fresh_artifact,
        surface=surface, judge_runs=tuple(artifact["judge_runs"]),
    )
