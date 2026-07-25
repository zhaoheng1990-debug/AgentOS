"""Shared no-write runtime helpers for v0.89."""

from __future__ import annotations

from typing import Any

from ..provider_telemetry import hash_payload
from .scifact_v0_89_holdout import (
    public_holdout,
    validate_holdout,
    validate_preregistration,
)


def validated_public_panel(
    panel: dict[str, Any],
    preregistration: dict[str, Any],
) -> dict[str, Any]:
    validate_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    return public_holdout(panel)


def validate_source_run(
    run: dict[str, Any],
    *,
    panel: dict[str, Any],
    expected_arm: str,
) -> None:
    if run.get("source_holdout_hash") != panel["artifact_hash"]:
        raise ValueError("scifact_v0_89_source_run_panel_mismatch")
    if run.get("arm_id") != expected_arm:
        raise ValueError("scifact_v0_89_source_run_arm_mismatch")


def finalize_run(
    *,
    runtime_version: str,
    arm_id: str,
    panel: dict[str, Any],
    public_panel: dict[str, Any],
    preregistration: dict[str, Any],
    provider_id: str,
    model_id: str,
    calls: list[dict[str, Any]],
    receipts: dict[str, Any],
    candidates: dict[str, Any],
    failures: list[dict[str, Any]],
    sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    value = {
        "runtime_version": runtime_version,
        "arm_id": arm_id,
        "source_holdout_hash": panel["artifact_hash"],
        "source_public_holdout_hash": public_panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hashes": dict(sorted((sources or {}).items())),
        "provider_id": provider_id,
        "model_id": model_id,
        "task_calls": calls,
        "receipts": receipts,
        "compiled_candidates": candidates,
        "failures": failures,
        "private_reference_exposed_to_provider": False,
        "provider_action_authority": False,
        "candidate_only": True,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "run_hash": hash_payload(value)}
