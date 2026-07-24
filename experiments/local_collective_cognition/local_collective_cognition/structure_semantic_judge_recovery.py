"""Bounded failed-batch recovery without erasing prior Provider work."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_semantic_judge_receipts import validate_judge_run


def merge_recovered_judge_run(primary, recovery, *, surface):
    validate_judge_run(primary, surface=surface)
    validate_judge_run(recovery, surface=surface)
    identity = ("experiment_id", "judge_provider_id", "judge_model_id",
                "blind_surface_hash", "source_artifact_hash")
    if any(primary[key] != recovery[key] for key in identity):
        raise ValueError("semantic_judge_recovery_identity_mismatch")
    primary_judgments = {item["batch_id"]: item for item in primary["judgments"]}
    recovery_judgments = {item["batch_id"]: item for item in recovery["judgments"]}
    if set(primary_judgments).intersection(recovery_judgments):
        raise ValueError("semantic_judge_recovery_repeats_completed_batch")
    failed = {item["batch_id"]: item for item in primary["failures"]}
    if not set(recovery["requested_batch_ids"]).issubset(failed):
        raise ValueError("semantic_judge_recovery_not_limited_to_failed_batch")
    recovered_ids = set(recovery_judgments)
    remaining = [item for item in primary["failures"] if item["batch_id"] not in recovered_ids]
    remaining.extend(recovery["failures"])
    judgments = [*primary["judgments"], *recovery["judgments"]]
    commitment = {
        "experiment_id": primary["experiment_id"],
        "judge_provider_id": primary["judge_provider_id"],
        "judge_model_id": primary["judge_model_id"],
        "blind_surface_hash": primary["blind_surface_hash"],
        "source_artifact_hash": primary["source_artifact_hash"],
        "successful_batches": len(judgments),
        "failed_batches": len({item["batch_id"] for item in remaining}),
        "judgments": judgments,
        "failures": remaining,
        "total_provider_calls": primary["total_provider_calls"] + recovery["total_provider_calls"],
        "total_input_tokens": primary["total_input_tokens"] + recovery["total_input_tokens"],
        "total_output_tokens": primary["total_output_tokens"] + recovery["total_output_tokens"],
        "requested_batch_ids": primary["requested_batch_ids"],
        "recovered_failures": [failed[item] for item in sorted(recovered_ids)],
        "recovery_run_hashes": [recovery["judge_run_hash"]],
        "recovery_attempted_batches": list(recovery["requested_batch_ids"]),
    }
    return {**commitment, "judge_run_hash": hash_payload(commitment)}
