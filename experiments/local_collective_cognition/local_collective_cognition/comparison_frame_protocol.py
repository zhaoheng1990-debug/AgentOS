"""Frozen v0.67 protocol and mechanism source lock."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload


MECHANISM_FILES = (
    "comparison_frame_types.py",
    "comparison_frame_schemas.py",
    "comparison_frame_contracts.py",
    "comparison_frame_tasks.py",
    "deterministic_basis_compiler.py",
    "comparison_frame_runtime.py",
    "comparison_frame_metrics.py",
)
FROZEN_HOLDOUT_HASH = (
    "5b3adb61d9a3bec24e2cb11e85840e1b7a2292fa253b2fc6a65a6936230dd8d1"
)


def build_calibration_preregistration(
    *, panel: dict[str, Any], frozen_holdout: dict[str, Any]
) -> dict[str, Any]:
    validate_panel(panel)
    validate_panel(frozen_holdout)
    if panel.get("case_count") != 12:
        raise ValueError("comparison_frame_calibration_count_invalid")
    if frozen_holdout.get("artifact_hash") != FROZEN_HOLDOUT_HASH:
        raise ValueError("comparison_frame_holdout_changed")
    commitment = {
        "preregistration_version": "comparison_frame_calibration_v0_67",
        "source_panel_hash": panel["artifact_hash"],
        "source_baseline_run_hash": panel["baseline_projection"]["run_hash"],
        "frozen_fresh_holdout_hash": frozen_holdout["artifact_hash"],
        "mechanism_source_hashes": mechanism_source_hashes(),
        "shared_admission_required": True,
        "free_provider_synthesis_allowed": False,
        "provider_compiler_override_allowed": False,
        "prompt_change_after_first_frame_receipt_allowed": False,
        "calibration_gate": {
            "candidate_valid_receipt_count_min": 12,
            "candidate_total_failure_count_max": 0,
            "candidate_label_accuracy_min": 11 / 12,
            "candidate_evidence_f1_not_below_baseline": True,
            "candidate_effective_cbit_above_baseline": True,
            "known_significance_case": "EI-CAL-11179",
            "known_orientation_case": "EI-CAL-5842",
            "known_multi_arm_case": "EI-CAL-3189",
            "known_unconstrained_timepoint_case": "EI-CAL-9330",
            "known_measurement_case": "EI-CAL-13793",
            "harmful_regression_count_max": 0,
        },
        "maximum_candidate_provider_tasks": 24,
        "maximum_candidate_physical_attempts": 48,
        "hard_candidate_token_ceiling": 150000,
        "fresh_holdout_authorized_only_after_full_pass": True,
        "semantic_coordinate_gold_available": False,
        "benchmark_native_claim": False,
        "fresh_generalization_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_holdout_preregistration(
    *,
    panel: dict[str, Any],
    calibration_decision: dict[str, Any],
) -> dict[str, Any]:
    validate_panel(panel)
    _validate_hash(calibration_decision)
    if panel["artifact_hash"] != FROZEN_HOLDOUT_HASH:
        raise ValueError("comparison_frame_holdout_changed")
    if calibration_decision.get("fresh_holdout_authorized") is not True:
        raise ValueError("comparison_frame_holdout_not_authorized")
    commitment = {
        "preregistration_version": "comparison_frame_holdout_v0_67",
        "source_panel_hash": panel["artifact_hash"],
        "source_calibration_decision_hash": calibration_decision[
            "artifact_hash"
        ],
        "mechanism_source_hashes": mechanism_source_hashes(),
        "shared_admission_required": True,
        "prompt_or_contract_tuning_allowed": False,
        "free_provider_synthesis_allowed": False,
        "provider_compiler_override_allowed": False,
        "holdout_gate": {
            "candidate_valid_receipt_count_min": 36,
            "candidate_total_failure_count_max": 0,
            "candidate_label_accuracy_above_baseline": True,
            "candidate_effective_cbit_above_baseline": True,
            "candidate_evidence_f1_floor_vs_baseline": -0.01,
            "correction_surplus_min": 1,
        },
        "maximum_total_provider_tasks": 144,
        "maximum_total_physical_attempts": 288,
        "hard_total_token_ceiling": 600000,
        "semantic_coordinate_gold_available": False,
        "benchmark_native_claim": False,
        "fresh_generalization_claim": False,
        "pretraining_contamination_excluded": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_comparison_frame_preregistration(
    value: dict[str, Any],
) -> None:
    _validate_hash(value)
    if value.get("mechanism_source_hashes") != mechanism_source_hashes():
        raise ValueError("comparison_frame_mechanism_source_changed")
    if value.get("free_provider_synthesis_allowed") is not False:
        raise ValueError("comparison_frame_synthesis_boundary_invalid")
    if value.get("provider_compiler_override_allowed") is not False:
        raise ValueError("comparison_frame_compiler_boundary_invalid")
    if value.get("core_write_allowed") is not False:
        raise ValueError("comparison_frame_core_boundary_invalid")
    if value.get("retention_write_allowed") is not False:
        raise ValueError("comparison_frame_retention_boundary_invalid")


def mechanism_source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in MECHANISM_FILES
    }


def _validate_hash(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("comparison_frame_preregistration_hash_invalid")
